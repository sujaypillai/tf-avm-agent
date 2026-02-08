"""
AVM Module Lookup Tool.

This tool provides functions to search and retrieve information about
Azure Verified Modules (AVM) for Terraform.
"""

from typing import Annotated

from pydantic import Field

from tf_avm_agent.lightning.telemetry import trace_tool
from tf_avm_agent.registry.avm_modules import (
    AVM_MODULES,
    AVMModule,
    get_all_categories,
    get_module_by_service,
    get_modules_by_category,
    search_modules,
)


@trace_tool("list_available_avm_modules")
def list_available_avm_modules(
    category: Annotated[
        str | None,
        Field(description="Optional category to filter by (compute, networking, storage, database, security, messaging, monitoring, ai)"),
    ] = None,
) -> str:
    """
    List all available Azure Verified Modules.

    Args:
        category: Optional category to filter by

    Returns:
        Formatted string listing all available modules
    """
    if category:
        modules = get_modules_by_category(category)
        if not modules:
            available = ", ".join(get_all_categories())
            return f"No modules found for category '{category}'. Available categories: {available}"
    else:
        modules = list(AVM_MODULES.values())

    # Group by category
    by_category: dict[str, list[AVMModule]] = {}
    for module in modules:
        if module.category not in by_category:
            by_category[module.category] = []
        by_category[module.category].append(module)

    lines = ["# Available Azure Verified Modules (AVM)\n"]

    for cat in sorted(by_category.keys()):
        lines.append(f"\n## {cat.title()}\n")
        for module in sorted(by_category[cat], key=lambda m: m.name):
            aliases = ", ".join(module.aliases[:3]) if module.aliases else "none"
            lines.append(f"- **{module.name}**: {module.description}")
            lines.append(f"  - Source: `{module.source}`")
            lines.append(f"  - Aliases: {aliases}")

    return "\n".join(lines)


@trace_tool("search_avm_modules")
def search_avm_modules(
    query: Annotated[str, Field(description="Search query to find relevant AVM modules")],
) -> str:
    """
    Search for Azure Verified Modules matching a query.

    Args:
        query: Search query string

    Returns:
        Formatted string with search results
    """
    results = search_modules(query)

    if not results:
        # Try to find similar modules
        suggestions = []
        query_words = query.lower().split()
        for module in AVM_MODULES.values():
            for word in query_words:
                if (
                    word in module.name.lower()
                    or word in module.description.lower()
                    or any(word in alias.lower() for alias in module.aliases)
                ):
                    if module not in suggestions:
                        suggestions.append(module)

        if suggestions:
            lines = [f"No exact matches for '{query}'. Did you mean:\n"]
            for module in suggestions[:5]:
                lines.append(f"- **{module.name}**: {module.description}")
            return "\n".join(lines)

        return f"No modules found matching '{query}'. Try listing all modules with list_available_avm_modules()."

    lines = [f"# Search Results for '{query}'\n"]
    for module in results:
        # Get latest version dynamically
        latest_version = module.get_latest_version()
        lines.append(f"\n## {module.name}")
        lines.append(f"- **Description**: {module.description}")
        lines.append(f"- **Source**: `{module.source}`")
        lines.append(f"- **Version**: {latest_version}")
        lines.append(f"- **Category**: {module.category}")
        lines.append(f"- **Azure Service**: {module.azure_service}")
        if module.aliases:
            lines.append(f"- **Aliases**: {', '.join(module.aliases)}")

    return "\n".join(lines)


@trace_tool("get_avm_module_info")
def get_avm_module_info(
    service_name: Annotated[
        str, Field(description="The name or alias of the Azure service (e.g., 'virtual_machine', 'vm', 'storage', 'aks')")
    ],
    fetch_latest: bool = True,
) -> str:
    """
    Get detailed information about a specific AVM module.

    Args:
        service_name: The name or alias of the service
        fetch_latest: Whether to fetch the latest version from the registry (default True)

    Returns:
        Detailed information about the module including usage examples
    """
    module = get_module_by_service(service_name)

    if not module:
        # Search for similar modules
        similar = search_modules(service_name)
        if similar:
            suggestions = ", ".join([m.name for m in similar[:5]])
            return f"Module '{service_name}' not found. Similar modules: {suggestions}"
        return f"Module '{service_name}' not found. Use list_available_avm_modules() to see all available modules."

    # Get version (latest or fallback)
    version = module.get_latest_version() if fetch_latest else module.version

    lines = [
        f"# {module.name}",
        "",
        f"**Description**: {module.description}",
        "",
        "## Module Details",
        f"- **Source**: `{module.source}`",
        f"- **Version**: `{version}`",
        f"- **Category**: {module.category}",
        f"- **Azure Service**: `{module.azure_service}`",
    ]

    if module.aliases:
        lines.append(f"- **Aliases**: {', '.join(module.aliases)}")

    if module.dependencies:
        lines.append(f"- **Dependencies**: {', '.join(module.dependencies)}")

    # Required variables
    if module.required_variables:
        lines.append("\n## Required Variables")
        for var in module.required_variables:
            if var.required:
                example = f" (e.g., `{var.example}`)" if var.example else ""
                lines.append(f"- `{var.name}` ({var.type}): {var.description}{example}")

    # Optional variables
    optional_vars = [v for v in module.required_variables if not v.required] + module.optional_variables
    if optional_vars:
        lines.append("\n## Optional Variables")
        for var in optional_vars:
            default = f", default: `{var.default}`" if var.default is not None else ""
            lines.append(f"- `{var.name}` ({var.type}): {var.description}{default}")

    # Outputs
    if module.outputs:
        lines.append("\n## Outputs")
        for output in module.outputs:
            lines.append(f"- `{output}`")

    # Example configuration with latest version
    if module.example_config:
        lines.append("\n## Example Configuration")
        lines.append("```hcl")
        example = module.get_example_config_with_latest_version() if fetch_latest else module.example_config
        lines.append(example.strip())
        lines.append("```")
    else:
        # Generate basic example
        lines.append("\n## Basic Usage")
        lines.append("```hcl")
        lines.append(f'module "{module.name}" {{')
        lines.append(f'  source  = "{module.source}"')
        lines.append(f'  version = "{version}"')
        lines.append("")
        for var in module.required_variables:
            if var.required:
                if var.example:
                    lines.append(f"  {var.name} = {_format_example_value(var.example)}")
                else:
                    lines.append(f"  {var.name} = <{var.type}>  # {var.description}")
        lines.append("}")
        lines.append("```")

    return "\n".join(lines)


def _format_example_value(value) -> str:
    """Format an example value for HCL."""
    if isinstance(value, str):
        return f'"{value}"'
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, list):
        items = ", ".join(f'"{v}"' if isinstance(v, str) else str(v) for v in value)
        return f"[{items}]"
    else:
        return str(value)


@trace_tool("get_module_dependencies")
def get_module_dependencies(
    service_name: Annotated[str, Field(description="The name of the Azure service")],
) -> str:
    """
    Get the dependencies for a specific AVM module.

    Args:
        service_name: The name of the service

    Returns:
        Information about module dependencies
    """
    module = get_module_by_service(service_name)

    if not module:
        return f"Module '{service_name}' not found."

    if not module.dependencies:
        return f"Module '{module.name}' has no direct dependencies."

    lines = [f"# Dependencies for {module.name}\n"]

    for dep_name in module.dependencies:
        dep_module = get_module_by_service(dep_name)
        if dep_module:
            lines.append(f"## {dep_module.name}")
            lines.append(f"- **Description**: {dep_module.description}")
            lines.append(f"- **Source**: `{dep_module.source}`")
            lines.append("")
        else:
            lines.append(f"## {dep_name}")
            lines.append("- Native Azure resource (use azurerm provider directly)")
            lines.append("")

    return "\n".join(lines)


@trace_tool("recommend_modules_for_architecture")
def recommend_modules_for_architecture(
    services: Annotated[
        list[str],
        Field(description="List of Azure services or capabilities needed"),
    ],
) -> str:
    """
    Recommend AVM modules for a given list of services or capabilities.

    Args:
        services: List of services or capabilities needed

    Returns:
        Recommendations for AVM modules to use
    """
    recommendations: dict[str, AVMModule] = {}
    not_found: list[str] = []

    for service in services:
        module = get_module_by_service(service)
        if module:
            recommendations[module.name] = module
            # Also add dependencies
            for dep in module.dependencies:
                dep_module = get_module_by_service(dep)
                if dep_module and dep_module.name not in recommendations:
                    recommendations[dep_module.name] = dep_module
        else:
            # Search for similar
            similar = search_modules(service)
            if similar:
                recommendations[similar[0].name] = similar[0]
            else:
                not_found.append(service)

    lines = ["# Recommended AVM Modules\n"]

    if recommendations:
        # Sort by category for better organization
        by_category: dict[str, list[AVMModule]] = {}
        for module in recommendations.values():
            if module.category not in by_category:
                by_category[module.category] = []
            by_category[module.category].append(module)

        # Define deployment order
        category_order = ["security", "networking", "storage", "database", "compute", "messaging", "monitoring", "ai"]

        for cat in category_order:
            if cat in by_category:
                lines.append(f"\n## {cat.title()}")
                for module in by_category[cat]:
                    lines.append(f"\n### {module.name}")
                    lines.append(f"- Source: `{module.source}`")
                    lines.append(f"- Version: `{module.version}`")
                    lines.append(f"- Description: {module.description}")

    if not_found:
        lines.append("\n## Services Not Found")
        lines.append("The following services could not be matched to AVM modules:")
        for service in not_found:
            lines.append(f"- {service}")
        lines.append("\nThese may need to be implemented using the azurerm provider directly.")

    return "\n".join(lines)
