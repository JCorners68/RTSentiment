/**
 * Newsletter Subscription System Terraform Module
 * Variables definition
 */

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "prod"
}

variable "location" {
  description = "Azure region where resources will be deployed"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group where resources will be deployed"
  type        = string
}

variable "aks_cluster_name" {
  description = "Name of the existing AKS cluster"
  type        = string
}

variable "cosmos_db_account_name" {
  description = "Name of the existing Cosmos DB account"
  type        = string
}

variable "cosmos_db_database_name" {
  description = "Name of the existing Cosmos DB database"
  type        = string
}

variable "create_new_apim" {
  description = "Whether to create a new API Management instance or use an existing one"
  type        = bool
  default     = false
}

variable "existing_apim_name" {
  description = "Name of the existing API Management instance (if create_new_apim is false)"
  type        = string
  default     = ""
}

variable "admin_email" {
  description = "Email address of the newsletter administrator"
  type        = string
}

variable "rate_limit_calls" {
  description = "Number of API calls allowed per renewal period"
  type        = number
  default     = 5
}

variable "rate_limit_period" {
  description = "Renewal period for rate limiting in seconds"
  type        = number
  default     = 1
}

variable "allowed_origins" {
  description = "Allowed origins for CORS"
  type        = string
  default     = "https://www.sentimark.ai"
}

variable "aks_ingress_hostname" {
  description = "Hostname for the AKS ingress controller"
  type        = string
}

variable "app_config_name" {
  description = "Name of the App Configuration resource to store connection strings"
  type        = string
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
