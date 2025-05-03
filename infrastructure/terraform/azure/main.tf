provider "azurerm" {
  features {}
  subscription_id = "644936a7-e58a-4ccb-a882-0005f213f5bd"
  tenant_id       = "1ced8c49-a03c-439c-9ff1-0c23f5128720"
}

# Define variables
variable "resource_group_name" {
  description = "Name of the resource group"
  default     = "rt-sentiment-uat"
}

variable "location" {
  description = "Azure region"
  default     = "westus"  # Changed to US West region for low latency
}

variable "aks_cluster_name" {
  description = "Name of the AKS cluster"
  default     = "rt-sentiment-aks"
}

variable "acr_name" {
  description = "Name of the Azure Container Registry"
  default     = "rtsentiregistry"
}

variable "ppg_name" {
  description = "Name of the Proximity Placement Group"
  default     = "rt-sentiment-ppg"
}

variable "storage_account_name" {
  description = "Name of the Storage Account"
  default     = "rtsentistorage"
}

variable "front_door_name" {
  description = "Name of Azure Front Door"
  default     = "rt-sentiment-fd"
}

variable "app_insights_name" {
  description = "Name of Application Insights"
  default     = "rt-sentiment-insights"
}

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
  sku                 = "Premium"  # Upgraded for better performance
  admin_enabled       = true
  
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

# Create AKS cluster with PPG for low latency
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_cluster_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "rt-sentiment"
  kubernetes_version  = "1.26.6"  # Specify a stable version
  
  # Configure with private cluster option for better security
  private_cluster_enabled = true

  # Configure with PPG for low latency
  default_node_pool {
    name                         = "default"
    node_count                   = 3
    vm_size                      = "Standard_D4s_v3"  # More capable VM for better performance
    os_disk_size_gb              = 100
    proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id
    availability_zones           = ["1", "2", "3"]  # For high availability
    only_critical_addons_enabled = false
    
    # Enable auto-scaling
    enable_auto_scaling = true
    min_count           = 2
    max_count           = 5
  }

  # Add a dedicated node pool for data processing
  node_pool {
    name                         = "datanodes"
    vm_size                      = "Standard_D8s_v3"  # Larger VMs for data processing
    node_count                   = 2
    os_disk_size_gb              = 200
    proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id
    
    # Taints to ensure only specific workloads are scheduled
    node_taints = ["workload=dataprocessing:NoSchedule"]
  }

  # Use managed identity
  identity {
    type = "SystemAssigned"
  }

  # Network profile
  network_profile {
    network_plugin     = "azure"
    network_policy     = "calico"
    service_cidr       = "10.0.0.0/16"
    dns_service_ip     = "10.0.0.10"
    docker_bridge_cidr = "172.17.0.1/16"
  }

  # Enable monitoring
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.workspace.id
  }
  
  tags = {
    environment = "uat"
    ppg         = var.ppg_name
  }
}

# Create Log Analytics Workspace for monitoring
resource "azurerm_log_analytics_workspace" "workspace" {
  name                = "rt-sentiment-logs"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  
  tags = {
    environment = "uat"
  }
}

# Create Application Insights
resource "azurerm_application_insights" "insights" {
  name                = var.app_insights_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
  
  tags = {
    environment = "uat"
  }
}

# Create Azure Front Door for global distribution with low latency
resource "azurerm_frontdoor" "frontdoor" {
  name                = var.front_door_name
  resource_group_name = azurerm_resource_group.rg.name
  
  frontend_endpoint {
    name                              = "DefaultEndpoint"
    host_name                         = "${var.front_door_name}.azurefd.net"
    session_affinity_enabled          = true
    session_affinity_ttl_seconds      = 300
    web_application_firewall_policy_link_id = azurerm_frontdoor_firewall_policy.wafpolicy.id
  }
  
  backend_pool {
    name = "DataAcquisitionBackend"
    
    backend {
      host_header = "data-acquisition.uat.example.com"
      address     = "data-acquisition.uat.example.com"
      http_port   = 80
      https_port  = 443
      weight      = 100
      priority    = 1
    }
    
    load_balancing_name = "LoadBalancingSettings"
    health_probe_name   = "HealthProbeSettings"
  }
  
  backend_pool_load_balancing {
    name = "LoadBalancingSettings"
    sample_size = 4
    successful_samples_required = 2
  }
  
  backend_pool_health_probe {
    name = "HealthProbeSettings"
    path = "/"
    protocol = "Https"
    interval_in_seconds = 30
  }
  
  routing_rule {
    name               = "DataAcquisitionRoutingRule"
    accepted_protocols = ["Http", "Https"]
    patterns_to_match  = ["/*"]
    frontend_endpoints = ["DefaultEndpoint"]
    forwarding_configuration {
      forwarding_protocol = "HttpsOnly"
      backend_pool_name   = "DataAcquisitionBackend"
    }
  }
  
  tags = {
    environment = "uat"
  }
}

# Create Web Application Firewall Policy for Front Door
resource "azurerm_frontdoor_firewall_policy" "wafpolicy" {
  name                = "rt-sentiment-waf-policy"
  resource_group_name = azurerm_resource_group.rg.name
  enabled             = true
  mode                = "Prevention"
  
  managed_rule {
    type    = "DefaultRuleSet"
    version = "1.0"
  }
  
  managed_rule {
    type    = "Microsoft_BotManagerRuleSet"
    version = "1.0"
  }
}

# Assign AcrPull role to AKS service principal
resource "azurerm_role_assignment" "acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}

# Output AKS cluster credentials
output "kube_config" {
  value     = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive = true
}

# Output ACR login server
output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

# Output resource group name
output "resource_group_name" {
  value = azurerm_resource_group.rg.name
}

# Output AKS cluster name
output "aks_cluster_name" {
  value = azurerm_kubernetes_cluster.aks.name
}

# Output Proximity Placement Group ID
output "ppg_id" {
  value = azurerm_proximity_placement_group.ppg.id
}

# Output Front Door endpoint
output "front_door_endpoint" {
  value = "https://${var.front_door_name}.azurefd.net"
}

# Output Application Insights Instrumentation Key
output "app_insights_instrumentation_key" {
  value     = azurerm_application_insights.insights.instrumentation_key
  sensitive = true
}