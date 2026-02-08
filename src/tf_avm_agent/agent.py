"""
Terraform AVM Agent.

An AI agent that generates Terraform code using Azure Verified Modules (AVM).
Built using the Microsoft Agent Framework.
"""

import asyncio
import base64
import json
import os
import uuid
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

# Microsoft Agent Framework imports
try:
    from agent_framework import ChatAgent
    from agent_framework.azure import AzureOpenAIChatClient
    from agent_framework.openai import OpenAIChatClient

    AGENT_FRAMEWORK_AVAILABLE = True
except ImportError:
    AGENT_FRAMEWORK_AVAILABLE = False
    ChatAgent = None
    AzureOpenAIChatClient = None
    OpenAIChatClient = None

from tf_avm_agent.registry.avm_modules import (
    AVM_MODULES,
    get_module_by_service,
    search_modules,
)
from tf_avm_agent.tools.avm_lookup import (
    get_avm_module_info,
    get_module_dependencies,
    list_available_avm_modules,
    recommend_modules_for_architecture,
    search_avm_modules,
)
from tf_avm_agent.tools.diagram_analyzer import (
    DIAGRAM_ANALYSIS_PROMPT,
    DiagramAnalysisResult,
    encode_image_to_base64,
    get_image_media_type,
    parse_diagram_analysis_response,
)
from tf_avm_agent.lightning.config import MODULE_COUNT_REWARD_THRESHOLD
from tf_avm_agent.lightning.telemetry import (
    TerraformAgentTracer,
    set_global_tracer,
)
from tf_avm_agent.tools.terraform_generator import (
    TerraformModuleConfig,
    TerraformProjectConfig,
    TerraformProjectOutput,
    generate_terraform_module,
    generate_terraform_project,
    validate_terraform_syntax,
    write_terraform_files,
)


# Agent system prompt
AGENT_SYSTEM_PROMPT = """You are a Terraform Infrastructure Expert specializing in Azure Verified Modules (AVM).

Your role is to help users generate Terraform code for deploying Azure infrastructure using Azure Verified Modules.

## CRITICAL: Conversation Context
- You MUST use information from the conversation history provided
- If services were previously identified (from a diagram, URL, or user input), USE THEM - do NOT ask again
- When the user asks to "generate Terraform" or "create a project", immediately proceed using the previously identified services
- Do NOT ask for services again if they were already identified in this conversation

You can:

1. **Analyze Architecture Diagrams**: When given an image of an Azure architecture diagram, identify all Azure services and their relationships.

2. **Accept Service Lists**: When given a list of Azure services, recommend appropriate AVM modules and generate Terraform code.

3. **Generate Terraform Projects**: Create complete, production-ready Terraform projects including:
   - providers.tf - Provider configuration
   - variables.tf - Input variables
   - main.tf - Resource definitions using AVM modules
   - outputs.tf - Output values
   - README.md - Documentation

4. **Lookup AVM Modules**: Search and retrieve information about available Azure Verified Modules.

## Guidelines:

- Always use Azure Verified Modules (AVM) when available instead of raw azurerm resources
- Follow Terraform best practices (consistent naming, proper variable usage, meaningful outputs)
- Include proper dependencies between modules
- Add helpful comments to generated code
- Consider security best practices (private endpoints, network rules, managed identities)
- When analyzing diagrams, identify all Azure services even if they don't have an AVM module
- **IMPORTANT**: When user confirms to generate, IMMEDIATELY generate the code using previously identified services

## Available Tools:

- `list_available_avm_modules`: List all available AVM modules, optionally filtered by category
- `search_avm_modules`: Search for modules by keyword
- `get_avm_module_info`: Get detailed information about a specific module
- `get_module_dependencies`: Get dependencies for a module
- `recommend_modules_for_architecture`: Recommend modules for a list of services
- `generate_terraform_module`: Generate code for a single module
- `generate_terraform_project`: Generate a complete Terraform project
- `write_terraform_files`: Write generated files to disk

## Workflow:
1. When services are identified (from diagram/URL/user), REMEMBER them
2. When user says "generate", "create project", or similar - USE the remembered services
3. Generate complete Terraform code immediately without asking again
4. Offer to write files to disk

Always explain what you're doing and provide clear next steps for the user.
"""


class ServiceInput(BaseModel):
    """Input for services-based generation."""

    services: list[str] = Field(description="List of Azure services to deploy")
    project_name: str = Field(description="Name for the Terraform project")
    location: str = Field(default="eastus", description="Azure region")
    output_dir: str | None = Field(default=None, description="Directory to write files")


class DiagramInput(BaseModel):
    """Input for diagram-based generation."""

    image_path: str = Field(description="Path to the architecture diagram image")
    project_name: str = Field(description="Name for the Terraform project")
    location: str = Field(default="eastus", description="Azure region")
    output_dir: str | None = Field(default=None, description="Directory to write files")


class TerraformAVMAgent:
    """
    Terraform AVM Agent that generates Terraform code using Azure Verified Modules.

    This agent can accept either:
    - A list of Azure services to deploy
    - An architecture diagram image

    And will generate a complete Terraform project using Azure Verified Modules.
    """

    def __init__(
        self,
        use_azure_openai: bool = False,
        azure_endpoint: str | None = None,
        azure_deployment: str | None = None,
        api_key: str | None = None,
        enable_lightning: bool = False,
    ):
        """
        Initialize the Terraform AVM Agent.

        Args:
            use_azure_openai: Use Azure OpenAI instead of OpenAI
            azure_endpoint: Azure OpenAI endpoint (required if use_azure_openai=True)
            azure_deployment: Azure OpenAI deployment name
            api_key: API key (uses environment variable if not provided)
            enable_lightning: Enable Agent Lightning telemetry and RL training
        """
        self.use_azure_openai = use_azure_openai

        # Read from environment variables if not provided
        if use_azure_openai:
            self.azure_endpoint = azure_endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT")
            # Support multiple env var names for deployment
            self.azure_deployment = (
                azure_deployment
                or os.environ.get("AZURE_OPENAI_DEPLOYMENT")
                or os.environ.get("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
            )
            self.api_key = api_key or os.environ.get("AZURE_OPENAI_API_KEY")
        else:
            self.azure_endpoint = azure_endpoint
            self.azure_deployment = azure_deployment
            self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

        self._agent = None
        self._loop = None
        self._conversation_history = []
        self._current_diagram = None
        self._identified_services = []

        # Agent Lightning integration
        self._enable_lightning = enable_lightning
        self._tracer = TerraformAgentTracer(enabled=enable_lightning)
        if enable_lightning:
            set_global_tracer(self._tracer)

    def _get_tools(self) -> list:
        """Get the list of tools for the agent."""
        return [
            list_available_avm_modules,
            search_avm_modules,
            get_avm_module_info,
            get_module_dependencies,
            recommend_modules_for_architecture,
            generate_terraform_module,
            self._generate_project_tool,
            self._write_files_tool,
        ]

    def _generate_project_tool(
        self,
        project_name: Annotated[str, Field(description="Name of the project")],
        services: Annotated[list[str], Field(description="List of Azure services to include")],
        location: Annotated[str, Field(description="Azure region")] = "eastus",
        resource_group_name: Annotated[str | None, Field(description="Resource group name")] = None,
    ) -> str:
        """Generate a complete Terraform project with AVM modules."""
        result = generate_terraform_project(
            project_name=project_name,
            services=services,
            location=location,
            resource_group_name=resource_group_name,
        )
        return result.summary

    def _write_files_tool(
        self,
        output_dir: Annotated[str, Field(description="Directory to write files to")],
        project_name: Annotated[str, Field(description="Name of the project")],
        services: Annotated[list[str], Field(description="List of Azure services")],
        location: Annotated[str, Field(description="Azure region")] = "eastus",
        overwrite: Annotated[bool, Field(description="Overwrite existing files")] = False,
    ) -> str:
        """Generate and write Terraform files to disk."""
        result = generate_terraform_project(
            project_name=project_name,
            services=services,
            location=location,
        )
        return write_terraform_files(output_dir, result, overwrite)

    async def _create_agent(self) -> "ChatAgent":
        """Create the agent instance."""
        if not AGENT_FRAMEWORK_AVAILABLE:
            raise ImportError(
                "Microsoft Agent Framework is not installed. "
                "Install it with: pip install agent-framework"
            )

        if self.use_azure_openai:
            if not self.azure_endpoint:
                raise ValueError(
                    "Azure OpenAI endpoint is required. "
                    "Set via 'azure_endpoint' parameter or 'AZURE_OPENAI_ENDPOINT' environment variable."
                )
            if not self.azure_deployment:
                raise ValueError(
                    "Azure OpenAI deployment name is required. "
                    "Set via 'azure_deployment' parameter or 'AZURE_OPENAI_DEPLOYMENT' environment variable."
                )
            from azure.identity import DefaultAzureCredential

            # Use DefaultAzureCredential (Entra ID) - API key auth may be disabled on the resource
            chat_client = AzureOpenAIChatClient(
                endpoint=self.azure_endpoint,
                deployment=self.azure_deployment,
                credential=DefaultAzureCredential(),
            )
        else:
            chat_client = OpenAIChatClient(api_key=self.api_key)

        return ChatAgent(
            chat_client=chat_client,
            instructions=AGENT_SYSTEM_PROMPT,
            tools=self._get_tools(),
        )

    async def run_async(self, prompt: str) -> str:
        """
        Run the agent with a text prompt.

        Args:
            prompt: The user's request

        Returns:
            The agent's response
        """
        task_id = str(uuid.uuid4())
        self._tracer.start_task(
            task_id=task_id,
            input_data={"prompt": prompt[:500]},
        )

        try:
            if self._agent is None:
                self._agent = await self._create_agent()

            # Add user message to history
            self._conversation_history.append({"role": "user", "content": prompt})

            # Build context from conversation history to maintain state
            # Include previous exchanges so the agent remembers identified services
            context_prompt = prompt
            if len(self._conversation_history) > 1:
                # Build conversation context
                history_context = "\n\n--- CONVERSATION HISTORY (for context) ---\n"
                for msg in self._conversation_history[:-1]:  # Exclude current message
                    role = "User" if msg["role"] == "user" else "Assistant"
                    # Truncate long messages to avoid token limits
                    content = msg["content"][:2000] + "..." if len(msg["content"]) > 2000 else msg["content"]
                    history_context += f"\n{role}: {content}\n"
                history_context += "\n--- END HISTORY ---\n\n"
                history_context += f"Current request: {prompt}"

                # Add reminder about identified services if any
                if self._identified_services:
                    history_context += f"\n\nPreviously identified services: {', '.join(self._identified_services)}"

                context_prompt = history_context

            # Run with conversation history context
            response = await self._agent.run(context_prompt)
            response_text = response.text if hasattr(response, "text") else str(response)

            # Emit LLM response action
            self._tracer.emit_action(
                action_type="llm_response",
                input_data={"prompt_length": len(context_prompt)},
                output_data={"response_length": len(response_text)},
            )

            # Extract and store any identified services from the response
            self._extract_services_from_response(response_text)

            # Add assistant response to history
            self._conversation_history.append({"role": "assistant", "content": response_text})

            self._tracer.end_task(success=True, output=response_text)
            return response_text

        except Exception as e:
            self._tracer.end_task(success=False, output=str(e))
            raise
    
    def _extract_services_from_response(self, response: str):
        """Extract and store identified Azure services from agent response."""
        # Common Azure service keywords to look for
        service_keywords = [
            "azure openai", "machine learning", "ai search", "cognitive search",
            "storage account", "adls", "data lake", "app service", "functions",
            "container apps", "aks", "kubernetes", "container registry", "acr",
            "key vault", "virtual network", "vnet", "subnet", "private endpoint",
            "dns zone", "network security group", "nsg", "application gateway",
            "waf", "log analytics", "managed identity", "sql", "cosmos", "redis",
            "event hub", "service bus", "api management", "front door"
        ]
        
        response_lower = response.lower()
        for service in service_keywords:
            if service in response_lower and service not in [s.lower() for s in self._identified_services]:
                # Capitalize properly
                self._identified_services.append(service.title())

    def run(self, prompt: str) -> str:
        """
        Run the agent with a text prompt (synchronous wrapper).

        Args:
            prompt: The user's request

        Returns:
            The agent's response
        """
        # Use a persistent event loop to maintain conversation state
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        return self._loop.run_until_complete(self.run_async(prompt))
    
    def clear_history(self):
        """Clear the conversation history."""
        self._conversation_history = []
        self._current_diagram = None
        self._identified_services = []
    
    def get_history(self) -> list:
        """Get the conversation history."""
        return self._conversation_history.copy()

    def analyze_diagram(self, image_path: str) -> str:
        """
        Analyze an architecture diagram to identify Azure services.

        Args:
            image_path: Path to the architecture diagram image

        Returns:
            The agent's analysis of the diagram
        """
        # Store the diagram path
        self._current_diagram = image_path
        
        # Create a prompt that asks the agent to analyze the diagram
        prompt = f"""I have loaded an architecture diagram from: {image_path}

Please analyze this diagram and:
1. List ALL Azure services you can identify from the filename and context
2. For each service, suggest the appropriate Azure Verified Module (AVM)
3. Identify relationships and dependencies between services
4. Note any networking components (VNets, subnets, private endpoints)
5. Identify security components (Key Vault, managed identities, NSGs)

IMPORTANT: After listing the services, REMEMBER them for the next step.
When I ask you to "generate Terraform", use these identified services WITHOUT asking again.

Based on the filename '{Path(image_path).name}', what Azure services would you expect to find in this architecture?

End your response with a clear list of services in this format:
**Identified Services:** service1, service2, service3, ..."""

        # Use persistent event loop
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        return self._loop.run_until_complete(self.run_async(prompt))

    def analyze_diagram_from_url(self, url: str, filename: str = "diagram") -> str:
        """
        Analyze an architecture diagram from a URL to identify Azure services.

        Args:
            url: URL to the architecture diagram image
            filename: The filename extracted from URL

        Returns:
            The agent's analysis of the diagram
        """
        # Store the diagram URL
        self._current_diagram = url
        
        # Create a prompt that asks the agent to analyze the diagram
        prompt = f"""I have loaded an architecture diagram from URL: {url}
Filename: {filename}

Please analyze this diagram and:
1. List ALL Azure services you can identify from the URL, filename, and context
2. For each service, suggest the appropriate Azure Verified Module (AVM)
3. Identify relationships and dependencies between services
4. Note any networking components (VNets, subnets, private endpoints)
5. Identify security components (Key Vault, managed identities, NSGs)

IMPORTANT: After listing the services, REMEMBER them for the next step.
When I ask you to "generate Terraform", use these identified services WITHOUT asking again.

Based on the URL and filename '{filename}', what Azure services would you expect to find in this architecture?

End your response with a clear list of services in this format:
**Identified Services:** service1, service2, service3, ..."""

        # Use persistent event loop
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
        
        return self._loop.run_until_complete(self.run_async(prompt))

    async def analyze_diagram_async(
        self,
        image_path: str,
        project_name: str,
        location: str = "eastus",
        output_dir: str | None = None,
    ) -> str:
        """
        Analyze an architecture diagram and generate Terraform code.

        Args:
            image_path: Path to the architecture diagram image
            project_name: Name for the project
            location: Azure region
            output_dir: Optional directory to write files

        Returns:
            The agent's response with analysis and generated code
        """
        # Encode the image
        image_data = encode_image_to_base64(image_path)
        media_type = get_image_media_type(image_path)

        # Create the prompt with image analysis request
        prompt = f"""Please analyze this Azure architecture diagram and generate a Terraform project.

Project Name: {project_name}
Location: {location}
{"Output Directory: " + output_dir if output_dir else ""}

Steps:
1. Analyze the diagram to identify all Azure services
2. Map each service to the appropriate AVM module
3. Generate a complete Terraform project
{"4. Write the files to " + output_dir if output_dir else ""}

[Image data is provided as base64 - this represents an architecture diagram that needs analysis]
"""

        # Note: In a full implementation, we would pass the image to a vision-capable model
        # For now, we'll use a text-based approach that asks the user to describe the diagram
        # or we'll use the agent framework's vision capabilities if available

        if self._agent is None:
            self._agent = await self._create_agent()

        response = await self._agent.run(prompt)
        return response.text if hasattr(response, "text") else str(response)

    def analyze_diagram(
        self,
        image_path: str,
        project_name: str,
        location: str = "eastus",
        output_dir: str | None = None,
    ) -> str:
        """
        Analyze an architecture diagram and generate Terraform code (synchronous).

        Args:
            image_path: Path to the architecture diagram image
            project_name: Name for the project
            location: Azure region
            output_dir: Optional directory to write files

        Returns:
            The agent's response
        """
        return asyncio.run(
            self.analyze_diagram_async(image_path, project_name, location, output_dir)
        )

    def generate_from_services(
        self,
        services: list[str],
        project_name: str,
        location: str = "eastus",
        output_dir: str | None = None,
    ) -> TerraformProjectOutput:
        """
        Generate Terraform code from a list of services.

        This method directly generates the code without using the LLM,
        which is useful for programmatic usage.

        Args:
            services: List of Azure services
            project_name: Name for the project
            location: Azure region
            output_dir: Optional directory to write files

        Returns:
            TerraformProjectOutput with generated files
        """
        self._tracer.emit_action(
            action_type="generate_from_services",
            input_data={
                "services": services,
                "project_name": project_name,
                "location": location,
            },
        )

        result = generate_terraform_project(
            project_name=project_name,
            services=services,
            location=location,
        )

        self._emit_validation_reward(result)

        if output_dir:
            write_terraform_files(output_dir, result)

        return result

    def _emit_validation_reward(self, result: TerraformProjectOutput) -> None:
        """Emit reward based on Terraform validation."""
        main_tf = next((f for f in result.files if f.filename == "main.tf"), None)
        if not main_tf:
            self._tracer.emit_reward(reward=-1.0, metadata={"error": "no_main_tf"})
            return

        is_valid, message = validate_terraform_syntax(main_tf.content)
        reward = 1.0 if is_valid else -0.5

        module_count = main_tf.content.count('module "')
        if module_count == 0:
            reward -= 0.3

        self._tracer.emit_reward(
            reward=reward,
            metadata={
                "validation_passed": is_valid,
                "validation_message": message,
                "module_count": module_count,
                "file_count": len(result.files),
            },
        )

    def list_modules(self, category: str | None = None) -> str:
        """
        List available AVM modules.

        Args:
            category: Optional category filter

        Returns:
            Formatted list of modules
        """
        return list_available_avm_modules(category)

    def search_modules(self, query: str) -> str:
        """
        Search for AVM modules.

        Args:
            query: Search query

        Returns:
            Search results
        """
        return search_avm_modules(query)

    def get_module_info(self, service_name: str) -> str:
        """
        Get information about a specific module.

        Args:
            service_name: The service name or alias

        Returns:
            Module information
        """
        return get_avm_module_info(service_name)


# Convenience function for quick generation
def generate_terraform(
    services: list[str],
    project_name: str,
    output_dir: str | None = None,
    location: str = "eastus",
) -> TerraformProjectOutput:
    """
    Quick function to generate Terraform code from a list of services.

    Args:
        services: List of Azure services
        project_name: Name for the project
        output_dir: Optional directory to write files
        location: Azure region

    Returns:
        TerraformProjectOutput with generated files
    """
    agent = TerraformAVMAgent()
    return agent.generate_from_services(
        services=services,
        project_name=project_name,
        location=location,
        output_dir=output_dir,
    )
