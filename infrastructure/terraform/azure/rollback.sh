#!/bin/bash
# Script to implement rollbacks for failed Terraform operations
# This provides a safety net for when Apply operations partially succeed but then fail

set -e

# Set colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="sit"
SNAPSHOT_NAME=""
RESTORE_SNAPSHOT=""
LIST_SNAPSHOTS=false
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FORCE=false
DRY_RUN=false

# Function to display usage
show_usage() {
  echo "Usage: $0 [OPTIONS]"
  echo
  echo "Manage Terraform state snapshots for rollback capabilities"
  echo
  echo "Options:"
  echo "  -e, --environment ENV     Environment: sit, uat, prod (default: sit)"
  echo "  -s, --snapshot NAME       Create a snapshot with the given name"
  echo "  -r, --restore NAME        Restore from the named snapshot"
  echo "  -l, --list                List available snapshots"
  echo "  -f, --force               Force operation without confirmation"
  echo "  -d, --dry-run             Dry run (don't actually make changes)"
  echo "  -h, --help                Show this help message"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -s|--snapshot)
      SNAPSHOT_NAME="$2"
      shift 2
      ;;
    -r|--restore)
      RESTORE_SNAPSHOT="$2"
      shift 2
      ;;
    -l|--list)
      LIST_SNAPSHOTS=true
      shift
      ;;
    -f|--force)
      FORCE=true
      shift
      ;;
    -d|--dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      show_usage
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      show_usage
      exit 1
      ;;
  esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(sit|uat|prod)$ ]]; then
  echo -e "${RED}Error: Environment must be sit, uat, or prod${NC}"
  exit 1
fi

# Check if backend config exists
BACKEND_CONFIG="backends/${ENVIRONMENT}.tfbackend"
if [ ! -f "$BACKEND_CONFIG" ]; then
  echo -e "${RED}Error: Backend config file not found: $BACKEND_CONFIG${NC}"
  echo -e "${YELLOW}You may need to run setup_terraform_backend.sh first${NC}"
  exit 1
fi

# Source backend config to get storage details
# This is a simplistic approach - for production use a more robust parsing method
source <(grep -v '^#' "$BACKEND_CONFIG" | sed 's/ *= */=/g')

# Check for Azure CLI login
echo -e "${BLUE}Checking Azure CLI login...${NC}"
if ! az account show &>/dev/null; then
  echo -e "${RED}Not logged in to Azure. Please run 'az login' first.${NC}"
  exit 1
fi

# Create snapshots directory
SNAPSHOTS_DIR="snapshots"
mkdir -p "$SNAPSHOTS_DIR"

# Define snapshot path
if [ -n "$SNAPSHOT_NAME" ]; then
  SNAPSHOT_FILENAME="${ENVIRONMENT}_${SNAPSHOT_NAME}_${TIMESTAMP}.tfstate"
else
  SNAPSHOT_FILENAME="${ENVIRONMENT}_${TIMESTAMP}.tfstate"
fi
SNAPSHOT_PATH="$SNAPSHOTS_DIR/$SNAPSHOT_FILENAME"

# List available snapshots
if [ "$LIST_SNAPSHOTS" = true ]; then
  echo -e "${BLUE}Available snapshots for $ENVIRONMENT environment:${NC}"
  ls -l "$SNAPSHOTS_DIR/${ENVIRONMENT}_"*.tfstate 2>/dev/null || echo -e "${YELLOW}No snapshots found.${NC}"
  exit 0
fi

# Create a snapshot of the current state
if [ -n "$SNAPSHOT_NAME" ]; then
  echo -e "${BLUE}Creating snapshot '${SNAPSHOT_NAME}' for $ENVIRONMENT environment...${NC}"
  
  if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN: Would create snapshot at $SNAPSHOT_PATH${NC}"
  else
    # Initialize with current backend to access state
    terraform init -backend-config="$BACKEND_CONFIG" -reconfigure
    
    # Pull current state and save it as a snapshot
    terraform state pull > "$SNAPSHOT_PATH"
    
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}Snapshot created at $SNAPSHOT_PATH${NC}"
      
      # Create metadata file with information about this snapshot
      METADATA_PATH="${SNAPSHOT_PATH}.meta"
      echo "timestamp: $TIMESTAMP" > "$METADATA_PATH"
      echo "environment: $ENVIRONMENT" >> "$METADATA_PATH"
      echo "name: $SNAPSHOT_NAME" >> "$METADATA_PATH"
      echo "creator: $(whoami)" >> "$METADATA_PATH"
      echo "resource_group: $resource_group_name" >> "$METADATA_PATH"
      echo "storage_account: $storage_account_name" >> "$METADATA_PATH"
      echo "container: $container_name" >> "$METADATA_PATH"
      echo "key: $key" >> "$METADATA_PATH"
      
      STATE_RESOURCES=$(terraform state list | wc -l)
      echo "resources: $STATE_RESOURCES" >> "$METADATA_PATH"
      echo -e "${GREEN}Snapshot metadata written to $METADATA_PATH${NC}"
    else
      echo -e "${RED}Failed to create snapshot!${NC}"
      exit 1
    fi
  fi
fi

# Restore from a snapshot
if [ -n "$RESTORE_SNAPSHOT" ]; then
  # Look for the snapshot file
  RESTORE_PATH=""
  if [ -f "$SNAPSHOTS_DIR/${ENVIRONMENT}_${RESTORE_SNAPSHOT}_"*.tfstate ]; then
    RESTORE_PATH=$(ls -t "$SNAPSHOTS_DIR/${ENVIRONMENT}_${RESTORE_SNAPSHOT}_"*.tfstate | head -1)
  elif [ -f "$RESTORE_SNAPSHOT" ]; then
    RESTORE_PATH="$RESTORE_SNAPSHOT"
  else
    echo -e "${RED}Error: Snapshot not found: $RESTORE_SNAPSHOT${NC}"
    echo -e "${YELLOW}Available snapshots for $ENVIRONMENT:${NC}"
    ls -1 "$SNAPSHOTS_DIR/${ENVIRONMENT}_"*.tfstate 2>/dev/null || echo "None"
    exit 1
  fi
  
  echo -e "${BLUE}Restoring from snapshot: $RESTORE_PATH${NC}"
  
  # Safety confirmation if not forced
  if [ "$FORCE" != true ] && [ "$DRY_RUN" != true ]; then
    echo -e "${RED}WARNING: This will overwrite the current state in the $ENVIRONMENT environment!${NC}"
    echo -e "${RED}All changes made since this snapshot will be lost.${NC}"
    read -p "Are you sure you want to proceed? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
      echo -e "${YELLOW}Restoration aborted by user.${NC}"
      exit 0
    fi
  fi
  
  if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN: Would restore state from $RESTORE_PATH to backend:${NC}"
    echo "  Resource Group: $resource_group_name"
    echo "  Storage Account: $storage_account_name"
    echo "  Container: $container_name"
    echo "  Key: $key"
  else
    # Initialize with current backend
    terraform init -backend-config="$BACKEND_CONFIG" -reconfigure
    
    # Create a backup of the current state before restoring
    BACKUP_PATH="$SNAPSHOTS_DIR/${ENVIRONMENT}_pre_restore_${TIMESTAMP}.tfstate"
    echo -e "${BLUE}Creating backup of current state at $BACKUP_PATH${NC}"
    terraform state pull > "$BACKUP_PATH"
    
    # Push the snapshot to the state storage
    echo -e "${BLUE}Pushing snapshot to remote state...${NC}"
    cat "$RESTORE_PATH" | terraform state push -
    
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}State successfully restored from snapshot!${NC}"
      echo -e "${YELLOW}Note: You may need to run 'terraform plan' to see what changes will be made to match the restored state.${NC}"
    else
      echo -e "${RED}Failed to restore state!${NC}"
      echo -e "${YELLOW}Your original state is backed up at: $BACKUP_PATH${NC}"
      exit 1
    fi
  fi
fi

# If no action specified, create a default snapshot
if [ -z "$SNAPSHOT_NAME" ] && [ -z "$RESTORE_SNAPSHOT" ] && [ "$LIST_SNAPSHOTS" = false ]; then
  echo -e "${BLUE}Creating default snapshot for $ENVIRONMENT environment...${NC}"
  
  if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN: Would create snapshot at $SNAPSHOT_PATH${NC}"
  else
    # Initialize with current backend to access state
    terraform init -backend-config="$BACKEND_CONFIG" -reconfigure
    
    # Pull current state and save it as a snapshot
    terraform state pull > "$SNAPSHOT_PATH"
    
    if [ $? -eq 0 ]; then
      echo -e "${GREEN}Default snapshot created at $SNAPSHOT_PATH${NC}"
    else
      echo -e "${RED}Failed to create default snapshot!${NC}"
      exit 1
    fi
  fi
fi