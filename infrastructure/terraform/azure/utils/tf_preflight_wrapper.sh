#!/bin/bash
# Terraform Pre-Flight Wrapper
#
# This script is a wrapper for run-terraform.sh that runs pre-flight checks
# before executing Terraform commands. It helps prevent common deployment
# failures by validating the environment first.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"
PREFLIGHT_SCRIPT="$SCRIPT_DIR/tf_preflight.sh"
TERRAFORM_SCRIPT="$PARENT_DIR/run-terraform.sh"

# Default settings
RUN_PREFLIGHT=true
SKIP_ON_FAILURE=false
ENVIRONMENT=""
BACKEND_CONFIG=""
PREFLIGHT_ONLY=false
PREFLIGHT_OPTIONS=""

# Function to display usage information
show_usage() {
  cat << EOF
Terraform Pre-Flight Wrapper

USAGE:
  $(basename "$0") [WRAPPER_OPTIONS] [TERRAFORM_OPTIONS] COMMAND

WRAPPER OPTIONS:
  --no-preflight              Skip pre-flight checks
  --skip-on-failure           Continue even if pre-flight checks fail
  --preflight-only            Run only pre-flight checks, don't execute Terraform
  --preflight-env ENV         Specify environment for pre-flight checks
  --preflight-backend FILE    Specify backend config for pre-flight checks
  --preflight-option OPTION   Pass additional option to pre-flight script
  --help                      Show this help message

EXAMPLES:
  # Run pre-flight checks before plan
  $(basename "$0") plan
  
  # Skip pre-flight checks
  $(basename "$0") --no-preflight plan
  
  # Run only pre-flight checks
  $(basename "$0") --preflight-only --preflight-env prod
  
  # Run with custom pre-flight options
  $(basename "$0") --preflight-option "--no-quota-check" plan
  
  # Run with terraform options
  $(basename "$0") --preflight-env sit -var 'foo=bar' plan
EOF
  exit 0
}

# Parse arguments for the wrapper
TERRAFORM_ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-preflight)
      RUN_PREFLIGHT=false
      shift
      ;;
    --skip-on-failure)
      SKIP_ON_FAILURE=true
      shift
      ;;
    --preflight-only)
      PREFLIGHT_ONLY=true
      shift
      ;;
    --preflight-env)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --preflight-backend)
      BACKEND_CONFIG="$2"
      shift 2
      ;;
    --preflight-option)
      PREFLIGHT_OPTIONS="$PREFLIGHT_OPTIONS $2"
      shift 2
      ;;
    --help)
      show_usage
      ;;
    *)
      # Pass all other arguments to Terraform
      TERRAFORM_ARGS+=("$1")
      shift
      ;;
  esac
done

# Attempt to determine environment from Terraform args if not explicitly set
if [ -z "$ENVIRONMENT" ]; then
  # Check for backend-config with environment indication
  for arg in "${TERRAFORM_ARGS[@]}"; do
    if [[ "$arg" == *"backend-config"*"sit"* ]]; then
      ENVIRONMENT="sit"
      break
    elif [[ "$arg" == *"backend-config"*"uat"* ]]; then
      ENVIRONMENT="uat"
      break
    elif [[ "$arg" == *"backend-config"*"prod"* ]]; then
      ENVIRONMENT="prod"
      break
    fi
  done
  
  # Check for var-file with environment indication
  for arg in "${TERRAFORM_ARGS[@]}"; do
    if [[ "$arg" == *"terraform.sit.tfvars"* ]]; then
      ENVIRONMENT="sit"
      break
    elif [[ "$arg" == *"terraform.uat.tfvars"* ]]; then
      ENVIRONMENT="uat"
      break
    elif [[ "$arg" == *"terraform.prod.tfvars"* ]]; then
      ENVIRONMENT="prod"
      break
    fi
  done
  
  # Default to SIT if not detected
  if [ -z "$ENVIRONMENT" ]; then
    ENVIRONMENT="sit"
    echo -e "${YELLOW}Environment not specified, defaulting to: $ENVIRONMENT${NC}"
  fi
fi

# Attempt to determine backend config from Terraform args if not explicitly set
if [ -z "$BACKEND_CONFIG" ]; then
  for arg in "${TERRAFORM_ARGS[@]}"; do
    if [[ "$arg" == *"-backend-config="* ]]; then
      BACKEND_CONFIG="${arg#*=}"
      break
    fi
  done
fi

# Determine what Terraform command is being run
TERRAFORM_COMMAND=""
for arg in "${TERRAFORM_ARGS[@]}"; do
  if [[ "$arg" == "plan" || "$arg" == "apply" || "$arg" == "destroy" || \
        "$arg" == "import" || "$arg" == "init" ]]; then
    TERRAFORM_COMMAND="$arg"
    break
  fi
done

# Skip pre-flight for certain commands
if [[ "$TERRAFORM_COMMAND" == "init" || "$TERRAFORM_COMMAND" == "output" || \
      "$TERRAFORM_COMMAND" == "state" || "$TERRAFORM_COMMAND" == "fmt" || \
      "$TERRAFORM_COMMAND" == "validate" || "$TERRAFORM_COMMAND" == "force-unlock" ]]; then
  RUN_PREFLIGHT=false
  echo -e "${YELLOW}Skipping pre-flight checks for command: $TERRAFORM_COMMAND${NC}"
fi

# Run pre-flight checks if enabled
if [ "$RUN_PREFLIGHT" = true ]; then
  echo -e "${BLUE}Running pre-flight checks for environment: $ENVIRONMENT${NC}"
  
  # Build pre-flight command
  PREFLIGHT_CMD="$PREFLIGHT_SCRIPT --environment $ENVIRONMENT"
  
  # Add backend config if specified
  if [ -n "$BACKEND_CONFIG" ]; then
    PREFLIGHT_CMD="$PREFLIGHT_CMD --backend $BACKEND_CONFIG"
  fi
  
  # Add any additional pre-flight options
  if [ -n "$PREFLIGHT_OPTIONS" ]; then
    PREFLIGHT_CMD="$PREFLIGHT_CMD $PREFLIGHT_OPTIONS"
  fi
  
  # Run pre-flight checks
  echo -e "${BLUE}Executing: $PREFLIGHT_CMD${NC}"
  if ! eval "$PREFLIGHT_CMD"; then
    echo -e "${RED}Pre-flight checks failed!${NC}"
    
    if [ "$SKIP_ON_FAILURE" = true ]; then
      echo -e "${YELLOW}Continuing despite pre-flight check failures${NC}"
    else
      echo -e "${RED}Aborting Terraform execution due to pre-flight check failures${NC}"
      echo -e "${YELLOW}Use --skip-on-failure to continue anyway${NC}"
      exit 1
    fi
  else
    echo -e "${GREEN}Pre-flight checks passed!${NC}"
  fi
fi

# Skip Terraform execution if only running pre-flight
if [ "$PREFLIGHT_ONLY" = true ]; then
  echo -e "${BLUE}Pre-flight only mode, skipping Terraform execution${NC}"
  exit 0
fi

# Execute Terraform with all original arguments
if [ "${#TERRAFORM_ARGS[@]}" -gt 0 ]; then
  echo -e "${BLUE}Executing Terraform command: ${TERRAFORM_ARGS[*]}${NC}"
  "$TERRAFORM_SCRIPT" "${TERRAFORM_ARGS[@]}"
else
  echo -e "${YELLOW}No Terraform arguments provided${NC}"
  echo -e "${YELLOW}Usage examples:${NC}"
  echo -e "${YELLOW}  $(basename "$0") plan${NC}"
  echo -e "${YELLOW}  $(basename "$0") apply${NC}"
  echo -e "${YELLOW}  $(basename "$0") --preflight-env prod destroy${NC}"
  exit 1
fi