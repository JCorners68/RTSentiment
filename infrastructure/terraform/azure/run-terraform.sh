#!/bin/bash
# Script to run Terraform commands with service principal authentication
# Enhanced with state locking support, better error handling, and secure credential management

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UTILS_DIR="$SCRIPT_DIR/utils"
SECURE_CREDS_SCRIPT="$UTILS_DIR/secure_credentials.sh"

# Load secure credentials handler if available
if [ -f "$SECURE_CREDS_SCRIPT" ]; then
    source "$SECURE_CREDS_SCRIPT" >/dev/null 2>&1
fi

# For backward compatibility, load bash aliases if secure credentials handler not available
if [ ! -f "$SECURE_CREDS_SCRIPT" ] && [ -f ~/.bash_aliases ]; then
    source ~/.bash_aliases >/dev/null 2>&1
fi

# Set color codes for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default timeout values in minutes
OPERATION_TIMEOUT=30
CLIENT_TIMEOUT=60
LOCK_TIMEOUT=600  # seconds

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
  echo "  -o, --operation-timeout MINS   Set operation timeout in minutes (default: $OPERATION_TIMEOUT)"
  echo "  -l, --lock-timeout SECS        Set state lock timeout in seconds (default: $LOCK_TIMEOUT)"
  echo "  -r, --retries COUNT            Number of lock acquisition retries (default: 10)"
  echo "  -d, --debug                    Enable Terraform debug logging"
  echo "  --no-secure-creds              Disable secure credential handling"
  echo "  --creds-method METHOD          Credential method: env, file, vault, msi (default: env)"
  echo "  --creds-profile PROFILE        Credential profile name (default: default)"
  echo "  --keyvault NAME                Azure Key Vault name for credentials"
  echo "  --use-msi                      Use managed identity for authentication"
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
  echo "State Management Options:"
  echo "  init -backend-config=backends/sit.tfbackend   Initialize with SIT backend"
  echo "  init -backend-config=backends/uat.tfbackend   Initialize with UAT backend"
  echo "  init -backend-config=backends/prod.tfbackend  Initialize with PROD backend"
  echo "  force-unlock LOCK_ID                          Forcibly unlock state"
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
  echo ""
  echo "  # Initialize with remote state and locking"
  echo "  ./run-terraform.sh init -backend-config=backends/sit.tfbackend"
  echo ""
  echo "  # Force unlock state if locked (use with caution!)"
  echo "  ./run-terraform.sh force-unlock LOCK_ID"
}

# Default values
CLIENT_ID=""
CLIENT_SECRET=""
TENANT_ID=""
SUBSCRIPTION_ID=""
JSON_CREDS=""
COMMAND=""
DEBUG_MODE=false
LOCK_RETRIES=10
USE_SECURE_CREDS=true
CREDS_METHOD="env"
CREDS_PROFILE="default"
AZURE_KEYVAULT=""
USE_MSI=false

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
    -o|--operation-timeout)
      OPERATION_TIMEOUT="$2"
      shift 2
      ;;
    --operation-timeout=*)
      OPERATION_TIMEOUT="${1#*=}"
      shift
      ;;
    -l|--lock-timeout)
      LOCK_TIMEOUT="$2"
      shift 2
      ;;
    --lock-timeout=*)
      LOCK_TIMEOUT="${1#*=}"
      shift
      ;;
    -r|--retries)
      LOCK_RETRIES="$2"
      shift 2
      ;;
    --retries=*)
      LOCK_RETRIES="${1#*=}"
      shift
      ;;
    -d|--debug)
      DEBUG_MODE=true
      shift
      ;;
    --no-secure-creds)
      USE_SECURE_CREDS=false
      shift
      ;;
    --creds-method)
      CREDS_METHOD="$2"
      shift 2
      ;;
    --creds-method=*)
      CREDS_METHOD="${1#*=}"
      shift
      ;;
    --creds-profile)
      CREDS_PROFILE="$2"
      shift 2
      ;;
    --creds-profile=*)
      CREDS_PROFILE="${1#*=}"
      shift
      ;;
    --keyvault)
      AZURE_KEYVAULT="$2"
      CREDS_METHOD="vault"
      shift 2
      ;;
    --keyvault=*)
      AZURE_KEYVAULT="${1#*=}"
      CREDS_METHOD="vault"
      shift
      ;;
    --use-msi)
      USE_MSI=true
      CREDS_METHOD="msi"
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

# Load credentials securely
ENV_FILE=""
if [ "$USE_SECURE_CREDS" = true ] && [ -f "$SECURE_CREDS_SCRIPT" ]; then
  echo -e "${BLUE}Using secure credential handling...${NC}"

  # Determine environment based on command line args
  ENVIRONMENT=""
  if [[ "$*" == *"terraform.sit.tfvars"* ]] || [[ "$*" == *"sit.tfbackend"* ]]; then
    ENVIRONMENT="sit"
  elif [[ "$*" == *"terraform.uat.tfvars"* ]] || [[ "$*" == *"uat.tfbackend"* ]]; then
    ENVIRONMENT="uat"
  elif [[ "$*" == *"terraform.prod.tfvars"* ]] || [[ "$*" == *"prod.tfbackend"* ]]; then
    ENVIRONMENT="prod"
  fi

  # Use managed identity if specified
  if [ "$USE_MSI" = true ]; then
    echo -e "${BLUE}Using managed identity authentication...${NC}"
    ENV_FILE=$("$SECURE_CREDS_SCRIPT" msi --quiet)

  # Use Azure Key Vault if specified
  elif [ -n "$AZURE_KEYVAULT" ]; then
    echo -e "${BLUE}Loading credentials from Azure Key Vault: $AZURE_KEYVAULT${NC}"
    if [ -n "$ENVIRONMENT" ]; then
      ENV_FILE=$("$SECURE_CREDS_SCRIPT" vault --keyvault "$AZURE_KEYVAULT" --environment "$ENVIRONMENT" --quiet)
    else
      ENV_FILE=$("$SECURE_CREDS_SCRIPT" vault --keyvault "$AZURE_KEYVAULT" --quiet)
    fi

  # Use specified credential method
  else
    # If we have environment, use it when loading credentials
    if [ -n "$ENVIRONMENT" ]; then
      ENV_FILE=$("$SECURE_CREDS_SCRIPT" load --method "$CREDS_METHOD" --profile "$CREDS_PROFILE" --environment "$ENVIRONMENT" --quiet)
    else
      ENV_FILE=$("$SECURE_CREDS_SCRIPT" load --method "$CREDS_METHOD" --profile "$CREDS_PROFILE" --quiet)
    fi
  fi

  # Check if credentials were loaded successfully
  if [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
    echo -e "${GREEN}Credentials loaded successfully${NC}"

    # Load environment variables from file
    source "$ENV_FILE"

    # Use environment variables for authentication
    CLIENT_ID="$ARM_CLIENT_ID"
    CLIENT_SECRET="$ARM_CLIENT_SECRET"
    TENANT_ID="$ARM_TENANT_ID"
    SUBSCRIPTION_ID="$ARM_SUBSCRIPTION_ID"

    # Set MSI flag if specified
    if [ "$ARM_USE_MSI" = "true" ]; then
      USE_MSI=true
    fi
  else
    echo -e "${YELLOW}Could not load credentials securely. Falling back to legacy method.${NC}"
    USE_SECURE_CREDS=false
  fi
fi

# Fall back to legacy credential loading if secure method failed or was disabled
if [ "$USE_SECURE_CREDS" = false ]; then
  echo -e "${YELLOW}Using legacy credential handling...${NC}"

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
      echo -e "${RED}Error: Missing required Azure credentials and providers.tf not found${NC}"
      echo "Please provide credentials via command line arguments"
      show_help
      exit 1
    fi
  fi
fi

# If we're using MSI, we don't need to create a tfvars file
if [ "$USE_MSI" = true ]; then
  echo -e "${BLUE}Using Managed Identity authentication.${NC}"
  # Create a minimal tfvars file for MSI
  echo "# Temporary auto vars file created by run-terraform.sh" > terraform.auto.tfvars
  if [ -n "$SUBSCRIPTION_ID" ]; then
    echo "subscription_id = \"$SUBSCRIPTION_ID\"" >> terraform.auto.tfvars
  fi
  echo "use_cli = false" >> terraform.auto.tfvars
  echo "use_msi = true" >> terraform.auto.tfvars
else
  # Create a temporary terraform.auto.tfvars file for service principal authentication
  echo "# Temporary auto vars file created by run-terraform.sh" > terraform.auto.tfvars
  echo "client_id = \"$CLIENT_ID\"" >> terraform.auto.tfvars
  echo "client_secret = \"$CLIENT_SECRET\"" >> terraform.auto.tfvars
  echo "tenant_id = \"$TENANT_ID\"" >> terraform.auto.tfvars
  echo "subscription_id = \"$SUBSCRIPTION_ID\"" >> terraform.auto.tfvars

  # Explicitly disable CLI and MSI auth
  echo "use_cli = false" >> terraform.auto.tfvars
  echo "use_msi = false" >> terraform.auto.tfvars
fi

# Set proper permissions on tfvars file
chmod 600 terraform.auto.tfvars

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

# Define environment variables for docker runs
ENV_VARS=()

# Add common variables
ENV_VARS+=("-e" "ARM_SUBSCRIPTION_ID=$SUBSCRIPTION_ID")

# Configure authentication method
if [ "$USE_MSI" = true ]; then
  # Managed Identity authentication
  ENV_VARS+=("-e" "ARM_USE_CLI=false")
  ENV_VARS+=("-e" "ARM_USE_MSI=true")
  ENV_VARS+=("-e" "TF_VAR_use_cli=false")
  ENV_VARS+=("-e" "TF_VAR_use_msi=true")

  # Add volume mount for Azure CLI configuration
  if [ -d "$HOME/.azure" ]; then
    ENV_VARS+=("-v" "$HOME/.azure:/root/.azure")
  fi
else
  # Service Principal authentication
  ENV_VARS+=("-e" "ARM_USE_CLI=false")
  ENV_VARS+=("-e" "ARM_USE_MSI=false")
  ENV_VARS+=("-e" "ARM_CLIENT_ID=$CLIENT_ID")
  ENV_VARS+=("-e" "ARM_CLIENT_SECRET=$CLIENT_SECRET")
  ENV_VARS+=("-e" "ARM_TENANT_ID=$TENANT_ID")
  ENV_VARS+=("-e" "TF_VAR_use_cli=false")
  ENV_VARS+=("-e" "TF_VAR_use_msi=false")
fi

# Add state locking enhancements and timeout configurations
# State locks are now configured with better timeouts and RBAC support
if [[ "$COMMAND" == "apply" || "$COMMAND" == "destroy" || "$COMMAND" == "plan" || "$COMMAND" == "import" ]]; then
  # Enable Azure AD authentication for better RBAC support with storage
  ENV_VARS+=("-e" "ARM_STORAGE_USE_AZUREAD=true")

  # Apply user-configured timeout settings or use defaults
  # Increase state lock timeout from default 60s to configured value for large state files
  # This helps with complex operations on large infrastructures
  ENV_VARS+=("-e" "TF_AZURE_STATE_LOCK_TIMEOUT=$LOCK_TIMEOUT")

  # Set operation timeout for individual Azure Resource Manager operations
  ENV_VARS+=("-e" "ARM_OPERATION_TIMEOUT_MINUTES=$OPERATION_TIMEOUT")

  # Increase client timeout for large operations
  ENV_VARS+=("-e" "ARM_CLIENT_TIMEOUT_MINUTES=$CLIENT_TIMEOUT")

  # Enable enhanced state locking with retry capability
  ENV_VARS+=("-e" "TF_LOCK_RETRY_COUNT=$LOCK_RETRIES")
  ENV_VARS+=("-e" "TF_LOCK_RETRY_WAIT_MIN=5")
  ENV_VARS+=("-e" "TF_LOCK_RETRY_WAIT_MAX=30")

  # Report configuration to user
  echo -e "${BLUE}Timeout Configuration:${NC}"
  echo "  Operation timeout: $OPERATION_TIMEOUT minutes"
  echo "  Lock timeout: $LOCK_TIMEOUT seconds"
  echo "  Lock retries: $LOCK_RETRIES"
fi

# Enable debug mode if requested
if [ "$DEBUG_MODE" = true ]; then
  ENV_VARS+=("-e" "TF_LOG=DEBUG")
  echo -e "${BLUE}Debug mode enabled.${NC}"
fi

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

# Enhanced error handling with detailed diagnostics and recovery suggestions
if [ $exit_code -ne 0 ]; then
  # Look for log files in multiple potential locations
  LOG_FILES=(".terraform/terraform.log" "terraform.tfstate.d/terraform.log" ".terraform.lock.hcl" ".terraform/tmp*.log")
  LOCK_ID=""

  echo -e "${YELLOW}Checking for error details...${NC}"

  # Check for state lock errors
  if grep -q "Error acquiring the state lock" ${LOG_FILES[@]} 2>/dev/null; then
    echo -e "${RED}Error: State lock could not be acquired.${NC}"
    echo -e "${YELLOW}The state is locked by another user or process.${NC}"

    # Try to extract the lock ID from logs
    LOCK_ID=$(grep -o 'ID: [a-zA-Z0-9-]*' ${LOG_FILES[@]} 2>/dev/null | head -1 | cut -d ' ' -f 2 || echo "")

    # Get lock owner information if available
    LOCK_INFO=""
    if [ -n "$LOCK_ID" ]; then
      echo -e "Lock ID: ${BLUE}$LOCK_ID${NC}"

      # Try to get more information about the lock
      if docker run --rm -v $(pwd):/workspace -w /workspace "${ENV_VARS[@]}" hashicorp/terraform:latest state pull 2>/dev/null | grep -q "LockInfo"; then
        LOCK_INFO=$(docker run --rm -v $(pwd):/workspace -w /workspace "${ENV_VARS[@]}" hashicorp/terraform:latest state pull | grep -A 10 "LockInfo" || echo "")
        echo -e "Lock info:\n$LOCK_INFO"
      fi

      echo -e "\nTo force-unlock the state (use with caution):"
      echo -e "   ${BLUE}./run-terraform.sh force-unlock $LOCK_ID${NC}"
    else
      echo -e "${YELLOW}Could not determine lock ID from logs.${NC}"
    fi

    # Offer remediation advice
    echo -e "\n${YELLOW}Possible remediation steps:${NC}"
    echo -e "1. Wait for the other operation to complete"
    echo -e "2. Check for stuck Terraform processes or failed CI jobs"
    echo -e "3. Use force-unlock if you're absolutely sure no other process is running"
    echo -e "4. If in a CI/CD environment, check if a previous job failed without releasing the lock"

  # Check for state loading errors
  elif grep -q "failed to load state" ${LOG_FILES[@]} 2>/dev/null; then
    echo -e "${RED}Error: Failed to load state.${NC}"
    echo -e "${YELLOW}This could be due to:${NC}"
    echo -e "1. Incorrect backend configuration"
    echo -e "2. Missing access permissions"
    echo -e "3. Backend storage account or container doesn't exist"
    echo -e "4. Service principal permissions issues"

    # Check available backends
    if [ -d "backends" ]; then
      echo -e "\nAvailable backend configurations:"
      ls -la backends/
    fi

    echo -e "\nTry running: ${BLUE}./setup_terraform_backend.sh --environment=${ENVIRONMENT:-sit}${NC}"
    echo -e "Or check credentials with: ${BLUE}az account show${NC}"

  # Check for Azure provider errors
  elif grep -q "authorization_failed\|AuthorizationFailed" ${LOG_FILES[@]} 2>/dev/null; then
    echo -e "${RED}Error: Azure authorization failed.${NC}"
    echo -e "${YELLOW}This could be due to:${NC}"
    echo -e "1. Expired or invalid credentials"
    echo -e "2. Insufficient permissions for the service principal"
    echo -e "3. Role assignments not fully propagated (can take up to 5 minutes)"

    echo -e "\nTry verifying your service principal permissions:"
    echo -e "   ${BLUE}az login --service-principal --username \$ARM_CLIENT_ID --password \$ARM_CLIENT_SECRET --tenant \$ARM_TENANT_ID${NC}"
    echo -e "   ${BLUE}az account show${NC}"

  # Check for timeout issues
  elif grep -q "context deadline exceeded\|operation timed out\|DeadlineExceeded" ${LOG_FILES[@]} 2>/dev/null; then
    echo -e "${RED}Error: Operation timed out.${NC}"
    echo -e "${YELLOW}This could be due to:${NC}"
    echo -e "1. Network connectivity issues"
    echo -e "2. Azure API throttling"
    echo -e "3. Timeouts too short for complex operations"

    echo -e "\nTry increasing the timeouts by setting these environment variables:"
    echo -e "   ${BLUE}ARM_OPERATION_TIMEOUT_MINUTES=60${NC}"
    echo -e "   ${BLUE}ARM_CLIENT_TIMEOUT_MINUTES=90${NC}"
    echo -e "Or run again with the --operation-timeout flag:"
    echo -e "   ${BLUE}./run-terraform.sh $COMMAND --operation-timeout=60${NC}"

  # Generic error handling as a fallback
  else
    echo -e "${RED}Terraform command failed with exit code $exit_code.${NC}"
    echo -e "${YELLOW}Check the output above for specific error messages.${NC}"

    # Try to display some state information if available
    if [ -d ".terraform" ]; then
      echo -e "\n${BLUE}Current Terraform configuration:${NC}"
      ls -la .terraform/

      # Check for provider configurations
      if [ -f "providers.tf" ]; then
        echo -e "\n${BLUE}Provider configuration:${NC}"
        grep -A 10 "provider" providers.tf | grep -v "password\|secret"
      fi
    fi

    echo -e "\n${YELLOW}Try running with debug logging:${NC}"
    echo -e "   ${BLUE}TF_LOG=DEBUG ./run-terraform.sh $COMMAND${NC}"
  fi
fi

# Clean up temporary files
rm -f terraform.auto.tfvars

# Clean up the secure environment file if it exists
if [ -n "$ENV_FILE" ] && [ -f "$ENV_FILE" ]; then
  rm -f "$ENV_FILE"
fi

# Make sure any temporary credential environment variables are unset
if [ -f "$SECURE_CREDS_SCRIPT" ]; then
  source "$SECURE_CREDS_SCRIPT" clear >/dev/null 2>&1
fi

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