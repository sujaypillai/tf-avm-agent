---
description: Add a new Azure Verified Module definition to the tf-avm-agent registry
mode: terraform-expert
---

# Add AVM Module to Registry

You are adding a new Azure Verified Module to the tf-avm-agent module registry.

## Input

Provide the module details:
- Azure service name (e.g., "Azure Cosmos DB")
- Terraform Registry module name (e.g., "Azure/avm-res-documentdb-databaseaccount/azurerm")
- Module category (compute, networking, storage, database, security, monitoring, integration, container)

## Steps

1. **Verify the module**: Check the Terraform Registry to confirm the module exists and get the latest version
2. **Define the module entry**: Create an `AVMModule` definition with:
   - `name`: Terraform Registry source path
   - `display_name`: Human-readable name
   - `description`: What the module provisions
   - `category`: One of the 8 standard categories
   - `service_names`: List of Azure service name variants for matching
   - `required_providers`: Usually `["azurerm"]`
   - `default_variables`: Common variable defaults
   - `outputs`: Key outputs the module exposes
   - `dependencies`: Other AVM modules this depends on
3. **Add to registry**: Insert the module in `src/tf_avm_agent/registry/avm_modules.py` in the appropriate category section
4. **Add to published modules**: Update `src/tf_avm_agent/registry/published_modules.py` if needed
5. **Test**: Run `pytest tests/` to verify the module is discoverable

## Conventions

- Service names should include common aliases (e.g., "Cosmos DB", "CosmosDB", "Azure Cosmos DB")
- Default variables should include `name`, `location`, and `resource_group_name`
- Dependencies should reference other modules by their registry name
