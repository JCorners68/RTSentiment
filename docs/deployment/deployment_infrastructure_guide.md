# Azure Infrastructure Deployment Guide

This guide explains how to deploy the Sentimark infrastructure to Azure using Terraform with a focus on Azure CLI authentication as the recommended method.

## Prerequisites

- Azure subscription with Contributor access
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed and configured
- Docker installed (for running Terraform via container)
- Git repository cloned locally

## Authentication Methods

### Method 1: Azure CLI Authentication (Recommended)

This method uses your existing Azure CLI login credentials and is the simplest approach.

1. Login to Azure CLI:
   ```bash
   az login
   ```

2. Verify your login and subscription:
   ```bash
   az account show
   ```

3. Navigate to the Terraform directory:
   ```bash
   cd infrastructure/terraform/azure
   ```

4. Run Terraform commands using the helper script without credentials (it will auto-detect Azure CLI):
   ```bash
   ./run-terraform.sh init
   ./run-terraform.sh plan -var-file=terraform.sit.tfvars
   ./run-terraform.sh apply
   ```

### Method 2: Service Principal Authentication

If you need to use a service principal (common for CI/CD pipelines):

1. Navigate to the Terraform directory:
   ```bash
   cd infrastructure/terraform/azure
   ```

2. Run Terraform commands with service principal credentials:
   ```bash
   ./run-terraform.sh --client-id=YOUR_CLIENT_ID \
                     --client-secret=YOUR_CLIENT_SECRET \
                     --tenant-id=YOUR_TENANT_ID \
                     --subscription-id=YOUR_SUBSCRIPTION_ID \
                     init
   
   ./run-terraform.sh --client-id=YOUR_CLIENT_ID \
                     --client-secret=YOUR_CLIENT_SECRET \
                     --tenant-id=YOUR_TENANT_ID \
                     --subscription-id=YOUR_SUBSCRIPTION_ID \
                     plan -var-file=terraform.sit.tfvars
   
   ./run-terraform.sh --client-id=YOUR_CLIENT_ID \
                     --client-secret=YOUR_CLIENT_SECRET \
                     --tenant-id=YOUR_TENANT_ID \
                     --subscription-id=YOUR_SUBSCRIPTION_ID \
                     apply
   ```

## Deployment Environments

We have multiple environment configurations:

- **SIT (System Integration Testing)**: Use `-var-file=terraform.sit.tfvars`
- **UAT (User Acceptance Testing)**: Use `-var-file=terraform.uat.tfvars` (Coming soon)
- **Production**: Use `-var-file=terraform.tfvars`

## Deployment Process

1. **Initialize**: Set up the working directory and download providers
   ```bash
   ./run-terraform.sh init
   ```

2. **Plan**: Preview changes that will be made to the infrastructure
   ```bash
   ./run-terraform.sh plan -var-file=terraform.sit.tfvars -out=tfplan
   ```

3. **Apply**: Create or update the infrastructure
   ```bash
   ./run-terraform.sh apply tfplan
   ```
   
   Or apply directly:
   ```bash
   ./run-terraform.sh apply -var-file=terraform.sit.tfvars
   ```

4. **Destroy** (when needed): Remove all resources
   ```bash
   ./run-terraform.sh destroy -var-file=terraform.sit.tfvars
   ```

## Troubleshooting

### Azure CLI Authentication Issues

If you encounter authentication issues:

1. Verify your Azure CLI login status:
   ```bash
   az account show
   ```

2. If needed, login again:
   ```bash
   az login
   ```

3. Select the correct subscription:
   ```bash
   az account set --subscription YOUR_SUBSCRIPTION_ID
   ```

### Service Principal Authentication Issues

If using service principal authentication:

1. Verify the service principal has sufficient permissions in the subscription
2. Check that all credentials (client ID, client secret, tenant ID, subscription ID) are correct
3. Ensure the service principal has not expired

## Outputs

After successful deployment, Terraform outputs will display:

- AKS cluster information
- Front Door endpoint URL
- Azure Container Registry URL
- Application Insights instrumentation key

Use these outputs to configure your application deployment.

## Next Steps

After infrastructure deployment:

1. Configure kubectl to access the AKS cluster:
   ```bash
   az aks get-credentials --resource-group sentimark-sit-rg --name sentimark-sit-aks
   ```

2. Deploy the application using Kubernetes manifests:
   ```bash
   kubectl apply -f infrastructure/kubernetes/base/
   ```

## Additional Resources

- [Azure Terraform Provider Documentation](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [Azure AKS Documentation](https://docs.microsoft.com/en-us/azure/aks/)
- [Azure CLI Documentation](https://docs.microsoft.com/en-us/cli/azure/)