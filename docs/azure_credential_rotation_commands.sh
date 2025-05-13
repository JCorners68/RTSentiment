#!/bin/bash
# Azure Cloud Shell commands for rotating credentials
# Execute these commands one by one in Azure Cloud Shell after replacing the placeholder values

# 1. Get resource names (helps identify resources)
echo "### Listing Azure resources to identify affected ones ###"
# List storage accounts
az storage account list --query "[].{name:name, resourceGroup:resourceGroup}" -o table

# List container registries
az acr list --query "[].{name:name, resourceGroup:resourceGroup}" -o table

# List AD applications
az ad app list --query "[].{displayName:displayName, appId:appId}" -o table

# 2. Storage Account key rotation
echo "### Storage Account key rotation command ###"
# Replace with your actual storage account and resource group
STORAGE_ACCOUNT_NAME="your_storage_account_name"
STORAGE_RESOURCE_GROUP="your_resource_group"

az storage account keys renew \
  --resource-group $STORAGE_RESOURCE_GROUP \
  --account-name $STORAGE_ACCOUNT_NAME \
  --key key1 \
  --query "[0].value" -o tsv

# 3. Container Registry credential rotation
echo "### Azure Container Registry credential rotation ###"
# Replace with your actual ACR name and resource group
ACR_NAME="your_container_registry_name"
ACR_RESOURCE_GROUP="your_resource_group"

az acr credential renew \
  --name $ACR_NAME \
  --resource-group $ACR_RESOURCE_GROUP \
  --password-name password1 \
  --query "passwords[0].value" -o tsv

# 4. Azure AD application credential reset
echo "### Azure AD Application credential reset ###"
# Replace with your actual Application (Client) ID
APP_ID="your_application_client_id"
SECRET_NAME="Rotated-$(date +%Y-%m-%d)"

az ad app credential reset \
  --id $APP_ID \
  --display-name "$SECRET_NAME" \
  --query "password" -o tsv

echo ""
echo "IMPORTANT: After running these commands, update the new credentials in your local environment files."
echo "DO NOT commit the actual credentials to the repository."
echo "Consider using Azure Key Vault or environment variables for credential management going forward."