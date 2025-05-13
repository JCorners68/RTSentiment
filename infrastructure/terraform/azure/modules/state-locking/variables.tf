/**
 * # State Locking Module Variables
 * 
 * This file contains all the variables that can be configured for the Terraform state locking module.
 */

variable "prefix" {
  description = "Prefix to use for resource names"
  type        = string
  default     = "sentimark"
}

variable "environment" {
  description = "Environment name (sit, uat, prod)"
  type        = string
  validation {
    condition     = contains(["sit", "uat", "prod"], var.environment)
    error_message = "Environment must be one of: sit, uat, prod."
  }
}

variable "location" {
  description = "Azure region where resources will be created"
  type        = string
  default     = "eastus"
}

variable "resource_group_name" {
  description = "Name of the resource group (if empty, will be generated using prefix and environment)"
  type        = string
  default     = ""
}

variable "storage_account_name" {
  description = "Name of the storage account (if empty, will be generated using prefix and environment)"
  type        = string
  default     = ""
}

variable "container_name" {
  description = "Name of the blob container for Terraform state"
  type        = string
  default     = "tfstate"
}

variable "storage_account_replication_type" {
  description = "Replication type for the storage account (LRS, GRS, RAGRS, ZRS)"
  type        = string
  default     = "LRS"
  validation {
    condition     = contains(["LRS", "GRS", "RAGRS", "ZRS"], var.storage_account_replication_type)
    error_message = "Replication type must be one of: LRS, GRS, RAGRS, ZRS."
  }
}

variable "blob_soft_delete_retention_days" {
  description = "Number of days to retain deleted blobs"
  type        = number
  default     = 7
  validation {
    condition     = var.blob_soft_delete_retention_days >= 1 && var.blob_soft_delete_retention_days <= 365
    error_message = "Blob soft delete retention days must be between 1 and 365."
  }
}

variable "container_delete_retention_days" {
  description = "Number of days to retain deleted containers"
  type        = number
  default     = 7
  validation {
    condition     = var.container_delete_retention_days >= 1 && var.container_delete_retention_days <= 365
    error_message = "Container delete retention days must be between 1 and 365."
  }
}

variable "create_resource_group" {
  description = "Whether to create the resource group"
  type        = bool
  default     = true
}

variable "create_storage_account" {
  description = "Whether to create the storage account"
  type        = bool
  default     = true
}

variable "create_storage_container" {
  description = "Whether to create the storage container"
  type        = bool
  default     = true
}

variable "create_resource_lock" {
  description = "Whether to create a resource lock to prevent accidental deletion"
  type        = bool
  default     = true
}

variable "service_principal_id" {
  description = "Object ID of the service principal that will access the state"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

variable "generate_backend_config" {
  description = "Whether to generate a backend config file"
  type        = bool
  default     = true
}

variable "backend_config_path" {
  description = "Path where the backend config file will be generated"
  type        = string
  default     = "backends"
}