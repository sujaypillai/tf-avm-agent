"""
TF AVM Agent - An AI agent that generates Terraform code using Azure Verified Modules.

This agent can accept a list of Azure services or an architecture diagram as input
and generate a complete Terraform project using Azure Verified Modules (AVM).
"""

__version__ = "0.1.0"

# Lazy imports via PEP 562 so that `import tf_avm_agent` works without
# pulling in agent-framework, pydantic, and other heavy optional deps.
_LAZY_IMPORTS = {
    "TerraformAVMAgent": "tf_avm_agent.agent",
    "generate_terraform": "tf_avm_agent.agent",
}


def __getattr__(name: str):
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value  # cache for subsequent access
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["TerraformAVMAgent", "generate_terraform", "__version__"]
