# Microsoft APM Integration Analysis for TF-AVM-Agent

## Executive Summary

This document analyzes [Microsoft APM (Agent Package Manager)](https://github.com/microsoft/apm) and presents a detailed plan for leveraging it within the **tf-avm-agent** project. APM is an open-source dependency manager for AI agents that standardizes how AI coding assistants (GitHub Copilot, Claude, Cursor, Codex, Gemini) are configured across projects. By integrating APM, tf-avm-agent can be packaged as a reusable, discoverable skill set that any developer can install with a single command, while also improving the development experience for contributors to the project itself.

---

## 1. What is Microsoft APM?

### 1.1 Overview

APM (Agent Package Manager) is a dependency manager for AI agent configuration — analogous to what `npm` is for JavaScript or `pip` for Python, but for AI agent skills, prompts, instructions, and tools. It uses a declarative manifest (`apm.yml`) to ensure every developer on a project gets the same AI agent setup.

### 1.2 Core Concepts

| Concept | Description |
|---------|-------------|
| **apm.yml** | Manifest file declaring all agentic dependencies (skills, prompts, instructions) |
| **Instructions** (`.instructions.md`) | Coding standards and guardrails scoped to file patterns |
| **Skills** (`SKILL.md`) | Package meta-guides for AI agent discoverability |
| **Prompts** (`.prompt.md`) | Reusable slash commands and workflow templates |
| **Agents** (`.agent.md`) | Specialized AI personas with defined expertise and tool boundaries |
| **Context** (`.context.md`) | Project knowledge, architecture patterns, and decisions |
| **Hooks** (`.json`) | Lifecycle event handlers (pre/post tool use) |
| **MCP Servers** | External tool integrations (APIs, databases, etc.) |

### 1.3 How APM Works

```
apm install <package>    # Install dependencies from GitHub, Azure DevOps, or files
apm compile              # Compile instructions into AGENTS.md / CLAUDE.md
apm init [name]          # Scaffold a new APM project
apm run <prompt>         # Execute a prompt workflow
apm deps list            # Show installed packages
```

APM resolves transitive dependencies, supports private repositories, and compiles agent-specific instruction files (`AGENTS.md` for Copilot/Cursor, `CLAUDE.md` for Claude).

---

## 2. Current TF-AVM-Agent Architecture

### 2.1 Project Structure

```
tf-avm-agent/
├── src/tf_avm_agent/
│   ├── agent.py              # AI agent (Microsoft Agent Framework)
│   ├── cli.py                # CLI interface (Typer/Rich)
│   ├── api.py                # FastAPI REST API
│   ├── tools/
│   │   ├── terraform_generator.py   # Terraform HCL code generation
│   │   ├── diagram_analyzer.py      # Architecture diagram → Azure services
│   │   ├── avm_lookup.py            # AVM module search/recommendation
│   │   └── terraform_utils.py       # Terraform CLI helpers
│   ├── registry/
│   │   ├── avm_modules.py           # 105+ AVM module definitions
│   │   ├── module_discovery.py      # Terraform Registry API integration
│   │   ├── published_modules.py     # Published module metadata
│   │   └── version_fetcher.py       # Version fetching with caching
│   └── lightning/
│       ├── telemetry.py             # Agent tracing/observability
│       ├── rewards.py               # RL reward calculation
│       ├── train.py                 # RL training loop
│       └── ...                      # A/B testing, self-correction, etc.
├── docs/
├── examples/
├── tests/
├── web/                             # FastAPI web UI
└── deploy/                          # Deployment (Terraform + Docker)
```

### 2.2 Key Capabilities

1. **Terraform Code Generation**: Produces complete projects (providers.tf, variables.tf, main.tf, outputs.tf) using Azure Verified Modules
2. **Architecture Diagram Analysis**: Vision-based extraction of Azure services from diagrams
3. **AVM Module Registry**: Built-in knowledge of 105+ modules across 8 categories
4. **Interactive Chat**: Conversational interface for module exploration and code generation
5. **REST API**: Programmatic access via FastAPI
6. **RL Training**: Agent Lightning integration for continuous improvement

---

## 3. Integration Opportunities

### 3.1 Dual Integration Strategy

There are two complementary ways to leverage APM:

| Strategy | Description | Benefit |
|----------|-------------|---------|
| **A. Package tf-avm-agent as an APM package** | Make the project's Terraform/AVM expertise installable via `apm install` | Other projects can reuse our skills, prompts, and coding standards |
| **B. Use APM for developer experience** | Use APM primitives within the project to standardize contributor onboarding | Contributors get consistent AI agent configuration instantly |

### 3.2 Strategy A — Package as APM Skill

By creating an APM package, any developer can run:

```bash
apm install sujaypillai/tf-avm-agent
```

This gives their AI coding assistant (Copilot, Claude, etc.) immediate knowledge of:
- Terraform best practices with Azure Verified Modules
- AVM module naming conventions and version constraints
- Azure resource naming rules and length limits
- Infrastructure-as-code patterns and dependencies

### 3.3 Strategy B — Improve Developer Experience

By adding APM primitives to the project, contributors who clone the repo and run `apm install && apm compile` get:
- Python coding standards specific to this project
- Terraform code generation conventions
- Pre-configured AI agent personas for common tasks
- Reusable prompts for code review, module addition, etc.

---

## 4. Detailed Implementation Plan

### Phase 1: Core APM Package Structure

**Goal**: Make tf-avm-agent an installable APM package.

#### 4.1 Create `apm.yml` Manifest

```yaml
name: tf-avm-agent
version: 1.0.0
description: AI-powered Terraform code generation using Azure Verified Modules (AVM)
dependencies:
  apm:
    - microsoft/GitHub-Copilot-for-Azure/plugin/skills/azure-compliance
```

#### 4.2 Create `SKILL.md`

A meta-guide that helps AI agents understand what the package does — enabling discoverability when installed as a dependency.

#### 4.3 Create `.apm/` Directory Structure

```
.apm/
├── instructions/
│   ├── terraform.instructions.md      # Terraform coding standards
│   └── python.instructions.md         # Python project conventions
├── prompts/
│   ├── generate-terraform.prompt.md   # Generate Terraform from services
│   ├── analyze-diagram.prompt.md      # Analyze architecture diagram
│   └── add-avm-module.prompt.md       # Add a new AVM module
├── agents/
│   └── terraform-expert.agent.md      # Terraform/AVM specialist persona
└── context/
    └── architecture.context.md        # Project architecture & patterns
```

### Phase 2: Instruction Primitives

#### 4.4 Terraform Instructions (`.apm/instructions/terraform.instructions.md`)

Scope: `**/*.tf` files — provides guidance on:
- Pessimistic version constraints (`~> X.0`)
- AVM module `enable_telemetry` pattern
- Variable validation blocks
- Resource naming conventions (kebab-case instance names, 24-char storage account limits)
- `locals` with `merge()` instead of variable defaults referencing other variables

#### 4.5 Python Instructions (`.apm/instructions/python.instructions.md`)

Scope: `**/*.py` files — provides guidance on:
- Type hints (Python 3.10+)
- Pydantic models for data validation
- Ruff linting rules (E, F, I, W)
- Registry pattern for module lookups (`module.get_latest_version()`)
- Lazy-loading imports for optional dependencies

### Phase 3: Agent Prompts

#### 4.6 Generate Terraform Prompt (`.apm/prompts/generate-terraform.prompt.md`)

A reusable slash command that walks the AI through generating a Terraform project:
1. Accept a list of Azure services
2. Map to AVM modules
3. Resolve dependencies
4. Generate complete project files

#### 4.7 Analyze Diagram Prompt (`.apm/prompts/analyze-diagram.prompt.md`)

A workflow for converting architecture diagrams to Terraform code.

#### 4.8 Add AVM Module Prompt (`.apm/prompts/add-avm-module.prompt.md`)

A guided workflow for adding new AVM module definitions to the registry.

### Phase 4: Agent Persona

#### 4.9 Terraform Expert Agent (`.apm/agents/terraform-expert.agent.md`)

A specialized AI persona with:
- Deep Terraform and Azure expertise
- Knowledge of all 105+ AVM modules
- Understanding of dependency resolution patterns
- Code review capabilities for Terraform configurations

### Phase 5: Context Documentation

#### 4.10 Architecture Context (`.apm/context/architecture.context.md`)

Project knowledge including:
- System architecture overview
- Module registry design
- Code generation pipeline
- Tool chain and dependencies

### Phase 6: Project Configuration

#### 4.11 Update `.gitignore`

Add `apm_modules/` to prevent committed dependency trees.

#### 4.12 Compilation Targets

After running `apm compile`, the project generates:
- `AGENTS.md` for GitHub Copilot / Cursor / Codex
- `CLAUDE.md` for Anthropic Claude

---

## 5. Benefits Analysis

### 5.1 For the TF-AVM-Agent Project

| Benefit | Impact |
|---------|--------|
| **Faster contributor onboarding** | New contributors get AI-assisted development immediately |
| **Consistent code quality** | Instructions enforce project conventions automatically |
| **Reusable workflows** | Prompts standardize common development tasks |
| **Better AI assistance** | Context files give AI agents deep project understanding |
| **Community discoverability** | Other projects can install and use our Terraform expertise |

### 5.2 For Consumers of the Package

| Benefit | Impact |
|---------|--------|
| **Instant Terraform expertise** | `apm install sujaypillai/tf-avm-agent` gives AI agents AVM knowledge |
| **Coding standards** | Terraform best practices applied automatically to `.tf` files |
| **Guided workflows** | Prompts walk through infrastructure generation step-by-step |
| **Expert persona** | AI behaves as a specialized Terraform/Azure consultant |

### 5.3 Synergy with Existing Features

| Existing Feature | APM Enhancement |
|-----------------|-----------------|
| **AVM Module Registry** | Instructions encode module conventions; context describes the registry |
| **Terraform Generator** | Prompts create guided generation workflows |
| **Diagram Analyzer** | Prompt workflow for diagram-to-code pipeline |
| **Agent Lightning RL** | APM packages can include hooks for telemetry/feedback collection |
| **CLI/API** | APM prompts can invoke the CLI/API for end-to-end workflows |

---

## 6. Dependency and Risk Assessment

### 6.1 Dependencies

| Dependency | Type | Risk |
|-----------|------|------|
| `apm-cli` (PyPI) | Optional dev dependency | Low — APM is open-source, community-driven, MIT licensed |
| `microsoft/GitHub-Copilot-for-Azure` | APM package dependency | Low — maintained by Microsoft, public access |

### 6.2 Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| APM is early-stage | All APM files are standard Markdown — they work without APM CLI too |
| Breaking changes in APM format | Primitives use stable Markdown + YAML frontmatter — minimal migration needed |
| Increased repo complexity | APM files are self-contained in `.apm/` — no impact on core source code |
| Token requirements for private deps | Only public packages are used; no tokens required |

---

## 7. Implementation Timeline

| Phase | Scope | Effort |
|-------|-------|--------|
| **Phase 1** | Core package structure (`apm.yml`, `SKILL.md`, `.apm/`) | 1 day |
| **Phase 2** | Instruction primitives (Terraform + Python standards) | 1 day |
| **Phase 3** | Agent prompts (generate, analyze, add-module) | 1 day |
| **Phase 4** | Agent persona (terraform-expert) | 0.5 day |
| **Phase 5** | Context documentation (architecture) | 0.5 day |
| **Phase 6** | Configuration (.gitignore, compilation) | 0.5 day |
| **Total** | | **~4.5 days** |

---

## 8. Future Enhancements

1. **MCP Server Integration**: Register the tf-avm-agent API as an MCP server, enabling AI agents to call it directly for Terraform generation
2. **Hooks for Validation**: Add post-tool hooks that automatically run `terraform validate` and `terraform fmt` after code generation
3. **Community Skill Library**: Publish individual skills (e.g., "generate-vnet", "setup-aks") as virtual packages
4. **CI/CD Integration**: Add APM compilation to the CI pipeline so `AGENTS.md` stays up-to-date
5. **Transitive Dependencies**: Leverage APM's dependency resolution to bundle Azure compliance skills from `microsoft/GitHub-Copilot-for-Azure`

---

## 9. References

- [Microsoft APM GitHub Repository](https://github.com/microsoft/apm)
- [APM Sample Package](https://github.com/microsoft/apm-sample-package)
- [APM CLI on PyPI](https://pypi.org/project/apm-cli/)
- [Agent Skills Specification](https://agentskills.io/specification)
- [AGENTS.md Standard](https://agents.md)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io)
- [Awesome AI Native Development](https://danielmeppiel.github.io/awesome-ai-native)
