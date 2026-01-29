#!/usr/bin/env python3
"""
AI Agent usage examples for the Terraform AVM Agent.

These examples require an OpenAI API key or Azure OpenAI endpoint.

Set your API key:
    export OPENAI_API_KEY="your-api-key"

Or for Azure OpenAI:
    export AZURE_OPENAI_ENDPOINT="https://your-endpoint.openai.azure.com"
    export AZURE_OPENAI_API_KEY="your-api-key"
"""

import asyncio
import os

from tf_avm_agent import TerraformAVMAgent


async def example_interactive_generation():
    """Example: Interactive code generation with AI."""
    print("=" * 60)
    print("Example: Interactive AI Generation")
    print("=" * 60)

    # Initialize the agent
    agent = TerraformAVMAgent()

    # Natural language request
    prompt = """
    I need to deploy a web application on Azure with the following requirements:
    - A containerized application using Azure Container Apps
    - A PostgreSQL database for data storage
    - A Redis cache for session management
    - Secure storage of secrets in Key Vault
    - Monitoring with Application Insights

    Please generate the Terraform code using Azure Verified Modules.
    """

    print(f"User request:\n{prompt}")
    print("\n--- Agent Response ---")

    response = await agent.run_async(prompt)
    print(response)


async def example_diagram_analysis():
    """Example: Analyze an architecture diagram."""
    print("\n" + "=" * 60)
    print("Example: Architecture Diagram Analysis")
    print("=" * 60)

    agent = TerraformAVMAgent()

    # Note: You would provide a real diagram path
    diagram_path = "./examples/sample-architecture.png"

    if os.path.exists(diagram_path):
        response = await agent.analyze_diagram_async(
            image_path=diagram_path,
            project_name="analyzed-architecture",
            location="eastus",
        )
        print(response)
    else:
        print(f"Sample diagram not found at {diagram_path}")
        print("To use this feature, provide an Azure architecture diagram image.")


async def example_conversation():
    """Example: Multi-turn conversation with the agent."""
    print("\n" + "=" * 60)
    print("Example: Multi-turn Conversation")
    print("=" * 60)

    agent = TerraformAVMAgent()

    # First turn: Ask about modules
    print("User: What AVM modules are available for databases?")
    response = await agent.run_async("What AVM modules are available for databases?")
    print(f"Agent: {response}\n")

    # Second turn: Ask for recommendation
    print("User: Which one would you recommend for a high-availability web application?")
    response = await agent.run_async(
        "Which one would you recommend for a high-availability web application?"
    )
    print(f"Agent: {response}\n")

    # Third turn: Generate code
    print("User: Generate Terraform code for that setup with PostgreSQL and Redis")
    response = await agent.run_async(
        "Generate Terraform code for that setup with PostgreSQL and Redis"
    )
    print(f"Agent: {response}")


async def example_azure_openai():
    """Example: Using Azure OpenAI instead of OpenAI."""
    print("\n" + "=" * 60)
    print("Example: Using Azure OpenAI")
    print("=" * 60)

    # Check for Azure OpenAI configuration
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4")

    if not endpoint:
        print("Azure OpenAI endpoint not configured.")
        print("Set AZURE_OPENAI_ENDPOINT environment variable to use this example.")
        return

    agent = TerraformAVMAgent(
        use_azure_openai=True,
        azure_endpoint=endpoint,
        azure_deployment=deployment,
        api_key=api_key,
    )

    response = await agent.run_async(
        "Generate a simple Terraform project with a virtual machine and storage account"
    )
    print(response)


def main():
    """Run the AI agent examples."""
    # Check for API key
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("AZURE_OPENAI_ENDPOINT"):
        print("Warning: No API key configured.")
        print("Set OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT environment variable.")
        print("Running without AI features...\n")

        # Show what would be done without actually calling the API
        print("Available AI features:")
        print("  - Interactive natural language code generation")
        print("  - Architecture diagram analysis")
        print("  - Multi-turn conversations")
        print("  - Azure OpenAI support")
        return

    # Run async examples
    asyncio.run(example_interactive_generation())
    asyncio.run(example_conversation())

    # Optionally run Azure OpenAI example
    if os.environ.get("AZURE_OPENAI_ENDPOINT"):
        asyncio.run(example_azure_openai())


if __name__ == "__main__":
    main()
