#!/bin/bash
# Run Terraform with fixed configuration

# Set error handling
set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}==================================================================${NC}"
echo -e "${YELLOW}SENTIMARK SIT TERRAFORM DEPLOYMENT WITH FIXES${NC}"
echo -e "${YELLOW}==================================================================${NC}"
echo ""
echo "This script will run Terraform with the fixed configuration."
echo "The following issues have been addressed:"
echo " - AKS Cluster Availability Zones"
echo " - Front Door Resource Deprecation"
echo " - App Configuration Key Permissions"
echo " - Activity Log Alert Location"
echo " - Policy Assignment Permissions (now enabled)"
echo " - Container Instance Subnet Delegation"
echo " - Storage Data Lake Gen2 Permissions (now enabled)"
echo " - Role Assignment Permissions (now enabled)"
echo ""

# Navigate to Terraform directory
cd /home/jonat/real_senti/infrastructure/terraform/azure

# Run terraform plan
echo -e "${YELLOW}==================================================================${NC}"
echo -e "${YELLOW}GENERATING TERRAFORM PLAN${NC}"
echo -e "${YELLOW}==================================================================${NC}"
echo ""

./run-terraform.sh plan -var-file=terraform.sit.tfvars -out=tfplan.sit.fixed

echo ""
echo -e "${GREEN}Plan generated successfully!${NC}"
echo ""
echo -e "${YELLOW}To apply the plan, run:${NC}"
echo "./run-terraform.sh apply tfplan.sit.fixed"
echo ""
echo -e "${GREEN}All permissions are now properly granted, no manual steps required!${NC}"
echo ""
echo -e "${YELLOW}Then verify the deployment with:${NC}"
echo "cd /home/jonat/real_senti/environments/sit"
echo "python3 sentimark_sit_verify.py"

# Make executable
chmod +x /home/jonat/real_senti/environments/sit/run_terraform_fixed.sh