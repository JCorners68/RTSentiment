# Sentimark - Azure App Configuration Module
# This module sets up Azure App Configuration for feature flags

# Azure App Configuration instance
resource "azurerm_app_configuration" "feature_flags" {
  name                = var.app_config_name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "standard"
  
  identity {
    type = "SystemAssigned"
  }
  
  tags = var.tags
}

# Add role assignment for the terraform service principal
resource "azurerm_role_assignment" "app_config_terraform_sp" {
  scope                = azurerm_app_configuration.feature_flags.id
  role_definition_name = "App Configuration Data Owner"
  principal_id         = "5c765214-89b0-4a9b-9e8f-ff6e763d1828" # Service Principal Object ID
}

# Create role assignment first and add a longer delay before adding keys
resource "time_sleep" "wait_for_rbac_propagation" {
  depends_on      = [
    azurerm_role_assignment.app_config_data_reader,
    azurerm_role_assignment.app_config_terraform_sp
  ]
  create_duration = "300s"  # 5 minutes for RBAC propagation - increased from 3 minutes
}

# Feature flags configuration using for_each to avoid concurrent RBAC issues
locals {
  feature_flags = {
    "feature.use-iceberg-backend" = {
      label = "production"
      value = var.enable_iceberg_backend ? "true" : "false"
      type  = "kv"
    },
    "feature.use-iceberg-optimizations" = {
      label = "production"
      value = var.enable_iceberg_optimizations ? "true" : "false"
      type  = "kv"
    },
    "feature.use-iceberg-partitioning" = {
      label = "production"
      value = var.enable_iceberg_partitioning ? "true" : "false"
      type  = "kv"
    },
    "feature.use-iceberg-time-travel" = {
      label = "production"
      value = var.enable_iceberg_time_travel ? "true" : "false"
      type  = "kv"
    },
    "deployment.iceberg-roll-percentage" = {
      label = "production"
      value = tostring(var.iceberg_roll_percentage)
      type  = "kv"
    }
  }
}

# Create feature flags one by one to avoid RBAC race conditions
resource "azurerm_app_configuration_key" "feature_flags" {
  for_each = local.feature_flags

  configuration_store_id = azurerm_app_configuration.feature_flags.id
  key                    = each.key
  label                  = each.value.label
  value                  = each.value.value
  type                   = each.value.type
  
  # Add short delay between creating each key and depend on RBAC propagation
  depends_on = [time_sleep.wait_for_rbac_propagation]
  
  # Use local-exec to add a small delay between creating each key
  # This helps avoid rate limiting and concurrent RBAC issues
  provisioner "local-exec" {
    command = "sleep 10"
  }
}

# Create role assignment for App Configuration Data Reader
resource "azurerm_role_assignment" "app_config_data_reader" {
  scope                = azurerm_app_configuration.feature_flags.id
  role_definition_name = "App Configuration Data Reader"
  principal_id         = var.service_principal_id
  
  depends_on = [azurerm_app_configuration.feature_flags]
}

# Create monitor alert for feature flag changes
resource "azurerm_monitor_activity_log_alert" "feature_flag_changes" {
  name                = "feature-flag-changes-alert"
  resource_group_name = var.resource_group_name
  location            = "global"  # Activity Log Alerts must use global location (not region specific)
  scopes              = [azurerm_app_configuration.feature_flags.id]
  description         = "Alert when feature flags are changed"
  
  criteria {
    operation_name = "Microsoft.AppConfiguration/configurationStores/write"
    category       = "Administrative"
  }
  
  action {
    action_group_id = var.alert_action_group_id
  }
  
  tags = var.tags
}