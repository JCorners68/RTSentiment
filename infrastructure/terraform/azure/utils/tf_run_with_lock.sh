#!/bin/bash
# tf_run_with_lock.sh - Run Terraform operations with distributed locking
# Wrapper script for run-terraform.sh that adds distributed locking

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOCK_SCRIPT="$SCRIPT_DIR/tf_distributed_lock.sh"
TERRAFORM_SCRIPT="$TERRAFORM_DIR/run-terraform.sh"

# Source shared utilities if available
if [[ -f "$SCRIPT_DIR/tf_shared_utils.sh" ]]; then
    source "$SCRIPT_DIR/tf_shared_utils.sh"
fi

# Default values
OPERATION=""
ENVIRONMENT=""
LOCK_TIMEOUT=3600 # Default lock timeout: 1 hour
SKIP_LOCKING=false
VERBOSE=false

function show_help() {
    echo "Usage: $(basename "$0") [options] <operation> [terraform args...]"
    echo
    echo "Runs Terraform operations with distributed locking to prevent concurrent operations."
    echo
    echo "Operations:"
    echo "  plan          Run terraform plan with automatic locking"
    echo "  apply         Run terraform apply with automatic locking"
    echo "  destroy       Run terraform destroy with automatic locking"
    echo "  custom        Run custom Terraform command with locking"
    echo
    echo "Options:"
    echo "  -e, --environment ENV   Environment to lock (dev, sit, uat, prod)"
    echo "  -t, --timeout SECONDS   Lock timeout in seconds (default: 3600)"
    echo "  -s, --skip-locking      Skip locking mechanism (use with caution)"
    echo "  -v, --verbose           Enable verbose output"
    echo "  -h, --help              Show this help message"
    echo
    echo "Examples:"
    echo "  $(basename "$0") -e sit plan"
    echo "  $(basename "$0") -e prod apply -auto-approve"
    echo "  $(basename "$0") -e dev -s plan -var-file=custom.tfvars"
    echo
}

function detect_environment() {
    # Try to detect environment from arguments passed to terraform
    for arg in "$@"; do
        if [[ "$arg" == *".tfvars" ]]; then
            local env
            env=$(basename "$arg" | sed -E 's/^(dev|sit|uat|prod).*\.tfvars$/\1/')
            if [[ "$env" =~ ^(dev|sit|uat|prod)$ ]]; then
                echo "$env"
                return 0
            fi
        fi
    done
    
    # Default to checking if we're in a specific backend folder
    if [[ -f "$TERRAFORM_DIR/backend.tf" ]]; then
        local backend_content
        backend_content=$(cat "$TERRAFORM_DIR/backend.tf")
        
        for env in dev sit uat prod; do
            if [[ "$backend_content" == *"${env}.tfbackend"* ]]; then
                echo "$env"
                return 0
            fi
        done
    fi
    
    # No environment detected
    return 1
}

function detect_operation() {
    # Determine the Terraform operation from the first argument
    local first_arg="$1"
    
    case "$first_arg" in
        plan|apply|destroy)
            echo "$first_arg"
            return 0
            ;;
        *)
            # For other operations, use 'custom'
            echo "custom"
            return 0
            ;;
    esac
}

function acquire_environment_lock() {
    local env="$1"
    local op="$2"
    local timeout="$3"
    
    # Check if the lock script exists
    if [[ ! -f "$LOCK_SCRIPT" ]]; then
        print_color "red" "Distributed lock script not found at $LOCK_SCRIPT"
        return 1
    fi
    
    # Try to acquire lock
    local lock_result
    if [[ "$VERBOSE" == true ]]; then
        lock_result=$("$LOCK_SCRIPT" -v -e "$env" -o "$op" -t "$timeout" acquire)
    else
        lock_result=$("$LOCK_SCRIPT" -e "$env" -o "$op" -t "$timeout" acquire)
    fi
    
    local lock_status=$?
    if [[ $lock_status -ne 0 ]]; then
        print_color "red" "Failed to acquire lock for $env environment:"
        echo "$lock_result"
        return 1
    fi
    
    print_color "green" "Successfully acquired lock for $env environment"
    return 0
}

function release_environment_lock() {
    local env="$1"
    local op="$2"
    
    # Try to release lock
    local release_result
    if [[ "$VERBOSE" == true ]]; then
        release_result=$("$LOCK_SCRIPT" -v -e "$env" -o "$op" release)
    else
        release_result=$("$LOCK_SCRIPT" -e "$env" -o "$op" release)
    fi
    
    local release_status=$?
    if [[ $release_status -ne 0 ]]; then
        print_color "yellow" "Warning: Failed to release lock for $env environment:"
        echo "$release_result"
        return 1
    fi
    
    print_color "green" "Successfully released lock for $env environment"
    return 0
}

function run_terraform() {
    local env="$1"
    local op="$2"
    shift 2
    
    # Check if run-terraform.sh exists
    if [[ ! -f "$TERRAFORM_SCRIPT" ]]; then
        print_color "red" "Terraform script not found at $TERRAFORM_SCRIPT"
        return 1
    fi
    
    # Run Terraform with the given operation and arguments
    print_color "blue" "Running 'terraform $op' for $env environment..."
    "$TERRAFORM_SCRIPT" "$op" "$@"
    local terraform_status=$?
    
    if [[ $terraform_status -ne 0 ]]; then
        print_color "red" "Terraform operation failed with exit code $terraform_status"
    else
        print_color "green" "Terraform operation completed successfully"
    fi
    
    return $terraform_status
}

# Parse command line arguments
POSITIONAL=()
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
        -t|--timeout)
            LOCK_TIMEOUT="$2"
            shift 2
            ;;
        -s|--skip-locking)
            SKIP_LOCKING=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done
set -- "${POSITIONAL[@]}" # Restore positional parameters

# Check if we have any arguments
if [[ ${#POSITIONAL[@]} -eq 0 ]]; then
    print_color "red" "No operation specified"
    show_help
    exit 1
fi

# Determine operation from the first argument
OPERATION=$(detect_operation "${POSITIONAL[0]}")

# Auto-detect environment if not specified
if [[ -z "$ENVIRONMENT" ]]; then
    ENVIRONMENT=$(detect_environment "$@")
    
    if [[ -z "$ENVIRONMENT" ]]; then
        print_color "red" "Could not auto-detect environment. Please specify with -e or --environment"
        exit 1
    else
        print_color "blue" "Auto-detected environment: $ENVIRONMENT"
    fi
fi

# Skip locking if requested
if [[ "$SKIP_LOCKING" == true ]]; then
    print_color "yellow" "Warning: Skipping distributed locking. Use with caution!"
    run_terraform "$ENVIRONMENT" "$OPERATION" "${@:2}"
    exit $?
fi

# Acquire lock for the environment
if ! acquire_environment_lock "$ENVIRONMENT" "$OPERATION" "$LOCK_TIMEOUT"; then
    print_color "red" "Failed to acquire lock. Aborting Terraform operation."
    exit 1
fi

# Setup trap to release lock on script exit
trap 'release_environment_lock "$ENVIRONMENT" "$OPERATION"' EXIT

# Run the terraform command
run_terraform "$ENVIRONMENT" "$OPERATION" "${@:2}"
TERRAFORM_STATUS=$?

# Exit with the status of the terraform command
exit $TERRAFORM_STATUS