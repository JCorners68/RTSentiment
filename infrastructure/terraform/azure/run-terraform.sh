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
  echo "  -t, --tenant-id TENANT_ID      Azure Tenant ID"
  echo "  -b, --subscription-id SUB_ID   Azure Subscription ID"
  echo "  -j, --json-creds JSON_FILE     Path to JSON credentials file"
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
  echo "  ./run-terraform.sh --client-id=00000000-0000-0000-0000-000000000000 \\"
  echo "                      --client-secret=secret \\"
  echo "                      --tenant-id=11111111-1111-1111-1111-111111111111 \\"
  echo "                      --subscription-id=22222222-2222-2222-2222-222222222222 \\"
  echo "                      plan"
  echo ""
  echo "  ./run-terraform.sh --json-creds=credentials.json apply"
}

# Default values
CLIENT_ID=""
CLIENT_SECRET=""
TENANT_ID=""
SUBSCRIPTION_ID=""
JSON_CREDS=""
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
    -t|--tenant-id)
      TENANT_ID="$2"
      shift 2
      ;;
    --tenant-id=*)
      TENANT_ID="${1#*=}"
      shift
      ;;
    -b|--subscription-id)
      SUBSCRIPTION_ID="$2"
      shift 2
      ;;
    --subscription-id=*)
      SUBSCRIPTION_ID="${1#*=}"
      shift
      ;;
    -j|--json-creds)
      JSON_CREDS="$2"
      shift 2
      ;;
    --json-creds=*)
      JSON_CREDS="${1#*=}"
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
      # Keep remaining arguments for passing to Terraform
      TERRAFORM_ARGS=("$1")
      shift
      while [[ $# -gt 0 ]]; do
        TERRAFORM_ARGS+=("$1")
        shift
      done
      break
      ;;
  esac
done

# Validate inputs
if [ -z "$COMMAND" ]; then
  echo "Error: No Terraform command specified."
  show_help
  exit 1
fi

# Initialize TERRAFORM_ARGS if not already set
if [ -z "${TERRAFORM_ARGS+x}" ]; then
  TERRAFORM_ARGS=()
fi

# Check if we need to extract credentials from JSON
if [ -n "$JSON_CREDS" ]; then
  if [ ! -f "$JSON_CREDS" ]; then
    echo "Error: JSON credentials file not found: $JSON_CREDS"
    exit 1
  fi
  
  echo "Extracting credentials from JSON file: $JSON_CREDS"
  CLIENT_ID=$(grep -o '"clientId": *"[^"]*"' "$JSON_CREDS" | cut -d'"' -f4)
  CLIENT_SECRET=$(grep -o '"clientSecret": *"[^"]*"' "$JSON_CREDS" | cut -d'"' -f4)
  TENANT_ID=$(grep -o '"tenantId": *"[^"]*"' "$JSON_CREDS" | cut -d'"' -f4)
  SUBSCRIPTION_ID=$(grep -o '"subscriptionId": *"[^"]*"' "$JSON_CREDS" | cut -d'"' -f4)
  
  if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ] || [ -z "$TENANT_ID" ] || [ -z "$SUBSCRIPTION_ID" ]; then
    echo "Error: Failed to extract all required credentials from JSON file."
    exit 1
  fi
fi

# Try to read from tfvars if tenant/subscription not provided
if [ -z "$TENANT_ID" ] && [ -f "terraform.tfvars" ]; then
  TENANT_ID=$(grep tenant_id terraform.tfvars | cut -d "=" -f2 | tr -d " \"")
  echo "Using tenant ID from terraform.tfvars: ${TENANT_ID:0:8}...${TENANT_ID:(-8)}"
fi

if [ -z "$SUBSCRIPTION_ID" ] && [ -f "terraform.tfvars" ]; then
  SUBSCRIPTION_ID=$(grep subscription_id terraform.tfvars | cut -d "=" -f2 | tr -d " \"")
  echo "Using subscription ID from terraform.tfvars: ${SUBSCRIPTION_ID:0:8}...${SUBSCRIPTION_ID:(-8)}"
fi

# Validate that we have all required credentials
if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ] || [ -z "$TENANT_ID" ] || [ -z "$SUBSCRIPTION_ID" ]; then
  echo "Error: Missing required Azure credentials"
  echo "Please provide either:"
  echo "  1. Individual credentials (client-id, client-secret, tenant-id, subscription-id)"
  echo "  2. A JSON credentials file with --json-creds"
  echo "  3. Ensure tenant_id and subscription_id are defined in terraform.tfvars"
  show_help
  exit 1
fi

# Display obscured credentials for verification
echo "Using Azure credentials:"
echo "Client ID: ${CLIENT_ID:0:8}...${CLIENT_ID:(-8)}"
echo "Client Secret: ********"
echo "Tenant ID: ${TENANT_ID:0:8}...${TENANT_ID:(-8)}"
echo "Subscription ID: ${SUBSCRIPTION_ID:0:8}...${SUBSCRIPTION_ID:(-8)}"

# Create a temporary terraform.auto.tfvars file to override the values in terraform.tfvars
echo "# Temporary auto vars file created by run-terraform.sh" > terraform.auto.tfvars
echo "client_id = \"$CLIENT_ID\"" >> terraform.auto.tfvars
echo "client_secret = \"$CLIENT_SECRET\"" >> terraform.auto.tfvars
echo "tenant_id = \"$TENANT_ID\"" >> terraform.auto.tfvars
echo "subscription_id = \"$SUBSCRIPTION_ID\"" >> terraform.auto.tfvars

# Run Terraform with Docker
echo "Running terraform $COMMAND with provided credentials..."
# Add -it flag for interactive commands that need input
if [ "$COMMAND" = "apply" ] || [ "$COMMAND" = "destroy" ]; then
  # Check if -auto-approve is in the remaining arguments
  auto_approve=false
  for arg in "$@"; do
    if [ "$arg" = "-auto-approve" ]; then
      auto_approve=true
      break
    fi
  done
  
  # If -auto-approve is not specified and this is an interactive terminal, use -it
  if [ "$auto_approve" = "false" ] && [ -t 0 ]; then
    echo "Interactive mode: you will be prompted to confirm the action"
    docker run --rm -it \
      -v $(pwd):/workspace \
      -w /workspace \
      -e ARM_CLIENT_ID="$CLIENT_ID" \
      -e ARM_CLIENT_SECRET="$CLIENT_SECRET" \
      -e ARM_SUBSCRIPTION_ID="$SUBSCRIPTION_ID" \
      -e ARM_TENANT_ID="$TENANT_ID" \
      hashicorp/terraform:latest $COMMAND "${TERRAFORM_ARGS[@]}"
  else
    # Either -auto-approve is set or we're not in an interactive terminal
    docker run --rm \
      -v $(pwd):/workspace \
      -w /workspace \
      -e ARM_CLIENT_ID="$CLIENT_ID" \
      -e ARM_CLIENT_SECRET="$CLIENT_SECRET" \
      -e ARM_SUBSCRIPTION_ID="$SUBSCRIPTION_ID" \
      -e ARM_TENANT_ID="$TENANT_ID" \
      hashicorp/terraform:latest $COMMAND "${TERRAFORM_ARGS[@]}"
  fi
else
  # For non-interactive commands like plan, validate, etc.
  docker run --rm \
    -v $(pwd):/workspace \
    -w /workspace \
    -e ARM_CLIENT_ID="$CLIENT_ID" \
    -e ARM_CLIENT_SECRET="$CLIENT_SECRET" \
    -e ARM_SUBSCRIPTION_ID="$SUBSCRIPTION_ID" \
    -e ARM_TENANT_ID="$TENANT_ID" \
    hashicorp/terraform:latest $COMMAND "${TERRAFORM_ARGS[@]-}"
fi

exit_code=$?

# Clean up temporary tfvars file
rm -f terraform.auto.tfvars

if [ $exit_code -eq 0 ]; then
  echo "Terraform $COMMAND completed successfully."
  
  # If this was a successful apply, display the outputs
  if [ "$COMMAND" = "apply" ]; then
    echo "Terraform outputs:"
    docker run --rm \
      -v $(pwd):/workspace \
      -w /workspace \
      -e ARM_CLIENT_ID="$CLIENT_ID" \
      -e ARM_CLIENT_SECRET="$CLIENT_SECRET" \
      -e ARM_SUBSCRIPTION_ID="$SUBSCRIPTION_ID" \
      -e ARM_TENANT_ID="$TENANT_ID" \
      hashicorp/terraform:latest output
      
    echo ""
    echo "Front Door endpoint:"
    docker run --rm \
      -v $(pwd):/workspace \
      -w /workspace \
      -e ARM_CLIENT_ID="$CLIENT_ID" \
      -e ARM_CLIENT_SECRET="$CLIENT_SECRET" \
      -e ARM_SUBSCRIPTION_ID="$SUBSCRIPTION_ID" \
      -e ARM_TENANT_ID="$TENANT_ID" \
      hashicorp/terraform:latest output -raw front_door_endpoint
  fi
else
  echo "Terraform $COMMAND failed with exit code $exit_code."
fi

exit $exit_code