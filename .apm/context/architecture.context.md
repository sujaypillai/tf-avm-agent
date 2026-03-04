---
description: Project architecture overview and design patterns for tf-avm-agent
---

# TF-AVM-Agent Architecture

## Overview

tf-avm-agent is an AI-powered code generator that produces production-ready Terraform projects using Azure Verified Modules (AVM). It accepts Azure service lists or architecture diagram images and generates complete Terraform project files.

## System Architecture

```
┌─────────────────────────────────────────────────┐
│                  Entry Points                     │
│  CLI (Typer/Rich) │ REST API (FastAPI) │ Python  │
└────────┬──────────┴──────────┬─────────┴────────┘
         │                     │
         ▼                     ▼
┌─────────────────────────────────────────────────┐
│              TerraformAVMAgent                    │
│         (Microsoft Agent Framework)               │
│                                                   │
│  Tools:                                           │
│  ├── list_available_avm_modules                   │
│  ├── search_avm_modules                           │
│  ├── get_avm_module_info                          │
│  ├── get_module_dependencies                      │
│  ├── recommend_modules_for_architecture           │
│  ├── generate_terraform_module                    │
│  ├── generate_terraform_project                   │
│  └── write_terraform_files                        │
└────────┬──────────┬──────────┬──────────────────┘
         │          │          │
         ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────────────────┐
│ AVM      │ │ Diagram  │ │ Terraform            │
│ Lookup   │ │ Analyzer │ │ Generator            │
│          │ │ (Vision) │ │ (HCL Code Gen)       │
└────┬─────┘ └──────────┘ └──────────┬───────────┘
     │                               │
     ▼                               ▼
┌──────────────────────┐  ┌─────────────────────┐
│ AVM Module Registry  │  │ Terraform Utils     │
│ 105+ modules         │  │ CLI integration     │
│ Version fetching     │  │ Validation          │
│ Module discovery     │  │ Formatting          │
└──────────────────────┘  └─────────────────────┘
```

## Key Design Patterns

### Registry Pattern

The AVM module registry (`registry/avm_modules.py`) maintains definitions for 105+ Azure Verified Modules organized by category. Each module includes:
- Terraform Registry source path
- Service name aliases for fuzzy matching
- Default variables, outputs, and dependencies
- Dynamic version fetching from Terraform Registry API

### Tool Pattern

All agent capabilities are implemented as decorated tool functions using the Microsoft Agent Framework. Tools accept typed parameters (Pydantic `Annotated[type, Field()]`) and return structured results.

### Code Generation Pipeline

1. **Service Resolution**: Map Azure service names → AVM module definitions
2. **Dependency Resolution**: Topological sort of module dependencies
3. **Version Fetching**: Query Terraform Registry for latest versions
4. **Template Generation**: Produce HCL blocks for providers, variables, modules, and outputs
5. **File Writing**: Write formatted `.tf` files to disk

### Telemetry and RL

The Agent Lightning integration provides:
- `@trace_tool` decorator for tool-level observability
- Reward functions for evaluating generation quality
- Self-correction mechanisms for iterative improvement
- A/B testing framework for comparing agent strategies

## Technology Stack

- **Python 3.10+** with Pydantic for data validation
- **Microsoft Agent Framework** for AI agent capabilities
- **Azure OpenAI / OpenAI API** for LLM access
- **FastAPI** for REST API server
- **Typer + Rich** for CLI interface
- **httpx** for async HTTP client (Registry API)
- **Agent Lightning** for RL training and telemetry
