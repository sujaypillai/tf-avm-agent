terraform {
  required_version = ">= 1.11"

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
  backend "azurerm" {
    # Backend config provided via -backend-config flags or backend config file
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

provider "azapi" {
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
  version = "~> 0.5"

  name                = "log-${local.resource_prefix}"
  resource_group_name = module.resource-group.name
  location            = var.location
  tags                = local.tags

  depends_on = [module.resource-group]
}

# ── Container Registry ────────────────────────────────────────────────────────

module "container-registry" {
  source  = "Azure/avm-res-containerregistry-registry/azurerm"
  version = "~> 0.5"

  name                    = "cr${replace(local.resource_prefix, "-", "")}web"
  resource_group_name     = module.resource-group.name
  location                = var.location
  sku                     = "Basic"
  admin_enabled           = false
  zone_redundancy_enabled = false
  tags                    = local.tags

  depends_on = [module.resource-group]
}

# ── Container Apps Environment ────────────────────────────────────────────────

module "container-apps-environment" {
  source  = "Azure/avm-res-app-managedenvironment/azurerm"
  version = "~> 0.4"

  name                = "cae-${local.resource_prefix}"
  resource_group_name = module.resource-group.name
  location            = var.location
  tags                = local.tags

  log_analytics_workspace = {
    resource_id = module.log-analytics-workspace.resource.id
  }

  zone_redundancy_enabled = false

  depends_on = [module.resource-group, module.log-analytics-workspace]
}

# ── User-assigned MI for ACR pull (breaks chicken-and-egg with system MI) ─────

resource "azurerm_user_assigned_identity" "acr_pull" {
  name                = "id-${local.resource_prefix}-acrpull"
  resource_group_name = module.resource-group.name
  location            = var.location
  tags                = local.tags
}

resource "azurerm_role_assignment" "acr_pull_uami" {
  scope                = module.container-registry.resource_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.acr_pull.principal_id
}

# ── Container App – Web frontend ──────────────────────────────────────────────

module "container-app-web" {
  source  = "Azure/avm-res-app-containerapp/azurerm"
  version = "0.7.4"

  name                                  = "ca-${local.resource_prefix}-web"
  resource_group_name                   = module.resource-group.name
  container_app_environment_resource_id = module.container-apps-environment.resource_id
  revision_mode                         = "Single"
  tags                                  = local.tags

  template = {
    containers = [
      {
        name   = "web"
        image  = "${module.container-registry.resource.login_server}/${var.image_name}:${var.image_tag}"
        cpu    = var.container_cpu
        memory = var.container_memory

        env = [
          {
            name  = "BACKEND_URL"
            value = trimprefix(module.container-app-api.fqdn_url, "https://")
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
      server   = module.container-registry.resource.login_server
      identity = azurerm_user_assigned_identity.acr_pull.id
    }
  ]

  managed_identities = {
    system_assigned            = true
    user_assigned_resource_ids = [azurerm_user_assigned_identity.acr_pull.id]
  }

  depends_on = [module.container-apps-environment, module.container-registry, module.container-app-api, azurerm_role_assignment.acr_pull_uami]
}

# ── Azure OpenAI (Cognitive Services) ─────────────────────────────────────────

module "openai" {
  source  = "Azure/avm-res-cognitiveservices-account/azurerm"
  version = "~> 0.11"

  name                  = "oai-${local.resource_prefix}"
  location              = var.location
  parent_id             = module.resource-group.resource_id
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "oai-${local.resource_prefix}"
  tags                  = local.tags

  local_auth_enabled = false # Use managed identity (Entra ID) only

  cognitive_deployments = {
    "gpt-4o" = {
      name = var.openai_deployment_name
      model = {
        format  = "OpenAI"
        name    = var.openai_model_name
        version = var.openai_model_version
      }
      scale = {
        type     = "Standard"
        capacity = var.openai_capacity
      }
    }
  }

  depends_on = [module.resource-group]
}

# ── OpenAI RBAC for API Container App ─────────────────────────────────────────

resource "azurerm_role_assignment" "api_openai_user" {
  scope                = module.openai.resource_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = module.container-app-api.identity[0].principal_id
}

# ── Container App – MCP Backend API ──────────────────────────────────────────

module "container-app-api" {
  source  = "Azure/avm-res-app-containerapp/azurerm"
  version = "0.7.4"

  name                                  = "ca-${local.resource_prefix}-api"
  resource_group_name                   = module.resource-group.name
  container_app_environment_resource_id = module.container-apps-environment.resource_id
  revision_mode                         = "Single"
  tags                                  = local.tags

  template = {
    containers = [
      {
        name   = "api"
        image  = "${module.container-registry.resource.login_server}/${var.api_image_name}:${var.image_tag}"
        cpu    = var.api_container_cpu
        memory = var.api_container_memory

        env = [
          {
            name  = "AZURE_OPENAI_ENDPOINT"
            value = module.openai.endpoint
          },
          {
            name  = "AZURE_OPENAI_DEPLOYMENT"
            value = var.openai_deployment_name
          }
        ]
      }
    ]

    min_replicas = var.min_replicas
    max_replicas = var.max_replicas
  }

  ingress = {
    external_enabled = false # Internal only — web frontend + future APIM
    target_port      = 8000
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
      server   = module.container-registry.resource.login_server
      identity = azurerm_user_assigned_identity.acr_pull.id
    }
  ]

  managed_identities = {
    system_assigned            = true
    user_assigned_resource_ids = [azurerm_user_assigned_identity.acr_pull.id]
  }

  depends_on = [module.container-apps-environment, module.container-registry, module.openai, azurerm_role_assignment.acr_pull_uami]
}
