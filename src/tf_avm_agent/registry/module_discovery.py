"""
AVM Module Discovery from Terraform Registry.

This module provides functions to discover and fetch all available
Azure Verified Modules (AVM) from the Terraform Registry.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Terraform Registry API
TERRAFORM_REGISTRY_API = "https://registry.terraform.io/v1/modules"
TERRAFORM_REGISTRY_SEARCH = "https://registry.terraform.io/v1/modules/search"

# Cache configuration
CACHE_DIR = Path.home() / ".cache" / "tf-avm-agent"
MODULES_CACHE_FILE = CACHE_DIR / "avm_modules_list.json"


@dataclass
class DiscoveredModule:
    """A module discovered from the Terraform Registry."""

    name: str
    source: str
    version: str
    description: str
    published_at: Optional[str] = None
    downloads: int = 0


# Mapping of module names to categories based on Azure service
CATEGORY_MAPPINGS = {
    "compute": [
        "virtualmachine", "virtualmachinescaleset", "disk", "gallery", "hostgroup",
        "proximityplacementgroup", "sshpublickey", "capacityreservationgroup",
        "diskencryptionset"
    ],
    "containers": [
        "containerapp", "managedenvironment", "containergroup", "registry",
        "managedcluster", "job"
    ],
    "networking": [
        "virtualnetwork", "subnet", "networkinterface", "networksecuritygroup",
        "publicipaddress", "publicipprefix", "loadbalancer", "applicationgateway",
        "azurefirewall", "firewallpolicy", "bastionhost", "dnszone", "privatednszone",
        "privateendpoint", "routetable", "natgateway", "ddosprotectionplan",
        "expressroutecircuit", "connection", "localnetworkgateway", "dnsresolver",
        "networkwatcher", "ipgroup", "networkmanager", "applicationsecuritygroup",
        "webapplicationfirewallpolicy", "frontdoorwebapplicationfirewallpolicy"
    ],
    "storage": [
        "storageaccount", "netappaccount"
    ],
    "database": [
        "databaseaccount", "mongocluster", "flexibleserver", "server",
        "managedinstance", "cluster"
    ],
    "security": [
        "vault", "userassignedidentity", "roleassignment", "certificateorder"
    ],
    "messaging": [
        "namespace", "topic", "domain", "eventhub", "servicebus", "relay"
    ],
    "monitoring": [
        "workspace", "component", "datacollectionendpoint", "autoscalesetting",
        "query"
    ],
    "ai": [
        "cognitiveservices", "machinelearningservices", "searchservice"
    ],
    "web": [
        "site", "serverfarm", "hostingenvironment", "staticsite", "workflow"
    ],
    "management": [
        "resourcegroup", "servicegroup", "automationaccount", "maintenanceconfiguration",
        "backupvault", "resourceguard", "dashboard"
    ],
    "integration": [
        "datafactory", "apimanagement", "appconfiguration"
    ],
    "analytics": [
        "databricks", "kusto", "operationalinsights"
    ],
    "avd": [
        "hostpool", "applicationgroup", "scalingplan", "desktopvirtualization"
    ],
    "hybrid": [
        "azurestackhci", "privatecloud", "openshiftcluster", "oracledatabase",
        "hybridcontainerservice", "arcsite"
    ],
    "other": []
}


def categorize_module(module_name: str) -> str:
    """
    Categorize a module based on its name.

    Args:
        module_name: The module name (e.g., "avm-res-compute-virtualmachine")

    Returns:
        The category string
    """
    name_lower = module_name.lower()

    # Extract the resource type from the name
    # Format: avm-res-<provider>-<resource>
    parts = name_lower.split("-")
    if len(parts) >= 4:
        resource_type = "-".join(parts[3:])  # Get everything after avm-res-provider
    else:
        resource_type = name_lower

    for category, keywords in CATEGORY_MAPPINGS.items():
        for keyword in keywords:
            if keyword in resource_type or keyword in name_lower:
                return category

    return "other"


def generate_module_key(module_name: str) -> str:
    """
    Generate a friendly key for a module.

    Args:
        module_name: The module name (e.g., "avm-res-compute-virtualmachine")

    Returns:
        A friendly key (e.g., "virtual_machine")
    """
    # Remove common prefixes
    name = module_name.lower()
    name = re.sub(r"^avm-res-", "", name)

    # Remove provider prefix (e.g., compute-, network-, etc.)
    parts = name.split("-")
    if len(parts) > 1:
        # Take the resource name part
        name = "_".join(parts[1:])
    else:
        name = parts[0]

    # Clean up
    name = name.replace("-", "_")

    return name


def generate_azure_service(module_name: str) -> str:
    """
    Generate the Azure service path from the module name.

    Args:
        module_name: The module name (e.g., "avm-res-compute-virtualmachine")

    Returns:
        Azure service path (e.g., "Microsoft.Compute/virtualMachines")
    """
    # Remove prefix
    name = re.sub(r"^avm-res-", "", module_name.lower())
    parts = name.split("-")

    if len(parts) >= 2:
        provider = parts[0].title()
        resource = "".join(p.title() for p in parts[1:])
        return f"Microsoft.{provider}/{resource}"

    return f"Microsoft.Resources/{module_name}"


async def search_avm_modules_from_registry(
    namespace: str = "Azure",
    provider: str = "azurerm",
    limit: int = 500,
    timeout: float = 60.0,
) -> list[DiscoveredModule]:
    """
    Search for all AVM modules in the Terraform Registry.

    Args:
        namespace: The module namespace (default: "Azure")
        provider: The provider (default: "azurerm")
        limit: Maximum number of modules to fetch
        timeout: Request timeout in seconds

    Returns:
        List of discovered modules
    """
    modules = []
    offset = 0
    page_size = 100  # Use larger page size

    async with httpx.AsyncClient(timeout=timeout) as client:
        while offset < limit:
            try:
                # List all modules from the Azure namespace
                url = f"{TERRAFORM_REGISTRY_API}/{namespace}"
                params = {
                    "offset": offset,
                    "limit": min(page_size, limit - offset),
                }

                response = await client.get(url, params=params)
                response.raise_for_status()

                data = response.json()
                module_list = data.get("modules", [])

                if not module_list:
                    break

                for mod in module_list:
                    # Only include avm-res modules (resource modules)
                    name = mod.get("name", "")
                    mod_provider = mod.get("provider", "")

                    # Filter for azurerm provider and avm-res prefix
                    if name.startswith("avm-res-") and mod_provider == provider:
                        modules.append(DiscoveredModule(
                            name=name,
                            source=f"{mod.get('namespace', namespace)}/{name}/{mod_provider}",
                            version=mod.get("version", "0.1.0"),
                            description=mod.get("description", ""),
                            published_at=mod.get("published_at"),
                            downloads=mod.get("downloads", 0),
                        ))

                offset += len(module_list)

                # Check if we've fetched all
                meta = data.get("meta", {})
                total = meta.get("total_count", len(module_list))
                if offset >= total:
                    break

            except httpx.HTTPError as e:
                logger.error(f"Error fetching modules from registry: {e}")
                break

    return modules


async def fetch_module_details(
    source: str,
    timeout: float = 10.0,
) -> Optional[dict]:
    """
    Fetch detailed information about a specific module.

    Args:
        source: Module source (e.g., "Azure/avm-res-compute-virtualmachine/azurerm")
        timeout: Request timeout in seconds

    Returns:
        Module details dict or None
    """
    try:
        parts = source.split("/")
        if len(parts) != 3:
            return None

        namespace, name, provider = parts
        url = f"{TERRAFORM_REGISTRY_API}/{namespace}/{name}/{provider}"

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    except Exception as e:
        logger.error(f"Error fetching module details for {source}: {e}")
        return None


def discover_modules_sync(
    namespace: str = "Azure",
    provider: str = "azurerm",
) -> list[DiscoveredModule]:
    """
    Synchronous wrapper for discovering modules.

    Args:
        namespace: The module namespace
        provider: The provider

    Returns:
        List of discovered modules
    """
    try:
        return asyncio.run(search_avm_modules_from_registry(namespace, provider))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(search_avm_modules_from_registry(namespace, provider))


async def fetch_published_modules_async(
    timeout: float = 60.0,
    max_concurrent: int = 20,
) -> list[DiscoveredModule]:
    """
    Fetch all published AVM modules from the authoritative list.

    This uses the official published modules list and fetches versions
    from the Terraform Registry.

    Args:
        timeout: Request timeout in seconds
        max_concurrent: Maximum concurrent requests

    Returns:
        List of discovered modules with versions
    """
    from tf_avm_agent.registry.published_modules import PUBLISHED_AVM_MODULES

    semaphore = asyncio.Semaphore(max_concurrent)
    modules = []

    async def fetch_module_version(mod_info: dict) -> DiscoveredModule:
        name = mod_info["name"]
        source = f"Azure/{name}/azurerm"
        version = "latest"

        async with semaphore:
            try:
                url = f"{TERRAFORM_REGISTRY_API}/Azure/{name}/azurerm"
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        version = data.get("version", "latest")
            except Exception as e:
                logger.debug(f"Could not fetch version for {name}: {e}")

        return DiscoveredModule(
            name=name,
            source=source,
            version=version,
            description=mod_info["display"],
        )

    tasks = [fetch_module_version(mod) for mod in PUBLISHED_AVM_MODULES]
    modules = await asyncio.gather(*tasks)

    return list(modules)


def fetch_published_modules_sync() -> list[DiscoveredModule]:
    """
    Synchronous wrapper for fetching published modules.

    Returns:
        List of discovered modules
    """
    try:
        return asyncio.run(fetch_published_modules_async())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(fetch_published_modules_async())


def save_discovered_modules(modules: list[DiscoveredModule], cache_file: Path = MODULES_CACHE_FILE) -> None:
    """Save discovered modules to cache."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    data = [
        {
            "name": m.name,
            "source": m.source,
            "version": m.version,
            "description": m.description,
            "published_at": m.published_at,
            "downloads": m.downloads,
        }
        for m in modules
    ]

    with open(cache_file, "w") as f:
        json.dump(data, f, indent=2)


def load_discovered_modules(cache_file: Path = MODULES_CACHE_FILE) -> list[DiscoveredModule]:
    """Load discovered modules from cache."""
    if not cache_file.exists():
        return []

    try:
        with open(cache_file, "r") as f:
            data = json.load(f)

        return [
            DiscoveredModule(
                name=m["name"],
                source=m["source"],
                version=m["version"],
                description=m.get("description", ""),
                published_at=m.get("published_at"),
                downloads=m.get("downloads", 0),
            )
            for m in data
        ]
    except Exception as e:
        logger.error(f"Error loading cached modules: {e}")
        return []
