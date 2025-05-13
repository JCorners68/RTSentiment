#!/bin/bash
# Script to detect drift between Terraform plan and apply phases
# This helps detect if changes were made to infrastructure between plan and apply

set -e

# Set colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
PLAN_FILE="tfplan"
ENVIRONMENT="sit"
VERBOSE=false
EXIT_ON_DRIFT=true

# Function to display usage
show_usage() {
  echo "Usage: $0 [OPTIONS]"
  echo
  echo "Detect infrastructure drift between Terraform plan and apply phases"
  echo
  echo "Options:"
  echo "  -p, --plan FILE          Path to plan file (default: tfplan)"
  echo "  -e, --environment ENV    Environment to check: sit, uat, prod (default: sit)"
  echo "  -v, --verbose            Show detailed drift information"
  echo "  -n, --no-exit            Don't exit on drift detection"
  echo "  -h, --help               Show this help message"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -p|--plan)
      PLAN_FILE="$2"
      shift 2
      ;;
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -v|--verbose)
      VERBOSE=true
      shift
      ;;
    -n|--no-exit)
      EXIT_ON_DRIFT=false
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

# Check if plan file exists
if [ ! -f "$PLAN_FILE" ]; then
  echo -e "${RED}Error: Plan file not found: $PLAN_FILE${NC}"
  exit 1
fi

# Check if BACKEND_CONFIG environment variable is set, otherwise use default
if [ -z "$BACKEND_CONFIG" ]; then
  BACKEND_CONFIG="backends/${ENVIRONMENT}.tfbackend"
fi

# Check if backend config exists
if [ ! -f "$BACKEND_CONFIG" ]; then
  echo -e "${RED}Error: Backend config file not found: $BACKEND_CONFIG${NC}"
  echo -e "${YELLOW}You may need to run setup_terraform_backend.sh first${NC}"
  exit 1
fi

echo -e "${BLUE}Detecting infrastructure drift...${NC}"
echo -e "${BLUE}Environment: $ENVIRONMENT${NC}"
echo -e "${BLUE}Plan file: $PLAN_FILE${NC}"

# Create a temporary directory for our work
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Extract the plan JSON
echo -e "${BLUE}Extracting plan details...${NC}"
terraform show -json "$PLAN_FILE" > "$TEMP_DIR/plan.json"

# Generate a new plan based on current state
echo -e "${BLUE}Generating fresh plan to compare with stored plan...${NC}"

# Generate a plan with the same target scope as the original plan
# First, we need to extract targets from the original plan file
PLAN_TARGETS=$(grep -o "\-target=[^ ]*" "$PLAN_FILE" 2>/dev/null || echo "")

# Create a new temp dir for the fresh plan
mkdir -p "$TEMP_DIR/fresh"
pushd "$TEMP_DIR/fresh" > /dev/null

# Initialize terraform in temp directory
echo -e "${BLUE}Initializing Terraform...${NC}"
terraform init -backend-config="$BACKEND_CONFIG" > /dev/null

# Generate a fresh plan
echo -e "${BLUE}Creating fresh plan...${NC}"
if [ -n "$PLAN_TARGETS" ]; then
  # If there are targets, use them for the fresh plan
  echo -e "${YELLOW}Original plan used targets: $PLAN_TARGETS${NC}"
  terraform plan -out="$TEMP_DIR/fresh.tfplan" $PLAN_TARGETS > /dev/null
else
  terraform plan -out="$TEMP_DIR/fresh.tfplan" > /dev/null
fi

# Convert fresh plan to JSON
terraform show -json "$TEMP_DIR/fresh.tfplan" > "$TEMP_DIR/fresh.json"

popd > /dev/null

# Compare the plans
echo -e "${BLUE}Comparing plans to detect drift...${NC}"

# Extract resource changes from both plans
jq -r '.resource_changes[] | "\(.address)|\(.change.actions[])"' "$TEMP_DIR/plan.json" | sort > "$TEMP_DIR/original_changes.txt"
jq -r '.resource_changes[] | "\(.address)|\(.change.actions[])"' "$TEMP_DIR/fresh.json" | sort > "$TEMP_DIR/fresh_changes.txt"

# Check if there are differences
if ! diff -q "$TEMP_DIR/original_changes.txt" "$TEMP_DIR/fresh_changes.txt" > /dev/null; then
  echo -e "${RED}DRIFT DETECTED: Infrastructure state has changed since plan was created!${NC}"
  
  if [ "$VERBOSE" = true ]; then
    echo -e "${YELLOW}Differences between original plan and current state:${NC}"
    echo "---------------------------------------------------------"
    
    # Show only in original plan
    echo -e "${RED}Resources in original plan but not in current state:${NC}"
    comm -23 "$TEMP_DIR/original_changes.txt" "$TEMP_DIR/fresh_changes.txt" | 
      awk -F'|' '{ printf "  %s (%s)\n", $1, $2 }'
    
    # Show only in fresh plan
    echo -e "${GREEN}Resources in current state but not in original plan:${NC}"
    comm -13 "$TEMP_DIR/original_changes.txt" "$TEMP_DIR/fresh_changes.txt" | 
      awk -F'|' '{ printf "  %s (%s)\n", $1, $2 }'
    
    echo "---------------------------------------------------------"
  fi
  
  echo -e "${YELLOW}RECOMMENDATION: Generate a new plan before applying changes${NC}"
  echo -e "${YELLOW}Run 'terraform plan -out=tfplan' to create a new plan${NC}"
  
  if [ "$EXIT_ON_DRIFT" = true ]; then
    exit 1
  fi
else
  echo -e "${GREEN}No drift detected. The plan is still accurate.${NC}"
fi