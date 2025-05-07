#!/bin/bash
# Script to run Terraform commands with service principal authentication only

# Load bash aliases for credentials if available (silently)
if [ -f ~/.bash_aliases ]; then
    source ~/.bash_aliases >/dev/null 2>&1
fi

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
  echo "  cost-plan   Create a plan for cost management only"
  echo "  cost-apply  Apply the cost management module only"
  echo "  state       Manage Terraform state (list, show, rm, etc.)"
  echo "  import      Import existing resources into Terraform"
  echo "  output      Display Terraform outputs"
  echo "  force-unlock Forcibly unlock the state file"
  echo ""
  echo "Examples:"
  echo "  ./run-terraform.sh --client-id=00000000-0000-0000-0000-000000000000 \\"
  echo "                      --client-secret=secret \\"
  echo "                      --tenant-id=11111111-1111-1111-1111-111111111111 \\"
  echo "                      --subscription-id=22222222-2222-2222-2222-222222222222 \\"
  echo "                      plan"
  echo ""
  echo "  ./run-terraform.sh --json-creds=credentials.json apply"
  echo ""
  echo "  ./run-terraform.sh cost-apply  # Apply only cost management module"
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
    init|validate|plan|apply|destroy|cost-plan|cost-apply|state|import|output|force-unlock)
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

# Convert TERRAFORM_ARGS to a proper array if it's not empty
if [ ${#TERRAFORM_ARGS[@]} -eq 0 ] && [ -n "$TERRAFORM_ARGS" ]; then
  TERRAFORM_ARGS=("$TERRAFORM_ARGS")
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

# Check for environment-specific credentials silently (no messages)
if [[ "$*" == *"terraform.sit.tfvars"* ]] && [ ! -z "${SIT_CLIENT_ID+x}" ]; then
  CLIENT_ID="${SIT_CLIENT_ID}"
  CLIENT_SECRET="${SIT_CLIENT_SECRET}"
  TENANT_ID="${SIT_TENANT_ID}"
  SUBSCRIPTION_ID="${SIT_SUBSCRIPTION_ID}"
elif [[ "$*" == *"terraform.uat.tfvars"* ]] && [ ! -z "${UAT_CLIENT_ID+x}" ]; then
  CLIENT_ID="${UAT_CLIENT_ID}"
  CLIENT_SECRET="${UAT_CLIENT_SECRET}"
  TENANT_ID="${UAT_TENANT_ID}"
  SUBSCRIPTION_ID="${UAT_SUBSCRIPTION_ID}"
elif [[ "$*" == *"terraform.prod.tfvars"* ]] && [ ! -z "${PROD_CLIENT_ID+x}" ]; then
  CLIENT_ID="${PROD_CLIENT_ID}"
  CLIENT_SECRET="${PROD_CLIENT_SECRET}"
  TENANT_ID="${PROD_TENANT_ID}"
  SUBSCRIPTION_ID="${PROD_SUBSCRIPTION_ID}"
elif [ -z "$CLIENT_ID" ] && [ ! -z "${SIT_CLIENT_ID+x}" ]; then
  CLIENT_ID="${SIT_CLIENT_ID}"
  CLIENT_SECRET="${SIT_CLIENT_SECRET}"
  TENANT_ID="${SIT_TENANT_ID}"
  SUBSCRIPTION_ID="${SIT_SUBSCRIPTION_ID}"
elif [ -z "$CLIENT_ID" ] && [ ! -z "${UAT_CLIENT_ID+x}" ]; then
  CLIENT_ID="${UAT_CLIENT_ID}"
  CLIENT_SECRET="${UAT_CLIENT_SECRET}"
  TENANT_ID="${UAT_TENANT_ID}"
  SUBSCRIPTION_ID="${UAT_SUBSCRIPTION_ID}"
fi

# Read from tfvars if needed (silently)
if [ -z "$TENANT_ID" ] && [ -f "terraform.tfvars" ]; then
  TENANT_ID=$(grep tenant_id terraform.tfvars | cut -d "=" -f2 | tr -d " \"")
fi

if [ -z "$SUBSCRIPTION_ID" ] && [ -f "terraform.tfvars" ]; then
  SUBSCRIPTION_ID=$(grep subscription_id terraform.tfvars | cut -d "=" -f2 | tr -d " \"")
fi

# Default to providers.tf if credentials still not found
if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ] || [ -z "$TENANT_ID" ] || [ -z "$SUBSCRIPTION_ID" ]; then
  # Read credentials from providers.tf if not specified via command line
  if [ -f "providers.tf" ]; then    
    # Extract credentials silently
    if [ -z "$CLIENT_ID" ]; then
      CLIENT_ID=$(grep -o 'client_id[[:space:]]*=[[:space:]]*"[^"]*"' providers.tf | cut -d'"' -f2)
    fi
    
    if [ -z "$CLIENT_SECRET" ]; then
      CLIENT_SECRET=$(grep -o 'client_secret[[:space:]]*=[[:space:]]*"[^"]*"' providers.tf | cut -d'"' -f2)
    fi
    
    if [ -z "$TENANT_ID" ]; then
      TENANT_ID=$(grep -o 'tenant_id[[:space:]]*=[[:space:]]*"[^"]*"' providers.tf | cut -d'"' -f2)
    fi
    
    if [ -z "$SUBSCRIPTION_ID" ]; then
      SUBSCRIPTION_ID=$(grep -o 'subscription_id[[:space:]]*=[[:space:]]*"[^"]*"' providers.tf | cut -d'"' -f2)
    fi
  else
    echo "Error: Missing required Azure credentials and providers.tf not found"
    echo "Please provide credentials via command line arguments"
    show_help
    exit 1
  fi
fi

# Create a temporary terraform.auto.tfvars file for service principal authentication
echo "# Temporary auto vars file created by run-terraform.sh" > terraform.auto.tfvars
echo "client_id = \"$CLIENT_ID\"" >> terraform.auto.tfvars
echo "client_secret = \"$CLIENT_SECRET\"" >> terraform.auto.tfvars
echo "tenant_id = \"$TENANT_ID\"" >> terraform.auto.tfvars
echo "subscription_id = \"$SUBSCRIPTION_ID\"" >> terraform.auto.tfvars

# Explicitly disable CLI and MSI auth
echo "use_cli = false" >> terraform.auto.tfvars
echo "use_msi = false" >> terraform.auto.tfvars

# Run Terraform with Docker

# Handle cost management specific commands
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

# Define environment variables for docker runs (service principal only)
ENV_VARS=(
  "-e" "ARM_USE_CLI=false"
  "-e" "ARM_USE_MSI=false"
  "-e" "ARM_CLIENT_ID=$CLIENT_ID" 
  "-e" "ARM_CLIENT_SECRET=$CLIENT_SECRET"
  "-e" "ARM_TENANT_ID=$TENANT_ID"
  "-e" "ARM_SUBSCRIPTION_ID=$SUBSCRIPTION_ID"
  "-e" "TF_VAR_use_cli=false"
  "-e" "TF_VAR_use_msi=false"
)

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
    docker run --rm -it \
      -v $(pwd):/workspace \
      -w /workspace \
      "${ENV_VARS[@]}" \
      hashicorp/terraform:latest $COMMAND $COST_MANAGEMENT_ARGS ${TERRAFORM_ARGS:+${TERRAFORM_ARGS[@]}}
  else
    # Either -auto-approve is set or we're not in an interactive terminal
    docker run --rm \
      -v $(pwd):/workspace \
      -w /workspace \
      "${ENV_VARS[@]}" \
      hashicorp/terraform:latest $COMMAND $COST_MANAGEMENT_ARGS ${TERRAFORM_ARGS:+${TERRAFORM_ARGS[@]}}
  fi
else
  # For non-interactive commands like plan, validate, etc.
  docker run --rm \
    -v $(pwd):/workspace \
    -w /workspace \
    "${ENV_VARS[@]}" \
    hashicorp/terraform:latest $COMMAND $COST_MANAGEMENT_ARGS ${TERRAFORM_ARGS:+${TERRAFORM_ARGS[@]}}
fi

exit_code=$?

# Clean up temporary tfvars file
rm -f terraform.auto.tfvars

if [ $exit_code -eq 0 ]; then
  # If this was a successful apply, display the outputs
  if [ "$COMMAND" = "apply" ]; then
    docker run --rm \
      -v $(pwd):/workspace \
      -w /workspace \
      "${ENV_VARS[@]}" \
      hashicorp/terraform:latest output
      
    # Display front door endpoint if available
    if docker run --rm -v $(pwd):/workspace -w /workspace "${ENV_VARS[@]}" hashicorp/terraform:latest output -json 2>/dev/null | grep -q "front_door_endpoint"; then
      docker run --rm \
        -v $(pwd):/workspace \
        -w /workspace \
        "${ENV_VARS[@]}" \
        hashicorp/terraform:latest output -raw front_door_endpoint
    fi
  fi
fi

exit $exit_code