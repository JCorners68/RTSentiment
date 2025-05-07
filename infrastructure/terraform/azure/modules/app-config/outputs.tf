# Sentimark - Azure App Configuration Module Outputs

output "app_config_id" {
  description = "ID of the Azure App Configuration instance"
  value       = azurerm_app_configuration.feature_flags.id
}

output "app_config_endpoint" {
  description = "Endpoint of the Azure App Configuration instance"
  value       = azurerm_app_configuration.feature_flags.endpoint
}

output "primary_read_key" {
  description = "Primary read key for the Azure App Configuration instance"
  value       = azurerm_app_configuration.feature_flags.primary_read_key
  sensitive   = true
}

output "secondary_read_key" {
  description = "Secondary read key for the Azure App Configuration instance"
  value       = azurerm_app_configuration.feature_flags.secondary_read_key
  sensitive   = true
}

output "identity_principal_id" {
  description = "Principal ID of the system-assigned identity"
  value       = azurerm_app_configuration.feature_flags.identity[0].principal_id
}

output "feature_flags" {
  description = "Map of configured feature flags and their values"
  value       = {
    use_iceberg_backend      = azurerm_app_configuration_key.feature_flags["feature.use-iceberg-backend"].value
    use_iceberg_optimizations = azurerm_app_configuration_key.feature_flags["feature.use-iceberg-optimizations"].value
    use_iceberg_partitioning = azurerm_app_configuration_key.feature_flags["feature.use-iceberg-partitioning"].value
    use_iceberg_time_travel  = azurerm_app_configuration_key.feature_flags["feature.use-iceberg-time-travel"].value
    iceberg_roll_percentage  = azurerm_app_configuration_key.feature_flags["deployment.iceberg-roll-percentage"].value
  }
}