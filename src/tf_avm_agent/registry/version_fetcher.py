"""
Dynamic Version Fetcher for Terraform Registry.

This module fetches the latest versions of Terraform modules from the
public Terraform Registry API, with caching to avoid excessive API calls.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Terraform Registry API base URL
TERRAFORM_REGISTRY_API = "https://registry.terraform.io/v1/modules"

# Cache configuration
CACHE_DIR = Path.home() / ".cache" / "tf-avm-agent"
CACHE_FILE = CACHE_DIR / "module_versions.json"
CACHE_TTL_SECONDS = 3600  # 1 hour cache TTL


@dataclass
class ModuleVersion:
    """Represents a module version from the registry."""

    namespace: str
    name: str
    provider: str
    version: str
    published_at: Optional[str] = None


class VersionCache:
    """Simple file-based cache for module versions."""

    def __init__(self, cache_file: Path = CACHE_FILE, ttl_seconds: int = CACHE_TTL_SECONDS):
        self.cache_file = cache_file
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cache from disk if it exists."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r") as f:
                    self._cache = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load cache: {e}")
                self._cache = {}

    def _save_cache(self) -> None:
        """Save cache to disk."""
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_file, "w") as f:
                json.dump(self._cache, f, indent=2)
        except IOError as e:
            logger.warning(f"Failed to save cache: {e}")

    def get(self, key: str) -> Optional[str]:
        """Get a cached version if not expired."""
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry.get("timestamp", 0) < self.ttl_seconds:
                return entry.get("version")
            # Expired entry
            del self._cache[key]
        return None

    def set(self, key: str, version: str) -> None:
        """Cache a version with timestamp."""
        self._cache[key] = {
            "version": version,
            "timestamp": time.time(),
        }
        self._save_cache()

    def clear(self) -> None:
        """Clear all cached entries."""
        self._cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()


# Global cache instance
_version_cache = VersionCache()


def parse_module_source(source: str) -> tuple[str, str, str]:
    """
    Parse a Terraform module source string.

    Args:
        source: Module source like "Azure/avm-res-compute-virtualmachine/azurerm"

    Returns:
        Tuple of (namespace, name, provider)
    """
    parts = source.split("/")
    if len(parts) != 3:
        raise ValueError(f"Invalid module source format: {source}")
    return parts[0], parts[1], parts[2]


async def fetch_latest_version_async(
    source: str,
    timeout: float = 10.0,
) -> Optional[str]:
    """
    Fetch the latest version of a module from the Terraform Registry asynchronously.

    Args:
        source: Module source like "Azure/avm-res-compute-virtualmachine/azurerm"
        timeout: Request timeout in seconds

    Returns:
        The latest version string, or None if fetch failed
    """
    # Check cache first
    cached = _version_cache.get(source)
    if cached:
        logger.debug(f"Cache hit for {source}: {cached}")
        return cached

    try:
        namespace, name, provider = parse_module_source(source)
    except ValueError as e:
        logger.error(f"Failed to parse module source: {e}")
        return None

    url = f"{TERRAFORM_REGISTRY_API}/{namespace}/{name}/{provider}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()

            data = response.json()
            version = data.get("version")

            if version:
                _version_cache.set(source, version)
                logger.info(f"Fetched latest version for {source}: {version}")
                return version

            logger.warning(f"No version found in response for {source}")
            return None

    except httpx.TimeoutException:
        logger.warning(f"Timeout fetching version for {source}")
        return None
    except httpx.HTTPStatusError as e:
        logger.warning(f"HTTP error fetching version for {source}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error fetching version for {source}: {e}")
        return None


def fetch_latest_version(
    source: str,
    timeout: float = 10.0,
) -> Optional[str]:
    """
    Fetch the latest version of a module from the Terraform Registry (sync wrapper).

    Args:
        source: Module source like "Azure/avm-res-compute-virtualmachine/azurerm"
        timeout: Request timeout in seconds

    Returns:
        The latest version string, or None if fetch failed
    """
    # Check cache first (avoid async overhead for cache hits)
    cached = _version_cache.get(source)
    if cached:
        return cached

    # Handle both standalone and nested async contexts (Python 3.10+ compatible)
    try:
        asyncio.get_running_loop()
        # Already in an async context - run in a separate thread to avoid conflict
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, fetch_latest_version_async(source, timeout)).result()
    except RuntimeError:
        # No running event loop - safe to use asyncio.run()
        return asyncio.run(fetch_latest_version_async(source, timeout))


async def fetch_all_versions_async(
    source: str,
    timeout: float = 10.0,
) -> list[str]:
    """
    Fetch all available versions of a module from the Terraform Registry.

    Args:
        source: Module source like "Azure/avm-res-compute-virtualmachine/azurerm"
        timeout: Request timeout in seconds

    Returns:
        List of version strings, newest first
    """
    try:
        namespace, name, provider = parse_module_source(source)
    except ValueError as e:
        logger.error(f"Failed to parse module source: {e}")
        return []

    url = f"{TERRAFORM_REGISTRY_API}/{namespace}/{name}/{provider}/versions"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()

            data = response.json()
            modules = data.get("modules", [])

            if modules and len(modules) > 0:
                versions = modules[0].get("versions", [])
                return [v.get("version") for v in versions if v.get("version")]

            return []

    except Exception as e:
        logger.error(f"Error fetching versions for {source}: {e}")
        return []


async def batch_fetch_versions_async(
    sources: list[str],
    timeout: float = 10.0,
    max_concurrent: int = 10,
) -> dict[str, Optional[str]]:
    """
    Fetch latest versions for multiple modules concurrently.

    Args:
        sources: List of module source strings
        timeout: Request timeout in seconds
        max_concurrent: Maximum concurrent requests

    Returns:
        Dictionary mapping source to version (or None if fetch failed)
    """
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(source: str) -> tuple[str, Optional[str]]:
        async with semaphore:
            version = await fetch_latest_version_async(source, timeout)
            return source, version

    tasks = [fetch_with_semaphore(source) for source in sources]
    results = await asyncio.gather(*tasks)

    return dict(results)


def clear_version_cache() -> None:
    """Clear the version cache."""
    _version_cache.clear()


def get_cached_version(source: str) -> Optional[str]:
    """Get a cached version without fetching."""
    return _version_cache.get(source)


def refresh_version(source: str) -> Optional[str]:
    """Force refresh a module's version from the registry."""
    # Clear from cache first
    if source in _version_cache._cache:
        del _version_cache._cache[source]
    return fetch_latest_version(source)
