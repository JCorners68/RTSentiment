#!/bin/bash
# Script to interact with private AKS cluster using az aks command invoke
# This approach eliminates the need for VPN connections and DNS resolution issues

# Variables
RESOURCE_GROUP="sentimark-sit-rg"
CLUSTER_NAME="sentimark-sit-aks"
DEFAULT_COMMAND="kubectl get nodes"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed.${NC}"
    exit 1
fi

# Display banner
echo -e "${BLUE}=====================================================${NC}"
echo -e "${BLUE}  Access Private AKS Cluster Without VPN or DNS Config ${NC}"
echo -e "${BLUE}=====================================================${NC}"
echo ""

# Parse command arguments
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}No command specified, using default: '${DEFAULT_COMMAND}'${NC}"
    KUBECTL_COMMAND="$DEFAULT_COMMAND"
else
    KUBECTL_COMMAND="$*"
fi

echo -e "Running command on AKS cluster: ${GREEN}${KUBECTL_COMMAND}${NC}"
echo ""

# Execute command on AKS cluster 
echo "Executing via az aks command invoke..."
az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "$KUBECTL_COMMAND"

exit_code=$?
if [ $exit_code -ne 0 ]; then
    echo -e "${RED}Command failed with exit code $exit_code${NC}"
    echo -e "${YELLOW}Possible issues:${NC}"
    echo "- Check if you're logged into Azure CLI (run 'az login')"
    echo "- Verify you have sufficient permissions for AKS command execution"
    echo "- Check if the cluster name and resource group are correct"
    exit $exit_code
fi

echo -e "${GREEN}Command executed successfully!${NC}"

# Display help message for future use
echo ""
echo -e "${BLUE}======== Quick Reference ========${NC}"
echo "Usage examples:"
echo "./aks_command.sh kubectl get pods -A"
echo "./aks_command.sh kubectl apply -f deployment.yaml"
echo "./aks_command.sh helm list -A"
echo ""
echo "You can use this script as a kubectl/helm wrapper to interact with your private AKS cluster"
echo "without needing to set up VPN or resolve DNS issues."