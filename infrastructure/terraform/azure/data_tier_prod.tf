# Sentimark - Data Tier Production Infrastructure
# This file contains the Terraform configuration for Phase 5 of the data tier implementation

# Random suffix for globally unique resource names
resource "random_string" "resource_suffix" {
  length  = 6
  special = false
  upper   = false
}

# Resource group for data tier production resources
resource "azurerm_resource_group" "data_tier" {
  name     = "${var.resource_group_name}-data-tier"
  location = var.location
  
  tags = merge(var.tags, {
    component = "data-tier"
    phase     = "production"
  })
}

# Network security group for data tier
resource "azurerm_network_security_group" "data_tier" {
  name                = "data-tier-nsg"
  location            = azurerm_resource_group.data_tier.location
  resource_group_name = azurerm_resource_group.data_tier.name
  
  security_rule {
    name                       = "AllowVNetInBound"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "VirtualNetwork"
  }
  
  tags = var.tags
}

# Virtual network for data tier
resource "azurerm_virtual_network" "data_tier" {
  name                = "data-tier-vnet"
  location            = azurerm_resource_group.data_tier.location
  resource_group_name = azurerm_resource_group.data_tier.name
  address_space       = ["10.1.0.0/16"]
  
  tags = var.tags
}

# Subnet for data tier services
resource "azurerm_subnet" "data_tier" {
  name                 = "data-tier-subnet"
  resource_group_name  = azurerm_resource_group.data_tier.name
  virtual_network_name = azurerm_virtual_network.data_tier.name
  address_prefixes     = ["10.1.0.0/24"]
  service_endpoints    = ["Microsoft.Storage", "Microsoft.KeyVault"]
  
  # Add required delegation for Container Instance
  delegation {
    name = "container-instance-delegation"
    service_delegation {
      name    = "Microsoft.ContainerInstance/containerGroups"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

# Associate NSG with subnet
resource "azurerm_subnet_network_security_group_association" "data_tier" {
  subnet_id                 = azurerm_subnet.data_tier.id
  network_security_group_id = azurerm_network_security_group.data_tier.id
}

# Iceberg module for data lake storage
module "iceberg" {
  source = "./modules/iceberg"
  
  base_name           = "sentimark"
  storage_account_name = "sentimarkice${random_string.resource_suffix.result}"
  resource_group_name = azurerm_resource_group.data_tier.name
  location            = azurerm_resource_group.data_tier.location
  tenant_id           = var.tenant_id
  subscription_id     = var.subscription_id
  service_principal_id = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  
  allowed_ips = []
  subnet_ids  = [azurerm_subnet.data_tier.id]
  
  # Docker Hub authentication
  docker_username  = var.docker_username
  docker_password  = var.docker_password
  deploy_container = var.deploy_container
  
  tags = merge(var.tags, {
    component = "iceberg"
  })
}

# App Configuration module for feature flags
module "app_config" {
  source = "./modules/app-config"
  
  app_config_name     = "sentimark-config-${random_string.resource_suffix.result}"
  resource_group_name = azurerm_resource_group.data_tier.name
  location            = azurerm_resource_group.data_tier.location
  service_principal_id = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  alert_action_group_id = module.monitoring.action_group_id
  
  # Start with Iceberg disabled but with infrastructure in place
  enable_iceberg_backend      = false
  enable_iceberg_optimizations = false
  enable_iceberg_partitioning = false
  enable_iceberg_time_travel  = false
  iceberg_roll_percentage     = 0
  
  tags = merge(var.tags, {
    component = "feature-flags"
  })
  
  depends_on = [module.monitoring]
}

# Monitoring module for observability
module "monitoring" {
  source = "./modules/monitoring"
  
  base_name          = "sentimark"
  log_analytics_name = "sentimark-iceberg-logs-${random_string.resource_suffix.result}"
  resource_group_name = azurerm_resource_group.data_tier.name
  location            = azurerm_resource_group.data_tier.location
  log_retention_days  = 30
  alert_email         = var.alert_email
  
  # Performance thresholds
  query_performance_threshold = 5000
  error_threshold             = 10
  
  tags = merge(var.tags, {
    component = "monitoring"
  })
}

# Key Vault for data tier secrets
resource "azurerm_key_vault" "data_tier" {
  name                       = "sentimark-dt-${random_string.resource_suffix.result}"
  location                   = azurerm_resource_group.data_tier.location
  resource_group_name        = azurerm_resource_group.data_tier.name
  tenant_id                  = var.tenant_id
  soft_delete_retention_days = 7
  purge_protection_enabled   = true
  sku_name                   = "standard"
  
  network_acls {
    default_action = "Deny"
    bypass         = "AzureServices"
    virtual_network_subnet_ids = [azurerm_subnet.data_tier.id]
    ip_rules       = ["0.0.0.0/0"]  # Allow all IPs for initial deployment (should be restricted in production)
  }
  
  # Access policy for terraform service principal is already configured in Azure 
  # We're not managing it via Terraform to avoid import issues
  
  tags = var.tags
}

# Grant AKS access to Key Vault
resource "azurerm_key_vault_access_policy" "aks" {
  key_vault_id = azurerm_key_vault.data_tier.id
  tenant_id    = var.tenant_id
  object_id    = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  
  secret_permissions = [
    "Get", "List"
  ]
}

# Access policy for terraform service principal is already configured in Azure
# Do not create it again to avoid conflict

# Store app config connection details in Key Vault
resource "azurerm_key_vault_secret" "app_config_endpoint" {
  name         = "app-config-endpoint"
  value        = module.app_config.app_config_endpoint
  key_vault_id = azurerm_key_vault.data_tier.id
  
  depends_on = [azurerm_key_vault_access_policy.aks]
}

resource "azurerm_key_vault_secret" "app_config_primary_key" {
  name         = "app-config-primary-key"
  value        = module.app_config.primary_read_key[0].connection_string
  key_vault_id = azurerm_key_vault.data_tier.id
  
  depends_on = [azurerm_key_vault_access_policy.aks]
}

# Store app insights connection details in Key Vault
resource "azurerm_key_vault_secret" "app_insights_connection_string" {
  name         = "app-insights-connection-string"
  value        = module.monitoring.app_insights_connection_string
  key_vault_id = azurerm_key_vault.data_tier.id
  
  depends_on = [azurerm_key_vault_access_policy.aks]
}

resource "azurerm_key_vault_secret" "app_insights_instrumentation_key" {
  name         = "app-insights-instrumentation-key"
  value        = module.monitoring.app_insights_instrumentation_key
  key_vault_id = azurerm_key_vault.data_tier.id
  
  depends_on = [azurerm_key_vault_access_policy.aks]
}

# Store Iceberg storage connection details in Key Vault
resource "azurerm_key_vault_secret" "iceberg_storage_connection_string" {
  name         = "iceberg-storage-connection-string"
  value        = module.iceberg.storage_account_primary_connection_string
  key_vault_id = azurerm_key_vault.data_tier.id
  
  depends_on = [azurerm_key_vault_access_policy.aks]
}

resource "azurerm_key_vault_secret" "iceberg_rest_catalog_url" {
  name         = "iceberg-rest-catalog-url"
  value        = "http://${module.iceberg.rest_catalog_name}:8181"
  key_vault_id = azurerm_key_vault.data_tier.id
  
  depends_on = [azurerm_key_vault_access_policy.aks]
}