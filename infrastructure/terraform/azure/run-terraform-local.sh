#!/bin/bash
# Script to run Terraform commands with Azure CLI authentication

# Make sure Azure CLI is available
if ! command -v az &> /dev/null; then
  echo "Azure CLI is not installed. Please install it first."
  exit 1
fi

# Check Azure CLI login status
az account show &> /dev/null
if [ $? -ne 0 ]; then
  echo "Not logged in to Azure CLI. Please run 'az login' first."
  exit 1
fi

# Display subscription info
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)

echo "Using Azure CLI authentication with:"
echo "Subscription: $SUBSCRIPTION_NAME"
echo "Tenant ID: $TENANT_ID"
echo "Subscription ID: $SUBSCRIPTION_ID"

# Handle cost management specific commands
COMMAND="$1"
shift  # Remove the first argument (the command)

COST_MANAGEMENT_ARGS=""
if [[ "$COMMAND" == "cost-plan" ]]; then
  COST_MANAGEMENT_ARGS="-target=module.cost_management"
  COMMAND="plan"
  echo "Planning cost management module only..."
elif [[ "$COMMAND" == "cost-apply" ]]; then
  COST_MANAGEMENT_ARGS="-target=module.cost_management"
  COMMAND="apply"
  echo "Applying cost management module only..."
fi

# Run Terraform directly
echo "Running terraform $COMMAND with Azure CLI authentication"
terraform $COMMAND $COST_MANAGEMENT_ARGS "$@"