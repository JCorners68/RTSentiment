/**
 * # Terraform State Locking Module
 * 
 * This module provides robust Azure Storage-based state locking for Terraform.
 * It configures and manages resources needed for secure state storage with proper locking,
 * helping prevent concurrent modification issues and corruption.
 */

locals {
  storage_account_name = lower(var.storage_account_name != "" ? var.storage_account_name : "${var.prefix}${var.environment}tf")
  resource_group_name  = var.resource_group_name != "" ? var.resource_group_name : "${var.prefix}-${var.environment}-rg"
  container_name       = var.container_name != "" ? var.container_name : "tfstate"
  location             = var.location
  tags = merge({
    environment = var.environment
    managed_by  = "terraform"
    module      = "state-locking"
  }, var.tags)
}

resource "azurerm_resource_group" "tf_state" {
  count    = var.create_resource_group ? 1 : 0
  name     = local.resource_group_name
  location = local.location
  tags     = local.tags
}

resource "azurerm_storage_account" "tf_state" {
  count                     = var.create_storage_account ? 1 : 0
  name                      = local.storage_account_name
  resource_group_name       = var.create_resource_group ? azurerm_resource_group.tf_state[0].name : local.resource_group_name
  location                  = local.location
  account_tier              = "Standard"
  account_replication_type  = var.storage_account_replication_type
  enable_https_traffic_only = true
  min_tls_version           = "TLS1_2"
  allow_blob_public_access  = false
  tags                      = local.tags

  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = var.blob_soft_delete_retention_days
    }
    container_delete_retention_policy {
      days = var.container_delete_retention_days
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}

resource "azurerm_storage_container" "tf_state_container" {
  count                 = var.create_storage_container ? 1 : 0
  name                  = local.container_name
  storage_account_name  = var.create_storage_account ? azurerm_storage_account.tf_state[0].name : local.storage_account_name
  container_access_type = "private"
}

# Resource lock to prevent accidental deletion
resource "azurerm_management_lock" "tf_state_lock" {
  count      = var.create_resource_lock && var.create_storage_account ? 1 : 0
  name       = "terraform-state-lock"
  scope      = azurerm_storage_account.tf_state[0].id
  lock_level = "CanNotDelete"
  notes      = "This lock prevents accidental deletion of the Terraform state storage account."
}

# Set up role assignments for the service principal
resource "azurerm_role_assignment" "tf_state_contributor" {
  count                = var.service_principal_id != "" && var.create_storage_account ? 1 : 0
  scope                = azurerm_storage_account.tf_state[0].id
  role_definition_name = "Storage Account Contributor"
  principal_id         = var.service_principal_id

  # Add a slight delay to allow Azure to propagate the role assignment
  provisioner "local-exec" {
    command = "sleep 30"
  }
}

resource "azurerm_role_assignment" "tf_state_data_owner" {
  count                = var.service_principal_id != "" && var.create_storage_account ? 1 : 0
  scope                = azurerm_storage_account.tf_state[0].id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = var.service_principal_id
  
  # Add a slight delay to allow Azure to propagate the role assignment
  provisioner "local-exec" {
    command = "sleep 30"
  }

  depends_on = [
    azurerm_role_assignment.tf_state_contributor
  ]
}

# Generate the backend configuration file
resource "local_file" "backend_config" {
  count    = var.generate_backend_config ? 1 : 0
  filename = "${var.backend_config_path}/${var.environment}.tfbackend"
  content  = <<-EOT
resource_group_name  = "${local.resource_group_name}"
storage_account_name = "${local.storage_account_name}"
container_name       = "${local.container_name}"
key                  = "${var.environment}.terraform.tfstate"
use_azuread_auth     = true
EOT
}