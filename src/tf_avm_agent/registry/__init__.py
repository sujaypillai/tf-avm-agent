"""AVM Module Registry for looking up Azure Verified Modules."""

from tf_avm_agent.registry.avm_modules import AVM_MODULES, AVMModule, get_module_by_service

__all__ = ["AVM_MODULES", "AVMModule", "get_module_by_service"]
