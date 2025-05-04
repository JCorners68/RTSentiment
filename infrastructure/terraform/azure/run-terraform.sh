#!/bin/bash
# Script to run Terraform commands with proper credentials

# Function to display help
show_help() {
  echo "Usage: ./run-terraform.sh [OPTIONS] COMMAND"
  echo ""
  echo "Run Terraform commands with proper Azure authentication."
  echo ""
  echo "Options:"
  echo "  -c, --client-id CLIENT_ID      Azure Service Principal Client ID"
  echo "  -s, --client-secret SECRET     Azure Service Principal Client Secret"
  echo "  -h, --help                     Show this help message"
  echo ""
  echo "Commands:"
  echo "  init        Initialize Terraform configuration"
  echo "  validate    Validate Terraform configuration"
  echo "  plan        Create a Terraform execution plan"
  echo "  apply       Apply the Terraform execution plan"
  echo "  destroy     Destroy the Terraform-managed infrastructure"
  echo ""
  echo "Examples:"
  echo "  ./run-terraform.sh --client-id=00000000-0000-0000-0000-000000000000 --client-secret=secret init"
  echo "  ./run-terraform.sh -c 00000000-0000-0000-0000-000000000000 -s secret plan"
}

# Default values
CLIENT_ID=""
CLIENT_SECRET=""
COMMAND=""

# Parse options
while [[ $# -gt 0 ]]; do
  case $1 in
    -c|--client-id)
      CLIENT_ID="$2"
      shift 2
      ;;
    --client-id=*)
      CLIENT_ID="${1#*=}"
      shift
      ;;
    -s|--client-secret)
      CLIENT_SECRET="$2"
      shift 2
      ;;
    --client-secret=*)
      CLIENT_SECRET="${1#*=}"
      shift
      ;;
    -h|--help)
      show_help
      exit 0
      ;;
    init|validate|plan|apply|destroy)
      COMMAND="$1"
      shift
      ;;
    *)
      echo "Unknown option: $1"
      show_help
      exit 1
      ;;
  esac
done

# Validate inputs
if [ -z "$COMMAND" ]; then
  echo "Error: No Terraform command specified."
  show_help
  exit 1
fi

# Run Terraform with Docker
if [ -n "$CLIENT_ID" ] && [ -n "$CLIENT_SECRET" ]; then
  # Use provided Service Principal credentials
  echo "Running terraform $COMMAND with provided Service Principal credentials..."
  docker run --rm \
    -v $(pwd):/workspace \
    -w /workspace \
    -e ARM_CLIENT_ID="$CLIENT_ID" \
    -e ARM_CLIENT_SECRET="$CLIENT_SECRET" \
    -e ARM_SUBSCRIPTION_ID=$(grep subscription_id terraform.tfvars | cut -d "=" -f2 | tr -d " \"") \
    -e ARM_TENANT_ID=$(grep tenant_id terraform.tfvars | cut -d "=" -f2 | tr -d " \"") \
    hashicorp/terraform:latest $COMMAND $@
else
  # Use environment credentials
  echo "Running terraform $COMMAND (using environment credentials)..."
  echo "Note: For authentication, please ensure Azure credentials are properly configured."
  docker run --rm \
    -v $(pwd):/workspace \
    -w /workspace \
    hashicorp/terraform:latest $COMMAND $@
fi