"""
Azure Verified Modules (AVM) Registry.

This module contains a comprehensive registry of available AVM modules for Terraform,
including their source paths, required variables, and common configurations.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AVMModuleVariable:
    """Represents a variable for an AVM module."""

    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None
    example: Any = None


@dataclass
class AVMModule:
    """Represents an Azure Verified Module."""

    name: str
    source: str
    version: str  # Fallback version if dynamic fetch fails
    description: str
    category: str
    azure_service: str
    required_variables: list[AVMModuleVariable] = field(default_factory=list)
    optional_variables: list[AVMModuleVariable] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    aliases: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    example_config: str = ""

    @property
    def registry_name(self) -> str:
        """Get the full AVM module name from the source (e.g., 'avm-res-compute-virtualmachine')."""
        # Source format: "Azure/avm-res-compute-virtualmachine/azurerm"
        parts = self.source.split("/")
        if len(parts) >= 2:
            return parts[1]
        return self.name

    def get_latest_version(self, use_cache: bool = True) -> str:
        """
        Get the latest version from the Terraform Registry.

        Args:
            use_cache: Whether to use cached version (default True)

        Returns:
            The latest version, or the fallback version if fetch fails
        """
        from tf_avm_agent.registry.version_fetcher import (
            fetch_latest_version,
            get_cached_version,
        )

        if use_cache:
            cached = get_cached_version(self.source)
            if cached:
                return cached

        latest = fetch_latest_version(self.source)
        if latest:
            return latest

        logger.warning(
            f"Failed to fetch latest version for {self.source}, using fallback: {self.version}"
        )
        return self.version

    def get_example_config_with_latest_version(self) -> str:
        """Get the example config with the latest version substituted."""
        if not self.example_config:
            return ""

        latest_version = self.get_latest_version()
        # Replace version in example config
        import re
        return re.sub(
            r'version\s*=\s*"[^"]*"',
            f'version = "{latest_version}"',
            self.example_config,
        )


# Comprehensive AVM Module Registry
AVM_MODULES: dict[str, AVMModule] = {
    # ============== Compute ==============
    "virtual_machine": AVMModule(
        name="virtual_machine",
        source="Azure/avm-res-compute-virtualmachine/azurerm",
        version="0.20.0",
        description="Deploy Azure Virtual Machines with best practices including availability zones and managed disks",
        category="compute",
        azure_service="Microsoft.Compute/virtualMachines",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the virtual machine"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
            AVMModuleVariable("zone", "number", "The availability zone", required=False, default=1),
            AVMModuleVariable(
                "virtualmachine_sku_size",
                "string",
                "The SKU size of the virtual machine",
                example="Standard_D2s_v3",
            ),
            AVMModuleVariable(
                "virtualmachine_os_type", "string", "The OS type (Windows or Linux)"
            ),
        ],
        optional_variables=[
            AVMModuleVariable(
                "admin_username", "string", "Admin username", required=False, default="azureuser"
            ),
            AVMModuleVariable(
                "disable_password_authentication",
                "bool",
                "Disable password auth for Linux",
                required=False,
                default=True,
            ),
        ],
        outputs=["resource_id", "name", "private_ip_address", "public_ip_address"],
        aliases=["vm", "virtual-machine", "compute", "server"],
        dependencies=["virtual_network", "resource_group"],
        example_config="""
module "virtual_machine" {
  source  = "Azure/avm-res-compute-virtualmachine/azurerm"
  version = "0.20.0"

  name                       = "vm-example"
  resource_group_name        = azurerm_resource_group.example.name
  location                   = azurerm_resource_group.example.location
  zone                       = 1
  virtualmachine_sku_size    = "Standard_D2s_v3"
  virtualmachine_os_type     = "Linux"

  source_image_reference = {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-jammy"
    sku       = "22_04-lts-gen2"
    version   = "latest"
  }

  network_interfaces = {
    network_interface_1 = {
      name = "nic-example"
      ip_configurations = {
        ip_configuration_1 = {
          name                          = "ipconfig1"
          private_ip_subnet_resource_id = azurerm_subnet.example.id
        }
      }
    }
  }
}
""",
    ),
    "virtual_machine_scale_set": AVMModule(
        name="virtual_machine_scale_set",
        source="Azure/avm-res-compute-virtualmachinescaleset/azurerm",
        version="0.6.0",
        description="Deploy Azure Virtual Machine Scale Sets for auto-scaling compute",
        category="compute",
        azure_service="Microsoft.Compute/virtualMachineScaleSets",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the VMSS"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
            AVMModuleVariable("sku_name", "string", "The SKU name", example="Standard_D2s_v3"),
            AVMModuleVariable("instances", "number", "Initial instance count", default=2),
        ],
        outputs=["resource_id", "name", "unique_id"],
        aliases=["vmss", "scale-set", "autoscale"],
        dependencies=["virtual_network", "resource_group"],
    ),
    "container_app": AVMModule(
        name="container_app",
        source="Azure/avm-res-app-containerapp/azurerm",
        version="0.5.0",
        description="Deploy Azure Container Apps for serverless container workloads",
        category="compute",
        azure_service="Microsoft.App/containerApps",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the container app"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable(
                "container_app_environment_resource_id",
                "string",
                "The resource ID of the Container App Environment",
            ),
        ],
        outputs=["resource_id", "name", "fqdn", "latest_revision_fqdn"],
        aliases=["containerapp", "container-app", "aca"],
        dependencies=["container_app_environment", "resource_group"],
        example_config="""
module "container_app" {
  source  = "Azure/avm-res-app-containerapp/azurerm"
  version = "0.5.0"

  name                                   = "ca-example"
  resource_group_name                    = azurerm_resource_group.example.name
  container_app_environment_resource_id  = module.container_app_environment.resource_id

  template = {
    containers = [
      {
        name   = "app"
        image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest"
        cpu    = 0.25
        memory = "0.5Gi"
      }
    ]
  }

  ingress = {
    external_enabled = true
    target_port      = 80
    transport        = "auto"
    traffic_weight = [
      {
        percentage      = 100
        latest_revision = true
      }
    ]
  }
}
""",
    ),
    "container_app_environment": AVMModule(
        name="container_app_environment",
        source="Azure/avm-res-app-managedenvironment/azurerm",
        version="0.3.0",
        description="Deploy Azure Container App Environment",
        category="compute",
        azure_service="Microsoft.App/managedEnvironments",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the environment"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        outputs=["resource_id", "name", "default_domain", "static_ip_address"],
        aliases=["cae", "container-app-env", "managed-environment"],
        dependencies=["resource_group", "log_analytics_workspace"],
    ),
    "kubernetes_cluster": AVMModule(
        name="kubernetes_cluster",
        source="Azure/avm-res-containerservice-managedcluster/azurerm",
        version="0.5.0",
        description="Deploy Azure Kubernetes Service (AKS) clusters",
        category="compute",
        azure_service="Microsoft.ContainerService/managedClusters",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the AKS cluster"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        optional_variables=[
            AVMModuleVariable(
                "kubernetes_version", "string", "Kubernetes version", required=False
            ),
            AVMModuleVariable(
                "sku_tier", "string", "AKS SKU tier", required=False, default="Standard"
            ),
        ],
        outputs=["resource_id", "name", "kube_config", "oidc_issuer_url"],
        aliases=["aks", "kubernetes", "k8s"],
        dependencies=["virtual_network", "resource_group"],
        example_config="""
module "aks_cluster" {
  source  = "Azure/avm-res-containerservice-managedcluster/azurerm"
  version = "0.5.0"

  name                = "aks-example"
  resource_group_name = azurerm_resource_group.example.name
  location            = azurerm_resource_group.example.location

  managed_identities = {
    system_assigned = true
  }

  default_node_pool = {
    name                 = "system"
    vm_size              = "Standard_D2s_v5"
    orchestrator_version = "1.29"
    vnet_subnet_id       = azurerm_subnet.example.id
    node_count           = 3
  }
}
""",
    ),
    "container_registry": AVMModule(
        name="container_registry",
        source="Azure/avm-res-containerregistry-registry/azurerm",
        version="0.5.0",
        description="Deploy Azure Container Registry for container image storage",
        category="compute",
        azure_service="Microsoft.ContainerRegistry/registries",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the container registry"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        optional_variables=[
            AVMModuleVariable("sku", "string", "SKU tier", required=False, default="Premium"),
        ],
        outputs=["resource_id", "name", "login_server", "admin_username"],
        aliases=["acr", "container-registry", "docker-registry"],
        dependencies=["resource_group"],
    ),
    "function_app": AVMModule(
        name="function_app",
        source="Azure/avm-res-web-site/azurerm",
        version="0.17.0",
        description="Deploy Azure Functions for serverless compute",
        category="compute",
        azure_service="Microsoft.Web/sites",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the function app"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
            AVMModuleVariable(
                "kind", "string", "The kind of web site", default="functionapp,linux"
            ),
            AVMModuleVariable(
                "os_type", "string", "The OS type (Windows or Linux)", default="Linux"
            ),
            AVMModuleVariable(
                "service_plan_resource_id",
                "string",
                "The resource ID of the App Service Plan",
            ),
        ],
        outputs=["resource_id", "name", "default_hostname", "identity"],
        aliases=["function", "functions", "azure-function", "serverless"],
        dependencies=["app_service_plan", "storage_account", "resource_group"],
        example_config="""
module "function_app" {
  source  = "Azure/avm-res-web-site/azurerm"
  version = "0.17.0"

  name                     = "func-example"
  resource_group_name      = azurerm_resource_group.example.name
  location                 = azurerm_resource_group.example.location
  kind                     = "functionapp,linux"
  os_type                  = "Linux"
  service_plan_resource_id = module.app_service_plan.resource_id

  site_config = {
    application_stack = {
      python_version = "3.11"
    }
  }

  function_app_storage_account_name       = module.storage_account.name
  function_app_storage_account_access_key = module.storage_account.primary_access_key
}
""",
    ),
    "web_app": AVMModule(
        name="web_app",
        source="Azure/avm-res-web-site/azurerm",
        version="0.17.0",
        description="Deploy Azure App Service Web Apps",
        category="compute",
        azure_service="Microsoft.Web/sites",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the web app"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
            AVMModuleVariable("kind", "string", "The kind of web site", default="app,linux"),
            AVMModuleVariable("os_type", "string", "The OS type", default="Linux"),
            AVMModuleVariable(
                "service_plan_resource_id", "string", "The App Service Plan resource ID"
            ),
        ],
        outputs=["resource_id", "name", "default_hostname"],
        aliases=["webapp", "app-service", "web"],
        dependencies=["app_service_plan", "resource_group"],
    ),
    "app_service_plan": AVMModule(
        name="app_service_plan",
        source="Azure/avm-res-web-serverfarm/azurerm",
        version="0.4.0",
        description="Deploy Azure App Service Plans",
        category="compute",
        azure_service="Microsoft.Web/serverfarms",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the App Service Plan"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
            AVMModuleVariable("os_type", "string", "The OS type", default="Linux"),
            AVMModuleVariable("sku_name", "string", "The SKU name", default="P1v3"),
        ],
        outputs=["resource_id", "name"],
        aliases=["asp", "service-plan"],
        dependencies=["resource_group"],
    ),
    # ============== Networking ==============
    "virtual_network": AVMModule(
        name="virtual_network",
        source="Azure/avm-res-network-virtualnetwork/azurerm",
        version="0.8.0",
        description="Deploy Azure Virtual Networks with subnets and service endpoints",
        category="networking",
        azure_service="Microsoft.Network/virtualNetworks",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the virtual network"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
            AVMModuleVariable(
                "address_space",
                "list(string)",
                "The address space for the VNet",
                example=["10.0.0.0/16"],
            ),
        ],
        optional_variables=[
            AVMModuleVariable(
                "subnets",
                "map(object)",
                "Map of subnets to create",
                required=False,
            ),
        ],
        outputs=["resource_id", "name", "subnets"],
        aliases=["vnet", "network", "virtual-network"],
        dependencies=["resource_group"],
        example_config="""
module "virtual_network" {
  source  = "Azure/avm-res-network-virtualnetwork/azurerm"
  version = "0.8.0"

  name                = "vnet-example"
  resource_group_name = azurerm_resource_group.example.name
  location            = azurerm_resource_group.example.location
  address_space       = ["10.0.0.0/16"]

  subnets = {
    default = {
      name             = "snet-default"
      address_prefixes = ["10.0.1.0/24"]
    }
    apps = {
      name             = "snet-apps"
      address_prefixes = ["10.0.2.0/24"]
      delegation = [{
        name = "Microsoft.Web.serverFarms"
        service_delegation = {
          name = "Microsoft.Web/serverFarms"
        }
      }]
    }
  }
}
""",
    ),
    "network_security_group": AVMModule(
        name="network_security_group",
        source="Azure/avm-res-network-networksecuritygroup/azurerm",
        version="0.4.0",
        description="Deploy Azure Network Security Groups",
        category="networking",
        azure_service="Microsoft.Network/networkSecurityGroups",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the NSG"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        outputs=["resource_id", "name"],
        aliases=["nsg", "security-group", "firewall-rules"],
        dependencies=["resource_group"],
    ),
    "application_gateway": AVMModule(
        name="application_gateway",
        source="Azure/avm-res-network-applicationgateway/azurerm",
        version="0.4.0",
        description="Deploy Azure Application Gateway for web application load balancing",
        category="networking",
        azure_service="Microsoft.Network/applicationGateways",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Application Gateway"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        outputs=["resource_id", "name", "frontend_ip_configuration"],
        aliases=["appgw", "app-gateway", "waf"],
        dependencies=["virtual_network", "public_ip", "resource_group"],
    ),
    "load_balancer": AVMModule(
        name="load_balancer",
        source="Azure/avm-res-network-loadbalancer/azurerm",
        version="0.4.0",
        description="Deploy Azure Load Balancer for network traffic distribution",
        category="networking",
        azure_service="Microsoft.Network/loadBalancers",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Load Balancer"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        outputs=["resource_id", "name", "frontend_ip_configuration"],
        aliases=["lb", "balancer"],
        dependencies=["virtual_network", "resource_group"],
    ),
    "public_ip": AVMModule(
        name="public_ip",
        source="Azure/avm-res-network-publicipaddress/azurerm",
        version="0.2.0",
        description="Deploy Azure Public IP Addresses",
        category="networking",
        azure_service="Microsoft.Network/publicIPAddresses",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Public IP"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        optional_variables=[
            AVMModuleVariable(
                "allocation_method", "string", "Allocation method", required=False, default="Static"
            ),
            AVMModuleVariable("sku", "string", "SKU", required=False, default="Standard"),
        ],
        outputs=["resource_id", "name", "ip_address"],
        aliases=["pip", "public-ip", "external-ip"],
        dependencies=["resource_group"],
    ),
    "private_endpoint": AVMModule(
        name="private_endpoint",
        source="Azure/avm-res-network-privateendpoint/azurerm",
        version="0.10.0",
        description="Deploy Azure Private Endpoints for secure connectivity",
        category="networking",
        azure_service="Microsoft.Network/privateEndpoints",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Private Endpoint"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
            AVMModuleVariable("subnet_resource_id", "string", "The subnet resource ID"),
        ],
        outputs=["resource_id", "name", "private_ip_address"],
        aliases=["pe", "private-link"],
        dependencies=["virtual_network", "resource_group"],
    ),
    "dns_zone": AVMModule(
        name="dns_zone",
        source="Azure/avm-res-network-dnszone/azurerm",
        version="0.3.0",
        description="Deploy Azure DNS Zones",
        category="networking",
        azure_service="Microsoft.Network/dnsZones",
        required_variables=[
            AVMModuleVariable("name", "string", "The DNS zone name"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
        ],
        outputs=["resource_id", "name", "name_servers"],
        aliases=["dns", "domain"],
        dependencies=["resource_group"],
    ),
    "private_dns_zone": AVMModule(
        name="private_dns_zone",
        source="Azure/avm-res-network-privatednszone/azurerm",
        version="0.3.0",
        description="Deploy Azure Private DNS Zones",
        category="networking",
        azure_service="Microsoft.Network/privateDnsZones",
        required_variables=[
            AVMModuleVariable("name", "string", "The Private DNS zone name"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
        ],
        outputs=["resource_id", "name"],
        aliases=["private-dns", "internal-dns"],
        dependencies=["virtual_network", "resource_group"],
    ),
    "front_door": AVMModule(
        name="front_door",
        source="Azure/avm-res-cdn-profile/azurerm",
        version="0.7.0",
        description="Deploy Azure Front Door for global load balancing and CDN",
        category="networking",
        azure_service="Microsoft.Cdn/profiles",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Front Door"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("sku_name", "string", "SKU name", default="Standard_AzureFrontDoor"),
        ],
        outputs=["resource_id", "name", "endpoints"],
        aliases=["frontdoor", "cdn", "afd"],
        dependencies=["resource_group"],
    ),
    "firewall": AVMModule(
        name="firewall",
        source="Azure/avm-res-network-azurefirewall/azurerm",
        version="0.4.0",
        description="Deploy Azure Firewall for network security",
        category="networking",
        azure_service="Microsoft.Network/azureFirewalls",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Azure Firewall"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        outputs=["resource_id", "name", "private_ip_address", "public_ip_address"],
        aliases=["azure-firewall", "fw"],
        dependencies=["virtual_network", "public_ip", "resource_group"],
    ),
    "bastion": AVMModule(
        name="bastion",
        source="Azure/avm-res-network-bastionhost/azurerm",
        version="0.4.0",
        description="Deploy Azure Bastion for secure RDP/SSH connectivity",
        category="networking",
        azure_service="Microsoft.Network/bastionHosts",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Bastion host"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        outputs=["resource_id", "name", "dns_name"],
        aliases=["bastion-host", "jump-box"],
        dependencies=["virtual_network", "public_ip", "resource_group"],
    ),
    "nat_gateway": AVMModule(
        name="nat_gateway",
        source="Azure/avm-res-network-natgateway/azurerm",
        version="0.3.0",
        description="Deploy Azure NAT Gateway for outbound connectivity",
        category="networking",
        azure_service="Microsoft.Network/natGateways",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the NAT Gateway"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        outputs=["resource_id", "name"],
        aliases=["nat", "outbound-gateway"],
        dependencies=["public_ip", "resource_group"],
    ),
    # ============== Storage ==============
    "storage_account": AVMModule(
        name="storage_account",
        source="Azure/avm-res-storage-storageaccount/azurerm",
        version="0.5.0",
        description="Deploy Azure Storage Accounts with containers, queues, tables, and file shares",
        category="storage",
        azure_service="Microsoft.Storage/storageAccounts",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the storage account"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        optional_variables=[
            AVMModuleVariable(
                "account_tier", "string", "Account tier", required=False, default="Standard"
            ),
            AVMModuleVariable(
                "account_replication_type",
                "string",
                "Replication type",
                required=False,
                default="LRS",
            ),
        ],
        outputs=[
            "resource_id",
            "name",
            "primary_access_key",
            "primary_connection_string",
            "primary_blob_endpoint",
        ],
        aliases=["storage", "blob", "files", "queue", "table"],
        dependencies=["resource_group"],
        example_config="""
module "storage_account" {
  source  = "Azure/avm-res-storage-storageaccount/azurerm"
  version = "0.5.0"

  name                     = "stexample"
  resource_group_name      = azurerm_resource_group.example.name
  location                 = azurerm_resource_group.example.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  containers = {
    data = {
      name                  = "data"
      container_access_type = "private"
    }
  }

  network_rules = {
    default_action = "Deny"
    bypass         = ["AzureServices"]
  }
}
""",
    ),
    # ============== Databases ==============
    "sql_server": AVMModule(
        name="sql_server",
        source="Azure/avm-res-sql-server/azurerm",
        version="0.3.0",
        description="Deploy Azure SQL Server",
        category="database",
        azure_service="Microsoft.Sql/servers",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the SQL server"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        outputs=["resource_id", "name", "fully_qualified_domain_name"],
        aliases=["mssql", "sql", "azure-sql"],
        dependencies=["resource_group"],
    ),
    "sql_database": AVMModule(
        name="sql_database",
        source="Azure/avm-res-sql-server/azurerm",
        version="0.3.0",
        description="Deploy Azure SQL Database (part of SQL Server module)",
        category="database",
        azure_service="Microsoft.Sql/servers/databases",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the database"),
        ],
        outputs=["resource_id", "name"],
        aliases=["sql-db", "database"],
        dependencies=["sql_server", "resource_group"],
    ),
    "postgresql_flexible": AVMModule(
        name="postgresql_flexible",
        source="Azure/avm-res-dbforpostgresql-flexibleserver/azurerm",
        version="0.4.0",
        description="Deploy Azure Database for PostgreSQL Flexible Server",
        category="database",
        azure_service="Microsoft.DBforPostgreSQL/flexibleServers",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the PostgreSQL server"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        optional_variables=[
            AVMModuleVariable(
                "sku_name",
                "string",
                "SKU name",
                required=False,
                default="GP_Standard_D2s_v3",
            ),
            AVMModuleVariable(
                "storage_mb", "number", "Storage in MB", required=False, default=32768
            ),
        ],
        outputs=["resource_id", "name", "fqdn"],
        aliases=["postgres", "postgresql", "pg"],
        dependencies=["virtual_network", "resource_group"],
        example_config="""
module "postgresql" {
  source  = "Azure/avm-res-dbforpostgresql-flexibleserver/azurerm"
  version = "0.4.0"

  name                = "psql-example"
  resource_group_name = azurerm_resource_group.example.name
  location            = azurerm_resource_group.example.location
  sku_name            = "GP_Standard_D2s_v3"
  storage_mb          = 32768
  version             = "16"

  administrator_login    = "psqladmin"
  administrator_password = var.postgresql_admin_password

  databases = {
    app = {
      name      = "appdb"
      charset   = "UTF8"
      collation = "en_US.utf8"
    }
  }
}
""",
    ),
    "mysql_flexible": AVMModule(
        name="mysql_flexible",
        source="Azure/avm-res-dbformysql-flexibleserver/azurerm",
        version="0.4.0",
        description="Deploy Azure Database for MySQL Flexible Server",
        category="database",
        azure_service="Microsoft.DBforMySQL/flexibleServers",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the MySQL server"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        outputs=["resource_id", "name", "fqdn"],
        aliases=["mysql"],
        dependencies=["virtual_network", "resource_group"],
    ),
    "cosmosdb": AVMModule(
        name="cosmosdb",
        source="Azure/avm-res-documentdb-databaseaccount/azurerm",
        version="0.10.0",
        description="Deploy Azure Cosmos DB accounts",
        category="database",
        azure_service="Microsoft.DocumentDB/databaseAccounts",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Cosmos DB account"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        optional_variables=[
            AVMModuleVariable(
                "offer_type", "string", "Offer type", required=False, default="Standard"
            ),
            AVMModuleVariable(
                "kind", "string", "Kind of Cosmos DB", required=False, default="GlobalDocumentDB"
            ),
        ],
        outputs=["resource_id", "name", "endpoint", "primary_key", "connection_strings"],
        aliases=["cosmos", "documentdb", "nosql"],
        dependencies=["resource_group"],
    ),
    "redis": AVMModule(
        name="redis",
        source="Azure/avm-res-cache-redis/azurerm",
        version="0.4.0",
        description="Deploy Azure Cache for Redis",
        category="database",
        azure_service="Microsoft.Cache/redis",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Redis cache"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        optional_variables=[
            AVMModuleVariable(
                "sku_name", "string", "SKU name", required=False, default="Standard"
            ),
            AVMModuleVariable("family", "string", "SKU family", required=False, default="C"),
            AVMModuleVariable("capacity", "number", "Cache capacity", required=False, default=1),
        ],
        outputs=["resource_id", "name", "hostname", "primary_access_key", "primary_connection_string"],
        aliases=["cache", "redis-cache"],
        dependencies=["resource_group"],
    ),
    # ============== Security & Identity ==============
    "key_vault": AVMModule(
        name="key_vault",
        source="Azure/avm-res-keyvault-vault/azurerm",
        version="0.10.0",
        description="Deploy Azure Key Vault for secrets, keys, and certificates management",
        category="security",
        azure_service="Microsoft.KeyVault/vaults",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Key Vault"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
            AVMModuleVariable("tenant_id", "string", "The Azure AD tenant ID"),
        ],
        optional_variables=[
            AVMModuleVariable("sku_name", "string", "SKU name", required=False, default="standard"),
            AVMModuleVariable(
                "soft_delete_retention_days",
                "number",
                "Soft delete retention days",
                required=False,
                default=90,
            ),
        ],
        outputs=["resource_id", "name", "vault_uri"],
        aliases=["keyvault", "vault", "secrets"],
        dependencies=["resource_group"],
        example_config="""
module "key_vault" {
  source  = "Azure/avm-res-keyvault-vault/azurerm"
  version = "0.10.0"

  name                = "kv-example"
  resource_group_name = azurerm_resource_group.example.name
  location            = azurerm_resource_group.example.location
  tenant_id           = data.azurerm_client_config.current.tenant_id

  sku_name                   = "standard"
  soft_delete_retention_days = 90
  purge_protection_enabled   = true

  network_acls = {
    default_action = "Deny"
    bypass         = "AzureServices"
  }

  role_assignments = {
    deployment_user = {
      role_definition_id_or_name = "Key Vault Administrator"
      principal_id               = data.azurerm_client_config.current.object_id
    }
  }
}
""",
    ),
    "managed_identity": AVMModule(
        name="managed_identity",
        source="Azure/avm-res-managedidentity-userassignedidentity/azurerm",
        version="0.4.0",
        description="Deploy Azure User Assigned Managed Identity",
        category="security",
        azure_service="Microsoft.ManagedIdentity/userAssignedIdentities",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the managed identity"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        outputs=["resource_id", "name", "client_id", "principal_id", "tenant_id"],
        aliases=["identity", "uami", "user-assigned-identity"],
        dependencies=["resource_group"],
    ),
    # ============== Messaging ==============
    "event_hub": AVMModule(
        name="event_hub",
        source="Azure/avm-res-eventhub-namespace/azurerm",
        version="0.8.0",
        description="Deploy Azure Event Hub namespace and hubs",
        category="messaging",
        azure_service="Microsoft.EventHub/namespaces",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Event Hub namespace"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        optional_variables=[
            AVMModuleVariable("sku", "string", "SKU", required=False, default="Standard"),
            AVMModuleVariable("capacity", "number", "Throughput units", required=False, default=1),
        ],
        outputs=["resource_id", "name", "default_primary_connection_string"],
        aliases=["eventhub", "event-hubs", "streaming"],
        dependencies=["resource_group"],
    ),
    "service_bus": AVMModule(
        name="service_bus",
        source="Azure/avm-res-servicebus-namespace/azurerm",
        version="0.5.0",
        description="Deploy Azure Service Bus namespace, queues, and topics",
        category="messaging",
        azure_service="Microsoft.ServiceBus/namespaces",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Service Bus namespace"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        optional_variables=[
            AVMModuleVariable("sku", "string", "SKU", required=False, default="Standard"),
        ],
        outputs=["resource_id", "name", "default_primary_connection_string"],
        aliases=["servicebus", "message-queue", "pubsub"],
        dependencies=["resource_group"],
    ),
    "event_grid": AVMModule(
        name="event_grid",
        source="Azure/avm-res-eventgrid-topic/azurerm",
        version="0.3.0",
        description="Deploy Azure Event Grid topics",
        category="messaging",
        azure_service="Microsoft.EventGrid/topics",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Event Grid topic"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        outputs=["resource_id", "name", "endpoint", "primary_access_key"],
        aliases=["eventgrid", "events"],
        dependencies=["resource_group"],
    ),
    # ============== Monitoring & Logging ==============
    "log_analytics_workspace": AVMModule(
        name="log_analytics_workspace",
        source="Azure/avm-res-operationalinsights-workspace/azurerm",
        version="0.5.0",
        description="Deploy Azure Log Analytics Workspace",
        category="monitoring",
        azure_service="Microsoft.OperationalInsights/workspaces",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Log Analytics workspace"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        optional_variables=[
            AVMModuleVariable(
                "sku", "string", "SKU name", required=False, default="PerGB2018"
            ),
            AVMModuleVariable(
                "retention_in_days", "number", "Log retention days", required=False, default=30
            ),
        ],
        outputs=["resource_id", "name", "workspace_id", "primary_shared_key"],
        aliases=["log-analytics", "logs", "workspace", "law"],
        dependencies=["resource_group"],
    ),
    "application_insights": AVMModule(
        name="application_insights",
        source="Azure/avm-res-insights-component/azurerm",
        version="0.2.0",
        description="Deploy Azure Application Insights for application monitoring",
        category="monitoring",
        azure_service="Microsoft.Insights/components",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of Application Insights"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
            AVMModuleVariable(
                "workspace_resource_id", "string", "The Log Analytics workspace resource ID"
            ),
        ],
        optional_variables=[
            AVMModuleVariable(
                "application_type", "string", "Application type", required=False, default="web"
            ),
        ],
        outputs=["resource_id", "name", "instrumentation_key", "connection_string"],
        aliases=["appinsights", "app-insights", "apm"],
        dependencies=["log_analytics_workspace", "resource_group"],
    ),
    # ============== AI & Machine Learning ==============
    "cognitive_services": AVMModule(
        name="cognitive_services",
        source="Azure/avm-res-cognitiveservices-account/azurerm",
        version="0.8.0",
        description="Deploy Azure Cognitive Services / Azure AI Services accounts",
        category="ai",
        azure_service="Microsoft.CognitiveServices/accounts",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Cognitive Services account"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
            AVMModuleVariable(
                "kind",
                "string",
                "The kind of Cognitive Service",
                example="OpenAI",
            ),
            AVMModuleVariable("sku_name", "string", "SKU name", default="S0"),
        ],
        outputs=["resource_id", "name", "endpoint", "primary_access_key"],
        aliases=["cognitive", "ai-services", "openai", "azure-openai"],
        dependencies=["resource_group"],
    ),
    "machine_learning": AVMModule(
        name="machine_learning",
        source="Azure/avm-res-machinelearningservices-workspace/azurerm",
        version="0.5.0",
        description="Deploy Azure Machine Learning workspaces",
        category="ai",
        azure_service="Microsoft.MachineLearningServices/workspaces",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the ML workspace"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        outputs=["resource_id", "name", "workspace_id"],
        aliases=["ml", "aml", "azure-ml"],
        dependencies=["storage_account", "key_vault", "application_insights", "resource_group"],
    ),
    "search_service": AVMModule(
        name="search_service",
        source="Azure/avm-res-search-searchservice/azurerm",
        version="0.3.0",
        description="Deploy Azure AI Search (formerly Cognitive Search)",
        category="ai",
        azure_service="Microsoft.Search/searchServices",
        required_variables=[
            AVMModuleVariable("name", "string", "The name of the Search service"),
            AVMModuleVariable("resource_group_name", "string", "The name of the resource group"),
            AVMModuleVariable("location", "string", "The Azure region for deployment"),
        ],
        optional_variables=[
            AVMModuleVariable("sku", "string", "SKU", required=False, default="standard"),
        ],
        outputs=["resource_id", "name", "query_keys", "primary_key"],
        aliases=["search", "cognitive-search", "ai-search"],
        dependencies=["resource_group"],
    ),
}


def get_module_by_service(service_name: str) -> AVMModule | None:
    """
    Get an AVM module by service name or alias.

    Args:
        service_name: The name or alias of the service

    Returns:
        The AVM module if found, None otherwise
    """
    service_lower = service_name.lower().replace(" ", "_").replace("-", "_")

    # Direct match
    if service_lower in AVM_MODULES:
        return AVM_MODULES[service_lower]

    # Search by alias
    for module in AVM_MODULES.values():
        if service_lower in [alias.lower().replace("-", "_") for alias in module.aliases]:
            return module

    # Partial match
    for key, module in AVM_MODULES.items():
        if service_lower in key or key in service_lower:
            return module
        for alias in module.aliases:
            alias_normalized = alias.lower().replace("-", "_")
            if service_lower in alias_normalized or alias_normalized in service_lower:
                return module

    return None


def get_modules_by_category(category: str) -> list[AVMModule]:
    """
    Get all AVM modules in a specific category.

    Args:
        category: The category name (compute, networking, storage, database, security, messaging, monitoring, ai)

    Returns:
        List of AVM modules in the category
    """
    return [module for module in AVM_MODULES.values() if module.category == category.lower()]


def get_all_categories() -> list[str]:
    """Get all available categories."""
    return list(set(module.category for module in AVM_MODULES.values()))


def search_modules(query: str) -> list[AVMModule]:
    """
    Search for AVM modules matching a query.

    Args:
        query: Search query string

    Returns:
        List of matching AVM modules
    """
    query_lower = query.lower()
    results = []

    for module in AVM_MODULES.values():
        # Check name, description, aliases
        if (
            query_lower in module.name.lower()
            or query_lower in module.description.lower()
            or any(query_lower in alias.lower() for alias in module.aliases)
            or query_lower in module.azure_service.lower()
        ):
            results.append(module)

    return results


def sync_modules_from_registry() -> dict[str, AVMModule]:
    """
    Synchronize modules from the Terraform Registry.

    This function discovers all AVM modules from the registry and merges
    them with the static registry. Registry entries take precedence for
    version information while static entries provide detailed variable/output info.

    Returns:
        Updated AVM_MODULES dictionary
    """
    from tf_avm_agent.registry.module_discovery import (
        fetch_published_modules_sync,
        generate_azure_service,
    )
    from tf_avm_agent.registry.published_modules import PUBLISHED_AVM_MODULES

    logger.info("Fetching all published AVM modules...")
    discovered = fetch_published_modules_sync()
    logger.info(f"Fetched {len(discovered)} published AVM modules")

    # Build a map of registry_name -> existing module for reference
    existing_by_registry_name: dict[str, tuple[str, AVMModule]] = {}
    for key, module in list(AVM_MODULES.items()):
        reg_name = module.registry_name
        if reg_name not in existing_by_registry_name:
            existing_by_registry_name[reg_name] = (key, module)

    # Create a lookup for published module info
    published_info = {m["name"]: m for m in PUBLISHED_AVM_MODULES}

    # Update or add modules from published list
    for mod in discovered:
        reg_name = mod.name  # This is already the registry name like "avm-res-compute-virtualmachine"
        info = published_info.get(reg_name, {})
        category = info.get("category", "other")

        if reg_name in existing_by_registry_name:
            # Update existing module's version if registry has newer
            key, existing = existing_by_registry_name[reg_name]
            if mod.version != "latest" and mod.version > existing.version:
                existing.version = mod.version
            # Update category from authoritative source
            existing.category = category
        else:
            # Add new module using registry name as the key
            key = reg_name
            AVM_MODULES[key] = AVMModule(
                name=reg_name,
                source=mod.source,
                version=mod.version if mod.version != "latest" else "0.1.0",
                description=info.get("display", mod.description) or f"Azure Verified Module for {reg_name}",
                category=category,
                azure_service=generate_azure_service(mod.name),
                aliases=[mod.name.replace("avm-res-", "")],
            )
            existing_by_registry_name[reg_name] = (key, AVM_MODULES[key])

    return AVM_MODULES


def get_all_modules(include_discovered: bool = True) -> dict[str, AVMModule]:
    """
    Get all available modules, optionally including dynamically discovered ones.

    Args:
        include_discovered: Whether to include modules discovered from registry

    Returns:
        Dictionary of all modules
    """
    if include_discovered:
        try:
            sync_modules_from_registry()
        except Exception as e:
            logger.warning(f"Failed to sync modules from registry: {e}")

    return AVM_MODULES
