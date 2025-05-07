# RT Sentiment Analysis - Azure Terraform Configuration
# Main infrastructure file for the UAT environment

# Provider configured in providers.tf
# This commented block is kept for reference
# provider "azurerm" {
#   features {}
#   # Note: resource_provider_registrations = "none" is retained to avoid timeout issues
#   # Ensure required providers (Microsoft.Monitor, Microsoft.Authorization) are registered
#   resource_provider_registrations = "none"
# }

# Get current subscription data
data "azurerm_subscription" "current" {}

# Create resource group for cost management if it doesn't exist
resource "azurerm_resource_group" "cost_management" {
  name     = "cost-management-resources"
  location = var.location
  
  tags = {
    environment = var.environment
    project     = "Sentimark" 
    managed_by  = "Terraform"
    CostCenter  = "Central IT"
  }
}

# Create main resource group for all resources
resource "azurerm_resource_group" "rg" {
  name     = var.resource_group_name
  location = var.location
  
  tags = {
    environment = var.environment
    project     = "Sentimark" 
    managed_by  = "Terraform"
    CostCenter  = "Sentimark"
  }
}

# Create storage account for application data
resource "azurerm_storage_account" "storage" {
  name                     = lower(replace("${var.environment}sentimarkstorage", "-", ""))
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  
  tags = {
    environment = var.environment
    project     = "Sentimark"
  }
}

# Create Container Registry for Docker images
resource "azurerm_container_registry" "acr" {
  name                = lower(replace("${var.environment}sentimarkacr", "-", ""))
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
  
  tags = {
    environment = var.environment
    project     = "Sentimark"
  }
}

# Create Proximity Placement Group for low latency
resource "azurerm_proximity_placement_group" "ppg" {
  name                = "${var.environment}-sentimark-ppg"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  
  tags = {
    environment = var.environment
    project     = "Sentimark"
  }
}

# Cost Management Module
module "cost_management" {
  source = "./modules/cost-management"
  
  environment         = var.environment
  resource_group_name = azurerm_resource_group.cost_management.name
  location            = var.location
  alert_email         = var.alert_email
  monthly_budget_amount = var.monthly_budget_amount
  autoshutdown_time   = var.autoshutdown_time
  apply_to_existing_vms = false # Set to true if you want to auto-shutdown existing VMs
  
  tags = {
    environment = var.environment
    project     = "Sentimark"
    managed_by  = "Terraform"
    CostCenter  = "Central IT"
  }
  
  depends_on = [azurerm_resource_group.cost_management]
}

# Create AKS cluster with PPG for low latency
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.aks_cluster_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "rt-sentiment"
  kubernetes_version  = var.kubernetes_version
  
  # Configure with private cluster option for better security
  private_cluster_enabled = true

  # Configure with PPG for low latency and spot instances for cost savings
  default_node_pool {
    name                         = "default"
    node_count                   = 1  # Single node for SIT environment to reduce vCPU usage
    vm_size                      = "Standard_D2s_v3"  # Smaller VM size with fewer CPUs
    os_disk_size_gb              = 64  # Reduced disk size
    proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id
    zones                        = []  # Explicitly set to empty array as westus doesn't support zones
    only_critical_addons_enabled = false
    temporary_name_for_rotation  = "tempnode1"  # Required for updating node pool properties (max 12 chars)
    
    # Spot instance configuration (save up to 90% on compute costs)
    # Note: System node pools (default) will run critical components
    # Keep a non-spot node for AKS system components
    #priority                     = "Spot"     # Uncomment if you want default pool as spot too (not recommended)
    #eviction_policy              = "Delete"   # Uncomment if you want default pool as spot
    #spot_max_price               = -1         # Uncomment if you want default pool as spot
    
    # Keeping default node pool as regular (not spot) to ensure system stability
    # This is recommended since system pods like CoreDNS run here
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
    environment = var.environment
    ppg         = var.ppg_name
    CostCenter  = "Sentimark"
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
    environment = var.environment
    CostCenter  = "Sentimark"
  }
}

# Create Application Insights
resource "azurerm_application_insights" "insights" {
  name                = var.app_insights_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.workspace.id
  
  tags = {
    environment = var.environment
    CostCenter  = "Sentimark"
  }
}

# Modern Azure Front Door (CDN) implementation
# Reference: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/cdn_frontdoor_profile

resource "azurerm_cdn_frontdoor_profile" "frontdoor" {
  count               = var.enable_cdn_frontdoor ? 1 : 0
  name                = var.front_door_name
  resource_group_name = azurerm_resource_group.rg.name
  sku_name            = "Standard_AzureFrontDoor"  # Using Standard SKU for SIT environment
  
  tags = {
    environment = var.environment
    CostCenter  = "Sentimark"
  }
}

resource "azurerm_cdn_frontdoor_endpoint" "default" {
  count                         = var.enable_cdn_frontdoor ? 1 : 0
  name                          = "default-endpoint"
  cdn_frontdoor_profile_id      = azurerm_cdn_frontdoor_profile.frontdoor[0].id
  enabled                       = true
}

resource "azurerm_cdn_frontdoor_origin_group" "data_acquisition" {
  count                   = var.enable_cdn_frontdoor ? 1 : 0
  name                    = "data-acquisition-origin-group"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.frontdoor[0].id
  
  load_balancing {
    sample_size                 = 4
    successful_samples_required = 2
    additional_latency_in_milliseconds = 0
  }

  health_probe {
    path                = "/health"
    protocol            = "Https"
    interval_in_seconds = 30
    request_type        = "GET"
  }
}

resource "azurerm_cdn_frontdoor_origin" "data_acquisition" {
  count                   = var.enable_cdn_frontdoor ? 1 : 0
  name                    = "data-acquisition-origin"
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.data_acquisition[0].id
  
  enabled                         = true
  host_name                       = "data-acquisition.${var.environment}.sentimark.com"
  http_port                       = 80
  https_port                      = 443
  origin_host_header              = "data-acquisition.${var.environment}.sentimark.com"
  priority                        = 1
  weight                          = 1000
  certificate_name_check_enabled  = true
}

resource "azurerm_cdn_frontdoor_rule_set" "default" {
  count                      = var.enable_cdn_frontdoor ? 1 : 0
  name                       = "defaultruleset"  # Must be between 1-60 chars, only letters and numbers, starting with a letter
  cdn_frontdoor_profile_id   = azurerm_cdn_frontdoor_profile.frontdoor[0].id
}

resource "azurerm_cdn_frontdoor_security_policy" "waf" {
  count                      = var.enable_cdn_frontdoor ? 1 : 0
  name                       = "wafsecuritypolicy"  # Alphanumeric only, no hyphens
  cdn_frontdoor_profile_id   = azurerm_cdn_frontdoor_profile.frontdoor[0].id

  security_policies {
    firewall {
      cdn_frontdoor_firewall_policy_id = azurerm_cdn_frontdoor_firewall_policy.wafpolicy[0].id

      association {
        domain {
          cdn_frontdoor_domain_id = azurerm_cdn_frontdoor_endpoint.default[0].id
        }
        patterns_to_match = ["/*"]
      }
    }
  }
}

resource "azurerm_cdn_frontdoor_firewall_policy" "wafpolicy" {
  count                      = var.enable_cdn_frontdoor ? 1 : 0
  name                       = "${var.environment}wafpolicy"  # Alphanumeric only, no hyphens
  resource_group_name        = azurerm_resource_group.rg.name
  sku_name                   = "Standard_AzureFrontDoor"  # Using Standard SKU for SIT environment
  enabled                    = true
  mode                       = "Prevention"
  
  # Note: managed_rule blocks are only available with Premium SKU
  # Using basic policy without managed rules for SIT environment
}

# Assign AcrPull role to AKS service principal
resource "azurerm_role_assignment" "acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.acr.id
  skip_service_principal_aad_check = true
}