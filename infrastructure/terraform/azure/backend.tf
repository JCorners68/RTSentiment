# Sentimark - Azure Terraform Backend Configuration

# Azure storage backend for storing Terraform state
# This configuration supports state locking to prevent concurrent modifications
# from multiple users or processes, avoiding potential state corruption

terraform {
  # Azure backend configuration - values are provided via backend-config files
  # To initialize the backend, run:
  # ./run-terraform.sh init -backend-config=backends/[environment].tfbackend
  # Example: ./run-terraform.sh init -backend-config=backends/sit.tfbackend

  backend "azurerm" {
    # No fixed values defined here - they come from backend-config files
    # Common settings for the backend:
    # - State locking is enabled by default with Azure Storage blobs
    # - Lease timeout for locks is 60 seconds by default

    # Connection/auth managed through Azure CLI or Service Principal
  }
}

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