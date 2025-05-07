# Sentimark - Azure Monitoring Module Outputs

output "log_analytics_workspace_id" {
  description = "ID of the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.iceberg_monitoring.id
}

output "log_analytics_workspace_name" {
  description = "Name of the Log Analytics workspace"
  value       = azurerm_log_analytics_workspace.iceberg_monitoring.name
}

output "app_insights_id" {
  description = "ID of the Application Insights instance"
  value       = azurerm_application_insights.data_tier.id
}

output "app_insights_app_id" {
  description = "App ID of the Application Insights instance"
  value       = azurerm_application_insights.data_tier.app_id
}

output "app_insights_instrumentation_key" {
  description = "Instrumentation key of the Application Insights instance"
  value       = azurerm_application_insights.data_tier.instrumentation_key
  sensitive   = true
}

output "app_insights_connection_string" {
  description = "Connection string of the Application Insights instance"
  value       = azurerm_application_insights.data_tier.connection_string
  sensitive   = true
}

output "dashboard_id" {
  description = "ID of the Iceberg monitoring dashboard"
  value       = azurerm_portal_dashboard.iceberg_dashboard.id
}

output "action_group_id" {
  description = "ID of the Iceberg alerts action group"
  value       = azurerm_monitor_action_group.iceberg_alerts.id
}

output "logs_storage_account_id" {
  description = "ID of the storage account for logs retention"
  value       = var.log_retention_days > 0 ? azurerm_storage_account.logs[0].id : null
}

output "logs_storage_account_name" {
  description = "Name of the storage account for logs retention"
  value       = var.log_retention_days > 0 ? azurerm_storage_account.logs[0].name : null
}