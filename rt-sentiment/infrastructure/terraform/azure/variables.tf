# RT Sentiment Analysis - Azure Terraform Variables

# Core Azure Configuration
variable "subscription_id" {
  description = "Azure subscription ID"
  default     = "644936a7-e58a-4ccb-a882-0005f213f5bd"
}

variable "tenant_id" {
  description = "Azure tenant ID"
  default     = "1ced8c49-a03c-439c-9ff1-0c23f5128720"
}

variable "client_id" {
  description = "Azure Service Principal Client ID"
  default     = ""
}

variable "client_secret" {
  description = "Azure Service Principal Client Secret"
  default     = ""
  sensitive   = true
}

# Resource Group
variable "resource_group_name" {
  description = "Name of the resource group"
  default     = "rt-sentiment-uat"
}

variable "location" {
  description = "Azure region"
  default     = "westus"  # US West region for low latency
}

# AKS Configuration
variable "aks_cluster_name" {
  description = "Name of the AKS cluster"
  default     = "rt-sentiment-aks"
}

variable "kubernetes_version" {
  description = "Kubernetes version to use"
  default     = "1.26.6"
}

variable "node_count" {
  description = "Default number of nodes in the AKS cluster"
  default     = 3
}

variable "vm_size" {
  description = "VM size for the default node pool"
  default     = "Standard_D4s_v3"  # More capable VM for better performance
}

# Proximity Placement Group
variable "ppg_name" {
  description = "Name of the Proximity Placement Group"
  default     = "rt-sentiment-ppg"
}

# Container Registry
variable "acr_name" {
  description = "Name of the Azure Container Registry"
  default     = "rtsentiregistry"
}

# Storage
variable "storage_account_name" {
  description = "Name of the Storage Account"
  default     = "rtsentistorage"
}

# Front Door
variable "front_door_name" {
  description = "Name of Azure Front Door"
  default     = "rt-sentiment-fd"
}

# Application Insights
variable "app_insights_name" {
  description = "Name of Application Insights"
  default     = "rt-sentiment-insights"
}

# Log Analytics
variable "log_analytics_name" {
  description = "Name of Log Analytics workspace"
  default     = "rt-sentiment-logs"
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {
    environment = "uat"
    project     = "rt-sentiment"
    managedBy   = "terraform"
  }
}

# Service configurations
variable "data_acquisition_host" {
  description = "Host name for data acquisition service"
  default     = "data-acquisition.uat.example.com"
}
