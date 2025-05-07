#!/bin/bash

# Direct Terraform wrapper script that uses the Docker container
# This script supports cost management commands

# Ensure we're logged in with az CLI
if ! az account show &>/dev/null; then
  echo "Not logged in to Azure CLI. Please run 'az login' first."
  exit 1
else
  echo "Azure CLI authenticated as $(az account show --query user.name -o tsv)"
  echo "Using subscription: $(az account show --query name -o tsv)"
  echo "Subscription ID: $(az account show --query id -o tsv)"
  echo "Tenant ID: $(az account show --query tenantId -o tsv)"
fi

# Parse command
COMMAND="$1"
shift

# Set up environment variables
export ARM_USE_CLI=true
export ARM_CLIENT_ID=""
export ARM_CLIENT_SECRET=""

# Handle cost management specific commands
COST_ARGS=""
if [[ "$COMMAND" == "cost-plan" ]]; then
  echo "Planning cost management module only..."
  COMMAND="plan"
  COST_ARGS="-target=module.cost_management"
elif [[ "$COMMAND" == "cost-apply" ]]; then
  echo "Applying cost management module only..."
  COMMAND="apply"
  COST_ARGS="-target=module.cost_management"
fi

# Run Terraform in Docker with Azure CLI authentication
docker run --rm -it \
  -v $(pwd):/workspace \
  -v $HOME/.azure:/root/.azure \
  -w /workspace \
  -e ARM_USE_CLI=true \
  hashicorp/terraform:latest \
  $COMMAND $COST_ARGS "$@"