# Sentimark - Azure Cost Management Module Variables

variable "environment" {
  description = "Deployment environment (dev, sit, uat, prod)"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group for cost management resources"
  type        = string
  default     = "cost-management-resources"
}

variable "location" {
  description = "Azure region for resources and policy assignments"
  type        = string
}

variable "alert_email" {
  description = "Email address for cost alerts and notifications"
  type        = string
  sensitive   = true
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

variable "apply_to_existing_vms" {
  description = "Whether to apply auto-shutdown to existing VMs"
  type        = bool
  default     = false
}

variable "allowed_vm_skus" {
  description = "List of allowed VM SKUs"
  type        = list(string)
  default     = [
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

variable "allowed_storage_skus" {
  description = "List of allowed Storage Account SKUs"
  type        = list(string)
  default     = [
    "Standard_LRS",
    "Standard_GRS",
    "Standard_ZRS"
  ]
}

variable "prohibited_resource_types" {
  description = "List of resource types that are not allowed"
  type        = list(string)
  default     = [
    "Microsoft.Network/applicationGateways",
    "Microsoft.Network/azureFirewalls",
    "Microsoft.Sql/managedInstances",
    "Microsoft.AVS/privateClouds"
  ]
}

variable "enable_policy_assignments" {
  description = "Whether to enable Azure policy assignments (requires Owner role)"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}