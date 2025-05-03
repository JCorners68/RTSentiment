provider "azurerm" {
  features {}
  # Note: It's generally recommended to configure provider credentials
  # via environment variables (ARM_CLIENT_ID, ARM_CLIENT_SECRET, etc.)
  # or OIDC in CI/CD, rather than hardcoding subscription/tenant IDs here.
  # subscription_id = "644936a7-e58a-4ccb-a882-0005f213f5bd" # Example - Prefer environment variables
  # tenant_id       = "1ced8c49-a03c-439c-9ff1-0c23f5128720" # Example - Prefer environment variables
}

# --- Variables ---

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "rt-sentiment-uat"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "westus" # Changed to US West region for low latency
}

variable "aks_cluster_name" {
  description = "Name of the AKS cluster"
  type        = string
  default     = "rt-sentiment-aks"
}

variable "acr_name" {
  description = "Name of the Azure Container Registry"
  type        = string
  # Ensure ACR names are globally unique and follow naming rules (lowercase letters/numbers)
  default = "rtsentiregistry" # Example: Consider adding random suffix or using org prefix
}

variable "ppg_name" {
  description = "Name of the Proximity Placement Group"
  type        = string
  default     = "rt-sentiment-ppg"
}

variable "storage_account_name" {
  description = "Name of the Storage Account"
  type        = string
  # Ensure storage account names are globally unique and follow naming rules (lowercase letters/numbers)
  default = "rtsentistorage" # Example: Consider adding random suffix or using org prefix
}

variable "front_door_name" {
  description = "Name of Azure Front Door"
  type        = string
  # Ensure Front Door names are globally unique and follow naming rules
  default = "rt-sentiment-fd" # Example: Consider adding random suffix or using org prefix
}

variable "app_insights_name" {
  description = "Name of Application Insights"
  type        = string
  default     = "rt-sentiment-insights"
}

# --- Resources ---

# Create a resource group
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

# Create a Proximity Placement Group for low latency
resource "azurerm_proximity_placement_group" "ppg" {
  name                = var.ppg_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  tags = {
    environment = "uat"
    purpose     = "low-latency"
  }
}

# Create Azure Container Registry
resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Premium" # Upgraded for better performance
  admin_enabled       = true      # Consider disabling admin if using SP/Managed Identity for auth

  # Enable geo-replication if needed in the future
  # georeplication_locations = ["eastus", "westeurope"]

  tags = {
    environment = "uat"
  }
}

# Create Storage Account
resource "azurerm_storage_account" "storage" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"

  tags = {
    environment = "uat"
  }
}

# Create Log Analytics Workspace for monitoring
resource "azurerm_log_analytics_workspace" "workspace" {
  name                = "rt-sentiment-logs" # Consider making this name variable
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    environment = "uat"
  }
}

# Create AKS cluster with PPG for low latency
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_cluster_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "rt-sentiment" # Consider making this unique if deploying multiple times
  kubernetes_version  = "1.26.6"       # Specify a stable version supported in your region

  # Configure with private cluster option for better security (ensure network connectivity)
  # private_cluster_enabled = true # Uncomment if needed, requires network setup

  # Default (System) Node Pool Configuration
  default_node_pool {
    name                         = "default" # System node pool name
    node_count                   = 3
    vm_size                      = "Standard_D4s_v3" # More capable VM for better performance
    os_disk_size_gb              = 100
    proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id
    availability_zones           = ["1", "2", "3"] # For high availability
    enable_auto_scaling          = true
    min_count                    = 2
    max_count                    = 5
    # only_critical_addons_enabled = true # Consider setting to true for system pool stability
    type                         = "VirtualMachineScaleSets" # Default, explicit is fine
    tags = {
      pool_type = "system"
    }
  }

  # Use managed identity (SystemAssigned is simpler for basic scenarios)
  identity {
    type = "SystemAssigned"
  }

  # Network profile
  network_profile {
    network_plugin     = "azure" # CNI plugin
    network_policy     = "calico" # Or "azure"
    service_cidr       = "10.0.0.0/16"
    dns_service_ip     = "10.0.0.10"
    docker_bridge_cidr = "172.17.0.1/16"
    # pod_cidr = "10.244.0.0/16" # Often required depending on CNI setup
  }

  # Enable monitoring with Azure Monitor for Containers
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.workspace.id
  }

  tags = {
    environment = "uat"
    ppg         = var.ppg_name
  }

  # Define dependency on PPG explicitly if needed (usually implicit)
  # depends_on = [azurerm_proximity_placement_group.ppg]
}

# **FIXED:** Define additional node pools using the separate resource type
# Add a dedicated node pool for data processing
resource "azurerm_kubernetes_cluster_node_pool" "datanodes" {
  name                         = "datanodes" # User node pool name
  kubernetes_cluster_id        = azurerm_kubernetes_cluster.aks.id # Link to the cluster
  vm_size                      = "Standard_D8s_v3" # Larger VMs for data processing
  node_count                   = 2
  os_disk_size_gb              = 200
  proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id
  availability_zones           = ["1", "2", "3"] # Also make user pools HA if needed
  enable_auto_scaling          = true            # Enable scaling for user pools too
  min_count                    = 1
  max_count                    = 4
  mode                         = "User" # Explicitly set mode to User

  # Taints to ensure only specific workloads are scheduled
  node_taints = ["workload=dataprocessing:NoSchedule"]
  tags = {
    pool_type = "user"
    workload  = "dataprocessing"
  }

  depends_on = [azurerm_kubernetes_cluster.aks] # Ensure cluster exists first
}


# Create Application Insights
resource "azurerm_application_insights" "insights" {
  name                = var.app_insights_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
  # Link to Log Analytics Workspace for unified logging (recommended)
  workspace_id = azurerm_log_analytics_workspace.workspace.id

  tags = {
    environment = "uat"
  }
}

# Create Web Application Firewall Policy for Front Door
resource "azurerm_frontdoor_firewall_policy" "wafpolicy" {
  name                = "RtSentimentWafPolicy"
  resource_group_name = azurerm_resource_group.rg.name
  enabled             = true
  mode                = "Prevention" # Or "Detection"

  # Example Managed Rulesets (Review and customize rules/actions as needed)
  managed_rule {
    type    = "DefaultRuleSet"
    version = "1.0" # Or newer like "2.0", "2.1"
    # action = "Block" # Default action
  }

  managed_rule {
    type    = "Microsoft_BotManagerRuleSet"
    version = "1.0"
    # action = "Block" # Default action
  }

  # Add custom rules or rate limiting if required
  # custom_rule { ... }
  # policy_settings { ... }

  tags = {
    environment = "uat"
  }
}


# Create Azure Front Door (Classic - Consider migrating to Front Door Standard/Premium)
# Note: azurerm_frontdoor is for Front Door Classic. For newer versions, use
# azurerm_cdn_frontdoor_profile, azurerm_cdn_frontdoor_endpoint, etc.
resource "azurerm_frontdoor" "frontdoor" {
  name                = var.front_door_name
  resource_group_name = azurerm_resource_group.rg.name

  frontend_endpoint {
    name                                 = "DefaultEndpoint" # Consider a more descriptive name
    host_name                            = "${var.front_door_name}.azurefd.net"
    session_affinity_enabled             = true # Or false depending on app requirements
    session_affinity_ttl_seconds         = 300
    # Link the WAF policy created above
    web_application_firewall_policy_link_id = azurerm_frontdoor_firewall_policy.wafpolicy.id
  }

  backend_pool {
    name = "DataAcquisitionBackend" # Name for this backend pool

    # Define the actual backend service (e.g., AKS Ingress IP or FQDN)
    # This example uses a placeholder FQDN. You'll likely need to replace this
    # with the actual public IP or FQDN of your AKS service/ingress controller.
    # You might need to create a Service of type LoadBalancer in K8s or use an Ingress Controller.
    backend {
      host_header = "data-acquisition.uat.example.com" # Host header FD sends to backend
      address     = "data-acquisition.uat.example.com" # Actual address of backend service
      http_port   = 80
      https_port  = 443
      weight      = 100 # For weighted load balancing (if multiple backends)
      priority    = 1   # For priority-based failover (if multiple backends)
    }

    # Reference the load balancing and health probe settings defined below
    load_balancing_name = "LoadBalancingSettings"
    health_probe_name   = "HealthProbeSettings"
  }

  # Define Load Balancing settings (how traffic is distributed within a backend pool)
  backend_pool_load_balancing {
    name                        = "LoadBalancingSettings"
    sample_size                 = 4 # Number of samples to consider for latency
    successful_samples_required = 2 # Number needed to determine lowest latency
    # additional_latency_milliseconds = 0 # Add latency tolerance if needed
  }

  # Define Health Probe settings (how Front Door checks backend health)
  backend_pool_health_probe {
    name                = "HealthProbeSettings"
    path                = "/" # Path to probe on your backend service
    protocol            = "Https" # Or Http
    interval_in_seconds = 30    # How often to probe
    # probe_method = "GET" # Default is GET
  }

  # Define Routing Rule (maps frontend endpoints to backend pools)
  routing_rule {
    name               = "DataAcquisitionRoutingRule"
    accepted_protocols = ["Http", "Https"] # Protocols accepted on the frontend
    patterns_to_match  = ["/*"]            # URL path patterns to match
    frontend_endpoints = ["DefaultEndpoint"] # Which frontend(s) this rule applies to

    # Define how matched traffic is forwarded
    forwarding_configuration {
      forwarding_protocol = "HttpsOnly" # Enforce HTTPS to backend, or "HttpOnly", "MatchRequest"
      backend_pool_name   = "DataAcquisitionBackend" # Which backend pool to forward to
      # cache_enabled = false # Enable caching if desired
    }
  }

  tags = {
    environment = "uat"
  }

  depends_on = [azurerm_frontdoor_firewall_policy.wafpolicy] # Explicit dependency
}


# Assign AcrPull role to AKS Managed Identity to allow pulling images from ACR
resource "azurerm_role_assignment" "acr_pull" {
  principal_id                           = azurerm_kubernetes_cluster.aks.identity[0].principal_id
  role_definition_name                   = "AcrPull"
  scope                                  = azurerm_container_registry.acr.id
  # skip_service_principal_aad_check = true # Generally not needed/recommended for managed identities
  depends_on = [
    azurerm_kubernetes_cluster.aks,
    azurerm_container_registry.acr
  ]
}

# --- Outputs ---

# Output AKS cluster credentials (use with caution)
output "kube_config_raw" {
  description = "Raw Kubernetes configuration for the AKS cluster. Handle with care."
  value       = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive   = true
}

# Output ACR login server
output "acr_login_server" {
  description = "The login server hostname of the Azure Container Registry"
  value       = azurerm_container_registry.acr.login_server
}

# Output resource group name
output "resource_group_name" {
  description = "The name of the resource group"
  value       = azurerm_resource_group.rg.name
}

# Output AKS cluster name
output "aks_cluster_name" {
  description = "The name of the AKS cluster"
  value       = azurerm_kubernetes_cluster.aks.name
}

# Output Proximity Placement Group ID
output "ppg_id" {
  description = "The resource ID of the Proximity Placement Group"
  value       = azurerm_proximity_placement_group.ppg.id
}

# Output Front Door endpoint URL
output "front_door_endpoint" {
  description = "The default frontend endpoint URL for the Azure Front Door"
  value       = "https://${azurerm_frontdoor.frontdoor.frontend_endpoint[0].host_name}"
}

# Output Application Insights Instrumentation Key
output "app_insights_instrumentation_key" {
  description = "The instrumentation key for Application Insights"
  value       = azurerm_application_insights.insights.instrumentation_key
  sensitive   = true
}
