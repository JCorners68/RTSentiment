#!/bin/bash
# Terraform State Lock Monitoring Utility
#
# This utility monitors Azure Storage Blob leases used by Terraform for state locking.
# It can detect stale locks, send notifications, and provide details about lock owners.
#
# Features:
# - Detects locks across all environments (SIT, UAT, PROD)
# - Provides detailed information about lock owners and creation times
# - Supports alerting thresholds based on lock age
# - Can automatically notify teams about stale locks
# - Generates detailed reports for troubleshooting
# - Supports Azure CLI and REST API methods for lock detection

set -e

# Colors for output formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default values
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
ENVIRONMENTS=("sit" "uat" "prod")
BACKEND_DIR="$PARENT_DIR/backends"
REPORT_DIR="$PARENT_DIR/lock_reports"
WARNING_THRESHOLD_MINUTES=30
CRITICAL_THRESHOLD_MINUTES=120
CHECK_INTERVAL_SECONDS=60
MONITOR_MODE=false
NOTIFY_MODE=false
DETAILED_OUTPUT=false
FIX_MODE=false
ENVIRONMENT=""
USE_REST_API=false
AZURE_CLI_AUTH=true
CHECK_ALL_FILES=false
NOTIFICATION_EMAIL=""
NOTIFICATION_WEBHOOK=""
NOTIFICATION_TEAMS_WEBHOOK=""
SLACK_WEBHOOK=""
MAX_RETRIES=3
META_FILE="$REPORT_DIR/lock_metadata.json"

# Show usage information
usage() {
  cat << EOF
Terraform State Lock Monitor - Utility for monitoring and managing Terraform state locks

USAGE:
  $(basename "$0") [OPTIONS] [ENVIRONMENT]

OPTIONS:
  -h, --help                   Show this help message
  -m, --monitor                Run in continuous monitoring mode
  -i, --interval SECONDS       Check interval in seconds (default: $CHECK_INTERVAL_SECONDS)
  -w, --warning MINUTES        Warning threshold in minutes (default: $WARNING_THRESHOLD_MINUTES)
  -c, --critical MINUTES       Critical threshold in minutes (default: $CRITICAL_THRESHOLD_MINUTES)
  -n, --notify                 Enable notifications for stale locks
  -e, --email ADDRESS          Email address for notifications
  -u, --webhook URL            Webhook URL for notifications
  -t, --teams-webhook URL      Microsoft Teams webhook for notifications
  -s, --slack-webhook URL      Slack webhook for notifications
  -d, --detailed               Show detailed lock information
  -f, --fix                    Attempt to fix stale locks (use with caution)
  -r, --rest-api               Use Azure REST API instead of CLI (requires additional setup)
  -a, --all-files              Check all state files, not just locked ones
  -v, --verbose                Enable verbose output

ENVIRONMENT:
  Specify environment to check (sit, uat, prod)
  If not specified, all environments will be checked

EXAMPLES:
  # Check all environments for locks
  $(basename "$0")

  # Check only production environment
  $(basename "$0") prod

  # Monitor locks every 5 minutes and send notifications
  $(basename "$0") --monitor --interval 300 --notify --email devops@example.com

  # Get detailed information about locks in UAT
  $(basename "$0") --detailed uat

  # Fix stale locks older than 2 hours in SIT environment
  $(basename "$0") --fix --critical 120 sit
EOF
  exit 0
}

# Function to log messages with timestamp
log() {
  local level="$1"
  local message="$2"
  local color="${NC}"
  
  case "$level" in
    "INFO") color="${GREEN}" ;;
    "WARNING") color="${YELLOW}" ;;
    "ERROR") color="${RED}" ;;
    "DEBUG") color="${BLUE}" ;;
    *) color="${NC}" ;;
  esac
  
  echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${color}${level}${NC}: ${message}"
}

# Function to create required directories
setup_directories() {
  mkdir -p "$REPORT_DIR"
  log "INFO" "Using report directory: $REPORT_DIR"

  # Initialize metadata file if it doesn't exist
  if [ ! -f "$META_FILE" ]; then
    echo "{}" > "$META_FILE"
  fi
}

# Function to parse arguments
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)
        usage
        ;;
      -m|--monitor)
        MONITOR_MODE=true
        shift
        ;;
      -i|--interval)
        CHECK_INTERVAL_SECONDS="$2"
        shift 2
        ;;
      -w|--warning)
        WARNING_THRESHOLD_MINUTES="$2"
        shift 2
        ;;
      -c|--critical)
        CRITICAL_THRESHOLD_MINUTES="$2"
        shift 2
        ;;
      -n|--notify)
        NOTIFY_MODE=true
        shift
        ;;
      -e|--email)
        NOTIFICATION_EMAIL="$2"
        shift 2
        ;;
      -u|--webhook)
        NOTIFICATION_WEBHOOK="$2"
        shift 2
        ;;
      -t|--teams-webhook)
        NOTIFICATION_TEAMS_WEBHOOK="$2"
        shift 2
        ;;
      -s|--slack-webhook)
        SLACK_WEBHOOK="$2"
        shift 2
        ;;
      -d|--detailed)
        DETAILED_OUTPUT=true
        shift
        ;;
      -f|--fix)
        FIX_MODE=true
        shift
        ;;
      -r|--rest-api)
        USE_REST_API=true
        shift
        ;;
      -a|--all-files)
        CHECK_ALL_FILES=true
        shift
        ;;
      -v|--verbose)
        set -x
        shift
        ;;
      sit|uat|prod)
        ENVIRONMENT="$1"
        shift
        ;;
      *)
        log "ERROR" "Unknown option: $1"
        usage
        ;;
    esac
  done

  # Validate notification options
  if [ "$NOTIFY_MODE" = true ] && [ -z "$NOTIFICATION_EMAIL" ] && [ -z "$NOTIFICATION_WEBHOOK" ] && 
     [ -z "$NOTIFICATION_TEAMS_WEBHOOK" ] && [ -z "$SLACK_WEBHOOK" ]; then
    log "WARNING" "Notification mode enabled but no notification methods provided."
    log "WARNING" "Please specify at least one of: --email, --webhook, --teams-webhook, --slack-webhook"
  fi

  # Validate environment
  if [ -n "$ENVIRONMENT" ]; then
    if [[ ! " ${ENVIRONMENTS[*]} " =~ " ${ENVIRONMENT} " ]]; then
      log "ERROR" "Invalid environment: $ENVIRONMENT. Must be one of: ${ENVIRONMENTS[*]}"
      exit 1
    fi
    ENVIRONMENTS=("$ENVIRONMENT")
  fi
}

# Function to verify Azure CLI is installed and logged in
check_azure_cli() {
  log "INFO" "Checking Azure CLI installation and login status..."
  
  if ! command -v az &> /dev/null; then
    log "ERROR" "Azure CLI is not installed. Please install it first."
    log "INFO" "Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
  fi
  
  if ! az account show &> /dev/null; then
    log "ERROR" "Not logged in to Azure. Please run 'az login' first."
    exit 1
  fi
  
  log "INFO" "Azure CLI check passed."
}

# Function to load backend configuration for an environment
load_backend_config() {
  local env="$1"
  local backend_file="$BACKEND_DIR/${env}.tfbackend"
  local resource_group=""
  local storage_account=""
  local container_name=""
  local key=""
  
  if [ ! -f "$backend_file" ]; then
    log "ERROR" "Backend configuration not found for $env: $backend_file"
    return 1
  fi
  
  resource_group=$(grep -E "^resource_group_name\s*=" "$backend_file" | cut -d '=' -f2 | tr -d ' "')
  storage_account=$(grep -E "^storage_account_name\s*=" "$backend_file" | cut -d '=' -f2 | tr -d ' "')
  container_name=$(grep -E "^container_name\s*=" "$backend_file" | cut -d '=' -f2 | tr -d ' "')
  key=$(grep -E "^key\s*=" "$backend_file" | cut -d '=' -f2 | tr -d ' "')
  
  if [ -z "$resource_group" ] || [ -z "$storage_account" ] || [ -z "$container_name" ]; then
    log "ERROR" "Invalid backend configuration for $env"
    return 1
  fi
  
  echo "$resource_group:$storage_account:$container_name:$key"
}

# Function to check for locks using Azure CLI
check_locks_cli() {
  local env="$1"
  local backend_info="$2"
  local report_file="$REPORT_DIR/${env}_locks.json"
  
  # Parse backend info
  IFS=':' read -r resource_group storage_account container_name key <<< "$backend_info"
  
  log "INFO" "Checking locks for $env environment..."
  log "DEBUG" "Storage Account: $storage_account, Container: $container_name"
  
  # List all blobs in the state container
  local blobs=""
  if [ "$CHECK_ALL_FILES" = true ]; then
    blobs=$(az storage blob list --account-name "$storage_account" --container-name "$container_name" \
      --auth-mode login --query "[].name" -o tsv || echo "")
  else
    blobs=$(az storage blob list --account-name "$storage_account" --container-name "$container_name" \
      --auth-mode login --query "[?properties.lease.status=='locked'].name" -o tsv || echo "")
  fi
  
  if [ -z "$blobs" ]; then
    log "INFO" "No locks found in $env environment."
    echo "[]" > "$report_file"
    return 0
  fi
  
  # Array to store lock information
  local locks_json="["
  local first_lock=true
  
  # For each locked blob, get lease information
  for blob in $blobs; do
    log "DEBUG" "Checking blob: $blob"
    
    # Get blob properties
    local properties=$(az storage blob show --account-name "$storage_account" --container-name "$container_name" \
      --name "$blob" --auth-mode login -o json || echo "{}")
    
    # Check if blob is locked
    local is_locked=$(echo "$properties" | jq -r '.properties.lease.status == "locked"')
    
    if [ "$is_locked" = "true" ] || [ "$CHECK_ALL_FILES" = true ]; then
      # Get lease ID and state
      local lease_status=$(echo "$properties" | jq -r '.properties.lease.status')
      local lease_state=$(echo "$properties" | jq -r '.properties.lease.state')
      local lease_duration=$(echo "$properties" | jq -r '.properties.lease.duration')
      
      # Get last modified time and calculate age
      local last_modified=$(echo "$properties" | jq -r '.properties.lastModified')
      local last_modified_epoch=$(date -d "$last_modified" +%s)
      local current_epoch=$(date +%s)
      local age_seconds=$((current_epoch - last_modified_epoch))
      local age_minutes=$((age_seconds / 60))
      
      # Determine lock status based on age
      local status="OK"
      if [ "$age_minutes" -ge "$CRITICAL_THRESHOLD_MINUTES" ]; then
        status="CRITICAL"
      elif [ "$age_minutes" -ge "$WARNING_THRESHOLD_MINUTES" ]; then
        status="WARNING"
      fi
      
      # Get metadata if possible (try to extract owner info)
      local metadata=$(az storage blob metadata show --account-name "$storage_account" \
        --container-name "$container_name" --name "$blob" --auth-mode login -o json 2>/dev/null || echo "{}")
      
      # Extract Terraform state info
      local state_content=""
      local owner=""
      local operation=""
      
      if [ "$DETAILED_OUTPUT" = true ]; then
        # Download state file for detailed analysis (if not locked)
        if [ "$lease_state" != "leased" ] || [ "$CHECK_ALL_FILES" = true ]; then
          # Download state file to temporary location
          local temp_file=$(mktemp)
          az storage blob download --account-name "$storage_account" --container-name "$container_name" \
            --name "$blob" --file "$temp_file" --auth-mode login &>/dev/null || true
          
          # Extract lock info from state file
          if [ -f "$temp_file" ]; then
            # Get lock info from state
            local lock_info=$(jq -r '.lockInfo // empty' "$temp_file" 2>/dev/null || echo "")
            if [ -n "$lock_info" ]; then
              owner=$(echo "$lock_info" | jq -r '.Who // "Unknown"')
              operation=$(echo "$lock_info" | jq -r '.Operation // "Unknown"')
            fi
            
            # Clean up
            rm "$temp_file"
          fi
        fi
      fi
      
      # Create JSON object for this lock
      if [ "$first_lock" = false ]; then
        locks_json+=","
      fi
      first_lock=false
      
      locks_json+=$(cat << EOF
{
  "environment": "$env",
  "blobName": "$blob",
  "isLocked": $is_locked,
  "leaseStatus": "$lease_status",
  "leaseState": "$lease_state",
  "leaseDuration": "$lease_duration",
  "lastModified": "$last_modified",
  "ageMinutes": $age_minutes,
  "status": "$status",
  "owner": "$owner",
  "operation": "$operation"
}
EOF
)
    fi
  done
  
  locks_json+="]"
  
  # Save report to file
  echo "$locks_json" > "$report_file"
  
  # Count locks by status
  local ok_count=$(echo "$locks_json" | jq -r '[.[] | select(.status == "OK")] | length')
  local warning_count=$(echo "$locks_json" | jq -r '[.[] | select(.status == "WARNING")] | length')
  local critical_count=$(echo "$locks_json" | jq -r '[.[] | select(.status == "CRITICAL")] | length')
  local total_count=$(echo "$locks_json" | jq -r '. | length')
  
  log "INFO" "$env: Found $total_count state files, $ok_count OK, $warning_count WARNING, $critical_count CRITICAL"
  
  # Return number of locks found
  echo "$total_count"
}

# Function to generate human-readable report
generate_report() {
  local env="$1"
  local report_file="$REPORT_DIR/${env}_locks.json"
  
  if [ ! -f "$report_file" ]; then
    log "ERROR" "Report file not found for $env: $report_file"
    return 1
  fi
  
  local locks=$(cat "$report_file")
  local total_count=$(echo "$locks" | jq -r '. | length')
  
  if [ "$total_count" -eq 0 ]; then
    log "INFO" "No locks found in $env environment."
    return 0
  fi
  
  log "INFO" "Lock report for $env environment:"
  echo
  
  # Display a table header
  printf "+%-20s+%-40s+%-10s+%-10s+%-15s+\n" "--------------------" "----------------------------------------" "----------" "----------" "---------------"
  printf "|%-20s|%-40s|%-10s|%-10s|%-15s|\n" " Environment" " Blob Name" " Status" " Age (min)" " Last Modified"
  printf "+%-20s+%-40s+%-10s+%-10s+%-15s+\n" "--------------------" "----------------------------------------" "----------" "----------" "---------------"
  
  # Iterate through locks
  echo "$locks" | jq -c '.[]' | while read -r lock; do
    local blob_env=$(echo "$lock" | jq -r '.environment')
    local blob_name=$(echo "$lock" | jq -r '.blobName')
    local status=$(echo "$lock" | jq -r '.status')
    local age_minutes=$(echo "$lock" | jq -r '.ageMinutes')
    local last_modified=$(echo "$lock" | jq -r '.lastModified' | cut -d 'T' -f1,2 | cut -d '.' -f1)
    
    # Truncate long blob names
    if [ ${#blob_name} -gt 38 ]; then
      blob_name="${blob_name:0:35}..."
    fi
    
    # Color-code status
    local status_display="$status"
    case "$status" in
      "OK") status_display="${GREEN}OK${NC}" ;;
      "WARNING") status_display="${YELLOW}WARNING${NC}" ;;
      "CRITICAL") status_display="${RED}CRITICAL${NC}" ;;
    esac
    
    printf "|%-20s|%-40s|%-22s|%-10s|%-15s|\n" " $blob_env" " $blob_name" " $status_display" " $age_minutes" " $last_modified"
  done
  
  printf "+%-20s+%-40s+%-10s+%-10s+%-15s+\n" "--------------------" "----------------------------------------" "----------" "----------" "---------------"
  echo
  
  # Show detailed information if requested
  if [ "$DETAILED_OUTPUT" = true ]; then
    echo "$locks" | jq -c '.[] | select(.status != "OK" or .isLocked == true)' | while read -r lock; do
      local blob_name=$(echo "$lock" | jq -r '.blobName')
      local lease_status=$(echo "$lock" | jq -r '.leaseStatus')
      local lease_state=$(echo "$lock" | jq -r '.leaseState')
      local owner=$(echo "$lock" | jq -r '.owner')
      local operation=$(echo "$lock" | jq -r '.operation')
      local age_minutes=$(echo "$lock" | jq -r '.ageMinutes')
      local last_modified=$(echo "$lock" | jq -r '.lastModified')
      
      echo -e "${BLUE}Detailed information for $blob_name:${NC}"
      echo "  Lease Status: $lease_status"
      echo "  Lease State: $lease_state"
      if [ -n "$owner" ]; then
        echo "  Owner: $owner"
      fi
      if [ -n "$operation" ]; then
        echo "  Operation: $operation"
      fi
      echo "  Age: $age_minutes minutes"
      echo "  Last Modified: $last_modified"
      echo
    done
  fi
}

# Function to send notifications about stale locks
send_notifications() {
  if [ "$NOTIFY_MODE" != true ]; then
    return 0
  fi
  
  local has_stale_locks=false
  local notification_body="Terraform State Lock Report - $(date +"%Y-%m-%d %H:%M:%S")\n\n"
  
  # Check all environments for stale locks
  for env in "${ENVIRONMENTS[@]}"; do
    local report_file="$REPORT_DIR/${env}_locks.json"
    
    if [ ! -f "$report_file" ]; then
      continue
    fi
    
    local stale_locks=$(jq -r '.[] | select(.status != "OK")' "$report_file")
    
    if [ -n "$stale_locks" ]; then
      has_stale_locks=true
      notification_body+="Stale locks found in $env environment:\n"
      
      echo "$stale_locks" | jq -c '.' | while read -r lock; do
        local blob_name=$(echo "$lock" | jq -r '.blobName')
        local status=$(echo "$lock" | jq -r '.status')
        local age_minutes=$(echo "$lock" | jq -r '.ageMinutes')
        local owner=$(echo "$lock" | jq -r '.owner // "Unknown"')
        
        notification_body+="- $blob_name: $status, Age: $age_minutes min, Owner: $owner\n"
      done
      
      notification_body+="\n"
    fi
  done
  
  # Send notifications if stale locks are found
  if [ "$has_stale_locks" = true ]; then
    log "INFO" "Sending notifications about stale locks..."
    
    # Send email notification
    if [ -n "$NOTIFICATION_EMAIL" ]; then
      log "INFO" "Sending email to $NOTIFICATION_EMAIL"
      echo -e "$notification_body" | mail -s "Terraform Lock Alert: Stale Locks Detected" "$NOTIFICATION_EMAIL"
    fi
    
    # Send webhook notification
    if [ -n "$NOTIFICATION_WEBHOOK" ]; then
      log "INFO" "Sending webhook notification"
      curl -X POST "$NOTIFICATION_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$(echo -e "$notification_body" | sed 's/"/\\"/g')\"}"
    fi
    
    # Send Microsoft Teams notification
    if [ -n "$NOTIFICATION_TEAMS_WEBHOOK" ]; then
      log "INFO" "Sending Microsoft Teams notification"
      local teams_payload="{
        \"@type\": \"MessageCard\",
        \"@context\": \"http://schema.org/extensions\",
        \"themeColor\": \"0076D7\",
        \"summary\": \"Terraform Lock Alert\",
        \"sections\": [{
          \"activityTitle\": \"Terraform Lock Alert: Stale Locks Detected\",
          \"activitySubtitle\": \"Generated at $(date +"%Y-%m-%d %H:%M:%S")\",
          \"text\": \"$(echo -e "$notification_body" | sed 's/"/\\"/g' | sed 's/\\n/<br>/g')\"
        }]
      }"
      curl -X POST "$NOTIFICATION_TEAMS_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "$teams_payload"
    fi
    
    # Send Slack notification
    if [ -n "$SLACK_WEBHOOK" ]; then
      log "INFO" "Sending Slack notification"
      local slack_payload="{
        \"text\": \"Terraform Lock Alert: Stale Locks Detected\",
        \"attachments\": [{
          \"color\": \"warning\",
          \"title\": \"Lock Report - $(date +"%Y-%m-%d %H:%M:%S")\",
          \"text\": \"$(echo -e "$notification_body" | sed 's/"/\\"/g' | sed 's/\\n/\\\\n/g')\"
        }]
      }"
      curl -X POST "$SLACK_WEBHOOK" \
        -H "Content-Type: application/json" \
        -d "$slack_payload"
    fi
  else
    log "INFO" "No stale locks found, no notifications sent."
  fi
}

# Function to attempt fixing stale locks
fix_stale_locks() {
  if [ "$FIX_MODE" != true ]; then
    return 0
  fi
  
  log "WARNING" "Attempting to fix stale locks..."
  
  # Check all environments for stale locks
  for env in "${ENVIRONMENTS[@]}"; do
    local report_file="$REPORT_DIR/${env}_locks.json"
    local backend_file="$BACKEND_DIR/${env}.tfbackend"
    
    if [ ! -f "$report_file" ] || [ ! -f "$backend_file" ]; then
      continue
    fi
    
    # Load backend configuration
    local backend_info=$(load_backend_config "$env")
    if [ -z "$backend_info" ]; then
      log "ERROR" "Could not load backend configuration for $env"
      continue
    fi
    
    # Parse backend info
    IFS=':' read -r resource_group storage_account container_name key <<< "$backend_info"
    
    # Find critical locks
    local critical_locks=$(jq -r ".[] | select(.status == \"CRITICAL\" and .isLocked == true)" "$report_file")
    
    if [ -z "$critical_locks" ]; then
      log "INFO" "No critical locks found in $env environment."
      continue
    fi
    
    log "WARNING" "Found critical locks in $env environment. Attempting to break leases..."
    
    # Process each critical lock
    echo "$critical_locks" | jq -c '.' | while read -r lock; do
      local blob_name=$(echo "$lock" | jq -r '.blobName')
      local age_minutes=$(echo "$lock" | jq -r '.ageMinutes')
      
      log "WARNING" "Breaking lease for $blob_name (age: $age_minutes minutes)..."
      
      # Break the lease using Azure CLI
      if az storage blob lease break --account-name "$storage_account" --container-name "$container_name" \
          --name "$blob_name" --auth-mode login &>/dev/null; then
        log "INFO" "Successfully broke lease for $blob_name"
        
        # Record the action in metadata
        jq --arg env "$env" \
           --arg blob "$blob_name" \
           --arg time "$(date +"%Y-%m-%d %H:%M:%S")" \
           --arg age "$age_minutes" \
           '.locks += [{"environment": $env, "blob": $blob, "fixTime": $time, "ageMinutes": $age|tonumber}]' \
           "$META_FILE" > "$META_FILE.new"
        mv "$META_FILE.new" "$META_FILE"
      else
        log "ERROR" "Failed to break lease for $blob_name"
      fi
    done
  done
}

# Main monitoring function
run_monitor() {
  log "INFO" "Starting Terraform state lock monitoring..."
  log "INFO" "Check interval: $CHECK_INTERVAL_SECONDS seconds"
  log "INFO" "Warning threshold: $WARNING_THRESHOLD_MINUTES minutes"
  log "INFO" "Critical threshold: $CRITICAL_THRESHOLD_MINUTES minutes"
  
  while true; do
    # Check all environments for locks
    for env in "${ENVIRONMENTS[@]}"; do
      local backend_info=$(load_backend_config "$env")
      if [ -n "$backend_info" ]; then
        check_locks_cli "$env" "$backend_info" > /dev/null
      fi
    done
    
    # Send notifications if needed
    send_notifications
    
    # Fix stale locks if enabled
    fix_stale_locks
    
    # Sleep until next check
    log "INFO" "Next check in $CHECK_INTERVAL_SECONDS seconds..."
    sleep "$CHECK_INTERVAL_SECONDS"
  done
}

# Main function
main() {
  parse_args "$@"
  setup_directories
  check_azure_cli
  
  # If monitor mode is enabled, run in loop
  if [ "$MONITOR_MODE" = true ]; then
    run_monitor
    exit 0
  fi
  
  # Otherwise, perform a single check
  for env in "${ENVIRONMENTS[@]}"; do
    local backend_info=$(load_backend_config "$env")
    if [ -n "$backend_info" ]; then
      check_locks_cli "$env" "$backend_info" > /dev/null
      generate_report "$env"
    fi
  done
  
  # Send notifications if enabled
  send_notifications
  
  # Fix stale locks if enabled
  fix_stale_locks
}

# Run main function
main "$@"