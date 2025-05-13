#!/bin/bash
# Terraform CI/CD pipeline script for automated infrastructure deployment
# This script is designed to be run from CI/CD pipelines with proper state locking

set -e

# Default values
ENVIRONMENT="sit"
ACTION="plan"
BACKEND_CONFIG=""
AUTO_APPROVE=false
WORKSPACE=""
COST_MODULE_ONLY=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage
show_usage() {
  echo "Usage: $0 [OPTIONS]"
  echo
  echo "Run Terraform commands safely in CI/CD environments with state locking"
  echo
  echo "Options:"
  echo "  -e, --environment ENV     Environment to target: sit, uat, prod (default: sit)"
  echo "  -a, --action ACTION       Action to perform: plan, apply, destroy (default: plan)"
  echo "  -w, --workspace NAME      Terraform workspace to use"
  echo "  -b, --backend-config PATH Path to backend config file"
  echo "  -c, --cost-only           Only operate on cost management module"
  echo "  -y, --auto-approve        Auto-approve applies and destroys"
  echo "  -h, --help                Show this help message"
  echo
  echo "Environment variables that should be set:"
  echo "  ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_TENANT_ID, ARM_SUBSCRIPTION_ID"
  echo "  TF_VAR_* variables for any inputs required by terraform"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -a|--action)
      ACTION="$2"
      shift 2
      ;;
    -w|--workspace)
      WORKSPACE="$2"
      shift 2
      ;;
    -b|--backend-config)
      BACKEND_CONFIG="$2"
      shift 2
      ;;
    -c|--cost-only)
      COST_MODULE_ONLY=true
      shift
      ;;
    -y|--auto-approve)
      AUTO_APPROVE=true
      shift
      ;;
    -h|--help)
      show_usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
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

# If backend config not specified, generate default path
if [ -z "$BACKEND_CONFIG" ]; then
  BACKEND_CONFIG="backends/${ENVIRONMENT}.tfbackend"
fi

# Check if backend config exists
if [ ! -f "$BACKEND_CONFIG" ]; then
  echo -e "${RED}Error: Backend config file not found: $BACKEND_CONFIG${NC}"
  echo -e "${YELLOW}You may need to run setup_terraform_backend.sh first${NC}"
  exit 1
fi

# Validate action
if [[ ! "$ACTION" =~ ^(plan|apply|destroy)$ ]]; then
  echo -e "${RED}Error: Action must be plan, apply, or destroy${NC}"
  exit 1
fi

# Check for required Azure environment variables
if [ -z "$ARM_CLIENT_ID" ] || [ -z "$ARM_CLIENT_SECRET" ] || [ -z "$ARM_TENANT_ID" ] || [ -z "$ARM_SUBSCRIPTION_ID" ]; then
  echo -e "${RED}Error: Missing required Azure credential environment variables${NC}"
  echo -e "Please ensure ARM_CLIENT_ID, ARM_CLIENT_SECRET, ARM_TENANT_ID, and ARM_SUBSCRIPTION_ID are set"
  exit 1
fi

# Enable enhanced state locking
export ARM_STORAGE_USE_AZUREAD=true
export TF_AZURE_STATE_LOCK_TIMEOUT=300
export TF_LOG=INFO

# Initialize Terraform with remote state
echo -e "${BLUE}Initializing Terraform with backend: $BACKEND_CONFIG${NC}"
terraform init -backend-config="$BACKEND_CONFIG"

# Select workspace if specified
if [ -n "$WORKSPACE" ]; then
  echo -e "${BLUE}Selecting workspace: $WORKSPACE${NC}"
  
  # Check if workspace exists, create if not
  if ! terraform workspace list | grep -q "$WORKSPACE"; then
    echo -e "${YELLOW}Workspace $WORKSPACE does not exist, creating...${NC}"
    terraform workspace new "$WORKSPACE"
  else
    terraform workspace select "$WORKSPACE"
  fi
fi

# Build common args
COMMON_ARGS=""
if [ "$COST_MODULE_ONLY" = true ]; then
  COMMON_ARGS="-target=module.cost_management"
fi

# Execute requested action
case "$ACTION" in
  plan)
    echo -e "${BLUE}Creating Terraform plan for $ENVIRONMENT...${NC}"
    if [ "$COST_MODULE_ONLY" = true ]; then
      echo -e "${YELLOW}Targeting cost management module only${NC}"
    fi
    
    terraform plan $COMMON_ARGS -out=tfplan
    
    # Create plan summary for CI logs
    echo -e "${GREEN}Plan generated successfully!${NC}"
    echo -e "Summary of changes:"
    terraform show -no-color tfplan | grep -E '^\s*[+~-]' | sort | uniq -c
    ;;
    
  apply)
    if [ -f "tfplan" ]; then
      echo -e "${BLUE}Applying existing Terraform plan...${NC}"
      terraform apply -auto-approve tfplan
    else
      echo -e "${BLUE}Creating and applying Terraform plan for $ENVIRONMENT...${NC}"
      if [ "$COST_MODULE_ONLY" = true ]; then
        echo -e "${YELLOW}Targeting cost management module only${NC}"
      fi
      
      APPLY_ARGS=""
      if [ "$AUTO_APPROVE" = true ]; then
        APPLY_ARGS="-auto-approve"
      fi
      
      terraform apply $APPLY_ARGS $COMMON_ARGS
    fi
    
    echo -e "${GREEN}Apply completed successfully!${NC}"
    terraform output
    ;;
    
  destroy)
    echo -e "${YELLOW}WARNING: You are about to destroy infrastructure in the $ENVIRONMENT environment!${NC}"
    if [ "$COST_MODULE_ONLY" = true ]; then
      echo -e "${YELLOW}Targeting cost management module only${NC}"
    fi
    
    # For destroy, always require confirmation unless auto-approve is set
    DESTROY_ARGS=""
    if [ "$AUTO_APPROVE" = true ]; then
      DESTROY_ARGS="-auto-approve"
    else
      echo -e "${RED}This action cannot be undone. Please confirm within 10 seconds...${NC}"
      sleep 10
      
      # Double-check confirmation
      read -p "Type 'yes' to confirm destruction: " CONFIRM
      if [ "$CONFIRM" != "yes" ]; then
        echo -e "${GREEN}Destruction cancelled.${NC}"
        exit 0
      fi
    fi
    
    terraform destroy $DESTROY_ARGS $COMMON_ARGS
    
    echo -e "${GREEN}Destroy completed successfully!${NC}"
    ;;
esac

# Create artifacts for CI/CD systems if needed
if [ "$ACTION" = "plan" ] && [ -n "$CI" ]; then
  # Create machine-readable JSON plan for automated analysis
  terraform show -json tfplan > tfplan.json
  
  # Create human-readable summary
  terraform show -no-color tfplan > tfplan.txt
  
  echo -e "${BLUE}Plan artifacts created: tfplan.json, tfplan.txt${NC}"
fi