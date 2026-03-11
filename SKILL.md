---
name: tf-avm-agent
description: Generate production-ready Terraform code using Azure Verified Modules (AVM). Use when asked about Azure infrastructure, Terraform module selection, or infrastructure-as-code generation.
license: MIT
metadata:
  author: sujaypillai
  version: "1.0.0"
  tags: ["terraform", "azure", "avm", "infrastructure-as-code", "ai-agent"]
---

# Terraform AVM Agent Skill

## What This Package Does

This package gives AI coding assistants deep expertise in Azure infrastructure generation using Terraform and Azure Verified Modules (AVM). It includes:

- **Terraform coding standards** for `.tf` files (version constraints, naming, validation)
- **Python project conventions** for the agent codebase
- **Guided prompts** for generating Terraform projects from service lists or architecture diagrams
- **Expert agent persona** specialized in Terraform and Azure

## When To Use

- When asked to create Azure infrastructure using Terraform
- When selecting Azure Verified Modules for a project
- When reviewing Terraform code for AVM best practices
- When converting architecture diagrams to infrastructure code
- When adding new Azure services to an existing Terraform project

## Available Prompts

- `/generate-terraform` — Generate a complete Terraform project from Azure service names
- `/analyze-diagram` — Convert an architecture diagram to Terraform code
- `/add-avm-module` — Add a new AVM module to the registry

## Key Conventions

- Use pessimistic version constraints (`~> X.0`) for providers and modules
- Always include `enable_telemetry = var.enable_telemetry` in AVM modules
- Use kebab-case for module instance names
- Storage accounts and Key Vaults need globally unique names (24 chars max)
- Use `locals` with `merge()` instead of variable defaults referencing other variables
- Fetch current module versions from Terraform Registry with `module.get_latest_version()`
