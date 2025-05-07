# Sentimark - Iceberg on Azure Module Outputs

output "storage_account_id" {
  description = "ID of the Iceberg storage account"
  value       = azurerm_storage_account.iceberg_storage.id
}

output "storage_account_name" {
  description = "Name of the Iceberg storage account"
  value       = azurerm_storage_account.iceberg_storage.name
}

output "storage_account_primary_key" {
  description = "Primary access key for the Iceberg storage account"
  value       = azurerm_storage_account.iceberg_storage.primary_access_key
  sensitive   = true
}

output "storage_account_primary_connection_string" {
  description = "Primary connection string for the Iceberg storage account"
  value       = azurerm_storage_account.iceberg_storage.primary_connection_string
  sensitive   = true
}

output "dfs_endpoint" {
  description = "Data Lake Storage endpoint"
  value       = azurerm_storage_account.iceberg_storage.primary_dfs_endpoint
}

output "warehouse_filesystem_name" {
  description = "Name of the Iceberg warehouse filesystem"
  value       = "warehouse"
}

output "metadata_filesystem_name" {
  description = "Name of the Iceberg metadata filesystem"
  value       = "metadata"
}

output "iceberg_identity_id" {
  description = "ID of the user-assigned identity for Iceberg"
  value       = azurerm_user_assigned_identity.iceberg_identity.id
}

output "iceberg_identity_principal_id" {
  description = "Principal ID of the user-assigned identity for Iceberg"
  value       = azurerm_user_assigned_identity.iceberg_identity.principal_id
}

output "iceberg_identity_client_id" {
  description = "Client ID of the user-assigned identity for Iceberg"
  value       = azurerm_user_assigned_identity.iceberg_identity.client_id
}

output "key_vault_id" {
  description = "ID of the Key Vault for Iceberg credentials"
  value       = azurerm_key_vault.iceberg_vault.id
}

output "rest_catalog_name" {
  description = "Name of the Iceberg REST catalog service"
  value       = var.deploy_container && length(azurerm_container_group.iceberg_rest_catalog) > 0 ? azurerm_container_group.iceberg_rest_catalog[0].name : "${var.base_name}-iceberg-rest-catalog"
}

output "rest_catalog_ip" {
  description = "IP address of the Iceberg REST catalog service (if deployed)"
  value       = var.deploy_container && length(azurerm_container_group.iceberg_rest_catalog) > 0 ? azurerm_container_group.iceberg_rest_catalog[0].ip_address : null
}