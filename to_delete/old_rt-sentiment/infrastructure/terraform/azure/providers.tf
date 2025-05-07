# RT Sentiment Analysis - Azure Terraform Providers

# Azure Provider Configuration
provider "azurerm" {
  features {}
  
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
  
  # For running in CI/CD pipeline with Service Principal
  # client_id       = var.client_id
  # client_secret   = var.client_secret
  
  # For local development, use Azure CLI authentication
  # Skip this for now since we're just validating the configuration
  skip_provider_registration = true
  use_cli                    = false
}

# Kubernetes Provider Configuration
provider "kubernetes" {
  host                   = azurerm_kubernetes_cluster.aks.kube_config[0].host
  client_certificate     = base64decode(azurerm_kubernetes_cluster.aks.kube_config[0].client_certificate)
  client_key             = base64decode(azurerm_kubernetes_cluster.aks.kube_config[0].client_key)
  cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.aks.kube_config[0].cluster_ca_certificate)
}

# Random Provider for generating unique names
provider "random" {
}

# Time provider for managing time-based resources
provider "time" {
}
