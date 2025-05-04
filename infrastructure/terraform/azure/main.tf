# Azure Cost Management with Built-in Policies
# This configuration uses built-in Azure policies to enforce cost management practices
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

# Configure the Azure Provider
provider "azurerm" {
  features {}
  # Note: resource_provider_registrations = "none" is retained to avoid timeout issues
  # Ensure required providers (Microsoft.Monitor, Microsoft.Authorization) are registered
  resource_provider_registrations = "none"
}

# Get current subscription data
data "azurerm_subscription" "current" {}

# Reference existing resource group
data "azurerm_resource_group" "cost_management" {
  name = "cost-management-resources"
}

# 1. Cost Alert Action Group
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

# 2. Built-in Policy Assignment - Allowed VM SKUs
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

# 3. Built-in Policy Assignment - Require tag on resource groups
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

# 4. Built-in Policy Assignment - Restrict Storage Account SKUs
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

# 5. Built-in Policy Assignment - Not allowed resource types
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

# 6. Output the subscription ID and policy assignment IDs for reference
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