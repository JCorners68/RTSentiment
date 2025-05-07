#!/bin/bash
# Simple wrapper for terraform that supports cost management commands

# Ensure we're logged in with az CLI
if ! az account show &>/dev/null; then
  echo "Not logged in to Azure CLI. Please run 'az login' first."
  exit 1
else
  echo "Azure CLI authenticated as $(az account show --query user.name -o tsv)"
  echo "Using subscription: $(az account show --query name -o tsv)"
fi

# Parse command
COMMAND="$1"
shift

# Handle cost management specific commands
if [[ "$COMMAND" == "cost-plan" ]]; then
  echo "Planning cost management module only..."
  terraform plan -target=module.cost_management "$@"
elif [[ "$COMMAND" == "cost-apply" ]]; then
  echo "Applying cost management module only..."
  terraform apply -target=module.cost_management "$@"
else
  # Run regular Terraform command
  terraform $COMMAND "$@"
fi