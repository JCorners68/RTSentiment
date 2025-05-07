# Sentimark - Azure Monitoring Module Variables

variable "base_name" {
  description = "Base name for resources"
  type        = string
  default     = "sentimark"
}

variable "log_analytics_name" {
  description = "Name of the Log Analytics workspace"
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

variable "log_retention_days" {
  description = "Number of days to retain logs"
  type        = number
  default     = 30
}

variable "alert_email" {
  description = "Email address for alerts"
  type        = string
}

variable "query_performance_threshold" {
  description = "Threshold in milliseconds for query performance alerts"
  type        = number
  default     = 5000
}

variable "error_threshold" {
  description = "Threshold for number of errors before alerting"
  type        = number
  default     = 10
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}