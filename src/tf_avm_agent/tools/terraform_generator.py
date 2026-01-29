"""
Terraform Code Generator Tool.

This tool generates Terraform code using Azure Verified Modules (AVM)
based on the identified Azure services.
"""

import os
from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field

from tf_avm_agent.registry.avm_modules import AVMModule, get_module_by_service


class TerraformModuleConfig(BaseModel):
    """Configuration for a Terraform module instance."""

    module_name: str = Field(description="Name for this module instance")
    avm_module: str = Field(description="The AVM module to use")
    variables: dict = Field(default_factory=dict, description="Variable values")
    depends_on: list[str] = Field(default_factory=list, description="Module dependencies")


class TerraformProjectConfig(BaseModel):
    """Configuration for a complete Terraform project."""

    project_name: str = Field(description="Name of the project")
    location: str = Field(default="eastus", description="Default Azure region")
    resource_group_name: str = Field(description="Name of the resource group")
    modules: list[TerraformModuleConfig] = Field(default_factory=list)
    tags: dict[str, str] = Field(default_factory=dict, description="Default tags")
    backend_config: dict | None = Field(default=None, description="Backend configuration")


class GeneratedFile(BaseModel):
    """A generated Terraform file."""

    filename: str
    content: str


class TerraformProjectOutput(BaseModel):
    """Output of Terraform project generation."""

    files: list[GeneratedFile] = Field(default_factory=list)
    summary: str = Field(default="")


def generate_terraform_module(
    service_name: Annotated[str, Field(description="The Azure service name to generate code for")],
    module_instance_name: Annotated[str, Field(description="Name for this module instance")],
    variables: Annotated[dict | None, Field(description="Variable values to set")] = None,
    use_resource_group_ref: Annotated[bool, Field(description="Reference resource group from azurerm_resource_group")] = True,
) -> str:
    """
    Generate Terraform code for a single AVM module.

    Args:
        service_name: The Azure service to generate code for
        module_instance_name: Name for this module instance
        variables: Variable values to override defaults
        use_resource_group_ref: Whether to use azurerm_resource_group reference

    Returns:
        Generated Terraform HCL code
    """
    module = get_module_by_service(service_name)
    if not module:
        return f"# Error: Module '{service_name}' not found"

    variables = variables or {}
    lines = [
        f'module "{module_instance_name}" {{',
        f'  source  = "{module.source}"',
        f'  version = "{module.version}"',
        "",
    ]

    # Add required variables
    for var in module.required_variables:
        if var.name in variables:
            value = _format_hcl_value(variables[var.name])
            lines.append(f"  {var.name} = {value}")
        elif var.name == "resource_group_name" and use_resource_group_ref:
            lines.append("  resource_group_name = azurerm_resource_group.main.name")
        elif var.name == "location" and use_resource_group_ref:
            lines.append("  location = azurerm_resource_group.main.location")
        elif var.name == "name":
            lines.append(f'  name = "{module_instance_name}"')
        elif var.required:
            if var.example:
                value = _format_hcl_value(var.example)
                lines.append(f"  {var.name} = {value}  # Example value - customize as needed")
            elif var.default is not None:
                value = _format_hcl_value(var.default)
                lines.append(f"  {var.name} = {value}")
            else:
                lines.append(f"  # {var.name} = <{var.type}>  # Required: {var.description}")

    # Add any additional variables from input
    for key, value in variables.items():
        if not any(v.name == key for v in module.required_variables):
            formatted = _format_hcl_value(value)
            lines.append(f"  {key} = {formatted}")

    lines.append("}")

    return "\n".join(lines)


def _format_hcl_value(value) -> str:
    """Format a Python value as HCL."""
    if isinstance(value, str):
        # Check if it's a reference (starts with module., var., data., etc.)
        if any(value.startswith(prefix) for prefix in ["module.", "var.", "data.", "azurerm_", "local."]):
            return value
        return f'"{value}"'
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, list):
        items = ",\n    ".join(_format_hcl_value(v) for v in value)
        return f"[\n    {items}\n  ]"
    elif isinstance(value, dict):
        items = []
        for k, v in value.items():
            items.append(f"    {k} = {_format_hcl_value(v)}")
        return "{\n" + "\n".join(items) + "\n  }"
    elif value is None:
        return "null"
    else:
        return str(value)


def generate_providers_tf(
    subscription_id: Annotated[str | None, Field(description="Azure subscription ID")] = None,
    terraform_version: Annotated[str, Field(description="Minimum Terraform version")] = "1.9.0",
    azurerm_version: Annotated[str, Field(description="AzureRM provider version constraint")] = "~> 4.0",
) -> str:
    """
    Generate the providers.tf file content.

    Args:
        subscription_id: Optional subscription ID
        terraform_version: Minimum Terraform version
        azurerm_version: AzureRM provider version constraint

    Returns:
        Content for providers.tf
    """
    lines = [
        "terraform {",
        f'  required_version = ">= {terraform_version}"',
        "",
        "  required_providers {",
        "    azurerm = {",
        '      source  = "hashicorp/azurerm"',
        f'      version = "{azurerm_version}"',
        "    }",
        "    random = {",
        '      source  = "hashicorp/random"',
        '      version = "~> 3.0"',
        "    }",
        "  }",
        "}",
        "",
        "provider \"azurerm\" {",
        "  features {",
        "    key_vault {",
        "      purge_soft_delete_on_destroy = false",
        "    }",
        "    resource_group {",
        "      prevent_deletion_if_contains_resources = false",
        "    }",
        "  }",
    ]

    if subscription_id:
        lines.append(f'  subscription_id = "{subscription_id}"')

    lines.extend([
        "  storage_use_azuread = true",
        "}",
    ])

    return "\n".join(lines)


def generate_variables_tf(
    project_config: Annotated[TerraformProjectConfig, Field(description="Project configuration")],
) -> str:
    """
    Generate the variables.tf file content.

    Args:
        project_config: The project configuration

    Returns:
        Content for variables.tf
    """
    lines = [
        'variable "location" {',
        '  description = "The Azure region for resource deployment"',
        '  type        = string',
        f'  default     = "{project_config.location}"',
        "}",
        "",
        'variable "resource_group_name" {',
        '  description = "The name of the resource group"',
        '  type        = string',
        f'  default     = "{project_config.resource_group_name}"',
        "}",
        "",
        'variable "project_name" {',
        '  description = "The name of the project (used for naming resources)"',
        '  type        = string',
        f'  default     = "{project_config.project_name}"',
        "}",
        "",
        'variable "environment" {',
        '  description = "The environment (dev, staging, prod)"',
        '  type        = string',
        '  default     = "dev"',
        "}",
        "",
        'variable "tags" {',
        '  description = "Tags to apply to all resources"',
        '  type        = map(string)',
        "  default     = {",
    ]

    default_tags = {
        "project": project_config.project_name,
        "managed_by": "terraform",
        **project_config.tags,
    }

    for key, value in default_tags.items():
        lines.append(f'    "{key}" = "{value}"')

    lines.extend([
        "  }",
        "}",
    ])

    return "\n".join(lines)


def generate_main_tf(
    modules: Annotated[list[TerraformModuleConfig], Field(description="List of module configurations")],
    resource_group_name: Annotated[str, Field(description="Resource group name")],
    location: Annotated[str, Field(description="Azure region")] = "eastus",
) -> str:
    """
    Generate the main.tf file content.

    Args:
        modules: List of module configurations
        resource_group_name: Name of the resource group
        location: Azure region

    Returns:
        Content for main.tf
    """
    lines = [
        "# -----------------------------------------------------------------------------",
        "# Data Sources",
        "# -----------------------------------------------------------------------------",
        "",
        "data \"azurerm_client_config\" \"current\" {}",
        "",
        "# -----------------------------------------------------------------------------",
        "# Random suffix for globally unique names",
        "# -----------------------------------------------------------------------------",
        "",
        'resource "random_string" "suffix" {',
        "  length  = 6",
        "  special = false",
        "  upper   = false",
        "}",
        "",
        "# -----------------------------------------------------------------------------",
        "# Local values",
        "# -----------------------------------------------------------------------------",
        "",
        "locals {",
        '  name_suffix = random_string.suffix.result',
        '  resource_group_name = var.resource_group_name != "" ? var.resource_group_name : "${var.project_name}-rg-${local.name_suffix}"',
        "}",
        "",
        "# -----------------------------------------------------------------------------",
        "# Resource Group",
        "# -----------------------------------------------------------------------------",
        "",
        'resource "azurerm_resource_group" "main" {',
        "  name     = local.resource_group_name",
        "  location = var.location",
        "  tags     = var.tags",
        "}",
        "",
        "# -----------------------------------------------------------------------------",
        "# AVM Modules",
        "# -----------------------------------------------------------------------------",
    ]

    # Generate module blocks
    for module_config in modules:
        module = get_module_by_service(module_config.avm_module)
        if not module:
            lines.append(f"\n# Warning: Module '{module_config.avm_module}' not found")
            continue

        lines.append("")
        lines.append(f"# {module.description}")
        module_code = generate_terraform_module(
            service_name=module_config.avm_module,
            module_instance_name=module_config.module_name,
            variables=module_config.variables,
        )
        lines.append(module_code)

        # Add depends_on if specified
        if module_config.depends_on:
            # Insert depends_on before the closing brace
            deps = ", ".join(f"module.{d}" for d in module_config.depends_on)
            lines[-1] = lines[-1].replace("}", f"\n  depends_on = [{deps}]\n}}")

    return "\n".join(lines)


def generate_outputs_tf(
    modules: Annotated[list[TerraformModuleConfig], Field(description="List of module configurations")],
) -> str:
    """
    Generate the outputs.tf file content.

    Args:
        modules: List of module configurations

    Returns:
        Content for outputs.tf
    """
    lines = [
        "# -----------------------------------------------------------------------------",
        "# Outputs",
        "# -----------------------------------------------------------------------------",
        "",
        'output "resource_group_name" {',
        '  description = "The name of the resource group"',
        "  value       = azurerm_resource_group.main.name",
        "}",
        "",
        'output "resource_group_id" {',
        '  description = "The ID of the resource group"',
        "  value       = azurerm_resource_group.main.id",
        "}",
    ]

    for module_config in modules:
        module = get_module_by_service(module_config.avm_module)
        if not module:
            continue

        module_name = module_config.module_name

        # Output the resource ID
        lines.extend([
            "",
            f'output "{module_name}_resource_id" {{',
            f'  description = "The resource ID of {module_name}"',
            f"  value       = module.{module_name}.resource_id",
            "}",
        ])

        # Add common outputs based on module type
        if "name" in module.outputs:
            lines.extend([
                "",
                f'output "{module_name}_name" {{',
                f'  description = "The name of {module_name}"',
                f"  value       = module.{module_name}.name",
                "}",
            ])

    return "\n".join(lines)


def generate_terraform_project(
    project_name: Annotated[str, Field(description="Name of the project")],
    services: Annotated[list[str], Field(description="List of Azure services to include")],
    location: Annotated[str, Field(description="Azure region")] = "eastus",
    resource_group_name: Annotated[str | None, Field(description="Resource group name")] = None,
    tags: Annotated[dict[str, str] | None, Field(description="Tags to apply")] = None,
) -> TerraformProjectOutput:
    """
    Generate a complete Terraform project with AVM modules.

    Args:
        project_name: Name of the project
        services: List of Azure services to include
        location: Azure region for deployment
        resource_group_name: Optional resource group name
        tags: Optional tags to apply

    Returns:
        TerraformProjectOutput with generated files
    """
    # Normalize project name
    project_name_normalized = project_name.lower().replace(" ", "-").replace("_", "-")
    rg_name = resource_group_name or f"rg-{project_name_normalized}"

    # Build module configurations
    module_configs: list[TerraformModuleConfig] = []
    added_modules: set[str] = set()
    dependencies_map: dict[str, list[str]] = {}

    # First pass: identify all needed modules including dependencies
    def add_module_with_deps(service_name: str) -> None:
        module = get_module_by_service(service_name)
        if not module or module.name in added_modules:
            return

        # Add dependencies first
        for dep in module.dependencies:
            if dep not in ["resource_group"]:  # We handle resource group separately
                add_module_with_deps(dep)
                if module.name not in dependencies_map:
                    dependencies_map[module.name] = []
                dep_module = get_module_by_service(dep)
                if dep_module:
                    dependencies_map[module.name].append(dep_module.name)

        added_modules.add(module.name)

    for service in services:
        add_module_with_deps(service)

    # Second pass: create module configurations in dependency order
    processed = set()

    def process_module(module_name: str) -> None:
        if module_name in processed:
            return

        module = get_module_by_service(module_name)
        if not module:
            return

        # Process dependencies first
        for dep in dependencies_map.get(module_name, []):
            process_module(dep)

        # Create module config
        instance_name = f"{module.name.replace('_', '-')}"
        variables = _get_default_variables(module, project_name_normalized)

        module_configs.append(
            TerraformModuleConfig(
                module_name=instance_name,
                avm_module=module.name,
                variables=variables,
                depends_on=dependencies_map.get(module_name, []),
            )
        )
        processed.add(module_name)

    for module_name in added_modules:
        process_module(module_name)

    # Create project config
    project_config = TerraformProjectConfig(
        project_name=project_name_normalized,
        location=location,
        resource_group_name=rg_name,
        modules=module_configs,
        tags=tags or {},
    )

    # Generate files
    files = [
        GeneratedFile(
            filename="providers.tf",
            content=generate_providers_tf(),
        ),
        GeneratedFile(
            filename="variables.tf",
            content=generate_variables_tf(project_config),
        ),
        GeneratedFile(
            filename="main.tf",
            content=generate_main_tf(
                modules=module_configs,
                resource_group_name=rg_name,
                location=location,
            ),
        ),
        GeneratedFile(
            filename="outputs.tf",
            content=generate_outputs_tf(module_configs),
        ),
        GeneratedFile(
            filename="terraform.tfvars.example",
            content=_generate_tfvars_example(project_config),
        ),
        GeneratedFile(
            filename=".gitignore",
            content=_generate_gitignore(),
        ),
        GeneratedFile(
            filename="README.md",
            content=_generate_readme(project_config, module_configs),
        ),
    ]

    # Generate summary
    module_summary = "\n".join(f"  - {m.module_name} ({m.avm_module})" for m in module_configs)
    summary = f"""Terraform project '{project_name}' generated successfully!

Files created:
  - providers.tf
  - variables.tf
  - main.tf
  - outputs.tf
  - terraform.tfvars.example
  - .gitignore
  - README.md

Modules included:
{module_summary}

Next steps:
1. Review and customize the generated code
2. Copy terraform.tfvars.example to terraform.tfvars and set your values
3. Run 'terraform init' to initialize the project
4. Run 'terraform plan' to preview changes
5. Run 'terraform apply' to deploy
"""

    return TerraformProjectOutput(files=files, summary=summary)


def _get_default_variables(module: AVMModule, project_name: str) -> dict:
    """Get default variable values for a module."""
    variables = {}

    # Set sensible defaults based on module type
    if module.name == "virtual_network":
        variables["address_space"] = ["10.0.0.0/16"]
        variables["subnets"] = {
            "default": {
                "name": "snet-default",
                "address_prefixes": ["10.0.1.0/24"],
            }
        }
    elif module.name == "storage_account":
        variables["account_tier"] = "Standard"
        variables["account_replication_type"] = "LRS"
    elif module.name == "key_vault":
        variables["tenant_id"] = "data.azurerm_client_config.current.tenant_id"
        variables["sku_name"] = "standard"
    elif module.name == "log_analytics_workspace":
        variables["sku"] = "PerGB2018"
        variables["retention_in_days"] = 30

    return variables


def _generate_tfvars_example(config: TerraformProjectConfig) -> str:
    """Generate example tfvars file."""
    return f'''# Example Terraform variables file
# Copy this to terraform.tfvars and customize the values

location            = "{config.location}"
resource_group_name = "{config.resource_group_name}"
project_name        = "{config.project_name}"
environment         = "dev"

tags = {{
  project     = "{config.project_name}"
  environment = "dev"
  managed_by  = "terraform"
}}
'''


def _generate_gitignore() -> str:
    """Generate .gitignore file for Terraform projects."""
    return """# Terraform files
*.tfstate
*.tfstate.*
*.tfstate.backup
.terraform/
.terraform.lock.hcl

# Sensitive files
*.tfvars
!*.tfvars.example
secrets.auto.tfvars

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Crash logs
crash.log
crash.*.log

# Override files
override.tf
override.tf.json
*_override.tf
*_override.tf.json
"""


def _generate_readme(config: TerraformProjectConfig, modules: list[TerraformModuleConfig]) -> str:
    """Generate README.md file."""
    module_list = "\n".join(f"- **{m.module_name}**: {m.avm_module}" for m in modules)

    return f'''# {config.project_name}

Terraform project generated using Azure Verified Modules (AVM).

## Overview

This project deploys the following Azure resources:

{module_list}

## Prerequisites

- [Terraform](https://www.terraform.io/downloads.html) >= 1.9.0
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) >= 2.50.0
- An Azure subscription

## Usage

1. **Authenticate with Azure:**

   ```bash
   az login
   az account set --subscription "<subscription-id>"
   ```

2. **Initialize Terraform:**

   ```bash
   terraform init
   ```

3. **Configure variables:**

   ```bash
   cp terraform.tfvars.example terraform.tfvars
   # Edit terraform.tfvars with your values
   ```

4. **Plan the deployment:**

   ```bash
   terraform plan
   ```

5. **Apply the configuration:**

   ```bash
   terraform apply
   ```

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `location` | Azure region | `{config.location}` |
| `resource_group_name` | Resource group name | `{config.resource_group_name}` |
| `project_name` | Project name | `{config.project_name}` |
| `environment` | Environment (dev/staging/prod) | `dev` |
| `tags` | Resource tags | See variables.tf |

## Modules

This project uses [Azure Verified Modules (AVM)](https://aka.ms/AVM) for Terraform.

## Clean Up

To destroy all resources:

```bash
terraform destroy
```

## License

This project is provided as-is under the MIT License.
'''


def write_terraform_files(
    output_dir: Annotated[str, Field(description="Directory to write files to")],
    project_output: Annotated[TerraformProjectOutput, Field(description="Generated project output")],
    overwrite: Annotated[bool, Field(description="Overwrite existing files")] = False,
) -> str:
    """
    Write generated Terraform files to disk.

    Args:
        output_dir: Directory to write files to
        project_output: The generated project output
        overwrite: Whether to overwrite existing files

    Returns:
        Summary of written files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    written_files = []
    skipped_files = []

    for file in project_output.files:
        file_path = output_path / file.filename

        if file_path.exists() and not overwrite:
            skipped_files.append(file.filename)
            continue

        file_path.write_text(file.content)
        written_files.append(file.filename)

    result_lines = [f"Files written to: {output_dir}"]

    if written_files:
        result_lines.append(f"\nWritten ({len(written_files)}):")
        for f in written_files:
            result_lines.append(f"  - {f}")

    if skipped_files:
        result_lines.append(f"\nSkipped (already exist) ({len(skipped_files)}):")
        for f in skipped_files:
            result_lines.append(f"  - {f}")
        result_lines.append("\nUse overwrite=True to overwrite existing files.")

    return "\n".join(result_lines)
