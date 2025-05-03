# Configure the Azure Provider
provider "azurerm" {
  features {}
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
  default     = "westus" # Consider using a region that supports Availability Zones if needed for production.
}

variable "aks_cluster_name" {
  description = "Name of the AKS cluster"
  type        = string
  default     = "rt-sentiment-aks"
}

variable "acr_name" {
  description = "Name of the Azure Container Registry"
  type        = string
  default     = "rtsentiregistry" # Ensure this name is globally unique
}

variable "ppg_name" {
  description = "Name of the Proximity Placement Group"
  type        = string
  default     = "rt-sentiment-ppg"
}

variable "storage_account_name" {
  description = "Name of the Storage Account"
  type        = string
  default     = "rtsentistorage" # Ensure this name is globally unique
}

variable "front_door_name" {
  description = "Name of Azure Front Door (Classic)"
  type        = string
  default     = "rt-sentiment-fd" # Ensure this name is globally unique
}

variable "app_insights_name" {
  description = "Name of Application Insights"
  type        = string
  default     = "rt-sentiment-insights"
}

variable "log_analytics_workspace_name" {
  description = "Name of the Log Analytics Workspace"
  type        = string
  default     = "rt-sentiment-logs"
}

# --- Resources ---

# Resource Group
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    environment = "uat"
    purpose     = "realtime-sentiment-analysis"
  }
}

# Proximity Placement Group
resource "azurerm_proximity_placement_group" "ppg" {
  name                = var.ppg_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  tags = {
    environment = "uat"
    purpose     = "low-latency-compute"
  }
}

# Azure Container Registry
resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Premium" # Premium SKU allows for features like private endpoints, geo-replication
  admin_enabled       = true      # Set to false if using service principals or managed identities for auth

  tags = {
    environment = "uat"
  }
}

# Storage Account
resource "azurerm_storage_account" "storage" {
  name                     = var.storage_account_name
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS" # Locally-redundant storage. Choose GRS, ZRS, etc. based on requirements.
  account_kind             = "StorageV2"

  tags = {
    environment = "uat"
  }
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "workspace" {
  name                = var.log_analytics_workspace_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    environment = "uat"
  }
}

# Azure Kubernetes Service (AKS) Cluster
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_cluster_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "${var.aks_cluster_name}-dns" # Make DNS prefix unique
  kubernetes_version  = "1.28"                        # Specify a desired Kubernetes version or use data source to get latest

  default_node_pool {
    name                = "default"
    vm_size             = "Standard_DS2_v2"
    node_count          = 1 # Initial node count
    min_count           = 1 # Minimum nodes for autoscaling
    max_count           = 3 # Maximum nodes for autoscaling
    enable_auto_scaling = true
    availability_zones  = ["1", "2", "3"]
    os_disk_size_gb     = 128 # Default OS disk size
    type                = "VirtualMachineScaleSets"
    # proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id # Assign PPG if default pool needs low latency
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin = "azure"       # Using Azure CNI
    service_cidr   = "10.0.0.0/16" # Ensure this doesn't overlap with other networks
    dns_service_ip = "10.0.0.10"   # Must be within service_cidr
  }

  # Enable monitoring with Log Analytics
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.workspace.id
  }

  tags = {
    environment = "uat"
  }

  depends_on = [
    azurerm_log_analytics_workspace.workspace # Ensure workspace exists before enabling monitoring
  ]
}

# Additional User Node Pool for Data Processing
resource "azurerm_kubernetes_cluster_node_pool" "datanodes" {
  name                         = "datanodes"
  kubernetes_cluster_id        = azurerm_kubernetes_cluster.aks.id
  vm_size                      = "Standard_D8s_v3"
  node_count                   = 2 # Initial node count
  os_disk_size_gb              = 200
  proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id # Place data nodes in PPG
  availability_zones           = ["1", "2", "3"]                          # Match AZs with default pool if region supports it
  enable_auto_scaling          = true
  min_count                    = 1
  max_count                    = 4
  mode                         = "User" # Dedicated node pool for specific workloads
  node_taints                  = ["workload=dataprocessing:NoSchedule"] # Taint to prevent general pods scheduling here

  tags = {
    pool_type = "user"
    workload  = "dataprocessing"
  }

  # No explicit depends_on needed here as kubernetes_cluster_id creates implicit dependency
}

# Application Insights
resource "azurerm_application_insights" "insights" {
  name                = var.app_insights_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.workspace.id # Link to Log Analytics Workspace

  tags = {
    environment = "uat"
  }

  depends_on = [
    azurerm_log_analytics_workspace.workspace # Ensure workspace exists first
  ]
}

# Azure Front Door (Classic) WAF Policy
resource "azurerm_frontdoor_firewall_policy" "wafpolicy" {
  name                              = "RtSentimentWafPolicy"
  resource_group_name               = azurerm_resource_group.rg.name
  enabled                           = true
  mode                              = "Prevention" # Use "Detection" to log only, "Prevention" to block
  redirect_url                      = "https://www.example.com/blocked.html" # Optional: Custom block response page
  custom_block_response_status_code = 403
  custom_block_response_body        = "PGh0bWw+PGhlYWQ+PHRpdGxlPkJsb2NrZWQ8L3RpdGxlPjwvaGVhZD48Ym9keT5SZXF1ZXN0IGJsb2NrZWQgYnkgV0FGLjwvYm9keT48L2h0bWw+" # Base64 encoded HTML

  # Managed rules define the sets of rules to apply.
  managed_rule {
    type    = "DefaultRuleSet"
    version = "2.1" # Use a recent Default Rule Set version
  }

  managed_rule {
    type    = "Microsoft_BotManagerRuleSet"
    version = "1.0"
  }

  tags = {
    environment = "uat"
  }
}

# Azure Front Door (Classic) Instance
resource "azurerm_frontdoor" "frontdoor" {
  name                = var.front_door_name
  resource_group_name = azurerm_resource_group.rg.name

  # Frontend Endpoint where users connect
  frontend_endpoint {
    name                              = "DefaultFrontendEndpoint" # Can rename if needed
    host_name                         = "${var.front_door_name}.azurefd.net" # Default FD domain
    session_affinity_enabled          = true
    session_affinity_ttl_seconds      = 300
    web_application_firewall_policy_link_id = azurerm_frontdoor_firewall_policy.wafpolicy.id
  }

  # Backend Pool pointing to your application (e.g., AKS Ingress Controller Service)
  backend_pool {
    name = "DataAcquisitionBackend"

    backend {
      # IMPORTANT: Replace address with the actual FQDN or IP of your AKS ingress/service endpoint
      # This usually requires creating a Kubernetes Service of type LoadBalancer
      # or using an Ingress Controller like Nginx or Traefik with a public IP.
      host_header = "data-acquisition.uat.example.com" # Host header sent to backend
      address     = "20.42.1.123"                      # Placeholder: Replace with Public IP or FQDN of AKS service/ingress
      http_port   = 80
      https_port  = 443
      weight      = 100 # Relative weight for traffic distribution (if multiple backends)
      priority    = 1   # Lower number means higher priority (failover)
    }

    load_balancing_name = "DefaultLoadBalancingSettings"
    health_probe_name   = "DefaultHealthProbeSettings"
  }

  # Load Balancing Settings for the Backend Pool
  backend_pool_load_balancing {
    name                        = "DefaultLoadBalancingSettings"
    sample_size                 = 4 # Number of samples to consider for health
    successful_samples_required = 2 # Number of successful samples to mark backend as healthy
  }

  # Health Probe Settings for the Backend Pool
  backend_pool_health_probe {
    name                = "DefaultHealthProbeSettings"
    path                = "/healthz" # IMPORTANT: Change to your actual health check endpoint path
    protocol            = "Https"    # Use Https if your backend service uses TLS
    probe_method        = "GET"      # Or HEAD
    interval_in_seconds = 30         # Frequency of health probes
  }

  # Routing Rule to connect Frontend Endpoint to Backend Pool
  routing_rule {
    name               = "DefaultRoutingRule"
    accepted_protocols = ["Http", "Https"] # Protocols accepted at the frontend
    patterns_to_match  = ["/*"]            # Route all traffic
    frontend_endpoints = ["DefaultFrontendEndpoint"] # Name defined in frontend_endpoint block

    forwarding_configuration {
      forwarding_protocol = "HttpsOnly" # Redirect HTTP to HTTPS, or use "MatchRequest"
      backend_pool_name   = "DataAcquisitionBackend" # Name defined in backend_pool block
    }
  }

  tags = {
    environment = "uat"
  }

  # Ensure WAF policy exists before creating Front Door that links to it
  depends_on = [azurerm_frontdoor_firewall_policy.wafpolicy]
}

# Role Assignment: Grant AKS Managed Identity 'AcrPull' role on ACR
resource "azurerm_role_assignment" "acr_pull" {
  principal_id         = azurerm_kubernetes_cluster.aks.identity[0].principal_id
  role_definition_name = "AcrPull" # Allows pulling images from the registry
  scope                = azurerm_container_registry.acr.id # Assign role at the ACR scope
}

# --- Outputs ---

output "kube_config_raw" {
  description = "Raw Kubernetes configuration for the AKS cluster. Handle with care as it contains credentials."
  value       = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive   = true # Mark as sensitive to prevent exposure in logs
}

output "acr_login_server" {
  description = "The login server hostname of the Azure Container Registry"
  value       = azurerm_container_registry.acr.login_server
}

output "resource_group_name" {
  description = "The name of the resource group where resources are deployed"
  value       = azurerm_resource_group.rg.name
}

output "aks_cluster_name" {
  description = "The name of the deployed AKS cluster"
  value       = azurerm_kubernetes_cluster.aks.name
}

output "ppg_id" {
  description = "The resource ID of the Proximity Placement Group"
  value       = azurerm_proximity_placement_group.ppg.id
}

output "front_door_endpoint" {
  description = "The default frontend endpoint URL for the Azure Front Door (Classic)"
  value       = "https://${azurerm_frontdoor.frontdoor.frontend_endpoint[0].host_name}"
}

output "app_insights_instrumentation_key" {
  description = "The instrumentation key for Application Insights (deprecated, use connection_string)"
  value       = azurerm_application_insights.insights.instrumentation_key
  sensitive   = true
}

output "app_insights_connection_string" {
  description = "The connection string for Application Insights"
  value       = azurerm_application_insights.insights.connection_string
  sensitive   = true
}

output "aks_identity_principal_id" {
  description = "The Principal ID of the AKS cluster's system-assigned managed identity"
  value       = azurerm_kubernetes_cluster.aks.identity[0].principal_id
}
