# RT Sentiment Analysis - Azure Terraform Backend Configuration

# Azure storage backend for storing Terraform state
# Uncomment and configure for production use

# terraform {
#   backend "azurerm" {
#     resource_group_name  = "rt-sentiment-tfstate"
#     storage_account_name = "rtsentitfstate"
#     container_name       = "tfstate"
#     key                  = "rt-sentiment.uat.terraform.tfstate"
#     subscription_id      = "644936a7-e58a-4ccb-a882-0005f213f5bd"
#     tenant_id            = "1ced8c49-a03c-439c-9ff1-0c23f5128720"
#   }
# }

# Required providers
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.0.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = ">= 2.0.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0.0"
    }
    time = {
      source  = "hashicorp/time"
      version = ">= 0.7.0"
    }
  }
  
  # Minimum Terraform version
  required_version = ">= 1.0.0"
}