---
description: Python coding standards for the tf-avm-agent project
applyTo: "**/*.py"
---

# Python Coding Standards

## Language Version

- Target Python 3.10+ — use modern syntax (`list[str]` instead of `List[str]`, `X | Y` union types)
- Use `from __future__ import annotations` only when needed for forward references

## Type Hints

- Use type hints for all function parameters and return types
- Use `Annotated[type, Field(...)]` for tool function parameters (Pydantic + Agent Framework convention)
- Use Pydantic `BaseModel` for structured data (tool inputs, configs, API responses)

## Code Style

- Follow Ruff linting rules: E (pycodestyle errors), F (pyflakes), I (isort), W (pycodestyle warnings)
- Maximum line length: 100 characters
- Use `logging.getLogger(__name__)` for module-level loggers
- Use lazy-loading imports for optional dependencies (wrap in try/except with availability flag)

## Project Patterns

- Registry lookups use `get_module_by_service()` to find AVM modules
- Always fetch current versions from Terraform Registry via `module.get_latest_version()`
- Use `@trace_tool` decorator from `lightning.telemetry` on tool functions for observability
- CLI commands are defined in `cli.py` using Typer with Rich formatting

## Testing

- Use `pytest` with `pytest-asyncio` for async tests
- Test files go in `tests/` directory, mirroring source structure
- Use descriptive test names: `test_<function>_<scenario>_<expected_result>`

## Error Handling

- Raise specific exceptions with descriptive messages
- Use try/except around external calls (Terraform CLI, Registry API, OpenAI API)
- Log errors at appropriate levels (`logger.warning` for recoverable, `logger.error` for failures)
