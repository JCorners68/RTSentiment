# Sentimark - Azure App Configuration Module Variables

variable "app_config_name" {
  description = "Name of the Azure App Configuration instance"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "location" {
  description = "Azure region"
  type        = string
}

variable "service_principal_id" {
  description = "Object ID of the service principal or managed identity"
  type        = string
}

variable "alert_action_group_id" {
  description = "ID of the action group for alerts"
  type        = string
}

variable "enable_iceberg_backend" {
  description = "Whether to enable the Iceberg backend"
  type        = bool
  default     = false
}

variable "enable_iceberg_optimizations" {
  description = "Whether to enable Iceberg optimizations"
  type        = bool
  default     = false
}

variable "enable_iceberg_partitioning" {
  description = "Whether to enable Iceberg partitioning"
  type        = bool
  default     = false
}

variable "enable_iceberg_time_travel" {
  description = "Whether to enable Iceberg time travel"
  type        = bool
  default     = false
}

variable "iceberg_roll_percentage" {
  description = "Percentage of traffic to route to Iceberg backend (0-100)"
  type        = number
  default     = 0
  
  validation {
    condition     = var.iceberg_roll_percentage >= 0 && var.iceberg_roll_percentage <= 100
    error_message = "Iceberg roll percentage must be between 0 and 100."
  }
}

variable "app_config_read_delay_seconds" {
  description = "Delay to wait for RBAC permissions to propagate before creating App Configuration keys"
  type        = number
  default     = 60
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}