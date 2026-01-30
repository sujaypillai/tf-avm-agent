"""AVM Module Registry for looking up Azure Verified Modules."""

from tf_avm_agent.registry.avm_modules import (
    AVM_MODULES,
    AVMModule,
    get_all_modules,
    get_module_by_service,
    sync_modules_from_registry,
)
from tf_avm_agent.registry.version_fetcher import (
    clear_version_cache,
    fetch_latest_version,
    get_cached_version,
    refresh_version,
)

__all__ = [
    "AVM_MODULES",
    "AVMModule",
    "get_module_by_service",
    "get_all_modules",
    "sync_modules_from_registry",
    "fetch_latest_version",
    "get_cached_version",
    "refresh_version",
    "clear_version_cache",
]
