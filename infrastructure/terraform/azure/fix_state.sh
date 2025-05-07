#\!/bin/bash
# Script to fix Terraform state conflicts between environments

set -e

# Display help message
show_help() {
  echo "Usage: ./fix_state.sh [OPTIONS] COMMAND"
  echo ""
  echo "Fix Terraform state conflicts between environments."
  echo ""
  echo "Commands:"
  echo "  list                List all resources in current state"
  echo "  remove UAT_RESOURCE Remove a UAT resource from state"
  echo "  migrate sit        Migrate to SIT-specific backend state"
  echo "  migrate uat        Migrate to UAT-specific backend state"
  echo ""
  echo "Options:"
  echo "  -h, --help          Show this help message"
  echo ""
  echo "Examples:"
  echo "  ./fix_state.sh list                            # List all resources in state"
  echo "  ./fix_state.sh remove azurerm_resource_group.rg # Remove resource from state"
  echo "  ./fix_state.sh migrate sit                      # Migrate to SIT backend"
}

# If no args or help flag, show help
if [ $# -eq 0 ] || [ "$1" == "-h" ] || [ "$1" == "--help" ]; then
  show_help
  exit 0
fi

COMMAND=$1

case $COMMAND in
  list)
    echo "Listing all resources in current Terraform state..."
    ./run-terraform.sh state list
    ;;
    
  remove)
    if [ -z "$2" ]; then
      echo "Error: No resource specified to remove."
      echo "Usage: ./fix_state.sh remove RESOURCE_ADDRESS"
      exit 1
    fi
    echo "Removing resource '$2' from state..."
    ./run-terraform.sh state rm "$2"
    ;;
    
  migrate)
    if [ "$2" \!= "sit" ] && [ "$2" \!= "uat" ]; then
      echo "Error: Invalid environment. Use 'sit' or 'uat'."
      exit 1
    fi
    
    ENV=$2
    BACKEND_CONFIG="backends/${ENV}.tfbackend"
    
    # Check if backend config exists
    if [ \! -f "$BACKEND_CONFIG" ]; then
      echo "Error: Backend config file not found: $BACKEND_CONFIG"
      exit 1
    fi
    
    echo "Migrating state to ${ENV}-specific backend..."
    echo "This will initialize Terraform with a new backend configuration."
    echo "When prompted about copying state, select 'yes'."
    echo ""
    
    # Initialize with new backend config
    ./run-terraform.sh init -backend-config="$BACKEND_CONFIG" -reconfigure
    echo ""
    echo "State migration complete. You can verify with:"
    echo "./fix_state.sh list"
    ;;
    
  *)
    echo "Error: Unknown command '$COMMAND'"
    show_help
    exit 1
    ;;
esac
