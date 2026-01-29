"""
Terraform AVM Agent.

An AI agent that generates Terraform code using Azure Verified Modules (AVM).
Built using the Microsoft Agent Framework.
"""

import asyncio
import base64
import json
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
from tf_avm_agent.tools.terraform_generator import (
    TerraformModuleConfig,
    TerraformProjectConfig,
    TerraformProjectOutput,
    generate_terraform_module,
    generate_terraform_project,
    write_terraform_files,
)


# Agent system prompt
AGENT_SYSTEM_PROMPT = """You are a Terraform Infrastructure Expert specializing in Azure Verified Modules (AVM).

Your role is to help users generate Terraform code for deploying Azure infrastructure using Azure Verified Modules.
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

## Available Tools:

- `list_available_avm_modules`: List all available AVM modules, optionally filtered by category
- `search_avm_modules`: Search for modules by keyword
- `get_avm_module_info`: Get detailed information about a specific module
- `get_module_dependencies`: Get dependencies for a module
- `recommend_modules_for_architecture`: Recommend modules for a list of services
- `generate_terraform_module`: Generate code for a single module
- `generate_terraform_project`: Generate a complete Terraform project
- `write_terraform_files`: Write generated files to disk

When the user provides a list of services or an architecture diagram, follow these steps:
1. Identify all required Azure services
2. Map services to AVM modules using the lookup tools
3. Determine dependencies between modules
4. Generate a complete Terraform project
5. Offer to write the files to disk

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
    ):
        """
        Initialize the Terraform AVM Agent.

        Args:
            use_azure_openai: Use Azure OpenAI instead of OpenAI
            azure_endpoint: Azure OpenAI endpoint (required if use_azure_openai=True)
            azure_deployment: Azure OpenAI deployment name
            api_key: API key (uses environment variable if not provided)
        """
        self.use_azure_openai = use_azure_openai
        self.azure_endpoint = azure_endpoint
        self.azure_deployment = azure_deployment
        self.api_key = api_key
        self._agent = None

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
            from azure.identity import DefaultAzureCredential

            chat_client = AzureOpenAIChatClient(
                endpoint=self.azure_endpoint,
                deployment=self.azure_deployment,
                credential=DefaultAzureCredential() if not self.api_key else None,
                api_key=self.api_key,
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
        if self._agent is None:
            self._agent = await self._create_agent()

        response = await self._agent.run(prompt)
        return response.text if hasattr(response, "text") else str(response)

    def run(self, prompt: str) -> str:
        """
        Run the agent with a text prompt (synchronous wrapper).

        Args:
            prompt: The user's request

        Returns:
            The agent's response
        """
        return asyncio.run(self.run_async(prompt))

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
        result = generate_terraform_project(
            project_name=project_name,
            services=services,
            location=location,
        )

        if output_dir:
            write_terraform_files(output_dir, result)

        return result

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
