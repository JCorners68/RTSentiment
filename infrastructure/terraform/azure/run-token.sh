#!/bin/bash
# Script to run Terraform with Azure access token authentication

# Make sure Azure CLI is installed
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

# Get access token for current login
ACCESS_TOKEN=$(az account get-access-token --query accessToken -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "Using access token authentication with:"
echo "Subscription ID: $SUBSCRIPTION_ID"
echo "Tenant ID: $TENANT_ID"

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

# Run Terraform with token-based authentication
# Note: ARM_ACCESS_TOKEN environment variable is used by the provider
export ARM_ACCESS_TOKEN="$ACCESS_TOKEN"
export ARM_SUBSCRIPTION_ID="$SUBSCRIPTION_ID"
export ARM_TENANT_ID="$TENANT_ID"

docker run --rm -it \
  -v "$(pwd):/workspace" \
  -w "/workspace" \
  -e ARM_ACCESS_TOKEN="$ARM_ACCESS_TOKEN" \
  -e ARM_SUBSCRIPTION_ID="$ARM_SUBSCRIPTION_ID" \
  -e ARM_TENANT_ID="$ARM_TENANT_ID" \
  hashicorp/terraform:latest \
  $COMMAND $COST_MANAGEMENT_ARGS "$@"