#!/bin/bash
# tf_distributed_lock.sh - Distributed locking system for Terraform operations
# Prevents conflicts when multiple developers run Terraform commands locally

set -e

# Configuration variables
LOCK_CONTAINER="terraform-locks"
LOCK_TIMEOUT=3600 # 1 hour in seconds
LOCK_CHECK_INTERVAL=5
OPERATION_TYPE=""
ENVIRONMENT=""
LOCK_IDENTIFIER=""
LOCK_FILE=""
LOCK_METADATA=""
FORCE_RELEASE=false
MAX_RETRY_ATTEMPTS=3
RETRY_BACKOFF=10
VERBOSE=false

# Source shared utilities if available
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/tf_shared_utils.sh" ]]; then
    source "$SCRIPT_DIR/tf_shared_utils.sh"
fi

#######################
# Function Definitions
#######################

function show_help() {
    echo "Usage: $(basename "$0") [options] <command>"
    echo
    echo "Distributed locking system for Terraform operations."
    echo
    echo "Commands:"
    echo "  acquire    Acquire a lock for an environment"
    echo "  release    Release a previously acquired lock"
    echo "  status     Check status of locks for an environment"
    echo "  list       List all active locks"
    echo
    echo "Options:"
    echo "  -e, --environment ENV   Environment to lock (dev, sit, uat, prod)"
    echo "  -o, --operation TYPE    Operation type (plan, apply, destroy)"
    echo "  -i, --identifier ID     Custom identifier (defaults to username@hostname)"
    echo "  -t, --timeout SECONDS   Lock timeout in seconds (default: 3600)"
    echo "  -f, --force             Force release a lock (use with caution)"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -h, --help              Show this help message"
    echo
    echo "Examples:"
    echo "  $(basename "$0") -e sit -o plan acquire"
    echo "  $(basename "$0") -e sit release"
    echo "  $(basename "$0") list"
    echo
}

function log() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Only show debug messages if verbose is enabled
    if [[ "$level" == "DEBUG" && "$VERBOSE" != true ]]; then
        return
    fi
    
    echo "[$timestamp] [$level] $message"
}

function validate_environment() {
    if [[ -z "$ENVIRONMENT" ]]; then
        log "ERROR" "Environment must be specified with -e or --environment"
        return 1
    fi
    
    case "$ENVIRONMENT" in
        dev|sit|uat|prod)
            return 0
            ;;
        *)
            log "ERROR" "Invalid environment: $ENVIRONMENT. Must be one of: dev, sit, uat, prod"
            return 1
            ;;
    esac
}

function validate_operation() {
    if [[ -z "$OPERATION_TYPE" ]]; then
        log "ERROR" "Operation type must be specified with -o or --operation"
        return 1
    fi
    
    case "$OPERATION_TYPE" in
        plan|apply|destroy|custom)
            return 0
            ;;
        *)
            log "ERROR" "Invalid operation type: $OPERATION_TYPE. Must be one of: plan, apply, destroy, custom"
            return 1
            ;;
    esac
}

function setup_azure_storage() {
    # Get storage account information from environment or config
    if [[ -z "$AZURE_STORAGE_ACCOUNT" ]]; then
        if command -v az &>/dev/null; then
            # Get account name from backend config or fallback to a naming convention
            BACKEND_CONFIG="$SCRIPT_DIR/../backends/${ENVIRONMENT}.tfbackend"
            if [[ -f "$BACKEND_CONFIG" ]]; then
                AZURE_STORAGE_ACCOUNT=$(grep "storage_account_name" "$BACKEND_CONFIG" | cut -d'=' -f2 | tr -d ' "')
            else
                # Fallback: construct storage account name based on convention
                AZURE_STORAGE_ACCOUNT="sentimarktfstate${ENVIRONMENT}"
            fi
            log "DEBUG" "Using storage account: $AZURE_STORAGE_ACCOUNT"
        else
            log "ERROR" "AZURE_STORAGE_ACCOUNT environment variable not set and az command not available"
            return 1
        fi
    fi
    
    # Ensure the lock container exists
    if command -v az &>/dev/null; then
        # Check if the container exists
        if ! az storage container exists --name "$LOCK_CONTAINER" --account-name "$AZURE_STORAGE_ACCOUNT" --auth-mode login &>/dev/null; then
            log "INFO" "Creating lock container $LOCK_CONTAINER"
            az storage container create --name "$LOCK_CONTAINER" --account-name "$AZURE_STORAGE_ACCOUNT" --auth-mode login
        fi
    else
        log "WARN" "Azure CLI not available, cannot verify or create lock container. Proceeding anyway."
    fi
    
    return 0
}

function generate_lock_file() {
    # Default identifier: username@hostname
    if [[ -z "$LOCK_IDENTIFIER" ]]; then
        LOCK_IDENTIFIER="$(whoami)@$(hostname)"
    fi
    
    # Generate lock file name
    if [[ "$OPERATION_TYPE" == "custom" ]]; then
        LOCK_FILE="${ENVIRONMENT}.lock"
    else
        LOCK_FILE="${ENVIRONMENT}_${OPERATION_TYPE}.lock"
    fi
    
    # Generate lock metadata
    LOCK_METADATA=$(cat <<EOF
{
    "environment": "$ENVIRONMENT",
    "operation": "$OPERATION_TYPE",
    "acquired_by": "$LOCK_IDENTIFIER",
    "acquired_at": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "expires_at": "$(date -u -d "+${LOCK_TIMEOUT} seconds" +"%Y-%m-%dT%H:%M:%SZ")",
    "timeout_seconds": $LOCK_TIMEOUT,
    "hostname": "$(hostname)",
    "pid": $$
}
EOF
)
    
    log "DEBUG" "Lock file: $LOCK_FILE"
    log "DEBUG" "Lock metadata: $LOCK_METADATA"
}

function acquire_lock() {
    local temp_file
    temp_file=$(mktemp)
    echo "$LOCK_METADATA" > "$temp_file"
    
    log "INFO" "Attempting to acquire lock for $ENVIRONMENT ($OPERATION_TYPE)..."
    
    local attempt=1
    while [[ $attempt -le $MAX_RETRY_ATTEMPTS ]]; do
        # Use az storage blob to upload with lease condition
        if az storage blob upload \
            --container-name "$LOCK_CONTAINER" \
            --name "$LOCK_FILE" \
            --file "$temp_file" \
            --if-none-match "*" \
            --account-name "$AZURE_STORAGE_ACCOUNT" \
            --auth-mode login \
            &>/dev/null; then
            
            # Successfully acquired lock
            log "INFO" "Lock acquired successfully for $ENVIRONMENT ($OPERATION_TYPE)"
            log "INFO" "Lock will expire after $LOCK_TIMEOUT seconds ($(date -d "+${LOCK_TIMEOUT} seconds"))"
            rm -f "$temp_file"
            return 0
        else
            # Check if lock exists
            if az storage blob exists \
                --container-name "$LOCK_CONTAINER" \
                --name "$LOCK_FILE" \
                --account-name "$AZURE_STORAGE_ACCOUNT" \
                --auth-mode login \
                &>/dev/null; then
                
                # Lock exists, get current lock info
                local lock_info
                lock_info=$(az storage blob download \
                    --container-name "$LOCK_CONTAINER" \
                    --name "$LOCK_FILE" \
                    --account-name "$AZURE_STORAGE_ACCOUNT" \
                    --auth-mode login \
                    -o json 2>/dev/null || echo '{}')
                
                # Check if lock is expired
                if [[ -n "$lock_info" && "$lock_info" != "{}" ]]; then
                    local expires_at
                    local acquired_by
                    
                    # Parse JSON using either jq (preferred) or grep as fallback
                    if command -v jq &>/dev/null; then
                        expires_at=$(echo "$lock_info" | jq -r '.expires_at // empty')
                        acquired_by=$(echo "$lock_info" | jq -r '.acquired_by // empty')
                    else
                        expires_at=$(echo "$lock_info" | grep -o '"expires_at": *"[^"]*"' | cut -d'"' -f4)
                        acquired_by=$(echo "$lock_info" | grep -o '"acquired_by": *"[^"]*"' | cut -d'"' -f4)
                    fi
                    
                    if [[ -n "$expires_at" ]]; then
                        local now
                        local exp_timestamp
                        now=$(date -u +%s)
                        exp_timestamp=$(date -u -d "$expires_at" +%s 2>/dev/null || echo 0)
                        
                        if [[ $now -gt $exp_timestamp ]]; then
                            # Lock is expired, force release and retry
                            log "INFO" "Found expired lock from $acquired_by (expired at $expires_at)"
                            release_lock true
                            continue
                        fi
                    fi
                    
                    # Lock is still valid
                    log "WARN" "Environment $ENVIRONMENT is already locked for operation: $OPERATION_TYPE"
                    log "WARN" "Lock is held by: $acquired_by"
                    
                    # Calculate time remaining
                    if [[ -n "$expires_at" ]]; then
                        local now
                        local exp_timestamp
                        local time_remaining
                        
                        now=$(date -u +%s)
                        exp_timestamp=$(date -u -d "$expires_at" +%s 2>/dev/null || echo 0)
                        time_remaining=$((exp_timestamp - now))
                        
                        if [[ $time_remaining -gt 0 ]]; then
                            log "INFO" "Lock expires in $time_remaining seconds (at $expires_at)"
                        else
                            log "WARN" "Lock appears to be expired but could not be automatically released. Try with --force"
                        fi
                    fi
                fi
            else
                # Lock doesn't exist but upload failed for some other reason
                log "WARN" "Failed to acquire lock due to an unexpected error (attempt $attempt/$MAX_RETRY_ATTEMPTS)"
            fi
            
            # If this is not the last attempt, wait before retrying
            if [[ $attempt -lt $MAX_RETRY_ATTEMPTS ]]; then
                local wait_time=$((RETRY_BACKOFF * attempt))
                log "INFO" "Retrying in $wait_time seconds..."
                sleep "$wait_time"
            fi
            
            attempt=$((attempt + 1))
        fi
    done
    
    log "ERROR" "Failed to acquire lock after $MAX_RETRY_ATTEMPTS attempts"
    rm -f "$temp_file"
    return 1
}

function release_lock() {
    local force=${1:-$FORCE_RELEASE}
    
    log "INFO" "Attempting to release lock for $ENVIRONMENT ($OPERATION_TYPE)..."
    
    # Check if lock exists
    if ! az storage blob exists \
        --container-name "$LOCK_CONTAINER" \
        --name "$LOCK_FILE" \
        --account-name "$AZURE_STORAGE_ACCOUNT" \
        --auth-mode login \
        &>/dev/null; then
        
        log "WARN" "No lock found for $ENVIRONMENT ($OPERATION_TYPE)"
        return 0
    fi
    
    # Get current lock info
    local lock_info
    lock_info=$(az storage blob download \
        --container-name "$LOCK_CONTAINER" \
        --name "$LOCK_FILE" \
        --account-name "$AZURE_STORAGE_ACCOUNT" \
        --auth-mode login \
        -o json 2>/dev/null || echo '{}')
    
    # Verify lock ownership unless force is true
    if [[ "$force" != true && -n "$lock_info" && "$lock_info" != "{}" ]]; then
        local acquired_by
        
        # Parse JSON using either jq (preferred) or grep as fallback
        if command -v jq &>/dev/null; then
            acquired_by=$(echo "$lock_info" | jq -r '.acquired_by // empty')
        else
            acquired_by=$(echo "$lock_info" | grep -o '"acquired_by": *"[^"]*"' | cut -d'"' -f4)
        fi
        
        if [[ -n "$acquired_by" && "$acquired_by" != "$LOCK_IDENTIFIER" ]]; then
            if [[ -z "$LOCK_IDENTIFIER" ]]; then
                LOCK_IDENTIFIER="$(whoami)@$(hostname)"
            fi
            
            log "ERROR" "Cannot release lock: lock is owned by $acquired_by, not $LOCK_IDENTIFIER"
            log "ERROR" "Use --force to override (with appropriate permissions)"
            return 1
        fi
    fi
    
    # Delete the lock blob
    if az storage blob delete \
        --container-name "$LOCK_CONTAINER" \
        --name "$LOCK_FILE" \
        --account-name "$AZURE_STORAGE_ACCOUNT" \
        --auth-mode login \
        &>/dev/null; then
        
        log "INFO" "Lock for $ENVIRONMENT ($OPERATION_TYPE) released successfully"
        return 0
    else
        log "ERROR" "Failed to release lock for $ENVIRONMENT ($OPERATION_TYPE)"
        return 1
    fi
}

function check_lock_status() {
    log "INFO" "Checking lock status for $ENVIRONMENT..."
    
    # Generate lock file pattern for the environment
    local lock_pattern="${ENVIRONMENT}"
    if [[ -n "$OPERATION_TYPE" ]]; then
        lock_pattern="${ENVIRONMENT}_${OPERATION_TYPE}"
    fi
    
    # List blobs matching the pattern
    local locks
    locks=$(az storage blob list \
        --container-name "$LOCK_CONTAINER" \
        --prefix "$lock_pattern" \
        --account-name "$AZURE_STORAGE_ACCOUNT" \
        --auth-mode login \
        -o json 2>/dev/null)
    
    # Check if any locks were found
    if [[ -z "$locks" || "$locks" == "[]" ]]; then
        log "INFO" "No active locks found for $ENVIRONMENT"
        return 0
    fi
    
    # Display information about each lock
    echo "Active locks for $ENVIRONMENT:"
    
    if command -v jq &>/dev/null; then
        # Use jq for better formatting
        local lock_files
        lock_files=$(echo "$locks" | jq -r '.[].name')
        
        for lock_file in $lock_files; do
            local lock_data
            lock_data=$(az storage blob download \
                --container-name "$LOCK_CONTAINER" \
                --name "$lock_file" \
                --account-name "$AZURE_STORAGE_ACCOUNT" \
                --auth-mode login \
                -o json 2>/dev/null || echo '{}')
            
            local operation
            local acquired_by
            local acquired_at
            local expires_at
            
            operation=$(echo "$lock_data" | jq -r '.operation // "unknown"')
            acquired_by=$(echo "$lock_data" | jq -r '.acquired_by // "unknown"')
            acquired_at=$(echo "$lock_data" | jq -r '.acquired_at // "unknown"')
            expires_at=$(echo "$lock_data" | jq -r '.expires_at // "unknown"')
            
            # Calculate time remaining
            local now
            local exp_timestamp
            local time_remaining
            local status
            
            now=$(date -u +%s)
            exp_timestamp=$(date -u -d "$expires_at" +%s 2>/dev/null || echo 0)
            time_remaining=$((exp_timestamp - now))
            
            if [[ $time_remaining -gt 0 ]]; then
                status="Active (expires in $time_remaining seconds)"
            else
                status="Expired ($((-time_remaining)) seconds ago)"
            fi
            
            echo "  Lock: $lock_file"
            echo "    Operation: $operation"
            echo "    Acquired by: $acquired_by"
            echo "    Acquired at: $acquired_at"
            echo "    Expires at: $expires_at"
            echo "    Status: $status"
            echo
        done
    else
        # Fallback to basic formatting
        echo "$locks" | while read -r line; do
            if [[ "$line" =~ \"name\":\"([^\"]+)\" ]]; then
                lock_file="${BASH_REMATCH[1]}"
                echo "  Lock: $lock_file"
                
                local lock_data
                lock_data=$(az storage blob download \
                    --container-name "$LOCK_CONTAINER" \
                    --name "$lock_file" \
                    --account-name "$AZURE_STORAGE_ACCOUNT" \
                    --auth-mode login \
                    -o json 2>/dev/null || echo '{}')
                
                if [[ "$lock_data" == "{}" ]]; then
                    echo "    Unable to retrieve lock data"
                else
                    echo "$lock_data" | grep -E 'operation|acquired_by|acquired_at|expires_at' | sed 's/^/    /'
                    
                    # Try to calculate expiration
                    if [[ "$lock_data" =~ \"expires_at\":\"([^\"]+)\" ]]; then
                        expires_at="${BASH_REMATCH[1]}"
                        now=$(date -u +%s)
                        exp_timestamp=$(date -u -d "$expires_at" +%s 2>/dev/null || echo 0)
                        time_remaining=$((exp_timestamp - now))
                        
                        if [[ $time_remaining -gt 0 ]]; then
                            echo "    Status: Active (expires in $time_remaining seconds)"
                        else
                            echo "    Status: Expired ($((-time_remaining)) seconds ago)"
                        fi
                    fi
                fi
                
                echo
            fi
        done
    fi
    
    return 0
}

function list_all_locks() {
    log "INFO" "Listing all active locks..."
    
    # List all blobs in the lock container
    local locks
    locks=$(az storage blob list \
        --container-name "$LOCK_CONTAINER" \
        --account-name "$AZURE_STORAGE_ACCOUNT" \
        --auth-mode login \
        -o json 2>/dev/null)
    
    # Check if any locks were found
    if [[ -z "$locks" || "$locks" == "[]" ]]; then
        log "INFO" "No active locks found"
        return 0
    fi
    
    # Display information about each lock
    echo "All active locks:"
    
    if command -v jq &>/dev/null; then
        # Use jq for better formatting
        local lock_files
        lock_files=$(echo "$locks" | jq -r '.[].name')
        
        for lock_file in $lock_files; do
            local environment
            environment=$(echo "$lock_file" | cut -d'_' -f1)
            
            local lock_data
            lock_data=$(az storage blob download \
                --container-name "$LOCK_CONTAINER" \
                --name "$lock_file" \
                --account-name "$AZURE_STORAGE_ACCOUNT" \
                --auth-mode login \
                -o json 2>/dev/null || echo '{}')
            
            local operation
            local acquired_by
            local acquired_at
            local expires_at
            
            operation=$(echo "$lock_data" | jq -r '.operation // "unknown"')
            acquired_by=$(echo "$lock_data" | jq -r '.acquired_by // "unknown"')
            acquired_at=$(echo "$lock_data" | jq -r '.acquired_at // "unknown"')
            expires_at=$(echo "$lock_data" | jq -r '.expires_at // "unknown"')
            
            # Calculate time remaining
            local now
            local exp_timestamp
            local time_remaining
            local status
            
            now=$(date -u +%s)
            exp_timestamp=$(date -u -d "$expires_at" +%s 2>/dev/null || echo 0)
            time_remaining=$((exp_timestamp - now))
            
            if [[ $time_remaining -gt 0 ]]; then
                status="Active (expires in $time_remaining seconds)"
            else
                status="Expired ($((-time_remaining)) seconds ago)"
            fi
            
            echo "  Environment: $environment"
            echo "  Lock: $lock_file"
            echo "    Operation: $operation"
            echo "    Acquired by: $acquired_by"
            echo "    Acquired at: $acquired_at"
            echo "    Expires at: $expires_at"
            echo "    Status: $status"
            echo
        done
    else
        # Fallback to basic formatting
        echo "$locks" | while read -r line; do
            if [[ "$line" =~ \"name\":\"([^\"]+)\" ]]; then
                lock_file="${BASH_REMATCH[1]}"
                environment=$(echo "$lock_file" | cut -d'_' -f1)
                
                echo "  Environment: $environment"
                echo "  Lock: $lock_file"
                
                local lock_data
                lock_data=$(az storage blob download \
                    --container-name "$LOCK_CONTAINER" \
                    --name "$lock_file" \
                    --account-name "$AZURE_STORAGE_ACCOUNT" \
                    --auth-mode login \
                    -o json 2>/dev/null || echo '{}')
                
                if [[ "$lock_data" == "{}" ]]; then
                    echo "    Unable to retrieve lock data"
                else
                    echo "$lock_data" | grep -E 'operation|acquired_by|acquired_at|expires_at' | sed 's/^/    /'
                    
                    # Try to calculate expiration
                    if [[ "$lock_data" =~ \"expires_at\":\"([^\"]+)\" ]]; then
                        expires_at="${BASH_REMATCH[1]}"
                        now=$(date -u +%s)
                        exp_timestamp=$(date -u -d "$expires_at" +%s 2>/dev/null || echo 0)
                        time_remaining=$((exp_timestamp - now))
                        
                        if [[ $time_remaining -gt 0 ]]; then
                            echo "    Status: Active (expires in $time_remaining seconds)"
                        else
                            echo "    Status: Expired ($((-time_remaining)) seconds ago)"
                        fi
                    fi
                fi
                
                echo
            fi
        done
    fi
    
    return 0
}

function watch_locks() {
    local watch_interval=${1:-$LOCK_CHECK_INTERVAL}
    log "INFO" "Watching locks every $watch_interval seconds. Press Ctrl+C to exit."
    
    while true; do
        clear
        list_all_locks
        echo "Last updated: $(date)"
        echo "Refreshing every $watch_interval seconds. Press Ctrl+C to exit."
        sleep "$watch_interval"
    done
}

#######################
# Main Script Logic
#######################

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -o|--operation)
            OPERATION_TYPE="$2"
            shift 2
            ;;
        -i|--identifier)
            LOCK_IDENTIFIER="$2"
            shift 2
            ;;
        -t|--timeout)
            LOCK_TIMEOUT="$2"
            shift 2
            ;;
        -f|--force)
            FORCE_RELEASE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        acquire|release|status|list|watch)
            COMMAND="$1"
            shift
            ;;
        *)
            log "ERROR" "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Validate arguments based on command
if [[ -z "$COMMAND" ]]; then
    log "ERROR" "No command specified"
    show_help
    exit 1
fi

# Ensure Azure storage account is available
if ! setup_azure_storage; then
    log "ERROR" "Failed to set up Azure storage for locking"
    exit 1
fi

# Handle commands
case "$COMMAND" in
    acquire)
        if ! validate_environment; then
            exit 1
        fi
        
        if ! validate_operation; then
            exit 1
        fi
        
        generate_lock_file
        
        if ! acquire_lock; then
            exit 1
        fi
        ;;
    release)
        if ! validate_environment; then
            exit 1
        fi
        
        # Operation type is optional for release, status, but needed for the lock filename
        if [[ -z "$OPERATION_TYPE" ]]; then
            OPERATION_TYPE="*"
            log "INFO" "No operation type specified, will release all locks for $ENVIRONMENT"
        else
            if ! validate_operation; then
                exit 1
            fi
        fi
        
        generate_lock_file
        
        if ! release_lock; then
            exit 1
        fi
        ;;
    status)
        if ! validate_environment; then
            exit 1
        fi
        
        check_lock_status
        ;;
    list)
        list_all_locks
        ;;
    watch)
        watch_locks "$LOCK_CHECK_INTERVAL"
        ;;
    *)
        log "ERROR" "Unknown command: $COMMAND"
        show_help
        exit 1
        ;;
esac

exit 0