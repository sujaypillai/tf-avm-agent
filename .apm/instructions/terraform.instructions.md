---
description: Terraform coding standards for Azure Verified Modules (AVM) projects
applyTo: "**/*.tf"
---

# Terraform AVM Coding Standards

## Provider and Module Versioning

- Use pessimistic version constraints for providers: `~> X.0`
- Use pessimistic version constraints for AVM modules: `~> X.0`
- Always pin the `azurerm` provider with `features {}` block
- Always set `required_version` for Terraform itself

## AVM Module Conventions

- Always include `enable_telemetry = var.enable_telemetry` in every AVM module block
- Define a `variable "enable_telemetry"` with `type = bool`, `default = true`, and a descriptive description
- Use the `name` argument with project prefix and resource type suffix
- Reference modules using the Terraform Registry source format: `"Azure/avm-res-<provider>-<resource>/azurerm"`

## Resource Naming

- Use kebab-case for module instance names (e.g., `module "avm-res-network-virtualnetwork"`)
- Storage accounts must have globally unique names with a 24-character maximum length — use `substr()` for truncation
- Key Vault names must also be globally unique with a 24-character maximum length — apply the same `substr()` pattern
- Apply a consistent naming pattern: `"${var.project_name}-<resource-type>"`

## Variables and Locals

- Variable defaults must not reference other variables — use `locals` with `merge()` instead
- Always add `validation` blocks for constrained variables (e.g., location, naming patterns)
- Use a shared `tags` variable of `type = map(string)` with sensible defaults via `locals`

## File Organization

- `providers.tf` — Provider configuration and required_providers block
- `variables.tf` — All input variables with descriptions and validation
- `main.tf` — Module instances and resource definitions
- `outputs.tf` — Output values from module instances
- `locals.tf` — Local value computations (optional, can be in main.tf)

## Formatting

- Run `terraform fmt` before committing
- Use 2-space indentation (Terraform default)
- Add descriptive comments as section headers (e.g., `# --- Virtual Network ---`)
- Group related resources together with blank lines between groups

## Dependencies

- Declare explicit `depends_on` when implicit dependencies are insufficient
- Order module blocks so that dependencies appear before dependents
- Use `module.<name>.<output>` references to create implicit dependency chains
