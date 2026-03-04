---
description: Generate a complete Terraform project from a list of Azure services using Azure Verified Modules
mode: terraform-expert
---

# Generate Terraform Project

You are generating a production-ready Terraform project using Azure Verified Modules (AVM).

## Input

Provide a comma-separated list of Azure services you need. For example:
- Virtual Network, Key Vault, Storage Account
- AKS, Container Registry, Log Analytics
- App Service, SQL Database, Redis Cache

## Steps

1. **Parse services**: Identify each Azure service from the input
2. **Map to AVM modules**: Find the matching Azure Verified Module for each service from the registry
3. **Resolve dependencies**: Determine which modules depend on others (e.g., AKS needs Virtual Network and Container Registry)
4. **Fetch latest versions**: Get the current module version from the Terraform Registry
5. **Generate files**: Create the complete Terraform project:
   - `providers.tf` — AzureRM provider with pessimistic version constraint
   - `variables.tf` — Project name, location, tags, enable_telemetry, and resource-specific variables
   - `main.tf` — All module blocks with proper dependencies and naming
   - `outputs.tf` — Key outputs from each module (IDs, names, endpoints)
   - `README.md` — Documentation for the generated project

## Conventions

- Use pessimistic version constraints (`~> X.0`)
- Include `enable_telemetry = var.enable_telemetry` in every module
- Use kebab-case for module instance names
- Use `substr()` for globally unique names (storage accounts, key vaults)
- Use `locals` with `merge()` for tag composition
