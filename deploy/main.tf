terraform {
  required_version = ">= 1.9"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"
    }
  }

  # Uncomment and configure to store state in Azure Blob Storage
  # backend "azurerm" {
  #   resource_group_name  = "rg-tfstate"
  #   storage_account_name = "stterraformstate"
  #   container_name       = "tfstate"
  #   key                  = "tf-avm-agent-web.tfstate"
  # }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

# ── Locals ───────────────────────────────────────────────────────────────────

locals {
  resource_prefix = "${var.app_name}-${var.environment}"

  default_tags = {
    application = var.app_name
    environment = var.environment
    managed_by  = "terraform"
  }

  tags = merge(local.default_tags, var.tags)
}

# ── Resource Group ────────────────────────────────────────────────────────────

module "resource-group" {
  source  = "Azure/avm-res-resources-resourcegroup/azurerm"
  version = "~> 0.2"

  name     = "rg-${local.resource_prefix}"
  location = var.location
  tags     = local.tags
}

# ── Log Analytics Workspace (required by Container Apps Environment) ──────────

module "log-analytics-workspace" {
  source  = "Azure/avm-res-operationalinsights-workspace/azurerm"
  version = "~> 0.4"

  name                = "log-${local.resource_prefix}"
  resource_group_name = module.resource-group.name
  location            = var.location
  tags                = local.tags

  depends_on = [module.resource-group]
}

# ── Container Registry ────────────────────────────────────────────────────────

module "container-registry" {
  source  = "Azure/avm-res-containerregistry-registry/azurerm"
  version = "~> 0.4"

  name                = "cr${replace(local.resource_prefix, "-", "")}web"
  resource_group_name = module.resource-group.name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags

  depends_on = [module.resource-group]
}

# ── Container Apps Environment ────────────────────────────────────────────────

module "container-apps-environment" {
  source  = "Azure/avm-res-app-managedenvironment/azurerm"
  version = "~> 0.1"

  name                       = "cae-${local.resource_prefix}"
  resource_group_name        = module.resource-group.name
  location                   = var.location
  log_analytics_workspace_id = module.log-analytics-workspace.resource_id
  tags                       = local.tags

  depends_on = [module.resource-group, module.log-analytics-workspace]
}

# ── Container App – Web frontend ──────────────────────────────────────────────

module "container-app-web" {
  source  = "Azure/avm-res-app-containerapp/azurerm"
  version = "~> 0.4"

  name                         = "ca-${local.resource_prefix}-web"
  resource_group_name          = module.resource-group.name
  container_app_environment_id = module.container-apps-environment.resource_id
  revision_mode                = "Single"
  tags                         = local.tags

  template = {
    containers = [
      {
        name   = "web"
        image  = "${module.container-registry.login_server}/${var.image_name}:${var.image_tag}"
        cpu    = var.container_cpu
        memory = var.container_memory

        env = [
          {
            name  = "BACKEND_URL"
            value = var.backend_url
          }
        ]
      }
    ]

    min_replicas = var.min_replicas
    max_replicas = var.max_replicas
  }

  ingress = {
    external_enabled = true
    target_port      = 80
    transport        = "http"

    traffic_weight = [
      {
        latest_revision = true
        percentage      = 100
      }
    ]
  }

  registries = [
    {
      server               = module.container-registry.login_server
      identity             = "system"
    }
  ]

  identity = {
    type = "SystemAssigned"
  }

  depends_on = [module.container-apps-environment, module.container-registry]
}

# ── ACR pull role assignment for the Container App identity ───────────────────

resource "azurerm_role_assignment" "acr_pull" {
  scope                = module.container-registry.resource_id
  role_definition_name = "AcrPull"
  principal_id         = module.container-app-web.system_assigned_mi_principal_id
}
