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

variable "use_msi" {
  description = "Whether to use Managed Service Identity for authentication"
  type        = bool
  default     = false
}

variable "use_cli" {
  description = "Whether to use Azure CLI for authentication (always set to false for service principal auth)"
  type        = bool
  default     = false
}

# Environment
variable "environment" {
  description = "Deployment environment (dev, sit, uat, prod)"
  default     = "sit"
}

# Resource Group
variable "resource_group_name" {
  description = "Name of the resource group"
  default     = "sentimark-sit-rg"
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

variable "enable_aks_availability_zones" {
  description = "Whether to enable availability zones in AKS node pools (not supported in all regions)"
  type        = bool
  default     = false
}

variable "kubernetes_version" {
  description = "Kubernetes version to use"
  default     = "1.26.6"
}

variable "node_count" {
  description = "Default number of nodes in the AKS cluster"
  default     = 2
}

variable "data_tier_node_count" {
  description = "Number of nodes for the data tier"
  default     = 1
}

variable "data_processing_node_count" {
  description = "Number of nodes for data processing"
  default     = 1
}

variable "enable_data_tier" {
  description = "Whether to enable the data tier"
  type        = bool
  default     = true
}

variable "data_tier_db_sku" {
  description = "SKU for the data tier database"
  default     = "Basic"
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

# Alerts and Notifications
variable "alert_email" {
  description = "Email address for alerts and notifications"
  type        = string
  default     = "jonathan.corners@gmail.com"
}

# Cost Management
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

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {
    environment = "sit"
    project     = "Sentimark"
    managed_by  = "Terraform"
    CostCenter  = "Sentimark"
  }
}

# Front Door Configuration 
variable "disable_classic_frontdoor" {
  description = "Whether to disable the classic Front Door resource (which is deprecated)"
  type        = bool
  default     = true
}

variable "enable_cdn_frontdoor" {
  description = "Whether to enable the new Azure Front Door (CDN) resource"
  type        = bool
  default     = false
}

# App Configuration
variable "app_config_read_delay_seconds" {
  description = "Delay to wait for RBAC permissions to propagate before creating App Configuration keys"
  type        = number
  default     = 60
}

# Policy Management
variable "enable_policy_assignments" {
  description = "Whether to enable Azure policy assignments (requires Owner role)"
  type        = bool
  default     = false
}

# Docker Hub Authentication
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

# Spot instance configuration variables
variable "enable_spot_instances" {
  description = "Whether to use spot instances for node pools (for cost savings)"
  type        = bool
  default     = false
}

variable "use_low_latency_pool" {
  description = "Whether to create the low-latency node pool"
  type        = bool
  default     = false
}

# Service Principal (for RBAC permissions)
variable "service_principal_object_id" {
  description = "Object ID of the Service Principal used for deployment"
  type        = string
  default     = "5c765214-89b0-4a9b-9e8f-ff6e763d1828"
}

# Service configurations
variable "data_acquisition_host" {
  description = "Host name for data acquisition service"
  default     = "data-acquisition.uat.example.com"
}