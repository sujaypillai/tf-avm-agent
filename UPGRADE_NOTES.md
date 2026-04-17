# Microsoft Agent Framework 1.0.1 GA Upgrade Notes

## Overview

Successfully upgraded `agent-framework` from beta (`>=1.0.0b260128`) to GA release `1.0.1`. This was a major upgrade involving several breaking changes.

## Changes Made

### 1. Dependency Updates

**pyproject.toml:**
```toml
# Before
agent = [
    "agent-framework>=1.0.0b260128",
    "agent-framework-azure-ai>=1.0.0b260128",
    "agent-framework-durabletask>=1.0.0b260128",
    ...
]

# After
agent = [
    "agent-framework==1.0.1",
    "agent-framework-openai==1.0.1",
    ...
]
```

**Note:** The beta package `agent-framework-azure-ai` has been replaced with `agent-framework-openai` in the GA release. The `agent-framework-durabletask` package is now included as a transitive dependency.

### 2. Type Renames

#### ChatAgent → Agent

**src/tf_avm_agent/agent.py:**
```python
# Before
from agent_framework import ChatAgent

# After
from agent_framework import Agent
```

### 3. Unified OpenAI Client

The GA release unified the OpenAI and Azure OpenAI clients into a single `OpenAIChatClient` class.

**Before (beta):**
```python
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework.openai import OpenAIChatClient

# Separate clients for Azure and OpenAI
if use_azure_openai:
    chat_client = AzureOpenAIChatClient(
        endpoint=azure_endpoint,
        deployment=deployment,
        credential=credential,
    )
else:
    chat_client = OpenAIChatClient(api_key=api_key)
```

**After (1.0.1 GA):**
```python
from agent_framework.openai import OpenAIChatClient

# Single unified client
if use_azure_openai:
    chat_client = OpenAIChatClient(
        model=deployment,
        azure_endpoint=azure_endpoint,
        credential=credential,
    )
else:
    chat_client = OpenAIChatClient(api_key=api_key)
```

The `OpenAIChatClient` now accepts both `api_key` (for OpenAI) and `azure_endpoint` + `credential` (for Azure OpenAI) parameters.

### 4. Python 3.13 Support

Added Python 3.13 to the CI test matrix and package classifiers to align with GA release support.

**.github/workflows/ci.yml:**
```yaml
matrix:
  python-version: ["3.10", "3.11", "3.12", "3.13"]
```

## Breaking Changes NOT Applicable

The following breaking changes mentioned in the upgrade guide did NOT affect this codebase:

1. **ChatMessage → Message**: This codebase doesn't use the `ChatMessage` class directly.
2. **WorkflowBuilder API changes**: This codebase doesn't use `WorkflowBuilder`, workflows, or multi-agent patterns.
3. **Checkpoint storage security**: This codebase doesn't use Microsoft Agent Framework's checkpoint storage feature (Lightning model checkpoints are separate).

## Testing

Created comprehensive test suite (`tests/test_agent_framework_1_0_1.py`) with 18 tests covering:

- Import validation for renamed types
- Unified OpenAIChatClient functionality
- Backward compatibility for existing features
- Package version verification

**Test Results:**
- 208 total tests passed
- All existing tests (190) continue to pass
- All new upgrade validation tests (18) pass
- Build and installation verified

## Migration Guide for Developers

If you're working on code that uses the Microsoft Agent Framework:

1. **Update imports:**
   - `ChatAgent` → `Agent`
   - `RawChatAgent` → `RawAgent`
   - `ChatMessage` → `Message`
   - Remove `agent_framework.azure.AzureOpenAIChatClient` imports

2. **Update Azure OpenAI client usage:**
   - Use `OpenAIChatClient` with `azure_endpoint` and `credential` parameters
   - Change `deployment` parameter to `model` parameter

3. **Test thoroughly:**
   - Run the full test suite
   - Verify agent instantiation for both OpenAI and Azure OpenAI
   - Test all agent functionality

## References

- [Python 2026 Significant Changes Guide](https://learn.microsoft.com/en-us/agent-framework/support/upgrade/python-2026-significant-changes)
- [Microsoft Agent Framework GitHub](https://github.com/microsoft/agent-framework)
- Package: https://pypi.org/project/agent-framework/1.0.1/

## Rollback Plan

If issues arise, rollback by:

1. Revert pyproject.toml dependencies to beta versions
2. Revert src/tf_avm_agent/agent.py changes
3. Remove tests/test_agent_framework_1_0_1.py
4. Revert .github/workflows/ci.yml Python 3.13 addition

```bash
git revert <commit-hash>
pip install -e ".[dev]"
pytest tests/
```
