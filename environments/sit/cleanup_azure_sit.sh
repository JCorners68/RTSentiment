#!/bin/bash

# RT Sentiment Analysis - SIT Environment Cleanup Script
# This script removes the SIT environment from Azure.

# Display a warning at the start
echo "WARNING: This script will destroy the entire SIT environment in Azure."
echo "All resources, including the AKS cluster, will be permanently deleted."
echo "Data stored in databases or other persistent storage will be lost."
read -p "Are you sure you want to continue? (y/n): " CONFIRM

if [[ $CONFIRM != "y" && $CONFIRM != "Y" ]]; then
    echo "Cleanup cancelled."
    exit 0
fi

# Set environment variables
SUBSCRIPTION_ID="644936a7-e58a-4ccb-a882-0005f213f5bd"
TENANT_ID="1ced8c49-a03c-439c-9ff1-0c23f5128720"
RESOURCE_GROUP="sentimark-sit-rg"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
TERRAFORM_DIR="${SCRIPT_DIR}/../../infrastructure/terraform/azure"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Azure CLI is not installed. Please install Azure CLI first."
    exit 1
fi

# Ensure Azure CLI is logged in
echo "Checking Azure CLI login status..."
az account show &> /dev/null
if [ $? -ne 0 ]; then
    echo "Not logged in to Azure CLI. Please run 'az login --tenant $TENANT_ID' first."
    exit 1
fi

# Set subscription
echo "Setting subscription to $SUBSCRIPTION_ID..."
az account set --subscription $SUBSCRIPTION_ID --tenant $TENANT_ID

# Navigate to the Terraform directory
cd "$TERRAFORM_DIR" || { echo "Error: Could not navigate to Terraform directory"; exit 1; }
echo "Working directory: $(pwd)"

# Check if Terraform state exists
if [ ! -f "terraform.tfstate" ]; then
    echo "Warning: Terraform state file not found. The environment may not have been deployed with Terraform."
    read -p "Do you want to attempt cleanup without Terraform state? This might not remove all resources. (y/n): " CONTINUE
    if [[ $CONTINUE != "y" && $CONTINUE != "Y" ]]; then
        echo "Cleanup cancelled."
        exit 0
    fi
    
    # Try to delete the resource group directly
    echo "Attempting to delete resource group $RESOURCE_GROUP directly..."
    az group delete --name $RESOURCE_GROUP --yes --no-wait
    echo "Resource group deletion has been initiated. Please check the Azure portal to confirm."
    exit 0
fi

# Try to destroy with Terraform
echo "Using Terraform to destroy the SIT environment..."
echo "This may take several minutes to complete..."

# Create SIT-specific tfvars file if it doesn't exist
if [ ! -f "terraform.sit.tfvars" ]; then
    cat > terraform.sit.tfvars << EOF
# SIT Environment Configuration
environment = "sit"
resource_group_name = "$RESOURCE_GROUP"
subscription_id = "$SUBSCRIPTION_ID"
tenant_id = "$TENANT_ID"
EOF
    echo "Created SIT-specific configuration file"
fi

# Run Terraform destroy
terraform init
terraform destroy -auto-approve -var-file=terraform.sit.tfvars

# Check if the destruction was successful
if [ $? -ne 0 ]; then
    echo "Error: Terraform destruction failed."
    read -p "Do you want to attempt direct resource group deletion? (y/n): " FORCE_DELETE
    if [[ $FORCE_DELETE == "y" || $FORCE_DELETE == "Y" ]]; then
        echo "Attempting to delete resource group $RESOURCE_GROUP directly..."
        az group delete --name $RESOURCE_GROUP --yes --no-wait
        echo "Resource group deletion has been initiated. Please check the Azure portal to confirm."
    else
        echo "Cleanup incomplete. You may need to manually remove resources from the Azure portal."
        exit 1
    fi
else
    echo "SIT environment has been successfully destroyed."
fi

# Clean up local configuration files
echo "Cleaning up local configuration files..."
rm -f "${SCRIPT_DIR}/config/kubeconfig"
rm -f "${SCRIPT_DIR}/config/service_endpoints.txt"
rm -f "${SCRIPT_DIR}/config/cluster_info.txt"
rm -f "${SCRIPT_DIR}/config/set_env.sh"

echo "SIT environment cleanup completed."