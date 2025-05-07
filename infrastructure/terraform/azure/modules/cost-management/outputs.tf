# Sentimark - Azure Cost Management Module Outputs

output "action_group_id" {
  description = "The ID of the cost alerts action group"
  value       = azurerm_monitor_action_group.cost_alerts.id
}

output "budget_id" {
  description = "The ID of the subscription budget"
  value       = azurerm_consumption_budget_subscription.monthly_budget.id
}

output "budget_details" {
  description = "Details about the subscription budget"
  value = {
    name     = azurerm_consumption_budget_subscription.monthly_budget.name
    amount   = var.monthly_budget_amount
    currency = "USD"
  }
}

output "policy_assignment_ids" {
  description = "IDs of the policy assignments"
  value = var.enable_policy_assignments ? {
    vm_skus             = azurerm_subscription_policy_assignment.allowed_vm_skus[0].id
    cost_tags           = azurerm_subscription_policy_assignment.require_cost_center_tag[0].id
    storage_skus        = azurerm_subscription_policy_assignment.allowed_storage_skus[0].id
    resource_types      = azurerm_subscription_policy_assignment.not_allowed_resource_types[0].id
    auto_shutdown       = azurerm_subscription_policy_assignment.auto_shutdown[0].id
    environment_tag     = azurerm_subscription_policy_assignment.require_environment_tag[0].id
    inherit_cost_center = azurerm_subscription_policy_assignment.inherit_cost_center_tag[0].id
  } : {
    vm_skus             = "not_enabled"
    cost_tags           = "not_enabled"
    storage_skus        = "not_enabled"
    resource_types      = "not_enabled"
    auto_shutdown       = "not_enabled"
    environment_tag     = "not_enabled"
    inherit_cost_center = "not_enabled"
  }
}

output "auto_shutdown_time" {
  description = "The configured time for auto-shutdown of Dev/Test VMs"
  value       = "All Dev/Test VMs will automatically shut down at ${var.autoshutdown_time} UTC"
}