# Simplified Azure Cost Management with Built-in Policies
# This version uses only built-in policies and individual VM auto-shutdown settings

# Configure the Azure Provider with disabled resource provider registration
provider "azurerm" {
  features {}
  
  # Disable automatic resource provider registration to avoid the timeout error
  resource_provider_registrations = "none"
}

# Get current subscription data
data "azurerm_subscription" "current" {}

# Create Resource Group for cost management resources
resource "azurerm_resource_group" "cost_management" {
  name     = "cost-management-resources"
  location = "westus"
}

# 1. Cost Alert Action Group
resource "azurerm_monitor_action_group" "cost_alerts" {
  name                = "cost-management-alerts"
  resource_group_name = azurerm_resource_group.cost_management.name
  short_name          = "costAlerts"

  email_receiver {
    name                    = "primary-contact"
    email_address           = "jonathan.corners@gmail.com"
    use_common_alert_schema = true
  }
}

# 2. Built-in Policy Assignment for VM Auto-Shutdown
# NOTE: We'll individually configure VM shutdown through the Azure Portal instead
# of using a policy to avoid permission issues

# 3. Built-in Policy Assignment - Allowed VM SKUs
resource "azurerm_subscription_policy_assignment" "allowed_vm_skus" {
  name                 = "allowed-vm-skus"
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/cccc23c7-8427-4f53-ad12-b6a63eb452b3" # Built-in policy for allowed VM SKUs
  subscription_id      = data.azurerm_subscription.current.id
  description          = "Allows only cost-effective VM SKUs and NCv3 for ML"
  display_name         = "Allowed VM SKUs"
  location             = "westus"
  
  parameters = <<PARAMETERS
  {
    "listOfAllowedSKUs": {
      "value": [
        "Standard_B1s",
        "Standard_B1ms",
        "Standard_B2s", 
        "Standard_B2ms",
        "Standard_B1ls",
        "Standard_NC6s_v3",
        "Standard_NC12s_v3",
        "Standard_NC24s_v3",
        "Standard_NC24rs_v3"
      ]
    }
  }
PARAMETERS
}

# 4. Built-in Policy Assignment - Require tag on resource groups
resource "azurerm_subscription_policy_assignment" "require_cost_center_tag" {
  name                 = "require-cost-center-tag"
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/96670d01-0a4d-4649-9c89-2d3abc0a5025" # Built-in policy for requiring a tag on resource groups
  subscription_id      = data.azurerm_subscription.current.id
  description          = "Requires all resource groups to have a CostCenter tag"
  display_name         = "Require CostCenter tag on resource groups"
  location             = "westus"
  
  parameters = <<PARAMETERS
  {
    "tagName": {
      "value": "CostCenter"
    }
  }
PARAMETERS
}

# 5. Built-in Policy Assignment - Restrict Storage Account SKUs
resource "azurerm_subscription_policy_assignment" "allowed_storage_skus" {
  name                 = "allowed-storage-skus"
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/7433c107-6db4-4ad1-b57a-a76dce0154a1" # Built-in policy for allowed storage account SKUs
  subscription_id      = data.azurerm_subscription.current.id
  description          = "Limits storage accounts to standard SKUs"
  display_name         = "Allowed Storage Account SKUs"
  location             = "westus"
  
  parameters = <<PARAMETERS
  {
    "listOfAllowedSKUs": {
      "value": [
        "Standard_LRS",
        "Standard_GRS",
        "Standard_ZRS"
      ]
    }
  }
PARAMETERS
}

# 6. Built-in Policy Assignment - Not allowed resource types
resource "azurerm_subscription_policy_assignment" "not_allowed_resource_types" {
  name                 = "not-allowed-resource-types"
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/6c112d4e-5bc7-47ae-a041-ea2d9dccd749" # Built-in policy for not allowed resource types
  subscription_id      = data.azurerm_subscription.current.id
  description          = "Prevents creation of expensive resource types"
  display_name         = "Not allowed resource types"
  location             = "westus"
  
  parameters = <<PARAMETERS
  {
    "listOfResourceTypesNotAllowed": {
      "value": [
        "Microsoft.Network/applicationGateways",
        "Microsoft.Network/azureFirewalls",
        "Microsoft.Sql/managedInstances",
        "Microsoft.AVS/privateClouds"
      ]
    }
  }
PARAMETERS
}

# 7. Output the subscription ID and policy assignment IDs for reference
output "subscription_id" {
  value = data.azurerm_subscription.current.id
}

output "policy_assignment_ids" {
  value = {
    vm_skus        = azurerm_subscription_policy_assignment.allowed_vm_skus.id
    cost_tags      = azurerm_subscription_policy_assignment.require_cost_center_tag.id
    storage_skus   = azurerm_subscription_policy_assignment.allowed_storage_skus.id
    resource_types = azurerm_subscription_policy_assignment.not_allowed_resource_types.id
  }
}
