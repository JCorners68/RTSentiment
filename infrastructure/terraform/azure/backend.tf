# Sentimark - Azure Terraform Backend Configuration

# Azure storage backend for storing Terraform state
# For local development, using local state file initially
# For production, uncomment and configure the azurerm backend

terraform {
  # Using local state for now
  # To use Azure storage for state, uncomment this section and run:
  # ./run-terraform.sh init -backend-config=backends/sit.tfbackend
  
  /*
  backend "azurerm" {
    # No fixed values here - provided via backend-config file
    # Common settings that don't change per environment could go here
  }
  */
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