#!/bin/bash
# Secure Credential Helper for Terraform
#
# This script provides secure credential handling for Terraform operations
# by using environment variables, Azure Key Vault, or managed identities
# without exposing credentials in plain text or writing them to disk.

set -e

# Colors for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Constants
CREDENTIAL_DIR="${HOME}/.sentimark/credentials"
CREDENTIAL_FILE="${CREDENTIAL_DIR}/.tf_creds"
TEMP_DIR=$(mktemp -d)
CREDENTIAL_MASK="********"
CREDS_ENV_PREFIX="TF_CREDS_"

# Clean up temporary files on exit
trap 'rm -rf "$TEMP_DIR"; unset_temp_env' EXIT INT TERM

# Function to show usage information
show_usage() {
  cat << EOF
Secure Credential Helper for Terraform

USAGE:
  $(basename "$0") [COMMAND] [OPTIONS]

COMMANDS:
  load           Load credentials into environment variables
  check          Check if credentials are available
  clear          Clear credentials from environment
  save           Save credentials (use with extreme caution)
  vault          Use Azure Key Vault for credentials
  msi            Configure for managed identity authentication

OPTIONS:
  -p, --profile NAME         Credential profile name (default: default)
  -e, --environment ENV      Environment name (sit, uat, prod)
  -k, --keyvault NAME        Azure Key Vault name
  -s, --secret-name NAME     Secret name in Key Vault
  -r, --resource-group RG    Resource group for Key Vault
  -m, --method METHOD        Auth method (env, file, vault, msi)
  -q, --quiet                Suppress non-error output
  -h, --help                 Show this help message

EXAMPLES:
  # Load credentials from environment variables
  $(basename "$0") load --method env

  # Use Azure Key Vault for credentials
  $(basename "$0") vault --keyvault myVault --environment prod

  # Configure for managed identity
  $(basename "$0") msi
EOF
  exit 0
}

# Function to validate that required tools are installed
check_prerequisites() {
  # Check for Azure CLI if using Key Vault or MSI
  if [[ "$AUTH_METHOD" == "vault" || "$AUTH_METHOD" == "msi" ]]; then
    if ! command -v az &> /dev/null; then
      echo -e "${RED}Error: Azure CLI not found. Please install Azure CLI.${NC}"
      exit 1
    fi
    
    # Check if logged in to Azure
    if ! az account show &> /dev/null; then
      echo -e "${YELLOW}Warning: Not logged in to Azure. Some features may not work.${NC}"
      echo -e "${YELLOW}Run 'az login' to authenticate.${NC}"
    fi
  fi
  
  # Check for jq for JSON processing
  if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq not found. Using fallback methods for JSON processing.${NC}"
  fi
}

# Function to create credential directory with secure permissions
setup_credential_dir() {
  if [ ! -d "$CREDENTIAL_DIR" ]; then
    mkdir -p "$CREDENTIAL_DIR"
    chmod 700 "$CREDENTIAL_DIR"  # Only owner can access
  fi
}

# Function to securely load credentials from environment variables
load_from_env() {
  local ARM_CLIENT_ID=${ARM_CLIENT_ID:-}
  local ARM_CLIENT_SECRET=${ARM_CLIENT_SECRET:-}
  local ARM_TENANT_ID=${ARM_TENANT_ID:-}
  local ARM_SUBSCRIPTION_ID=${ARM_SUBSCRIPTION_ID:-}
  
  # Check for required variables
  if [ -z "$ARM_CLIENT_ID" ] || [ -z "$ARM_CLIENT_SECRET" ] || \
     [ -z "$ARM_TENANT_ID" ] || [ -z "$ARM_SUBSCRIPTION_ID" ]; then
    # Check for alternate environment variables (TF_VAR_*)
    ARM_CLIENT_ID=${TF_VAR_client_id:-$ARM_CLIENT_ID}
    ARM_CLIENT_SECRET=${TF_VAR_client_secret:-$ARM_CLIENT_SECRET}
    ARM_TENANT_ID=${TF_VAR_tenant_id:-$ARM_TENANT_ID}
    ARM_SUBSCRIPTION_ID=${TF_VAR_subscription_id:-$ARM_SUBSCRIPTION_ID}
    
    # Also check for SIT/UAT/PROD specific variables
    if [ -n "$ENVIRONMENT" ]; then
      ENV_UPPER=$(echo "$ENVIRONMENT" | tr '[:lower:]' '[:upper:]')
      eval ARM_CLIENT_ID=\${${ENV_UPPER}_CLIENT_ID:-$ARM_CLIENT_ID}
      eval ARM_CLIENT_SECRET=\${${ENV_UPPER}_CLIENT_SECRET:-$ARM_CLIENT_SECRET}
      eval ARM_TENANT_ID=\${${ENV_UPPER}_TENANT_ID:-$ARM_TENANT_ID}
      eval ARM_SUBSCRIPTION_ID=\${${ENV_UPPER}_SUBSCRIPTION_ID:-$ARM_SUBSCRIPTION_ID}
    fi
  fi
  
  # Validate required variables
  if [ -z "$ARM_CLIENT_ID" ] || [ -z "$ARM_CLIENT_SECRET" ] || \
     [ -z "$ARM_TENANT_ID" ] || [ -z "$ARM_SUBSCRIPTION_ID" ]; then
    return 1
  fi
  
  # Set temporary environment variables with unique prefix
  export "${CREDS_ENV_PREFIX}CLIENT_ID=$ARM_CLIENT_ID"
  export "${CREDS_ENV_PREFIX}CLIENT_SECRET=$ARM_CLIENT_SECRET"
  export "${CREDS_ENV_PREFIX}TENANT_ID=$ARM_TENANT_ID"
  export "${CREDS_ENV_PREFIX}SUBSCRIPTION_ID=$ARM_SUBSCRIPTION_ID"
  
  return 0
}

# Function to load credentials from secure credential file
load_from_file() {
  local profile=${1:-default}
  local cred_file="${CREDENTIAL_DIR}/${profile}.creds"
  
  if [ ! -f "$cred_file" ]; then
    echo -e "${RED}Error: Credential file not found: $cred_file${NC}"
    return 1
  fi
  
  # Check file permissions
  local file_perms=$(stat -c "%a" "$cred_file")
  if [ "$file_perms" != "600" ]; then
    echo -e "${YELLOW}Warning: Insecure permissions on credential file: $file_perms${NC}"
    echo -e "${YELLOW}Fixing permissions...${NC}"
    chmod 600 "$cred_file"
  fi
  
  # Source the credential file
  source "$cred_file"
  
  # Validate required variables
  if [ -z "$ARM_CLIENT_ID" ] || [ -z "$ARM_CLIENT_SECRET" ] || \
     [ -z "$ARM_TENANT_ID" ] || [ -z "$ARM_SUBSCRIPTION_ID" ]; then
    return 1
  fi
  
  # Set temporary environment variables with unique prefix
  export "${CREDS_ENV_PREFIX}CLIENT_ID=$ARM_CLIENT_ID"
  export "${CREDS_ENV_PREFIX}CLIENT_SECRET=$ARM_CLIENT_SECRET"
  export "${CREDS_ENV_PREFIX}TENANT_ID=$ARM_TENANT_ID"
  export "${CREDS_ENV_PREFIX}SUBSCRIPTION_ID=$ARM_SUBSCRIPTION_ID"
  
  return 0
}

# Function to load credentials from Azure Key Vault
load_from_vault() {
  local vault_name=$1
  local secret_name=$2
  local resource_group=$3
  
  if [ -z "$vault_name" ]; then
    echo -e "${RED}Error: Key Vault name not specified${NC}"
    return 1
  fi
  
  if [ -z "$secret_name" ]; then
    secret_name="terraform-${ENVIRONMENT:-default}-credentials"
  fi
  
  # Attempt to get secret from Key Vault
  local secret_json=""
  if [ -n "$resource_group" ]; then
    secret_json=$(az keyvault secret show --vault-name "$vault_name" \
      --name "$secret_name" --resource-group "$resource_group" --query value -o tsv 2>/dev/null || echo "")
  else
    secret_json=$(az keyvault secret show --vault-name "$vault_name" \
      --name "$secret_name" --query value -o tsv 2>/dev/null || echo "")
  fi
  
  if [ -z "$secret_json" ]; then
    echo -e "${RED}Error: Could not retrieve secret from Key Vault${NC}"
    return 1
  fi
  
  # Parse JSON secret
  if command -v jq &> /dev/null; then
    local CLIENT_ID=$(echo "$secret_json" | jq -r '.clientId // .client_id // empty')
    local CLIENT_SECRET=$(echo "$secret_json" | jq -r '.clientSecret // .client_secret // empty')
    local TENANT_ID=$(echo "$secret_json" | jq -r '.tenantId // .tenant_id // empty')
    local SUBSCRIPTION_ID=$(echo "$secret_json" | jq -r '.subscriptionId // .subscription_id // empty')
  else
    # Fallback if jq is not available
    local CLIENT_ID=$(echo "$secret_json" | grep -o '"clientId"\s*:\s*"[^"]*"' | cut -d'"' -f4)
    local CLIENT_SECRET=$(echo "$secret_json" | grep -o '"clientSecret"\s*:\s*"[^"]*"' | cut -d'"' -f4)
    local TENANT_ID=$(echo "$secret_json" | grep -o '"tenantId"\s*:\s*"[^"]*"' | cut -d'"' -f4)
    local SUBSCRIPTION_ID=$(echo "$secret_json" | grep -o '"subscriptionId"\s*:\s*"[^"]*"' | cut -d'"' -f4)
    
    # Try alternate key formats if needed
    if [ -z "$CLIENT_ID" ]; then
      CLIENT_ID=$(echo "$secret_json" | grep -o '"client_id"\s*:\s*"[^"]*"' | cut -d'"' -f4)
    fi
    if [ -z "$CLIENT_SECRET" ]; then
      CLIENT_SECRET=$(echo "$secret_json" | grep -o '"client_secret"\s*:\s*"[^"]*"' | cut -d'"' -f4)
    fi
    if [ -z "$TENANT_ID" ]; then
      TENANT_ID=$(echo "$secret_json" | grep -o '"tenant_id"\s*:\s*"[^"]*"' | cut -d'"' -f4)
    fi
    if [ -z "$SUBSCRIPTION_ID" ]; then
      SUBSCRIPTION_ID=$(echo "$secret_json" | grep -o '"subscription_id"\s*:\s*"[^"]*"' | cut -d'"' -f4)
    fi
  fi
  
  # Validate required variables
  if [ -z "$CLIENT_ID" ] || [ -z "$CLIENT_SECRET" ] || \
     [ -z "$TENANT_ID" ] || [ -z "$SUBSCRIPTION_ID" ]; then
    echo -e "${RED}Error: Invalid secret format or missing required fields${NC}"
    return 1
  fi
  
  # Set temporary environment variables with unique prefix
  export "${CREDS_ENV_PREFIX}CLIENT_ID=$CLIENT_ID"
  export "${CREDS_ENV_PREFIX}CLIENT_SECRET=$CLIENT_SECRET"
  export "${CREDS_ENV_PREFIX}TENANT_ID=$TENANT_ID"
  export "${CREDS_ENV_PREFIX}SUBSCRIPTION_ID=$SUBSCRIPTION_ID"
  
  return 0
}

# Function to configure for managed identity
configure_msi() {
  # Set temporary environment variables for MSI
  export "${CREDS_ENV_PREFIX}USE_MSI=true"
  export "${CREDS_ENV_PREFIX}USE_CLI=false"
  
  # Get subscription ID if available
  local subscription_id=$(az account show --query id -o tsv 2>/dev/null || echo "")
  if [ -n "$subscription_id" ]; then
    export "${CREDS_ENV_PREFIX}SUBSCRIPTION_ID=$subscription_id"
  else
    echo -e "${YELLOW}Warning: Could not determine subscription ID${NC}"
    echo -e "${YELLOW}Make sure to set ARM_SUBSCRIPTION_ID or run 'az login'${NC}"
  fi
  
  return 0
}

# Function to save credentials to file (with warning)
save_credentials() {
  local profile=${1:-default}
  local cred_file="${CREDENTIAL_DIR}/${profile}.creds"
  
  # Create credential directory with secure permissions
  setup_credential_dir
  
  # Check if file exists and warn
  if [ -f "$cred_file" ]; then
    echo -e "${YELLOW}Warning: Credential file already exists: $cred_file${NC}"
    read -p "Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
      echo -e "${YELLOW}Operation cancelled.${NC}"
      return 1
    fi
  fi
  
  # Write credentials to file with secure permissions
  touch "$cred_file"
  chmod 600 "$cred_file"
  
  cat > "$cred_file" << EOF
# Terraform credentials for profile: $profile
# Created: $(date)
# WARNING: This file contains sensitive information
# It should NEVER be committed to version control

export ARM_CLIENT_ID="${TF_CREDS_CLIENT_ID:-$ARM_CLIENT_ID}"
export ARM_CLIENT_SECRET="${TF_CREDS_CLIENT_SECRET:-$ARM_CLIENT_SECRET}"
export ARM_TENANT_ID="${TF_CREDS_TENANT_ID:-$ARM_TENANT_ID}"
export ARM_SUBSCRIPTION_ID="${TF_CREDS_SUBSCRIPTION_ID:-$ARM_SUBSCRIPTION_ID}"
export ARM_USE_CLI=false
export ARM_USE_MSI=false
EOF
  
  echo -e "${GREEN}Credentials saved to $cred_file${NC}"
  echo -e "${YELLOW}WARNING: This file contains secrets and should be protected.${NC}"
  
  return 0
}

# Function to check if credentials are available
check_credentials() {
  local client_id="${TF_CREDS_CLIENT_ID:-$ARM_CLIENT_ID}"
  local client_secret="${TF_CREDS_CLIENT_SECRET:-$ARM_CLIENT_SECRET}"
  local tenant_id="${TF_CREDS_TENANT_ID:-$ARM_TENANT_ID}"
  local subscription_id="${TF_CREDS_SUBSCRIPTION_ID:-$ARM_SUBSCRIPTION_ID}"
  local use_msi="${TF_CREDS_USE_MSI:-$ARM_USE_MSI}"
  
  if [ "$use_msi" = "true" ]; then
    echo -e "${GREEN}Using Managed Identity authentication${NC}"
    return 0
  fi
  
  # Check for required variables
  if [ -z "$client_id" ] || [ -z "$client_secret" ] || \
     [ -z "$tenant_id" ] || [ -z "$subscription_id" ]; then
    echo -e "${RED}Error: Missing required Azure credentials${NC}"
    echo -e "${YELLOW}Required variables not set:${NC}"
    [ -z "$client_id" ] && echo -e "${YELLOW}- Client ID${NC}"
    [ -z "$client_secret" ] && echo -e "${YELLOW}- Client Secret${NC}"
    [ -z "$tenant_id" ] && echo -e "${YELLOW}- Tenant ID${NC}"
    [ -z "$subscription_id" ] && echo -e "${YELLOW}- Subscription ID${NC}"
    return 1
  fi
  
  echo -e "${GREEN}Credentials are available:${NC}"
  echo -e "Client ID: ${client_id}"
  echo -e "Client Secret: ${CREDENTIAL_MASK}"
  echo -e "Tenant ID: ${tenant_id}"
  echo -e "Subscription ID: ${subscription_id}"
  return 0
}

# Function to clear credentials from environment
clear_credentials() {
  unset_temp_env
  unset ARM_CLIENT_ID ARM_CLIENT_SECRET ARM_TENANT_ID ARM_SUBSCRIPTION_ID
  unset TF_VAR_client_id TF_VAR_client_secret TF_VAR_tenant_id TF_VAR_subscription_id
  echo -e "${GREEN}Credentials cleared from environment.${NC}"
  return 0
}

# Function to unset temporary environment variables
unset_temp_env() {
  unset "${CREDS_ENV_PREFIX}CLIENT_ID" "${CREDS_ENV_PREFIX}CLIENT_SECRET" \
        "${CREDS_ENV_PREFIX}TENANT_ID" "${CREDS_ENV_PREFIX}SUBSCRIPTION_ID" \
        "${CREDS_ENV_PREFIX}USE_MSI" "${CREDS_ENV_PREFIX}USE_CLI"
}

# Function to get credentials as environment variables
get_env_exports() {
  echo "export ARM_CLIENT_ID=\"${TF_CREDS_CLIENT_ID:-}\""
  echo "export ARM_CLIENT_SECRET=\"${TF_CREDS_CLIENT_SECRET:-}\""
  echo "export ARM_TENANT_ID=\"${TF_CREDS_TENANT_ID:-}\""
  echo "export ARM_SUBSCRIPTION_ID=\"${TF_CREDS_SUBSCRIPTION_ID:-}\""
  
  if [ "${TF_CREDS_USE_MSI:-}" = "true" ]; then
    echo "export ARM_USE_MSI=true"
    echo "export ARM_USE_CLI=false"
  fi
}

# Function to create environment-specific variables file
create_env_file() {
  local env_file="$TEMP_DIR/tf_env_vars"
  
  cat > "$env_file" << EOF
# Terraform environment variables
# Generated: $(date)
# This file is temporary and will be deleted

ARM_CLIENT_ID="${TF_CREDS_CLIENT_ID:-}"
ARM_CLIENT_SECRET="${TF_CREDS_CLIENT_SECRET:-}"
ARM_TENANT_ID="${TF_CREDS_TENANT_ID:-}"
ARM_SUBSCRIPTION_ID="${TF_CREDS_SUBSCRIPTION_ID:-}"
EOF
  
  if [ "${TF_CREDS_USE_MSI:-}" = "true" ]; then
    echo "ARM_USE_MSI=true" >> "$env_file"
    echo "ARM_USE_CLI=false" >> "$env_file"
  else
    echo "ARM_USE_MSI=false" >> "$env_file"
    echo "ARM_USE_CLI=false" >> "$env_file"
  fi
  
  chmod 600 "$env_file"
  echo "$env_file"
}

# Validate credentials with Azure CLI (optional)
validate_credentials() {
  local client_id="${TF_CREDS_CLIENT_ID:-$ARM_CLIENT_ID}"
  local client_secret="${TF_CREDS_CLIENT_SECRET:-$ARM_CLIENT_SECRET}"
  local tenant_id="${TF_CREDS_TENANT_ID:-$ARM_TENANT_ID}"
  local use_msi="${TF_CREDS_USE_MSI:-$ARM_USE_MSI}"
  
  if [ "$use_msi" = "true" ]; then
    # For MSI, just check if we can get token
    if ! az account get-access-token --output none; then
      echo -e "${RED}Error: Failed to validate managed identity credentials${NC}"
      return 1
    fi
  else
    # For service principal, try to login
    if [ -n "$client_id" ] && [ -n "$client_secret" ] && [ -n "$tenant_id" ]; then
      if ! az login --service-principal --username "$client_id" \
           --password "$client_secret" --tenant "$tenant_id" --output none; then
        echo -e "${RED}Error: Failed to validate service principal credentials${NC}"
        return 1
      fi
    else
      echo -e "${RED}Error: Missing required credentials for validation${NC}"
      return 1
    fi
  fi
  
  echo -e "${GREEN}Credentials validated successfully.${NC}"
  return 0
}

# Main function to process commands
main() {
  local COMMAND=""
  local PROFILE="default"
  local ENVIRONMENT=""
  local KEY_VAULT=""
  local SECRET_NAME=""
  local RESOURCE_GROUP=""
  local AUTH_METHOD="env"
  local QUIET=false
  
  # Parse command first (if provided)
  if [ $# -gt 0 ]; then
    case "$1" in
      load|check|clear|save|vault|msi)
        COMMAND="$1"
        shift
        ;;
    esac
  fi
  
  # Parse options
  while [ $# -gt 0 ]; do
    case "$1" in
      -p|--profile)
        PROFILE="$2"
        shift 2
        ;;
      -e|--environment)
        ENVIRONMENT="$2"
        shift 2
        ;;
      -k|--keyvault)
        KEY_VAULT="$2"
        shift 2
        ;;
      -s|--secret-name)
        SECRET_NAME="$2"
        shift 2
        ;;
      -r|--resource-group)
        RESOURCE_GROUP="$2"
        shift 2
        ;;
      -m|--method)
        AUTH_METHOD="$2"
        shift 2
        ;;
      -q|--quiet)
        QUIET=true
        shift
        ;;
      -h|--help)
        show_usage
        ;;
      *)
        echo -e "${RED}Error: Unknown option: $1${NC}"
        show_usage
        ;;
    esac
  done
  
  # Set default command if not provided
  if [ -z "$COMMAND" ]; then
    COMMAND="load"
  fi
  
  # Check prerequisites
  check_prerequisites
  
  # Process command
  case "$COMMAND" in
    load)
      case "$AUTH_METHOD" in
        env)
          if ! load_from_env; then
            [ "$QUIET" = false ] && echo -e "${YELLOW}Warning: Could not load credentials from environment variables${NC}"
          else
            [ "$QUIET" = false ] && echo -e "${GREEN}Loaded credentials from environment variables${NC}"
          fi
          ;;
        file)
          if ! load_from_file "$PROFILE"; then
            [ "$QUIET" = false ] && echo -e "${YELLOW}Warning: Could not load credentials from file${NC}"
          else
            [ "$QUIET" = false ] && echo -e "${GREEN}Loaded credentials from file: $PROFILE${NC}"
          fi
          ;;
        vault)
          if ! load_from_vault "$KEY_VAULT" "$SECRET_NAME" "$RESOURCE_GROUP"; then
            [ "$QUIET" = false ] && echo -e "${YELLOW}Warning: Could not load credentials from Key Vault${NC}"
          else
            [ "$QUIET" = false ] && echo -e "${GREEN}Loaded credentials from Key Vault: $KEY_VAULT${NC}"
          fi
          ;;
        msi)
          configure_msi
          [ "$QUIET" = false ] && echo -e "${GREEN}Configured for managed identity authentication${NC}"
          ;;
        *)
          echo -e "${RED}Error: Unknown authentication method: $AUTH_METHOD${NC}"
          echo -e "${YELLOW}Supported methods: env, file, vault, msi${NC}"
          exit 1
          ;;
      esac
      
      # Return environment file path
      env_file=$(create_env_file)
      echo "$env_file"
      ;;
    check)
      check_credentials
      ;;
    clear)
      clear_credentials
      ;;
    save)
      if ! save_credentials "$PROFILE"; then
        exit 1
      fi
      ;;
    vault)
      if ! load_from_vault "$KEY_VAULT" "$SECRET_NAME" "$RESOURCE_GROUP"; then
        exit 1
      fi
      [ "$QUIET" = false ] && echo -e "${GREEN}Loaded credentials from Key Vault: $KEY_VAULT${NC}"
      
      # Return environment file path
      env_file=$(create_env_file)
      echo "$env_file"
      ;;
    msi)
      configure_msi
      [ "$QUIET" = false ] && echo -e "${GREEN}Configured for managed identity authentication${NC}"
      
      # Return environment file path
      env_file=$(create_env_file)
      echo "$env_file"
      ;;
    *)
      echo -e "${RED}Error: Unknown command: $COMMAND${NC}"
      show_usage
      ;;
  esac
}

# Run main function if script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  main "$@"
fi