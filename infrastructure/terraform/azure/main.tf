provider "azurerm" {
  features {}
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "rt-sentiment-uat"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "westus"
}

variable "aks_cluster_name" {
  description = "Name of the AKS cluster"
  type        = string
  default     = "rt-sentiment-aks"
}

variable "acr_name" {
  description = "Name of the Azure Container Registry"
  type        = string
  default     = "rtsentiregistry"
}

variable "ppg_name" {
  description = "Name of the Proximity Placement Group"
  type        = string
  default     = "rt-sentiment-ppg"
}

variable "storage_account_name" {
  description = "Name of the Storage Account"
  type        = string
  default     = "rtsentistorage"
}

variable "front_door_name" {
  description = "Name of Azure Front Door"
  type        = string
  default     = "rt-sentiment-fd"
}

variable "app_insights_name" {
  description = "Name of Application Insights"
  type        = string
  default     = "rt-sentiment-insights"
}

resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
}

resource "azurerm_proximity_placement_group" "ppg" {
  name                = var.ppg_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  tags = {
    environment = "uat"
    purpose     = "low-latency"
  }
}

resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Premium"
  admin_enabled       = true

  tags = {
    environment = "uat"
  }
}

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

resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_cluster_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "aksdns"

  default_node_pool {
    name                = "default"
    vm_size             = "Standard_DS2_v2"
    node_count          = 1
    min_count           = 1
    max_count           = 3
    enable_auto_scaling = true
    availability_zones  = ["1", "2", "3"]
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin     = "azure"
    docker_bridge_cidr = "172.17.0.1/16"
    service_cidr       = "10.0.0.0/16"
    dns_service_ip     = "10.0.0.10"
  }

  tags = {
    environment = "uat"
  }
}

resource "azurerm_kubernetes_cluster_node_pool" "datanodes" {
  name                         = "datanodes"
  kubernetes_cluster_id        = azurerm_kubernetes_cluster.aks.id
  vm_size                      = "Standard_D8s_v3"
  node_count                   = 2
  os_disk_size_gb              = 200
  proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id
  availability_zones           = ["1", "2", "3"]
  enable_auto_scaling          = true
  min_count                    = 1
  max_count                    = 4
  mode                         = "User"
  node_taints                  = ["workload=dataprocessing:NoSchedule"]

  tags = {
    pool_type = "user"
    workload  = "dataprocessing"
  }

  depends_on = [azurerm_kubernetes_cluster.aks]
}

resource "azurerm_application_insights" "insights" {
  name                = var.app_insights_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.workspace.id

  tags = {
    environment = "uat"
  }
}

resource "azurerm_frontdoor_firewall_policy" "wafpolicy" {
  name                = "RtSentimentWafPolicy"
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

  tags = {
    environment = "uat"
  }
}

resource "azurerm_frontdoor" "frontdoor" {
  name                = var.front_door_name
  resource_group_name = azurerm_resource_group.rg.name

  frontend_endpoint {
    name                             = "DefaultEndpoint"
    host_name                        = "${var.front_door_name}.azurefd.net"
    session_affinity_enabled         = true
    session_affinity_ttl_seconds     = 300
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
    name                        = "LoadBalancingSettings"
    sample_size                 = 4
    successful_samples_required = 2
  }

  backend_pool_health_probe {
    name                = "HealthProbeSettings"
    path                = "/"
    protocol            = "Https"
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

  depends_on = [azurerm_frontdoor_firewall_policy.wafpolicy]
}

resource "azurerm_role_assignment" "acr_pull" {
  principal_id         = azurerm_kubernetes_cluster.aks.identity[0].principal_id
  role_definition_name = "AcrPull"
  scope                = azurerm_container_registry.acr.id

  depends_on = [
    azurerm_kubernetes_cluster.aks,
    azurerm_container_registry.acr
  ]
}

output "kube_config_raw" {
  description = "Raw Kubernetes configuration for the AKS cluster. Handle with care."
  value       = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive   = true
}

output "acr_login_server" {
  description = "The login server hostname of the Azure Container Registry"
  value       = azurerm_container_registry.acr.login_server
}

output "resource_group_name" {
  description = "The name of the resource group"
  value       = azurerm_resource_group.rg.name
}

output "aks_cluster_name" {
  description = "The name of the AKS cluster"
  value       = azurerm_kubernetes_cluster.aks.name
}

output "ppg_id" {
  description = "The resource ID of the Proximity Placement Group"
  value       = azurerm_proximity_placement_group.ppg.id
}

output "front_door_endpoint" {
  description = "The default frontend endpoint URL for the Azure Front Door"
  value       = "https://${azurerm_frontdoor.frontdoor.frontend_endpoint[0].host_name}"
}

output "app_insights_instrumentation_key" {
  description = "The instrumentation key for Application Insights"
  value       = azurerm_application_insights.insights.instrumentation_key
  sensitive   = true
}
