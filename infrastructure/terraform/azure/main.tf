# RT Sentiment Analysis - Azure Terraform Configuration
# Main infrastructure file for the UAT environment

# Configure the Azure Provider
provider "azurerm" {
  features {}
  # Note: resource_provider_registrations = "none" is retained to avoid timeout issues
  # Ensure required providers (Microsoft.Monitor, Microsoft.Authorization) are registered
  resource_provider_registrations = "none"
}

# Get current subscription data
data "azurerm_subscription" "current" {}

# Reference existing resource group
data "azurerm_resource_group" "cost_management" {
  name = "cost-management-resources"
}

# 1. Cost Alert Action Group
resource "azurerm_monitor_action_group" "cost_alerts" {
  name                = "cost-management-alerts"
  resource_group_name = data.azurerm_resource_group.cost_management.name
  short_name          = "costAlerts"

  email_receiver {
    name                    = "primary-contact"
    email_address           = var.alert_email
    use_common_alert_schema = true
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
    zones                        = [1, 2, 3]  # For high availability
    only_critical_addons_enabled = false
  }

  # Use managed identity
  identity {
    type = "SystemAssigned"
  }

  # Network profile
  network_profile {
    network_plugin = "azure"
    network_policy = "calico"
    service_cidr   = "10.0.0.0/16"
    dns_service_ip = "10.0.0.10"
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
  name                = "rtsentimentwafpolicy"
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