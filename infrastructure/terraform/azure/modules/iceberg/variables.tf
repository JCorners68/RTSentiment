# Sentimark - Iceberg on Azure Module Variables

variable "base_name" {
  description = "Base name for resources"
  type        = string
  default     = "sentimark"
}

variable "storage_account_name" {
  description = "Name of the storage account for Iceberg"
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

variable "tenant_id" {
  description = "Azure tenant ID"
  type        = string
}

variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "service_principal_id" {
  description = "Object ID of the service principal or managed identity"
  type        = string
}

variable "allowed_ips" {
  description = "List of allowed IP addresses to access the storage"
  type        = list(string)
  default     = []
}

variable "subnet_ids" {
  description = "List of subnet IDs that can access the storage"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "docker_username" {
  description = "Docker Hub username for authenticated pulls (to avoid rate limiting)"
  type        = string
  default     = ""
}

variable "docker_password" {
  description = "Docker Hub password or access token for authenticated pulls"
  type        = string
  default     = ""
  sensitive   = true
}

variable "deploy_container" {
  description = "Whether to deploy the Iceberg REST catalog container"
  type        = bool
  default     = true
}