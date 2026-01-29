#!/usr/bin/env python3
"""
Basic usage examples for the Terraform AVM Agent.

This script demonstrates how to use the agent programmatically.
"""

from tf_avm_agent import TerraformAVMAgent, generate_terraform
from tf_avm_agent.tools.avm_lookup import (
    get_avm_module_info,
    list_available_avm_modules,
    recommend_modules_for_architecture,
    search_avm_modules,
)


def example_quick_generation():
    """Example: Quick generation from a list of services."""
    print("=" * 60)
    print("Example 1: Quick Generation from Services")
    print("=" * 60)

    # Generate a Terraform project for a simple web app
    result = generate_terraform(
        services=["virtual_machine", "storage_account", "key_vault"],
        project_name="simple-webapp",
        location="eastus",
    )

    print(f"\nGenerated {len(result.files)} files:")
    for file in result.files:
        print(f"  - {file.filename}")

    print("\n--- main.tf preview ---")
    main_tf = next(f for f in result.files if f.filename == "main.tf")
    print(main_tf.content[:1500] + "...")


def example_with_output_directory():
    """Example: Generate and save to disk."""
    print("\n" + "=" * 60)
    print("Example 2: Generate and Save to Disk")
    print("=" * 60)

    result = generate_terraform(
        services=["aks", "acr", "postgresql"],
        project_name="microservices-platform",
        location="westeurope",
        output_dir="./generated/microservices",
    )

    print(f"\nProject saved to: ./generated/microservices")
    print(result.summary)


def example_module_lookup():
    """Example: Looking up AVM modules."""
    print("\n" + "=" * 60)
    print("Example 3: Module Lookup")
    print("=" * 60)

    # List modules by category
    print("\n--- Networking Modules ---")
    print(list_available_avm_modules("networking"))

    # Search for modules
    print("\n--- Search for 'database' ---")
    print(search_avm_modules("database"))

    # Get detailed module info
    print("\n--- Virtual Machine Module Info ---")
    print(get_avm_module_info("vm"))


def example_architecture_recommendation():
    """Example: Get module recommendations for an architecture."""
    print("\n" + "=" * 60)
    print("Example 4: Architecture Recommendations")
    print("=" * 60)

    # Define the services needed
    services = [
        "web server",
        "database",
        "cache",
        "monitoring",
        "secrets management",
    ]

    print(f"Services requested: {services}")
    print("\n--- Recommended AVM Modules ---")
    print(recommend_modules_for_architecture(services))


def example_agent_class():
    """Example: Using the TerraformAVMAgent class."""
    print("\n" + "=" * 60)
    print("Example 5: Using TerraformAVMAgent Class")
    print("=" * 60)

    agent = TerraformAVMAgent()

    # List modules
    print("\n--- List all module categories ---")
    categories = agent.list_modules()
    print(categories[:500] + "...")

    # Search modules
    print("\n--- Search for 'storage' ---")
    print(agent.search_modules("storage"))

    # Get module info
    print("\n--- Get info about Key Vault ---")
    print(agent.get_module_info("keyvault"))


def example_complex_architecture():
    """Example: Generate a complex multi-tier architecture."""
    print("\n" + "=" * 60)
    print("Example 6: Complex Multi-Tier Architecture")
    print("=" * 60)

    # Define a complex architecture
    services = [
        # Networking
        "virtual_network",
        "application_gateway",
        # Compute
        "kubernetes_cluster",
        "container_registry",
        # Data
        "postgresql_flexible",
        "redis",
        "storage_account",
        # Security
        "key_vault",
        "managed_identity",
        # Monitoring
        "log_analytics_workspace",
        "application_insights",
    ]

    result = generate_terraform(
        services=services,
        project_name="enterprise-platform",
        location="eastus2",
    )

    print(f"\nGenerated {len(result.files)} files for enterprise platform:")
    for file in result.files:
        print(f"  - {file.filename}")

    # Show the main.tf structure
    main_tf = next(f for f in result.files if f.filename == "main.tf")
    modules = [line for line in main_tf.content.split("\n") if line.startswith("module ")]
    print(f"\nModules in main.tf ({len(modules)}):")
    for module in modules:
        print(f"  {module}")


if __name__ == "__main__":
    # Run examples that don't require API keys
    example_quick_generation()
    example_module_lookup()
    example_architecture_recommendation()
    example_agent_class()
    example_complex_architecture()

    # Uncomment to run example that writes to disk
    # example_with_output_directory()

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)
