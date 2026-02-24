output "resource_group_name" {
  description = "Name of the resource group that contains all deployment resources."
  value       = module.resource-group.name
}

output "container_registry_login_server" {
  description = "Login server URL for the Azure Container Registry."
  value       = module.container-registry.login_server
}

output "container_app_fqdn" {
  description = "Fully-qualified domain name of the web Container App (public HTTPS URL)."
  value       = "https://${module.container-app-web.fqdn}"
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
  description = "Principal ID of the system-assigned managed identity for the web Container App (used for ACR pull)."
  value       = module.container-app-web.system_assigned_mi_principal_id
}
