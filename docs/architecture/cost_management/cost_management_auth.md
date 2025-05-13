# Cost Management Authentication Guide

## Overview

This document provides guidance on authentication options for deploying the cost management module in the Sentimark infrastructure.

## Authentication Options

When deploying the cost management module, you have several authentication options:

### Option 1: Azure CLI Authentication (Recommended for Local Development)

The simplest approach for local development is using Azure CLI:

1. Install Terraform locally
2. Run `az login` to authenticate with Azure
3. Navigate to the terraform directory: `cd infrastructure/terraform/azure`
4. Run Terraform commands directly:
   ```bash
   terraform init
   terraform plan -target=module.cost_management
   terraform apply -target=module.cost_management
   ```

### Option 2: Service Principal Authentication (Recommended for CI/CD)

For CI/CD pipelines or automated deployments:

1. Create a service principal with Contributor access
2. Update the `terraform.tfvars` file with:
   ```
   client_id     = "YOUR_SP_CLIENT_ID"
   client_secret = "YOUR_SP_CLIENT_SECRET"
   ```
3. Run the terraform commands with these credentials:
   ```bash
   terraform init
   terraform plan -target=module.cost_management
   terraform apply -target=module.cost_management
   ```

### Option 3: Docker with Azure CLI Authentication

When using Docker for isolation:

```bash
# First login with Azure CLI
az login

# Run Terraform in Docker with mounted credentials
docker run --rm \
  -v $(pwd):/workspace \
  -v $HOME/.azure:/root/.azure \
  -w /workspace \
  -e ARM_USE_CLI=true \
  hashicorp/terraform:latest \
  plan -target=module.cost_management
```

### Option 4: Access Token Authentication

For short-lived operations:

```bash
# Get current access token
ACCESS_TOKEN=$(az account get-access-token --query accessToken -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

# Run Terraform with the token
docker run --rm \
  -v $(pwd):/workspace \
  -w /workspace \
  -e ARM_ACCESS_TOKEN=$ACCESS_TOKEN \
  -e ARM_SUBSCRIPTION_ID=$SUBSCRIPTION_ID \
  -e ARM_TENANT_ID=$TENANT_ID \
  hashicorp/terraform:latest \
  plan -target=module.cost_management
```

## Troubleshooting Authentication Issues

### Common Error Messages

1. **"executable file not found in $PATH"**
   - The Docker container doesn't have Azure CLI installed
   - Solution: Use Option 2 or 4 above which don't require Azure CLI

2. **"unauthorized_client"** 
   - Service principal credentials may be incorrect
   - Solution: Verify client_id, client_secret match your Azure tenant

3. **"no Authorizer could be configured"**
   - No valid authentication method was found
   - Solution: Make sure environment variables are correctly passed

4. **"Service Principal not found"**
   - The service principal doesn't exist or you don't have access
   - Solution: Check service principal in Azure portal

### Provider Configuration

For direct token authentication, use this provider configuration:

```hcl
provider "azurerm" {
  features {}
  
  # Basic subscription and tenant - explicitly defined
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
}
```

For service principal authentication:

```hcl
provider "azurerm" {
  features {}
  
  subscription_id = var.subscription_id
  tenant_id       = var.tenant_id
  client_id       = var.client_id
  client_secret   = var.client_secret
}
```

## Next Steps

Once authentication is resolved, the cost management module should deploy successfully. You can then proceed to configure:

1. Budget thresholds
2. Alert emails
3. Auto-shutdown schedules
4. Resource restrictions

See the main [Cost Management documentation](cost_management.md) for details on these features.