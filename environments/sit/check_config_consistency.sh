#!/bin/bash
# Consistency checker script for SIT environment configuration
# This script ensures that all configuration files use consistent settings

set -e

# Color codes for nicer output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}SIT Environment Configuration Consistency Check${NC}"
echo -e "${BLUE}==========================================${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../" && pwd)"

echo -e "${BLUE}Checking configuration files for consistency...${NC}"
echo ""

# Files to check
DEPLOY_SCRIPT="$SCRIPT_DIR/deploy_azure_sit.sh"
TERRAFORM_VARS="$REPO_ROOT/infrastructure/terraform/azure/terraform.sit.tfvars"
VERIFICATION_SCRIPT="$SCRIPT_DIR/sentimark_sit_verify.py"

# Check if files exist
if [ ! -f "$DEPLOY_SCRIPT" ]; then
  echo -e "${RED}ERROR: Deploy script not found at $DEPLOY_SCRIPT${NC}"
  exit 1
fi

if [ ! -f "$TERRAFORM_VARS" ]; then
  echo -e "${RED}ERROR: Terraform variables file not found at $TERRAFORM_VARS${NC}"
  exit 1
fi

if [ ! -f "$VERIFICATION_SCRIPT" ]; then
  echo -e "${RED}ERROR: Verification script not found at $VERIFICATION_SCRIPT${NC}"
  exit 1
fi

# Extract configuration values from files
DEPLOY_LOCATION=$(grep "LOCATION=" "$DEPLOY_SCRIPT" | grep -v "#" | head -1 | cut -d'"' -f2)
DEPLOY_RG=$(grep "RESOURCE_GROUP=" "$DEPLOY_SCRIPT" | grep -v "#" | head -1 | cut -d'"' -f2)
DEPLOY_AKS=$(grep "AKS_CLUSTER=" "$DEPLOY_SCRIPT" | grep -v "#" | head -1 | cut -d'"' -f2)

TF_LOCATION=$(grep "location =" "$TERRAFORM_VARS" | head -1 | awk -F'"' '{print $2}')
TF_RG=$(grep "resource_group_name =" "$TERRAFORM_VARS" | head -1 | awk -F'"' '{print $2}')
TF_AKS=$(grep "aks_cluster_name =" "$TERRAFORM_VARS" | head -1 | awk -F'"' '{print $2}')

VERIFY_LOCATION=$(grep "region.*=" "$VERIFICATION_SCRIPT" | head -1 | awk -F'"' '{print $2}')

# Check consistency
errors=0
warnings=0

echo -e "${BLUE}Checking region consistency:${NC}"
if [ "$DEPLOY_LOCATION" = "$TF_LOCATION" ] && [ "$DEPLOY_LOCATION" = "$VERIFY_LOCATION" ]; then
  echo -e "${GREEN}✓ Region consistent across all files: $DEPLOY_LOCATION${NC}"
else
  echo -e "${RED}× Region inconsistent:${NC}"
  echo -e "  - Deploy script: $DEPLOY_LOCATION"
  echo -e "  - Terraform vars: $TF_LOCATION"
  echo -e "  - Verification script: $VERIFY_LOCATION"
  errors=$((errors+1))
fi

echo -e "${BLUE}Checking resource group name consistency:${NC}"
if [ "$DEPLOY_RG" = "$TF_RG" ]; then
  echo -e "${GREEN}✓ Resource group consistent: $DEPLOY_RG${NC}"
else
  echo -e "${RED}× Resource group inconsistent:${NC}"
  echo -e "  - Deploy script: $DEPLOY_RG"
  echo -e "  - Terraform vars: $TF_RG"
  errors=$((errors+1))
fi

echo -e "${BLUE}Checking AKS cluster name consistency:${NC}"
if [ "$DEPLOY_AKS" = "$TF_AKS" ]; then
  echo -e "${GREEN}✓ AKS cluster name consistent: $DEPLOY_AKS${NC}"
else
  echo -e "${RED}× AKS cluster name inconsistent:${NC}"
  echo -e "  - Deploy script: $DEPLOY_AKS"
  echo -e "  - Terraform vars: $TF_AKS"
  errors=$((errors+1))
fi

# Check terraform.sit.tfvars config for best practices
echo -e "${BLUE}Checking Terraform configuration for best practices:${NC}"

# Check for policy assignments
TF_POLICIES=$(grep "enable_policy_assignments" "$TERRAFORM_VARS" | grep -v "#" | awk -F'=' '{print $2}' | tr -d ' ')
if [ "$TF_POLICIES" = "false" ]; then
  echo -e "${GREEN}✓ Policy assignments disabled for SIT environment${NC}"
else
  echo -e "${YELLOW}! Policy assignments enabled for SIT environment - may cause auth errors${NC}"
  warnings=$((warnings+1))
fi

# Check for container deployment
TF_CONTAINER=$(grep "deploy_container" "$TERRAFORM_VARS" | grep -v "#" | awk -F'=' '{print $2}' | tr -d ' ')
if [ "$TF_CONTAINER" = "false" ]; then
  echo -e "${GREEN}✓ Container deployment disabled for SIT environment${NC}"
else
  echo -e "${YELLOW}! Container deployment enabled - may cause subnet delegation errors${NC}"
  warnings=$((warnings+1))
fi

# Check for AKS availability zones
TF_ZONES=$(grep "enable_aks_availability_zones" "$TERRAFORM_VARS" | grep -v "#" | awk -F'=' '{print $2}' | tr -d ' ')
if [ "$TF_ZONES" = "false" ]; then
  echo -e "${GREEN}✓ AKS availability zones disabled for westus region${NC}"
else
  echo -e "${RED}× AKS availability zones enabled but not supported in westus${NC}"
  errors=$((errors+1))
fi

# Output summary
echo ""
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}Summary:${NC}"
if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
  echo -e "${GREEN}All configuration files are consistent and follow best practices!${NC}"
  exit 0
elif [ $errors -eq 0 ]; then
  echo -e "${YELLOW}Configuration has $warnings warning(s) but no critical errors.${NC}"
  exit 0
else
  echo -e "${RED}Configuration has $errors error(s) and $warnings warning(s).${NC}"
  echo -e "${RED}Please fix the errors before deploying.${NC}"
  exit 1
fi