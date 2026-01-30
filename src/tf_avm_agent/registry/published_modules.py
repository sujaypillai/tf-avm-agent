"""
Official AVM Published Modules List.

This file contains the authoritative list of all published Azure Verified Modules
from https://azure.github.io/Azure-Verified-Modules/indexes/terraform/tf-resource-modules/
"""

# Complete list of 105 published AVM resource modules as of January 2026
# Source: https://azure.github.io/Azure-Verified-Modules/indexes/terraform/tf-resource-modules/

PUBLISHED_AVM_MODULES = [
    {"name": "avm-res-apimanagement-service", "display": "API Management Service", "category": "integration"},
    {"name": "avm-res-app-containerapp", "display": "Container App", "category": "containers"},
    {"name": "avm-res-app-job", "display": "App Job", "category": "containers"},
    {"name": "avm-res-app-managedenvironment", "display": "App Managed Environment", "category": "containers"},
    {"name": "avm-res-appconfiguration-configurationstore", "display": "App Configuration Store", "category": "integration"},
    {"name": "avm-res-authorization-roleassignment", "display": "Role Assignment", "category": "security"},
    {"name": "avm-res-automation-automationaccount", "display": "Automation Account", "category": "management"},
    {"name": "avm-res-avs-privatecloud", "display": "AVS Private Cloud", "category": "hybrid"},
    {"name": "avm-res-azurestackhci-cluster", "display": "Azure Stack HCI Cluster", "category": "hybrid"},
    {"name": "avm-res-azurestackhci-logicalnetwork", "display": "AzureStackHCI Logical Network", "category": "hybrid"},
    {"name": "avm-res-azurestackhci-virtualmachineinstance", "display": "Stack HCI Virtual Machine Instance", "category": "hybrid"},
    {"name": "avm-res-batch-batchaccount", "display": "Batch Account", "category": "compute"},
    {"name": "avm-res-cache-redis", "display": "Redis Cache", "category": "database"},
    {"name": "avm-res-cdn-profile", "display": "CDN Profile", "category": "networking"},
    {"name": "avm-res-certificateregistration-certificateorder", "display": "Certificate Orders", "category": "security"},
    {"name": "avm-res-cognitiveservices-account", "display": "Cognitive Service", "category": "ai"},
    {"name": "avm-res-communication-emailservice", "display": "Email Communication Service", "category": "messaging"},
    {"name": "avm-res-compute-capacityreservationgroup", "display": "Capacity Reservation Group", "category": "compute"},
    {"name": "avm-res-compute-disk", "display": "Compute Disk", "category": "compute"},
    {"name": "avm-res-compute-diskencryptionset", "display": "Disk Encryption Set", "category": "compute"},
    {"name": "avm-res-compute-gallery", "display": "Azure Compute Gallery", "category": "compute"},
    {"name": "avm-res-compute-hostgroup", "display": "Host Groups", "category": "compute"},
    {"name": "avm-res-compute-proximityplacementgroup", "display": "Proximity Placement Group", "category": "compute"},
    {"name": "avm-res-compute-sshpublickey", "display": "Public SSH Key", "category": "compute"},
    {"name": "avm-res-compute-virtualmachine", "display": "Virtual Machine", "category": "compute"},
    {"name": "avm-res-compute-virtualmachinescaleset", "display": "Virtual Machine Scale Set", "category": "compute"},
    {"name": "avm-res-containerinstance-containergroup", "display": "Container Instance", "category": "containers"},
    {"name": "avm-res-containerregistry-registry", "display": "Azure Container Registry (ACR)", "category": "containers"},
    {"name": "avm-res-containerservice-managedcluster", "display": "AKS Managed Cluster", "category": "containers"},
    {"name": "avm-res-databricks-workspace", "display": "Azure Databricks Workspace", "category": "analytics"},
    {"name": "avm-res-datafactory-factory", "display": "Data Factory", "category": "analytics"},
    {"name": "avm-res-dataprotection-backupvault", "display": "Data Protection Backup Vault", "category": "management"},
    {"name": "avm-res-dataprotection-resourceguard", "display": "Data Protection Resource Guard", "category": "management"},
    {"name": "avm-res-dbformysql-flexibleserver", "display": "DB for MySQL Flexible Server", "category": "database"},
    {"name": "avm-res-dbforpostgresql-flexibleserver", "display": "DB for PostgreSQL Flexible Server", "category": "database"},
    {"name": "avm-res-desktopvirtualization-applicationgroup", "display": "Azure Virtual Desktop (AVD) Application Group", "category": "avd"},
    {"name": "avm-res-desktopvirtualization-hostpool", "display": "Azure Virtual Desktop (AVD) Host Pool", "category": "avd"},
    {"name": "avm-res-desktopvirtualization-scalingplan", "display": "Azure Virtual Desktop (AVD) Scaling Plan", "category": "avd"},
    {"name": "avm-res-desktopvirtualization-workspace", "display": "Azure Virtual Desktop (AVD) Workspace", "category": "avd"},
    {"name": "avm-res-devcenter-devcenter", "display": "Dev Center", "category": "developer"},
    {"name": "avm-res-devopsinfrastructure-pool", "display": "DevOps Pools", "category": "developer"},
    {"name": "avm-res-documentdb-databaseaccount", "display": "CosmosDB Database Account", "category": "database"},
    {"name": "avm-res-documentdb-mongocluster", "display": "Cosmos DB for MongoDB (vCore)", "category": "database"},
    {"name": "avm-res-edge-site", "display": "Azure Arc Site Manager", "category": "hybrid"},
    {"name": "avm-res-eventgrid-domain", "display": "Event Grid Domain", "category": "messaging"},
    {"name": "avm-res-eventgrid-topic", "display": "Event Grid Topic", "category": "messaging"},
    {"name": "avm-res-eventhub-namespace", "display": "Event Hub Namespace", "category": "messaging"},
    {"name": "avm-res-features-feature", "display": "Azure Feature Exposure Control (AFEC)", "category": "management"},
    {"name": "avm-res-hybridcontainerservice-provisionedclusterinstance", "display": "AKS Arc", "category": "hybrid"},
    {"name": "avm-res-insights-autoscalesetting", "display": "Auto Scale Settings", "category": "monitoring"},
    {"name": "avm-res-insights-component", "display": "Application Insight", "category": "monitoring"},
    {"name": "avm-res-insights-datacollectionendpoint", "display": "Data Collection Endpoint", "category": "monitoring"},
    {"name": "avm-res-keyvault-vault", "display": "Key Vault", "category": "security"},
    {"name": "avm-res-kusto-cluster", "display": "Kusto Clusters", "category": "analytics"},
    {"name": "avm-res-logic-workflow", "display": "Logic Apps (Workflow)", "category": "integration"},
    {"name": "avm-res-machinelearningservices-workspace", "display": "Machine Learning Services Workspace", "category": "ai"},
    {"name": "avm-res-maintenance-maintenanceconfiguration", "display": "Maintenance Configuration", "category": "management"},
    {"name": "avm-res-managedidentity-userassignedidentity", "display": "User Assigned Identity", "category": "security"},
    {"name": "avm-res-management-servicegroup", "display": "Management Service Groups", "category": "management"},
    {"name": "avm-res-netapp-netappaccount", "display": "Azure NetApp File", "category": "storage"},
    {"name": "avm-res-network-applicationgateway", "display": "Application Gateway", "category": "networking"},
    {"name": "avm-res-network-applicationgatewaywebapplicationfirewallpolicy", "display": "Application Gateway WAF Policy", "category": "networking"},
    {"name": "avm-res-network-applicationsecuritygroup", "display": "Application Security Group (ASG)", "category": "networking"},
    {"name": "avm-res-network-azurefirewall", "display": "Azure Firewall", "category": "networking"},
    {"name": "avm-res-network-bastionhost", "display": "Bastion Host", "category": "networking"},
    {"name": "avm-res-network-connection", "display": "Virtual Network Gateway Connection", "category": "networking"},
    {"name": "avm-res-network-ddosprotectionplan", "display": "DDoS Protection", "category": "networking"},
    {"name": "avm-res-network-dnsresolver", "display": "DNS Resolver", "category": "networking"},
    {"name": "avm-res-network-dnszone", "display": "Public DNS Zone", "category": "networking"},
    {"name": "avm-res-network-expressroutecircuit", "display": "ExpressRoute Circuit", "category": "networking"},
    {"name": "avm-res-network-firewallpolicy", "display": "Azure Firewall Policy", "category": "networking"},
    {"name": "avm-res-network-frontdoorwebapplicationfirewallpolicy", "display": "Front Door WAF Policy", "category": "networking"},
    {"name": "avm-res-network-ipgroup", "display": "IP Group", "category": "networking"},
    {"name": "avm-res-network-loadbalancer", "display": "Loadbalancer", "category": "networking"},
    {"name": "avm-res-network-localnetworkgateway", "display": "Local Network Gateway", "category": "networking"},
    {"name": "avm-res-network-natgateway", "display": "NAT Gateway", "category": "networking"},
    {"name": "avm-res-network-networkinterface", "display": "Network Interface", "category": "networking"},
    {"name": "avm-res-network-networkmanager", "display": "Azure Virtual Network Manager", "category": "networking"},
    {"name": "avm-res-network-networksecuritygroup", "display": "Network Security Group", "category": "networking"},
    {"name": "avm-res-network-networkwatcher", "display": "Azure Network Watcher", "category": "networking"},
    {"name": "avm-res-network-privatednszone", "display": "Private DNS Zone", "category": "networking"},
    {"name": "avm-res-network-privateendpoint", "display": "Private Endpoint", "category": "networking"},
    {"name": "avm-res-network-publicipaddress", "display": "Public IP Address", "category": "networking"},
    {"name": "avm-res-network-publicipprefix", "display": "Public IP Prefix", "category": "networking"},
    {"name": "avm-res-network-routetable", "display": "Route Table", "category": "networking"},
    {"name": "avm-res-network-virtualnetwork", "display": "Virtual Network", "category": "networking"},
    {"name": "avm-res-operationalinsights-workspace", "display": "Log Analytics Workspace", "category": "monitoring"},
    {"name": "avm-res-oracledatabase-cloudexadatainfrastructure", "display": "Oracle Exadata Infrastructure", "category": "database"},
    {"name": "avm-res-oracledatabase-cloudvmcluster", "display": "Oracle VM Cluster", "category": "database"},
    {"name": "avm-res-portal-dashboard", "display": "Azure Portal Dashboard", "category": "management"},
    {"name": "avm-res-recoveryservices-vault", "display": "Recovery Services Vault", "category": "management"},
    {"name": "avm-res-redhatopenshift-openshiftcluster", "display": "OpenShift Cluster", "category": "containers"},
    {"name": "avm-res-relay-namespace", "display": "Relay Namespace", "category": "messaging"},
    {"name": "avm-res-resourcegraph-query", "display": "Resource Graph Query", "category": "management"},
    {"name": "avm-res-resources-resourcegroup", "display": "Resource Group", "category": "management"},
    {"name": "avm-res-search-searchservice", "display": "Search Service", "category": "ai"},
    {"name": "avm-res-servicebus-namespace", "display": "Service Bus Namespace", "category": "messaging"},
    {"name": "avm-res-sql-managedinstance", "display": "SQL Managed Instance", "category": "database"},
    {"name": "avm-res-sql-server", "display": "Azure SQL Server", "category": "database"},
    {"name": "avm-res-storage-storageaccount", "display": "Storage Account", "category": "storage"},
    {"name": "avm-res-web-connection", "display": "API Connection", "category": "web"},
    {"name": "avm-res-web-hostingenvironment", "display": "App Service Environment", "category": "web"},
    {"name": "avm-res-web-serverfarm", "display": "App Service Plan", "category": "web"},
    {"name": "avm-res-web-site", "display": "Web/Function App", "category": "web"},
    {"name": "avm-res-web-staticsite", "display": "Static Web App", "category": "web"},
]


def get_published_module_names() -> list[str]:
    """Get list of all published AVM module names."""
    return [m["name"] for m in PUBLISHED_AVM_MODULES]


def get_published_modules_by_category() -> dict[str, list[dict]]:
    """Get published modules grouped by category."""
    by_category: dict[str, list[dict]] = {}
    for mod in PUBLISHED_AVM_MODULES:
        cat = mod["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(mod)
    return by_category
