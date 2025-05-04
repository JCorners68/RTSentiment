# Azure Cost Optimization and Governance Framework
# 
# This configuration implements a comprehensive cost management strategy including:
# - Resource restrictions (VM sizes, storage types)
# - Cost tracking tags enforcement
# - Auto-shutdown schedules for dev/test VMs
# - Budget alerts and monitoring
# - Resource type restrictions
#
# Assumptions:
# - Resource group 'cost-management-resources' already exists and is referenced via data block
# - Service principal has 'Contributor' role at subscription scope for policy assignments
# - Terraform state is stored in Azure Blob Storage backend
# - Email address and location are provided via variables (e.g., GitHub Actions secrets)

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  required_version = ">= 1.5.0"

  # Backend configuration for Azure Blob Storage
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "tfstateaccount"
    container_name       = "tfstate"
    key                  = "cost-management.tfstate"
  }
}

# Variables
variable "alert_email" {
  description = "Email address for cost alerts"
  type        = string
  sensitive   = true
}

variable "location" {
  description = "Azure region for resources and policy assignments"
  type        = string
  default     = "westus"
}

variable "monthly_budget_amount" {
  description = "Monthly budget amount in USD for the subscription"
  type        = number
  default     = 1000
}

variable "autoshutdown_time" {
  description = "Time to automatically shutdown dev VMs (in 24h format, UTC)"
  type        = string
  default     = "1900" # 7 PM UTC
}

# Configure the Azure Provider
provider "azurerm" {
  features {}
  # Use "none" option to avoid timeout issues when required providers
  # (Microsoft.Monitor, Microsoft.Authorization) are already registered
  resource_provider_registrations = "none"
}

# Get current subscription data
data "azurerm_subscription" "current" {}

# Reference existing resource group
data "azurerm_resource_group" "cost_management" {
  name = "cost-management-resources"
}

#########################################
# 1. COST MONITORING AND ALERTING
#########################################

# 1.1 Cost Alert Action Group
resource "azurerm_monitor_action_group" "cost_alerts" {
  name                = "cost-management-alerts"
  resource_group_name = data.azurerm_resource_group.cost_management.name
  short_name          = "costAlerts"

  email_receiver {
    name                    = "primary-contact"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }
}

# 1.2 Create Subscription Budget with Alerts
resource "azurerm_consumption_budget_subscription" "monthly_budget" {
  name            = "monthly-subscription-budget"
  subscription_id = data.azurerm_subscription.current.id

  amount     = var.monthly_budget_amount
  time_grain = "Monthly"

  time_period {
    start_date = "2023-01-01T00:00:00Z"
    # No end date makes this a recurring monthly budget
  }

  notification {
    enabled        = true
    threshold      = 70.0
    operator       = "GreaterThan"
    threshold_type = "Forecasted"

    contact_emails = [
      var.alert_email
    ]

    contact_groups = [
      azurerm_monitor_action_group.cost_alerts.id
    ]
  }

  notification {
    enabled        = true
    threshold      = 90.0
    operator       = "GreaterThan"
    threshold_type = "Forecasted"

    contact_emails = [
      var.alert_email
    ]
    
    contact_groups = [
      azurerm_monitor_action_group.cost_alerts.id
    ]
  }

  notification {
    enabled        = true
    threshold      = 100.0
    operator       = "GreaterThan"
    threshold_type = "Actual"

    contact_emails = [
      var.alert_email
    ]
    
    contact_groups = [
      azurerm_monitor_action_group.cost_alerts.id
    ]
  }
}

#########################################
# 2. RESOURCE RESTRICTIONS
#########################################

# 2.1 VM SKU Restrictions
resource "azurerm_subscription_policy_assignment" "allowed_vm_skus" {
  name                 = "allowed-vm-skus"
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/cccc23c7-8427-4f53-ad12-b6a63eb452b3" # Built-in policy for allowed VM SKUs
  subscription_id      = data.azurerm_subscription.current.id
  description          = "Allows only cost-effective VM SKUs and NCv3 for ML"
  display_name         = "Allowed VM SKUs"
  location             = var.location

  parameters = jsonencode({
    listOfAllowedSKUs = {
      value = [
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
  })
}

# 2.2 Storage Account SKU Restrictions
resource "azurerm_subscription_policy_assignment" "allowed_storage_skus" {
  name                 = "allowed-storage-skus"
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/7433c107-6db4-4ad1-b57a-a76dce0154a1" # Built-in policy for allowed storage account SKUs
  subscription_id      = data.azurerm_subscription.current.id
  description          = "Limits storage accounts to standard SKUs"
  display_name         = "Allowed Storage Account SKUs"
  location             = var.location

  parameters = jsonencode({
    listOfAllowedSKUs = {
      value = [
        "Standard_LRS",
        "Standard_GRS",
        "Standard_ZRS"
      ]
    }
  })
}

# 2.3 Prohibited Resource Types
resource "azurerm_subscription_policy_assignment" "not_allowed_resource_types" {
  name                 = "not-allowed-resource-types"
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/6c112d4e-5bc7-47ae-a041-ea2d9dccd749" # Built-in policy for not allowed resource types
  subscription_id      = data.azurerm_subscription.current.id
  description          = "Prevents creation of expensive resource types"
  display_name         = "Not allowed resource types"
  location             = var.location

  parameters = jsonencode({
    listOfResourceTypesNotAllowed = {
      value = [
        "Microsoft.Network/applicationGateways",
        "Microsoft.Network/azureFirewalls",
        "Microsoft.Sql/managedInstances",
        "Microsoft.AVS/privateClouds"
      ]
    }
  })
}

#########################################
# 3. AUTO-SHUTDOWN CONFIGURATION
#########################################

# 3.1 Custom Policy Definition for VM Auto-shutdown
resource "azurerm_policy_definition" "auto_shutdown" {
  name         = "auto-shutdown-vms"
  policy_type  = "Custom"
  mode         = "All"
  display_name = "Configure automatic shutdown for VMs"
  description  = "This policy configures VMs to automatically shut down at a specified time"

  metadata = <<METADATA
    {
      "category": "Compute",
      "version": "1.0.0"
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
        "field": "tags.Environment",
        "in": ["Dev", "Test", "Development", "Testing"]
      }
    ]
  },
  "then": {
    "effect": "deployIfNotExists",
    "details": {
      "type": "Microsoft.DevTestLab/schedules",
      "name": "shutdown-computevm-${var.autoshutdown_time}",
      "roleDefinitionIds": [
        "/providers/Microsoft.Authorization/roleDefinitions/b24988ac-6180-42a0-ab88-20f7382dd24c"
      ],
      "existenceCondition": {
        "field": "name",
        "like": "shutdown-computevm-*"
      },
      "deployment": {
        "properties": {
          "mode": "incremental",
          "template": {
            "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {
              "vmName": {
                "type": "string"
              },
              "location": {
                "type": "string"
              },
              "shutdownTime": {
                "type": "string"
              }
            },
            "resources": [
              {
                "name": "[concat('shutdown-computevm-', parameters('shutdownTime'))]",
                "type": "Microsoft.DevTestLab/schedules",
                "apiVersion": "2018-09-15",
                "location": "[parameters('location')]",
                "properties": {
                  "status": "Enabled",
                  "taskType": "ComputeVmShutdownTask",
                  "dailyRecurrence": {
                    "time": "[parameters('shutdownTime')]"
                  },
                  "timeZoneId": "UTC",
                  "targetResourceId": "[resourceId('Microsoft.Compute/virtualMachines', parameters('vmName'))]",
                  "notificationSettings": {
                    "status": "Enabled",
                    "timeInMinutes": 30,
                    "emailRecipient": "[parameters('emailRecipient')]",
                    "notificationLocale": "en"
                  }
                }
              }
            ]
          },
          "parameters": {
            "vmName": {
              "value": "[field('name')]"
            },
            "location": {
              "value": "[field('location')]"
            },
            "shutdownTime": {
              "value": "${var.autoshutdown_time}"
            },
            "emailRecipient": {
              "value": "${var.alert_email}"
            }
          }
        }
      }
    }
  }
}
POLICY_RULE
}

# 3.2 Auto-shutdown Policy Assignment
resource "azurerm_subscription_policy_assignment" "auto_shutdown" {
  name                 = "auto-shutdown-vms"
  policy_definition_id = azurerm_policy_definition.auto_shutdown.id
  subscription_id      = data.azurerm_subscription.current.id
  description          = "Automatically shuts down development VMs at ${var.autoshutdown_time} UTC"
  display_name         = "Auto-Shutdown for Dev/Test VMs"
  location             = var.location
}

# 3.3 Direct Auto-Shutdown Schedule for Existing VMs
# This creates a schedule for existing VMs that are tagged for development/testing
# Used in conjunction with the policy for future VMs
resource "azurerm_dev_test_global_vm_shutdown_schedule" "existing_vms" {
  for_each = {
    for vm in data.azurerm_resources.development_vms.resources : 
    vm.name => vm
  }

  virtual_machine_id = each.value.id
  location           = each.value.location
  enabled            = true

  daily_recurrence_time = replace(var.autoshutdown_time, "", ":")  # Convert "1900" to "19:00"
  timezone              = "UTC"

  notification_settings {
    enabled         = true
    time_in_minutes = 30
    email           = var.alert_email
  }

  tags = {
    AutoShutdownManaged = "true"
  }
}

# Data source to find existing VMs with development/testing tags
data "azurerm_resources" "development_vms" {
  type = "Microsoft.Compute/virtualMachines"

  required_tags = {
    Environment = "Dev|Test|Development|Testing"
  }
}

#########################################
# 4. GOVERNANCE & TAG MANAGEMENT
#########################################

# 4.1 Require Cost Center Tag on Resource Groups
resource "azurerm_subscription_policy_assignment" "require_cost_center_tag" {
  name                 = "require-cost-center-tag"
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/96670d01-0a4d-4649-9c89-2d3abc0a5025" # Built-in policy for requiring a tag on resource groups
  subscription_id      = data.azurerm_subscription.current.id
  description          = "Requires all resource groups to have a CostCenter tag"
  display_name         = "Require CostCenter tag on resource groups"
  location             = var.location

  parameters = jsonencode({
    tagName = {
      value = "CostCenter"
    }
  })
}

# 4.2 Require Environment Tag on Resources
resource "azurerm_subscription_policy_assignment" "require_environment_tag" {
  name                 = "require-environment-tag"
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/871b6d14-10aa-478d-b590-94f262ecfa99" # Built-in policy for requiring a tag on resources
  subscription_id      = data.azurerm_subscription.current.id
  description          = "Requires all resources to have an Environment tag"
  display_name         = "Require Environment tag on resources"
  location             = var.location

  parameters = jsonencode({
    tagName = {
      value = "Environment"
    }
  })
}

# 4.3 Inherit CostCenter Tag from Resource Group
resource "azurerm_subscription_policy_assignment" "inherit_cost_center_tag" {
  name                 = "inherit-cost-center-tag"
  policy_definition_id = "/providers/Microsoft.Authorization/policyDefinitions/ea3f2387-9b95-492a-a190-fcdc54f7b070" # Built-in policy for inheriting a tag from resource group
  subscription_id      = data.azurerm_subscription.current.id
  description          = "Adds the CostCenter tag from the resource group to resources that don't have it"
  display_name         = "Inherit CostCenter tag from resource group"
  location             = var.location

  parameters = jsonencode({
    tagName = {
      value = "CostCenter"
    }
  })
}

#########################################
# OUTPUTS
#########################################

output "subscription_id" {
  value = data.azurerm_subscription.current.id
}

output "policy_assignment_ids" {
  value = {
    vm_skus             = azurerm_subscription_policy_assignment.allowed_vm_skus.id
    cost_tags           = azurerm_subscription_policy_assignment.require_cost_center_tag.id
    storage_skus        = azurerm_subscription_policy_assignment.allowed_storage_skus.id
    resource_types      = azurerm_subscription_policy_assignment.not_allowed_resource_types.id
    auto_shutdown       = azurerm_subscription_policy_assignment.auto_shutdown.id
    environment_tag     = azurerm_subscription_policy_assignment.require_environment_tag.id
    inherit_cost_center = azurerm_subscription_policy_assignment.inherit_cost_center_tag.id
  }
}

output "budget_details" {
  value = {
    name     = azurerm_consumption_budget_subscription.monthly_budget.name
    amount   = var.monthly_budget_amount
    currency = "USD"
  }
}

output "auto_shutdown_time" {
  value = "All Dev/Test VMs will automatically shut down at ${var.autoshutdown_time} UTC"
}