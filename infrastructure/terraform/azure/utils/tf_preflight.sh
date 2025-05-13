#!/bin/bash
# Terraform Pre-Flight Environment Check Utility
#
# This script performs comprehensive checks of the Azure environment
# before running Terraform operations to prevent common failures.
#
# Features:
# - Validates Azure authentication and permissions
# - Checks resource provider registrations
# - Verifies subscription quotas and limits
# - Validates backend storage accessibility
# - Checks network connectivity to required services
# - Validates Terraform configuration syntax
# - Performs security and compliance checks

set -e

# Colors for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
TERRAFORM_DIR="$PARENT_DIR"
RESULTS_DIR="$TERRAFORM_DIR/preflight_results"
TIMESTAMP=$(date +"%Y%m%d%H%M%S")
RESULTS_FILE="$RESULTS_DIR/preflight_${TIMESTAMP}.json"

# Default values
ENVIRONMENT="sit"
BACKEND_CONFIG=""
VERBOSE=false
FAIL_FAST=false
CHECK_QUOTAS=true
CHECK_NETWORK=true
CHECK_PERMISSIONS=true
CHECK_SYNTAX=true
CHECK_SECURITY=true
CHECK_PROVIDERS=true
CHECK_STATE=true
OUTPUT_FORMAT="text"
SKIP_WARNINGS=false
TIMEOUT_SECONDS=300

# Function to display usage information
show_usage() {
  cat << EOF
Terraform Pre-Flight Environment Check Utility

USAGE:
  $(basename "$0") [OPTIONS]

OPTIONS:
  -e, --environment ENV     Environment to check (sit, uat, prod)
  -b, --backend CONFIG      Backend configuration file
  -v, --verbose             Enable verbose output
  -f, --fail-fast           Stop on first failure
  -o, --output FORMAT       Output format (text, json, markdown)
  -t, --timeout SECONDS     Timeout for checks in seconds (default: 300)
  --no-quota-check          Skip quota checks
  --no-network-check        Skip network connectivity checks
  --no-permission-check     Skip permission checks
  --no-syntax-check         Skip Terraform syntax validation
  --no-security-check       Skip security and compliance checks
  --no-provider-check       Skip resource provider checks
  --no-state-check          Skip state accessibility checks
  --skip-warnings           Only fail on errors, ignore warnings
  -h, --help                Show this help message

EXAMPLES:
  # Basic check for SIT environment
  $(basename "$0") --environment sit

  # Check UAT with custom backend config
  $(basename "$0") --environment uat --backend backends/uat.tfbackend

  # Quick check (skip long-running checks)
  $(basename "$0") --no-quota-check --no-network-check

  # Generate JSON report
  $(basename "$0") --output json > preflight.json
EOF
  exit 0
}

# Function to log messages
log() {
  local level="$1"
  local message="$2"
  local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
  
  # Choose color based on level
  local color=""
  case "$level" in
    "INFO") color="$GREEN" ;;
    "WARNING") color="$YELLOW" ;;
    "ERROR") color="$RED" ;;
    "CHECK") color="$BLUE" ;;
    "RESULT") color="$CYAN" ;;
    *) color="$NC" ;;
  esac
  
  # Print to console if not in JSON mode
  if [ "$OUTPUT_FORMAT" != "json" ]; then
    echo -e "[${timestamp}] ${color}${level}${NC}: ${message}"
  fi
  
  # Add to results array for JSON output
  if [ -n "$RESULTS_ARRAY" ]; then
    RESULTS_ARRAY+=("{\"timestamp\":\"${timestamp}\",\"level\":\"${level}\",\"message\":\"${message}\"}")
  fi
}

# Function to set up results directory
setup_results_dir() {
  mkdir -p "$RESULTS_DIR"
  
  # Initialize results array for JSON output
  if [ "$OUTPUT_FORMAT" = "json" ]; then
    RESULTS_ARRAY=()
  fi
}

# Function to check Azure CLI and login status
check_azure_cli() {
  log "CHECK" "Verifying Azure CLI installation and login status"
  
  # Check if Azure CLI is installed
  if ! command -v az &> /dev/null; then
    log "ERROR" "Azure CLI is not installed"
    return 1
  fi
  
  # Try to get account information
  local account_info=""
  account_info=$(az account show 2>/dev/null || echo "")
  
  if [ -z "$account_info" ]; then
    log "ERROR" "Not logged into Azure. Run 'az login' first"
    return 1
  fi
  
  # Extract subscription info
  local subscription_name=$(echo "$account_info" | jq -r '.name')
  local subscription_id=$(echo "$account_info" | jq -r '.id')
  local user_type=$(echo "$account_info" | jq -r '.user.type')
  
  log "INFO" "Using subscription: $subscription_name ($subscription_id)"
  log "INFO" "Authentication type: $user_type"
  
  # Check if user is a service principal
  if [ "$user_type" = "servicePrincipal" ]; then
    log "INFO" "Authenticated as service principal"
    
    # Get service principal details
    local sp_id=$(echo "$account_info" | jq -r '.user.name')
    
    # Check if service principal exists
    if ! az ad sp show --id "$sp_id" &>/dev/null; then
      log "ERROR" "Service principal $sp_id not found or no permission to view it"
      return 1
    fi
    
    log "INFO" "Service principal validation passed"
  fi
  
  log "RESULT" "Azure CLI check passed"
  return 0
}

# Function to load backend configuration
load_backend_config() {
  log "CHECK" "Loading backend configuration"
  
  # If backend config is provided, use it
  if [ -n "$BACKEND_CONFIG" ]; then
    if [ ! -f "$BACKEND_CONFIG" ]; then
      log "ERROR" "Backend configuration file not found: $BACKEND_CONFIG"
      return 1
    fi
    log "INFO" "Using provided backend configuration: $BACKEND_CONFIG"
  else
    # Otherwise, try to find it based on environment
    BACKEND_CONFIG="$TERRAFORM_DIR/backends/${ENVIRONMENT}.tfbackend"
    if [ ! -f "$BACKEND_CONFIG" ]; then
      log "WARNING" "Default backend configuration file not found: $BACKEND_CONFIG"
      log "WARNING" "State checks will be skipped"
      return 0
    fi
    log "INFO" "Using default backend configuration: $BACKEND_CONFIG"
  fi
  
  # Extract storage account information
  RESOURCE_GROUP=$(grep -E "^resource_group_name\s*=" "$BACKEND_CONFIG" | cut -d '=' -f2 | tr -d ' "')
  STORAGE_ACCOUNT=$(grep -E "^storage_account_name\s*=" "$BACKEND_CONFIG" | cut -d '=' -f2 | tr -d ' "')
  CONTAINER_NAME=$(grep -E "^container_name\s*=" "$BACKEND_CONFIG" | cut -d '=' -f2 | tr -d ' "')
  STATE_KEY=$(grep -E "^key\s*=" "$BACKEND_CONFIG" | cut -d '=' -f2 | tr -d ' "')
  
  # Check required values
  if [ -z "$RESOURCE_GROUP" ] || [ -z "$STORAGE_ACCOUNT" ] || [ -z "$CONTAINER_NAME" ]; then
    log "ERROR" "Invalid backend configuration - missing required values"
    return 1
  fi
  
  log "INFO" "Extracted backend configuration:"
  log "INFO" "  Resource Group: $RESOURCE_GROUP"
  log "INFO" "  Storage Account: $STORAGE_ACCOUNT"
  log "INFO" "  Container: $CONTAINER_NAME"
  log "INFO" "  State Key: $STATE_KEY"
  
  log "RESULT" "Backend configuration loaded successfully"
  return 0
}

# Function to check permission on storage account
check_storage_permissions() {
  if [ "$CHECK_STATE" = false ] || [ -z "$STORAGE_ACCOUNT" ]; then
    return 0
  fi
  
  log "CHECK" "Verifying access permissions to backend storage"
  
  # Check if resource group exists
  if ! az group show --name "$RESOURCE_GROUP" &>/dev/null; then
    log "ERROR" "Resource group not found: $RESOURCE_GROUP"
    log "ERROR" "Cannot check storage permissions"
    return 1
  fi
  
  # Check if storage account exists
  if ! az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    log "ERROR" "Storage account not found: $STORAGE_ACCOUNT"
    return 1
  fi
  
  # Check read permissions
  log "INFO" "Checking read permissions on storage account"
  if ! az storage account show --name "$STORAGE_ACCOUNT" --resource-group "$RESOURCE_GROUP" &>/dev/null; then
    log "ERROR" "No read permissions on storage account"
    return 1
  fi
  
  # Check container access
  log "INFO" "Checking container access"
  if ! az storage container exists --name "$CONTAINER_NAME" --account-name "$STORAGE_ACCOUNT" --auth-mode login &>/dev/null; then
    log "ERROR" "Cannot access container: $CONTAINER_NAME"
    return 1
  fi
  
  # Check blob read/write access (using a test blob)
  log "INFO" "Checking blob read/write access"
  TEST_BLOB="preflight-test-${TIMESTAMP}.txt"
  
  # Try to create a test blob
  if ! echo "Preflight test" | az storage blob upload --account-name "$STORAGE_ACCOUNT" --container-name "$CONTAINER_NAME" \
       --name "$TEST_BLOB" --auth-mode login --file /dev/stdin &>/dev/null; then
    log "ERROR" "Cannot write to container: $CONTAINER_NAME"
    return 1
  fi
  
  # Try to read the test blob
  if ! az storage blob download --account-name "$STORAGE_ACCOUNT" --container-name "$CONTAINER_NAME" \
       --name "$TEST_BLOB" --auth-mode login --file /dev/null &>/dev/null; then
    log "ERROR" "Cannot read from container: $CONTAINER_NAME"
    # Try to clean up the test blob even if read failed
    az storage blob delete --account-name "$STORAGE_ACCOUNT" --container-name "$CONTAINER_NAME" \
      --name "$TEST_BLOB" --auth-mode login &>/dev/null || true
    return 1
  fi
  
  # Clean up the test blob
  az storage blob delete --account-name "$STORAGE_ACCOUNT" --container-name "$CONTAINER_NAME" \
    --name "$TEST_BLOB" --auth-mode login &>/dev/null || log "WARNING" "Could not delete test blob: $TEST_BLOB"
  
  # Check for lease operations (needed for state locking)
  log "INFO" "Checking lease operations (for state locking)"
  TEST_BLOB="preflight-lease-test-${TIMESTAMP}.txt"
  
  # Create a test blob for lease operations
  if ! echo "Lease test" | az storage blob upload --account-name "$STORAGE_ACCOUNT" --container-name "$CONTAINER_NAME" \
       --name "$TEST_BLOB" --auth-mode login --file /dev/stdin &>/dev/null; then
    log "ERROR" "Cannot create test blob for lease operations"
    return 1
  fi
  
  # Try to acquire a lease
  LEASE_ID=$(az storage blob lease acquire --account-name "$STORAGE_ACCOUNT" --container-name "$CONTAINER_NAME" \
             --name "$TEST_BLOB" --auth-mode login --lease-duration 15 -o tsv 2>/dev/null || echo "")
  
  if [ -z "$LEASE_ID" ]; then
    log "ERROR" "Cannot acquire lease on blob - state locking will not work"
    # Try to clean up even if lease failed
    az storage blob delete --account-name "$STORAGE_ACCOUNT" --container-name "$CONTAINER_NAME" \
      --name "$TEST_BLOB" --auth-mode login &>/dev/null || true
    return 1
  fi
  
  # Try to release the lease
  if ! az storage blob lease release --account-name "$STORAGE_ACCOUNT" --container-name "$CONTAINER_NAME" \
       --name "$TEST_BLOB" --lease-id "$LEASE_ID" --auth-mode login &>/dev/null; then
    log "WARNING" "Could not release lease - but lease will expire in 15 seconds"
  fi
  
  # Clean up the test blob
  az storage blob delete --account-name "$STORAGE_ACCOUNT" --container-name "$CONTAINER_NAME" \
    --name "$TEST_BLOB" --auth-mode login &>/dev/null || log "WARNING" "Could not delete lease test blob: $TEST_BLOB"
  
  log "RESULT" "Storage permission checks passed"
  return 0
}

# Function to check if an existing state file exists and is accessible
check_state_file() {
  if [ "$CHECK_STATE" = false ] || [ -z "$STORAGE_ACCOUNT" ] || [ -z "$STATE_KEY" ]; then
    return 0
  fi
  
  log "CHECK" "Checking state file accessibility"
  
  # Check if state file exists
  if az storage blob exists --account-name "$STORAGE_ACCOUNT" --container-name "$CONTAINER_NAME" \
     --name "$STATE_KEY" --auth-mode login -o tsv --query exists 2>/dev/null | grep -q "True"; then
    log "INFO" "State file exists: $STATE_KEY"
    
    # Try to download state file stats
    STATE_INFO=$(az storage blob show --account-name "$STORAGE_ACCOUNT" --container-name "$CONTAINER_NAME" \
                 --name "$STATE_KEY" --auth-mode login 2>/dev/null || echo "")
    
    if [ -n "$STATE_INFO" ]; then
      # Extract state file information
      STATE_SIZE=$(echo "$STATE_INFO" | jq -r '.properties.contentLength // 0')
      STATE_MODIFIED=$(echo "$STATE_INFO" | jq -r '.properties.lastModified // "unknown"')
      STATE_LEASE_STATUS=$(echo "$STATE_INFO" | jq -r '.properties.lease.status // "unknown"')
      STATE_LEASE_STATE=$(echo "$STATE_INFO" | jq -r '.properties.lease.state // "unknown"')
      
      log "INFO" "State file details:"
      log "INFO" "  Size: $STATE_SIZE bytes"
      log "INFO" "  Last modified: $STATE_MODIFIED"
      log "INFO" "  Lease status: $STATE_LEASE_STATUS"
      log "INFO" "  Lease state: $STATE_LEASE_STATE"
      
      # Check if state file is locked
      if [ "$STATE_LEASE_STATE" = "leased" ]; then
        log "WARNING" "State file is currently locked (has an active lease)"
        log "WARNING" "Another Terraform operation may be in progress"
      fi
    else
      log "WARNING" "Could not retrieve state file information"
    fi
  else
    log "INFO" "State file does not exist: $STATE_KEY"
    log "INFO" "This appears to be a new deployment"
  fi
  
  log "RESULT" "State file check completed"
  return 0
}

# Function to check subscription-level permissions
check_subscription_permissions() {
  if [ "$CHECK_PERMISSIONS" = false ]; then
    return 0
  fi
  
  log "CHECK" "Checking subscription-level permissions"
  
  # Get current subscription ID
  SUBSCRIPTION_ID=$(az account show --query id -o tsv)
  
  # List of subscription-level permissions to check
  # These are commonly needed for Terraform to function properly
  local required_actions=(
    "Microsoft.Resources/subscriptions/resourceGroups/write"
    "Microsoft.Resources/subscriptions/resourceGroups/read"
    "Microsoft.Resources/subscriptions/read"
  )
  
  log "INFO" "Checking permissions for subscription: $SUBSCRIPTION_ID"
  
  # Get permissions
  permissions=$(az role assignment list --scope "/subscriptions/$SUBSCRIPTION_ID" --assignee-object-id $(az ad signed-in-user show --query id -o tsv) 2>/dev/null || echo "[]")
  
  if [ "$permissions" = "[]" ]; then
    log "WARNING" "No role assignments found at subscription level"
    log "WARNING" "This may indicate insufficient permissions"
  else
    log "INFO" "Found $(echo "$permissions" | jq '. | length') role assignments at subscription level"
  fi
  
  # Check resource provider permissions (without making actual API calls)
  log "INFO" "Checking role-based access to key resource providers"
  roles=$(az role assignment list --query "[].roleDefinitionName" -o tsv 2>/dev/null)
  
  # Check for key roles
  if echo "$roles" | grep -q "Owner"; then
    log "INFO" "Has Owner role - sufficient permissions for all operations"
  elif echo "$roles" | grep -q "Contributor"; then
    log "INFO" "Has Contributor role - sufficient for most operations"
  else
    # Check for more specific roles
    if ! echo "$roles" | grep -q "Storage Blob Data Contributor"; then
      log "WARNING" "Missing Storage Blob Data Contributor role - may cause state lock issues"
    fi
    
    if ! echo "$roles" | grep -q "Key Vault Contributor"; then
      log "WARNING" "Missing Key Vault Contributor role - may cause issues with Key Vault operations"
    fi
  fi
  
  log "RESULT" "Subscription permission check completed"
  return 0
}

# Function to check AKS-related permissions
check_aks_permissions() {
  if [ "$CHECK_PERMISSIONS" = false ]; then
    return 0
  fi
  
  # Check if AKS is used in this deployment
  if grep -q "azurerm_kubernetes_cluster" "$TERRAFORM_DIR"/*.tf 2>/dev/null; then
    log "CHECK" "Checking AKS-related permissions"
    
    # List of roles needed for AKS
    local aks_roles=("Azure Kubernetes Service Cluster Admin Role" 
                      "Azure Kubernetes Service Contributor Role")
    
    # Get assigned roles
    roles=$(az role assignment list --query "[].roleDefinitionName" -o tsv 2>/dev/null)
    
    # Check for AKS roles
    local has_aks_role=false
    for role in "${aks_roles[@]}"; do
      if echo "$roles" | grep -q "$role"; then
        log "INFO" "Has $role - sufficient for AKS operations"
        has_aks_role=true
      fi
    done
    
    # Check for general admin roles as well
    if echo "$roles" | grep -q "Owner\|Contributor"; then
      has_aks_role=true
    fi
    
    if [ "$has_aks_role" = false ]; then
      log "WARNING" "Missing AKS-specific roles - may cause issues with Kubernetes cluster operations"
    fi
    
    log "RESULT" "AKS permission check completed"
  fi
  
  return 0
}

# Function to check resource provider registration
check_resource_providers() {
  if [ "$CHECK_PROVIDERS" = false ]; then
    return 0
  fi
  
  log "CHECK" "Checking resource provider registrations"
  
  # Detect which providers are being used in the Terraform files
  local used_providers=()
  
  # Common providers to check
  local common_providers=(
    "Microsoft.Storage"
    "Microsoft.Compute"
    "Microsoft.Network"
    "Microsoft.KeyVault"
    "Microsoft.ContainerService"
    "Microsoft.ContainerRegistry"
    "Microsoft.OperationalInsights"
    "Microsoft.DBforPostgreSQL"
    "Microsoft.Sql"
    "Microsoft.Dashboard"
    "Microsoft.OperationsManagement"
    "Microsoft.Authorization"
  )
  
  # Scan Terraform files for provider usage
  if [ -d "$TERRAFORM_DIR" ]; then
    for provider in "${common_providers[@]}"; do
      if grep -q "$provider" "$TERRAFORM_DIR"/*.tf 2>/dev/null; then
        used_providers+=("$provider")
      fi
    done
  fi
  
  # If we couldn't detect any, check a minimum set
  if [ ${#used_providers[@]} -eq 0 ]; then
    used_providers=(
      "Microsoft.Storage"
      "Microsoft.Compute"
      "Microsoft.Network"
    )
    log "INFO" "Could not detect providers, checking default set"
  else
    log "INFO" "Detected ${#used_providers[@]} providers in Terraform code"
  fi
  
  # Check registration status of providers
  for provider in "${used_providers[@]}"; do
    log "INFO" "Checking provider: $provider"
    local status=$(az provider show --namespace "$provider" --query "registrationState" -o tsv 2>/dev/null || echo "Unknown")
    
    if [ "$status" = "Registered" ]; then
      log "INFO" "Provider $provider is registered"
    elif [ "$status" = "NotRegistered" ]; then
      log "WARNING" "Provider $provider is not registered - deployment will fail"
      log "INFO" "To register, run: az provider register --namespace $provider"
    else
      log "WARNING" "Could not determine registration status for $provider"
    fi
  done
  
  log "RESULT" "Resource provider checks completed"
  return 0
}

# Function to check subscription quotas
check_subscription_quotas() {
  if [ "$CHECK_QUOTAS" = false ]; then
    return 0
  fi
  
  log "CHECK" "Checking subscription quotas and limits"
  
  # Get current subscription ID and location
  SUBSCRIPTION_ID=$(az account show --query id -o tsv)
  
  # Determine locations to check based on Terraform files
  local locations=()
  
  # Try to extract locations from Terraform files
  if [ -d "$TERRAFORM_DIR" ]; then
    # Extract location values from Terraform files
    local tf_locations=$(grep -h -E 'location\s*=|location_name' "$TERRAFORM_DIR"/*.tf 2>/dev/null | grep -o '"[^"]*"' | tr -d '"' | sort | uniq)
    
    # Add found locations to the array
    for loc in $tf_locations; do
      # Skip variables and references
      if [[ ! "$loc" =~ ^\$ ]]; then
        locations+=("$loc")
      fi
    done
  fi
  
  # If no locations were found, use a default
  if [ ${#locations[@]} -eq 0 ]; then
    case "$ENVIRONMENT" in
      "sit") locations=("eastus") ;;
      "uat") locations=("eastus") ;;
      "prod") locations=("eastus" "westus") ;;
      *) locations=("eastus") ;;
    esac
    log "INFO" "Could not detect locations, checking default set"
  else
    log "INFO" "Detected locations in Terraform code: ${locations[*]}"
  fi
  
  # Check core quotas for key resources, for each location
  for location in "${locations[@]}"; do
    log "INFO" "Checking quotas for location: $location"
    
    # Check virtual machine quota
    local vm_quota=$(az vm list-usage --location "$location" --query "[?name.value=='standardDSv3Family'].limit" -o tsv 2>/dev/null || echo "Unknown")
    local vm_usage=$(az vm list-usage --location "$location" --query "[?name.value=='standardDSv3Family'].currentValue" -o tsv 2>/dev/null || echo "Unknown")
    
    if [ "$vm_quota" != "Unknown" ] && [ "$vm_usage" != "Unknown" ]; then
      log "INFO" "VM quota (Standard DSv3): $vm_usage / $vm_quota"
      
      # Calculate usage percentage
      local usage_pct=$((vm_usage * 100 / vm_quota))
      if [ $usage_pct -gt 80 ]; then
        log "WARNING" "VM quota usage is high ($usage_pct%) - may impact deployments"
      fi
    else
      log "WARNING" "Could not retrieve VM quota information"
    fi
    
    # Check network quota (public IPs)
    local ip_quota=$(az network list-usages --location "$location" --query "[?name.value=='PublicIPAddresses'].limit" -o tsv 2>/dev/null | head -n 1 || echo "Unknown")
    local ip_usage=$(az network list-usages --location "$location" --query "[?name.value=='PublicIPAddresses'].currentValue" -o tsv 2>/dev/null | head -n 1 || echo "Unknown")
    
    if [ "$ip_quota" != "Unknown" ] && [ "$ip_usage" != "Unknown" ]; then
      log "INFO" "Public IP quota: $ip_usage / $ip_quota"
      
      # Calculate usage percentage
      local usage_pct=$((ip_usage * 100 / ip_quota))
      if [ $usage_pct -gt 80 ]; then
        log "WARNING" "Public IP quota usage is high ($usage_pct%) - may impact deployments"
      fi
    else
      log "WARNING" "Could not retrieve public IP quota information"
    fi
  done
  
  log "RESULT" "Quota checks completed"
  return 0
}

# Function to check network connectivity
check_network_connectivity() {
  if [ "$CHECK_NETWORK" = false ]; then
    return 0
  fi
  
  log "CHECK" "Checking network connectivity to Azure services"
  
  # List of key Azure endpoints to check
  local endpoints=(
    "management.azure.com"
    "login.microsoftonline.com"
    "graph.microsoft.com"
    "$STORAGE_ACCOUNT.blob.core.windows.net"
  )
  
  for endpoint in "${endpoints[@]}"; do
    log "INFO" "Checking connectivity to: $endpoint"
    
    # Try HTTPS connection
    if curl -s -m 5 -o /dev/null -w "%{http_code}" "https://$endpoint" | grep -q -E "^[2-3][0-9][0-9]$"; then
      log "INFO" "Successfully connected to $endpoint"
    else
      log "WARNING" "Could not connect to $endpoint - network connectivity issues may impact deployment"
    fi
  done
  
  log "RESULT" "Network connectivity checks completed"
  return 0
}

# Function to validate Terraform syntax
check_terraform_syntax() {
  if [ "$CHECK_SYNTAX" = false ]; then
    return 0
  fi
  
  log "CHECK" "Validating Terraform syntax"
  
  # Change to Terraform directory
  pushd "$TERRAFORM_DIR" > /dev/null
  
  # Run terraform validate
  if terraform validate -json | grep -q '"valid": true'; then
    log "INFO" "Terraform configuration is valid"
  else
    log "WARNING" "Terraform configuration has syntax issues"
    
    # Show detailed validation errors
    local validation_errors=$(terraform validate 2>&1 || true)
    if [ -n "$validation_errors" ]; then
      log "INFO" "Validation errors:"
      while IFS= read -r line; do
        log "INFO" "  $line"
      done <<< "$validation_errors"
    fi
  fi
  
  # Check for deprecated syntax
  if grep -r "data\.azurerm_client_config" --include="*.tf" . | grep -v "# nocheck"; then
    log "WARNING" "Using deprecated data.azurerm_client_config pattern"
  fi
  
  # Check for provider version constraints
  if ! grep -q "required_providers" *.tf; then
    log "WARNING" "No provider version constraints found"
    log "INFO" "Consider adding explicit provider version constraints"
  fi
  
  # Return to original directory
  popd > /dev/null
  
  log "RESULT" "Terraform syntax validation completed"
  return 0
}

# Function to check security and compliance
check_security_compliance() {
  if [ "$CHECK_SECURITY" = false ]; then
    return 0
  fi
  
  log "CHECK" "Checking security and compliance considerations"
  
  # Checking for secure defaults in configuration
  
  # Check for storage account encryption
  if grep -r "azurerm_storage_account" --include="*.tf" "$TERRAFORM_DIR" | grep -v "enable_https_traffic_only.*true"; then
    log "WARNING" "Some storage accounts may not have HTTPS traffic enabled"
  fi
  
  # Check for publicly accessible storage
  if grep -r "allow_blob_public_access.*true" --include="*.tf" "$TERRAFORM_DIR"; then
    log "WARNING" "Public blob access is enabled for some storage accounts"
  fi
  
  # Check for unencrypted managed disks
  if grep -r "azurerm_managed_disk" --include="*.tf" "$TERRAFORM_DIR" | grep -v "encryption_settings"; then
    log "WARNING" "Some managed disks may not have encryption explicitly enabled"
  fi
  
  # Check for resources without tags
  if grep -r "resource\s*\"azurerm_" --include="*.tf" "$TERRAFORM_DIR" | grep -v "tags"; then
    log "WARNING" "Some resources may not have tags configured"
  fi
  
  # Check for network security groups
  if grep -r "azurerm_network_security_group" --include="*.tf" "$TERRAFORM_DIR" | grep -q "source_address_prefix.*\"*\*\"*"; then
    log "WARNING" "Some network security groups have wildcard source address prefixes"
  fi
  
  # Check for diagnostic settings
  if grep -r "azurerm_kubernetes_cluster\|azurerm_key_vault\|azurerm_sql_server" --include="*.tf" "$TERRAFORM_DIR" | grep -v "azurerm_monitor_diagnostic_setting"; then
    log "WARNING" "Some resources may not have diagnostic settings configured"
  fi
  
  # Check for environment-specific security
  if [ "$ENVIRONMENT" = "prod" ]; then
    # Check for production-specific security requirements
    
    # Check for access logging
    if ! grep -q "azurerm_monitor_activity_log_alert" --include="*.tf" "$TERRAFORM_DIR"; then
      log "WARNING" "No activity log alerts found in production environment"
    fi
    
    # Check for disaster recovery
    if ! grep -q "azurerm_recovery_services_vault" --include="*.tf" "$TERRAFORM_DIR"; then
      log "WARNING" "No recovery services vault found in production environment"
    fi
  fi
  
  log "RESULT" "Security and compliance checks completed"
  return 0
}

# Function to handle timeout
handle_timeout() {
  log "ERROR" "Preflight checks timed out after $TIMEOUT_SECONDS seconds"
  generate_report "Timed out"
  exit 1
}

# Function to generate final report
generate_report() {
  local status="$1"
  
  # Generate report based on requested format
  case "$OUTPUT_FORMAT" in
    "json")
      # Convert results array to JSON
      mkdir -p "$(dirname "$RESULTS_FILE")"
      echo "{\"status\":\"$status\",\"timestamp\":\"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\",\"environment\":\"$ENVIRONMENT\",\"results\":[$(IFS=,; echo "${RESULTS_ARRAY[*]}")],\"location\":\"$RESULTS_FILE\"}" > "$RESULTS_FILE"
      
      # Output to stdout
      cat "$RESULTS_FILE"
      ;;
      
    "markdown")
      # Generate Markdown report
      mkdir -p "$(dirname "$RESULTS_FILE")"
      
      cat > "$RESULTS_FILE.md" << EOF
# Terraform Pre-Flight Check Report

## Summary
- **Status**: $status
- **Environment**: $ENVIRONMENT
- **Timestamp**: $(date)
- **Report File**: $RESULTS_FILE.md

## Check Results

EOF
      
      # Process the results array into Markdown
      for result in "${RESULTS_ARRAY[@]}"; do
        local level=$(echo "$result" | jq -r '.level')
        local message=$(echo "$result" | jq -r '.message')
        local timestamp=$(echo "$result" | jq -r '.timestamp')
        
        # Add icon based on level
        local icon=""
        case "$level" in
          "INFO") icon="ℹ️" ;;
          "WARNING") icon="⚠️" ;;
          "ERROR") icon="❌" ;;
          "CHECK") icon="🔍" ;;
          "RESULT") icon="✅" ;;
          *) icon="•" ;;
        esac
        
        echo "- $icon **$level** ($timestamp): $message" >> "$RESULTS_FILE.md"
      done
      
      # Add recommendations section
      cat >> "$RESULTS_FILE.md" << EOF

## Recommendations

- Address any warnings or errors before deploying
- For quota issues, request quota increases in advance
- For permissions issues, ensure service principal has necessary roles
- Re-run preflight checks after addressing issues

EOF
      
      # Output report location
      echo "Markdown report generated: $RESULTS_FILE.md"
      ;;
      
    *)
      # Text report is already shown in logs during execution
      log "INFO" "Preflight checks completed with status: $status"
      log "INFO" "Report stored at: $RESULTS_FILE"
      ;;
  esac
}

# Main function
main() {
  # Parse command line arguments
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -e|--environment)
        ENVIRONMENT="$2"
        shift 2
        ;;
      -b|--backend)
        BACKEND_CONFIG="$2"
        shift 2
        ;;
      -v|--verbose)
        VERBOSE=true
        shift
        ;;
      -f|--fail-fast)
        FAIL_FAST=true
        shift
        ;;
      -o|--output)
        OUTPUT_FORMAT="$2"
        shift 2
        ;;
      -t|--timeout)
        TIMEOUT_SECONDS="$2"
        shift 2
        ;;
      --no-quota-check)
        CHECK_QUOTAS=false
        shift
        ;;
      --no-network-check)
        CHECK_NETWORK=false
        shift
        ;;
      --no-permission-check)
        CHECK_PERMISSIONS=false
        shift
        ;;
      --no-syntax-check)
        CHECK_SYNTAX=false
        shift
        ;;
      --no-security-check)
        CHECK_SECURITY=false
        shift
        ;;
      --no-provider-check)
        CHECK_PROVIDERS=false
        shift
        ;;
      --no-state-check)
        CHECK_STATE=false
        shift
        ;;
      --skip-warnings)
        SKIP_WARNINGS=true
        shift
        ;;
      -h|--help)
        show_usage
        ;;
      *)
        log "ERROR" "Unknown option: $1"
        show_usage
        ;;
    esac
  done
  
  # Validate environment
  if [[ ! "$ENVIRONMENT" =~ ^(sit|uat|prod)$ ]]; then
    log "ERROR" "Invalid environment specified. Must be one of: sit, uat, prod"
    exit 1
  fi
  
  # Set up results directory and prepare for output
  setup_results_dir
  
  # Set up timeout handling
  trap handle_timeout SIGALRM
  [ "$TIMEOUT_SECONDS" -gt 0 ] && eval "sleep $TIMEOUT_SECONDS & sleep_pid=\$!; (sleep $TIMEOUT_SECONDS && kill \$sleep_pid 2>/dev/null) & trap_pid=\$!"
  
  # Track errors and warnings
  ERROR_COUNT=0
  WARNING_COUNT=0
  
  # Run checks and track success/failure
  
  # Check Azure CLI
  if ! check_azure_cli; then
    ERROR_COUNT=$((ERROR_COUNT + 1))
    [ "$FAIL_FAST" = true ] && log "ERROR" "Failing fast due to Azure CLI check failure" && generate_report "Failed" && exit 1
  fi
  
  # Load backend configuration
  if ! load_backend_config; then
    if [ "$CHECK_STATE" = true ]; then
      ERROR_COUNT=$((ERROR_COUNT + 1))
      [ "$FAIL_FAST" = true ] && log "ERROR" "Failing fast due to backend configuration loading failure" && generate_report "Failed" && exit 1
    else
      WARNING_COUNT=$((WARNING_COUNT + 1))
    fi
  fi
  
  # Check storage permissions
  if ! check_storage_permissions; then
    if [ "$CHECK_STATE" = true ]; then
      ERROR_COUNT=$((ERROR_COUNT + 1))
      [ "$FAIL_FAST" = true ] && log "ERROR" "Failing fast due to storage permission check failure" && generate_report "Failed" && exit 1
    else
      WARNING_COUNT=$((WARNING_COUNT + 1))
    fi
  fi
  
  # Check if state file exists and is accessible
  if ! check_state_file; then
    WARNING_COUNT=$((WARNING_COUNT + 1))
  fi
  
  # Check subscription permissions
  if ! check_subscription_permissions; then
    WARNING_COUNT=$((WARNING_COUNT + 1))
  fi
  
  # Check AKS-related permissions
  if ! check_aks_permissions; then
    WARNING_COUNT=$((WARNING_COUNT + 1))
  fi
  
  # Check resource provider registration
  if ! check_resource_providers; then
    WARNING_COUNT=$((WARNING_COUNT + 1))
  fi
  
  # Check subscription quotas
  if ! check_subscription_quotas; then
    WARNING_COUNT=$((WARNING_COUNT + 1))
  fi
  
  # Check network connectivity
  if ! check_network_connectivity; then
    WARNING_COUNT=$((WARNING_COUNT + 1))
  fi
  
  # Check Terraform syntax
  if ! check_terraform_syntax; then
    WARNING_COUNT=$((WARNING_COUNT + 1))
  fi
  
  # Check security and compliance
  if ! check_security_compliance; then
    WARNING_COUNT=$((WARNING_COUNT + 1))
  fi
  
  # Clean up timeout handler
  [ "$TIMEOUT_SECONDS" -gt 0 ] && kill $trap_pid 2>/dev/null || true
  
  # Generate summary
  log "INFO" "Preflight check summary:"
  log "INFO" "  Environment: $ENVIRONMENT"
  log "INFO" "  Errors: $ERROR_COUNT"
  log "INFO" "  Warnings: $WARNING_COUNT"
  
  # Determine status
  if [ $ERROR_COUNT -gt 0 ]; then
    STATUS="Failed"
    log "ERROR" "Preflight checks failed with $ERROR_COUNT errors"
    generate_report "$STATUS"
    exit 1
  elif [ $WARNING_COUNT -gt 0 ] && [ "$SKIP_WARNINGS" = false ]; then
    STATUS="Warning"
    log "WARNING" "Preflight checks completed with $WARNING_COUNT warnings"
    generate_report "$STATUS"
    exit 0
  else
    STATUS="Passed"
    log "INFO" "All preflight checks passed successfully"
    generate_report "$STATUS"
    exit 0
  fi
}

# Run main function
main "$@"