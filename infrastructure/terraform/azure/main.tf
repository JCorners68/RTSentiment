# Azure Cost Management Terraform Configuration - main.tf

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

# 2. Policy to Enforce VM Auto-Shutdown 
resource "azurerm_policy_definition" "enforce_vm_shutdown" {
  name         = "enforce-vm-shutdown"
  policy_type  = "Custom"
  mode         = "All"
  display_name = "Enforce VM Shutdown Schedule"
  
  metadata = <<METADATA
    {
      "category": "Cost Management"
    }
  METADATA
  
  policy_rule = <<POLICY_RULE
{
  "if": {
    "field": "type",
    "equals": "Microsoft.Compute/virtualMachines"
  },
  "then": {
    "effect": "deployIfNotExists",
    "details": {
      "type": "Microsoft.DevTestLab/schedules",
      "name": "[concat('shutdown-computevm-', field('name'))]",
      "evaluationDelay": "AfterProvisioning",
      "existenceCondition": {
        "field": "name",
        "like": "[concat('shutdown-computevm-', field('name'))]"
      },
      "roleDefinitionIds": [
        "/providers/Microsoft.Authorization/roleDefinitions/b24988ac-6180-42a0-ab88-20f7382dd24c"
      ],
      "deployment": {
        "properties": {
          "mode": "incremental",
          "template": {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {},
            "resources": [
              {
                "type": "Microsoft.DevTestLab/schedules",
                "apiVersion": "2018-09-15",
                "name": "[concat('shutdown-computevm-', field('name'))]",
                "location": "[field('location')]",
                "properties": {
                  "status": "Enabled",
                  "taskType": "ComputeVmShutdownTask",
                  "dailyRecurrence": {
                    "time": "2000"
                  },
                  "timeZoneId": "UTC",
                  "targetResourceId": "[field('id')]",
                  "notificationSettings": {
                    "status": "Enabled",
                    "timeInMinutes": 30,
                    "emailRecipient": "jonathan.corners@gmail.com",
                    "notificationLocale": "en"
                  }
                }
              }
            ]
          }
        }
      }
    }
  }
}
POLICY_RULE
}

# 3. Policy to Allow NCv3 VMs but Restrict Other VM Sizes
resource "azurerm_policy_definition" "restrict_vm_sizes" {
  name         = "restrict-vm-sizes-allow-ncsv3"
  policy_type  = "Custom"
  mode         = "Indexed"
  display_name = "Restrict VM Sizes but Allow NCv3 for ML"
  
  metadata = <<METADATA
    {
      "category": "Cost Management"
    }
  METADATA
  
  policy_rule = <<POLICY_RULE
{
  "if": {
    "allOf": [
      {
        "field": "type",
        "equals": "Microsoft.Compute/virtualMachines"
      },
      {
        "not": {
          "anyOf": [
            {
              "field": "Microsoft.Compute/virtualMachines/sku.name",
              "in": [
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
          ]
        }
      }
    ]
  },
  "then": {
    "effect": "deny"
  }
}
POLICY_RULE
}

# 4. Policy to Prevent Expensive Resources (Except NCv3)
resource "azurerm_policy_definition" "prevent_expensive_resources" {
  name         = "prevent-expensive-resources"
  policy_type  = "Custom"
  mode         = "All"
  display_name = "Prevent Creation of Expensive Resources"
  
  metadata = <<METADATA
    {
      "category": "Cost Management"
    }
  METADATA
  
  policy_rule = <<POLICY_RULE
{
  "if": {
    "anyOf": [
      {
        "field": "type",
        "equals": "Microsoft.Network/applicationGateways"
      },
      {
        "field": "type",
        "equals": "Microsoft.Network/azureFirewalls"
      },
      {
        "field": "type",
        "equals": "Microsoft.Sql/managedInstances"
      },
      {
        "field": "type",
        "equals": "Microsoft.AVS/privateClouds"
      }
    ]
  },
  "then": {
    "effect": "deny"
  }
}
POLICY_RULE
}

# 5. Policy to Enforce Resource Tagging for Cost Tracking
resource "azurerm_policy_definition" "require_cost_center_tag" {
  name         = "require-cost-center-tag"
  policy_type  = "Custom"
  mode         = "Indexed"
  display_name = "Require Cost Center Tag for Resources"
  
  metadata = <<METADATA
    {
      "category": "Cost Management"
    }
  METADATA
  
  policy_rule = <<POLICY_RULE
{
  "if": {
    "field": "tags['CostCenter']",
    "exists": "false"
  },
  "then": {
    "effect": "deny"
  }
}
POLICY_RULE
}

# 6. Policy to Enforce Maximum Storage Account Size
resource "azurerm_policy_definition" "restrict_storage_sku" {
  name         = "restrict-storage-sku"
  policy_type  = "Custom"
  mode         = "Indexed"
  display_name = "Restrict Storage Account to Standard SKUs"
  
  metadata = <<METADATA
    {
      "category": "Cost Management"
    }
  METADATA
  
  policy_rule = <<POLICY_RULE
{
  "if": {
    "allOf": [
      {
        "field": "type",
        "equals": "Microsoft.Storage/storageAccounts"
      },
      {
        "not": {
          "field": "Microsoft.Storage/storageAccounts/sku.name",
          "in": [
            "Standard_LRS",
            "Standard_GRS",
            "Standard_ZRS"
          ]
        }
      }
    ]
  },
  "then": {
    "effect": "deny"
  }
}
POLICY_RULE
}

# 7. Policy to Limit NCv3 VM Usage to 6 Cores Total
resource "azurerm_policy_definition" "limit_ncsv3_cores" {
  name         = "limit-ncsv3-cores"
  policy_type  = "Custom"
  mode         = "All"
  display_name = "Limit NCv3 VM Usage to 6 Cores Total"
  
  metadata = <<METADATA
    {
      "category": "Cost Management"
    }
  METADATA
  
  # This policy is for informational purposes only - enforcing core quotas
  # is handled by Azure subscription quotas, not by policy
  description = "This policy is informational to remind users of the 6-core NCv3 quota limit"
  
  policy_rule = <<POLICY_RULE
{
  "if": {
    "allOf": [
      {
        "field": "type",
        "equals": "Microsoft.Compute/virtualMachines"
      },
      {
        "field": "Microsoft.Compute/virtualMachines/sku.name",
        "like": "Standard_NC*_v3"
      }
    ]
  },
  "then": {
    "effect": "audit"
  }
}
POLICY_RULE
}

# Assign the Policies to the Subscription
resource "azurerm_subscription_policy_assignment" "assign_enforce_vm_shutdown" {
  name                 = "enforce-vm-shutdown"
  policy_definition_id = azurerm_policy_definition.enforce_vm_shutdown.id
  subscription_id      = data.azurerm_subscription.current.id
  display_name         = "Enforce VM Auto-Shutdown"
  description          = "Automatically applies shutdown schedules to all VMs"
  location             = "westus"
}

resource "azurerm_subscription_policy_assignment" "assign_require_cost_center" {
  name                 = "cost-center-tag-policy"
  policy_definition_id = azurerm_policy_definition.require_cost_center_tag.id
  subscription_id      = data.azurerm_subscription.current.id
  display_name         = "Require Cost Center Tags"
  description          = "Policy to enforce cost center tags on all resources"
  location             = "westus"
}

resource "azurerm_subscription_policy_assignment" "assign_restrict_vm_sizes" {
  name                 = "vm-size-restriction-policy"
  policy_definition_id = azurerm_policy_definition.restrict_vm_sizes.id
  subscription_id      = data.azurerm_subscription.current.id
  display_name         = "Restrict VM Sizes"
  description          = "Policy to limit VM sizes to cost-effective options and NCv3 for ML"
  location             = "westus"
}

resource "azurerm_subscription_policy_assignment" "assign_restrict_storage_sku" {
  name                 = "storage-sku-restriction-policy"
  policy_definition_id = azurerm_policy_definition.restrict_storage_sku.id
  subscription_id      = data.azurerm_subscription.current.id
  display_name         = "Restrict Storage SKUs"
  description          = "Policy to limit storage accounts to standard SKUs"
  location             = "westus"
}

resource "azurerm_subscription_policy_assignment" "assign_limit_ncsv3_cores" {
  name                 = "limit-ncsv3-cores-policy"
  policy_definition_id = azurerm_policy_definition.limit_ncsv3_cores.id
  subscription_id      = data.azurerm_subscription.current.id
  display_name         = "Audit NCv3 VM Usage"
  description          = "Policy to audit NCv3 VM usage to stay within 6-core quota"
  location             = "westus"
}

# Uncomment this if you want to prevent expensive resources entirely 
# resource "azurerm_subscription_policy_assignment" "assign_prevent_expensive_resources" {
#   name                 = "prevent-expensive-resources"
#   policy_definition_id = azurerm_policy_definition.prevent_expensive_resources.id
#   subscription_id      = data.azurerm_subscription.current.id
#   display_name         = "Prevent Expensive Resources"
#   description          = "Policy to prevent creation of expensive resource types"
#   location             = "westus"
# }

# 8. Output the subscription ID and policy assignment IDs for reference
output "subscription_id" {
  value = data.azurerm_subscription.current.id
}

output "policy_assignment_ids" {
  value = {
    vm_shutdown     = azurerm_subscription_policy_assignment.assign_enforce_vm_shutdown.id
    cost_tags       = azurerm_subscription_policy_assignment.assign_require_cost_center.id
    vm_sizes        = azurerm_subscription_policy_assignment.assign_restrict_vm_sizes.id
    storage_skus    = azurerm_subscription_policy_assignment.assign_restrict_storage_sku.id
    ncsv3_core_limit = azurerm_subscription_policy_assignment.assign_limit_ncsv3_cores.id
  }
}
