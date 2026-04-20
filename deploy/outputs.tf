output "resource_group_name" {
  description = "Name of the resource group that contains all deployment resources."
  value       = module.resource-group.name
}

output "container_registry_login_server" {
  description = "Login server URL for the Azure Container Registry."
  value       = module.container-registry.resource.login_server
}

output "container_app_fqdn" {
  description = "Fully-qualified domain name of the web Container App (public HTTPS URL)."
  value       = module.container-app-web.fqdn_url
}

output "container_app_name" {
  description = "Name of the web Container App resource."
  value       = module.container-app-web.name
}

output "container_apps_environment_id" {
  description = "Resource ID of the Container Apps Environment."
  value       = module.container-apps-environment.resource_id
}

output "web_identity_principal_id" {
  description = "Principal ID of the system-assigned managed identity for the web Container App."
  value       = module.container-app-web.identity[0].principal_id
}

output "acr_pull_identity_id" {
  description = "Resource ID of the user-assigned managed identity used for ACR pull."
  value       = azurerm_user_assigned_identity.acr_pull.id
}

# ── API Container App ────────────────────────────────────────────────────────

output "api_container_app_fqdn" {
  description = "Fully-qualified domain name of the API Container App (internal)."
  value       = module.container-app-api.fqdn_url
}

output "api_container_app_name" {
  description = "Name of the API Container App resource."
  value       = module.container-app-api.name
}

output "api_identity_principal_id" {
  description = "Principal ID of the system-assigned managed identity for the API Container App."
  value       = module.container-app-api.identity[0].principal_id
}

# ── Azure OpenAI ─────────────────────────────────────────────────────────────

output "openai_endpoint" {
  description = "Endpoint URL for the Azure OpenAI service."
  value       = module.openai.endpoint
}

output "openai_resource_id" {
  description = "Resource ID of the Azure OpenAI (Cognitive Services) account."
  value       = module.openai.resource_id
}


