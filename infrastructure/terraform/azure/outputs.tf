# RT Sentiment Analysis - Azure Terraform Outputs

# Resource Group
output "resource_group_name" {
  value = azurerm_resource_group.rg.name
  description = "The name of the resource group"
}

output "resource_group_id" {
  value = azurerm_resource_group.rg.id
  description = "The ID of the resource group"
}

# AKS
output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
  description = "The name of the AKS cluster"
}

output "aks_cluster_id" {
  value = azurerm_kubernetes_cluster.aks.id
  description = "The ID of the AKS cluster"
}

output "kube_config" {
  value     = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive = true
  description = "The kube config for the AKS cluster (sensitive)"
}

output "kube_host" {
  value     = azurerm_kubernetes_cluster.aks.kube_config[0].host
  sensitive = true
  description = "The Kubernetes cluster API server URL (sensitive)"
}

# Container Registry
output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
  description = "The login server for the Azure Container Registry"
}

output "acr_admin_username" {
  value     = azurerm_container_registry.acr.admin_username
  sensitive = true
  description = "The admin username for the Azure Container Registry (sensitive)"
}

output "acr_admin_password" {
  value     = azurerm_container_registry.acr.admin_password
  sensitive = true
  description = "The admin password for the Azure Container Registry (sensitive)"
}

# Proximity Placement Group
output "ppg_id" {
  value = azurerm_proximity_placement_group.ppg.id
  description = "The ID of the Proximity Placement Group"
}

# Storage Account
output "storage_account_name" {
  value = azurerm_storage_account.storage.name
  description = "The name of the Storage Account"
}

output "storage_account_primary_key" {
  value     = azurerm_storage_account.storage.primary_access_key
  sensitive = true
  description = "The primary access key for the Storage Account (sensitive)"
}

# Front Door
output "front_door_endpoint" {
  value = "https://${var.front_door_name}.azurefd.net"
  description = "The endpoint for Azure Front Door"
}

# Application Insights
output "app_insights_instrumentation_key" {
  value     = azurerm_application_insights.insights.instrumentation_key
  sensitive = true
  description = "The instrumentation key for Application Insights (sensitive)"
}

output "app_insights_connection_string" {
  value     = azurerm_application_insights.insights.connection_string
  sensitive = true
  description = "The connection string for Application Insights (sensitive)"
}

# Log Analytics
output "log_analytics_workspace_id" {
  value = azurerm_log_analytics_workspace.workspace.id
  description = "The ID of the Log Analytics workspace"
}