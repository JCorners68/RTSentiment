#!/bin/bash
# tf_shared_utils.sh - Shared utilities for Terraform scripts
# Contains common functions used across multiple scripts

# Default configuration
DEFAULT_TIMEOUT=600 # 10 minutes in seconds
DEFAULT_RETRY_ATTEMPTS=3
DEFAULT_RETRY_BACKOFF=5

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

#######################
# Function Definitions
#######################

# Print colorized message
# Usage: print_color "color" "message"
function print_color() {
    local color="$1"
    local message="$2"
    
    case "$color" in
        red) echo -e "${RED}${message}${NC}" ;;
        green) echo -e "${GREEN}${message}${NC}" ;;
        yellow) echo -e "${YELLOW}${message}${NC}" ;;
        blue) echo -e "${BLUE}${message}${NC}" ;;
        magenta) echo -e "${MAGENTA}${message}${NC}" ;;
        cyan) echo -e "${CYAN}${message}${NC}" ;;
        *) echo "$message" ;;
    esac
}

# Check if a command exists
# Usage: command_exists "command_name"
function command_exists() {
    command -v "$1" &> /dev/null
}

# Get the Terraform state storage account name for an environment
# Usage: get_storage_account_name "environment"
function get_storage_account_name() {
    local environment="$1"
    local storage_account=""
    
    # Try to get from backend config
    local backend_config="$SCRIPT_DIR/../backends/${environment}.tfbackend"
    if [[ -f "$backend_config" ]]; then
        storage_account=$(grep "storage_account_name" "$backend_config" | cut -d'=' -f2 | tr -d ' "')
    fi
    
    # Fallback to naming convention
    if [[ -z "$storage_account" ]]; then
        storage_account="sentimarktfstate${environment}"
    fi
    
    echo "$storage_account"
}

# Get the current logged in Azure user
# Usage: get_current_azure_user
function get_current_azure_user() {
    if command_exists az; then
        az account show --query user.name -o tsv 2>/dev/null || echo "unknown"
    else
        echo "unknown"
    fi
}

# Check if Azure CLI is logged in
# Usage: check_azure_login
function check_azure_login() {
    if ! command_exists az; then
        print_color "red" "Azure CLI not installed"
        return 1
    fi
    
    if ! az account show &>/dev/null; then
        print_color "red" "Not logged into Azure CLI"
        return 1
    fi
    
    return 0
}

# Run a command with retries
# Usage: run_with_retry "command" "max_attempts" "backoff_seconds"
function run_with_retry() {
    local cmd="$1"
    local max_attempts="${2:-$DEFAULT_RETRY_ATTEMPTS}"
    local backoff="${3:-$DEFAULT_RETRY_BACKOFF}"
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if eval "$cmd"; then
            return 0
        else
            local exit_code=$?
            print_color "yellow" "Command failed with exit code $exit_code (attempt $attempt/$max_attempts)"
            
            if [[ $attempt -lt $max_attempts ]]; then
                local wait_time=$((backoff * attempt))
                print_color "yellow" "Retrying in $wait_time seconds..."
                sleep "$wait_time"
            fi
            
            attempt=$((attempt + 1))
        fi
    done
    
    print_color "red" "Command failed after $max_attempts attempts"
    return 1
}

# Get timestamp in ISO8601 format
# Usage: get_iso_timestamp
function get_iso_timestamp() {
    date -u +"%Y-%m-%dT%H:%M:%SZ"
}

# Generate a unique identifier
# Usage: generate_unique_id
function generate_unique_id() {
    echo "$(whoami)_$(hostname)_$(date +%s)_$$"
}

# Check if running in CI environment
# Usage: is_ci_environment
function is_ci_environment() {
    if [[ -n "${CI:-}" || -n "${GITHUB_ACTIONS:-}" || -n "${TF_IN_AUTOMATION:-}" ]]; then
        return 0
    else
        return 1
    fi
}

# Get the current Terraform workspace
# Usage: get_terraform_workspace
function get_terraform_workspace() {
    if command_exists terraform; then
        terraform workspace show 2>/dev/null || echo "default"
    else
        echo "default"
    fi
}

# Check if Terraform state file exists locally
# Usage: tf_state_exists
function tf_state_exists() {
    [[ -f terraform.tfstate ]]
}

# Get Terraform version
# Usage: get_terraform_version
function get_terraform_version() {
    if command_exists terraform; then
        terraform version -json | grep -o '"terraform_version":"[^"]*"' | cut -d'"' -f4
    else
        echo "unknown"
    fi
}

# Create temporary directory with automatic cleanup
# Usage: tmp_dir=$(create_temp_dir "prefix")
function create_temp_dir() {
    local prefix="${1:-terraform}"
    local tmp_dir
    tmp_dir=$(mktemp -d "/tmp/${prefix}_XXXXXX")
    
    # Register cleanup function
    trap 'rm -rf "$tmp_dir"' EXIT
    
    echo "$tmp_dir"
}

# Sanitize a string for use in filenames
# Usage: sanitize_filename "string"
function sanitize_filename() {
    echo "$1" | tr -cd '[:alnum:]._-'
}

# Verify Azure storage account exists and is accessible
# Usage: verify_storage_account "storage_account_name"
function verify_storage_account() {
    local storage_account="$1"
    
    if ! check_azure_login; then
        return 1
    fi
    
    if ! az storage account show --name "$storage_account" &>/dev/null; then
        print_color "red" "Storage account $storage_account does not exist or is not accessible"
        return 1
    fi
    
    return 0
}

# Get a list of active Azure subscriptions
# Usage: get_azure_subscriptions
function get_azure_subscriptions() {
    if ! check_azure_login; then
        return 1
    fi
    
    az account list --query "[].{name:name, id:id, isDefault:isDefault}" -o json
}

# Get the current Azure subscription
# Usage: get_current_subscription
function get_current_subscription() {
    if ! check_azure_login; then
        return 1
    fi
    
    az account show --query "{name:name, id:id}" -o json
}

# Check if a resource group exists
# Usage: resource_group_exists "resource_group_name"
function resource_group_exists() {
    local resource_group="$1"
    
    if ! check_azure_login; then
        return 1
    fi
    
    az group exists --name "$resource_group" --query "exists" -o tsv
}

# Display a table of environment variables that are used by Terraform
# Usage: show_terraform_environment_vars
function show_terraform_environment_vars() {
    print_color "cyan" "Current Terraform Environment Variables:"
    print_color "cyan" "==========================================="
    
    # Core Terraform variables
    echo "ARM_CLIENT_ID:         ${ARM_CLIENT_ID:-(not set)}"
    echo "ARM_CLIENT_SECRET:     ${ARM_CLIENT_SECRET:+(set)}"
    echo "ARM_TENANT_ID:         ${ARM_TENANT_ID:-(not set)}"
    echo "ARM_SUBSCRIPTION_ID:   ${ARM_SUBSCRIPTION_ID:-(not set)}"
    echo "ARM_ACCESS_KEY:        ${ARM_ACCESS_KEY:+(set)}"
    echo "ARM_USE_MSI:           ${ARM_USE_MSI:-(not set)}"
    echo "ARM_ENVIRONMENT:       ${ARM_ENVIRONMENT:-(not set)}"
    
    # Terraform behavior variables
    echo "TF_LOG:                ${TF_LOG:-(not set)}"
    echo "TF_LOG_PATH:           ${TF_LOG_PATH:-(not set)}"
    echo "TF_VAR_files:          ${TF_VAR_files:-(not set)}"
    echo "TF_CLI_ARGS:           ${TF_CLI_ARGS:-(not set)}"
    echo "TF_DATA_DIR:           ${TF_DATA_DIR:-(not set)}"
    echo "TF_PLUGIN_CACHE_DIR:   ${TF_PLUGIN_CACHE_DIR:-(not set)}"
    echo "TF_IN_AUTOMATION:      ${TF_IN_AUTOMATION:-(not set)}"
    
    # Azure CLI environment
    echo "AZURE_CONFIG_DIR:      ${AZURE_CONFIG_DIR:-(not set)}"
    
    print_color "cyan" "==========================================="
}