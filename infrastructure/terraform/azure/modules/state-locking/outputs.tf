/**
 * # State Locking Module Outputs
 * 
 * This file defines the outputs from the Terraform state locking module.
 */

output "resource_group_name" {
  description = "Name of the resource group containing the state storage"
  value       = var.create_resource_group ? azurerm_resource_group.tf_state[0].name : local.resource_group_name
}

output "storage_account_name" {
  description = "Name of the storage account for state"
  value       = var.create_storage_account ? azurerm_storage_account.tf_state[0].name : local.storage_account_name
}

output "container_name" {
  description = "Name of the blob container for state"
  value       = var.create_storage_container ? azurerm_storage_container.tf_state_container[0].name : local.container_name
}

output "storage_account_id" {
  description = "ID of the storage account"
  value       = var.create_storage_account ? azurerm_storage_account.tf_state[0].id : null
}

output "backend_config_path" {
  description = "Path to the generated backend config file"
  value       = var.generate_backend_config ? "${var.backend_config_path}/${var.environment}.tfbackend" : null
}

output "backend_config_content" {
  description = "Content of the backend config file"
  value       = <<-EOT
resource_group_name  = "${local.resource_group_name}"
storage_account_name = "${local.storage_account_name}"
container_name       = "${local.container_name}"
key                  = "${var.environment}.terraform.tfstate"
use_azuread_auth     = true
EOT
}