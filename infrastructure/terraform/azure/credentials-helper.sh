#!/bin/bash
# Helper script to configure Terraform to use direct credentials 
# (not requiring Azure CLI or Service Principal)

# Get the access token from your current az cli session
ACCESS_TOKEN=$(az account get-access-token --query accessToken -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

# Create a Terraform auto.tfvars file
cat > direct-auth.auto.tfvars << EOF
# Auto-generated credentials for direct authentication
# Do not commit this file
subscription_id = "$SUBSCRIPTION_ID"
tenant_id       = "$TENANT_ID"
EOF

# Set environment variables for ARM provider
export ARM_ACCESS_TOKEN="$ACCESS_TOKEN"
export ARM_SUBSCRIPTION_ID="$SUBSCRIPTION_ID"
export ARM_TENANT_ID="$TENANT_ID"

echo "Access token and environment variables configured successfully."
echo "ARM_ACCESS_TOKEN is set (hidden for security)"
echo "ARM_SUBSCRIPTION_ID=$ARM_SUBSCRIPTION_ID"
echo "ARM_TENANT_ID=$ARM_TENANT_ID"