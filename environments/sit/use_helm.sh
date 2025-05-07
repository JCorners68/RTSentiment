#!/bin/bash
# Script to install Sentimark services using Helm charts

set -e

# Variables
RESOURCE_GROUP="sentimark-sit-rg"
CLUSTER_NAME="sentimark-sit-aks"
RELEASE_NAME="sit"
NAMESPACE="sit"
HELM_DIR="/home/jonat/real_senti/infrastructure/helm"
VALUES_FILE="$HELM_DIR/sentimark-services/values.yaml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Deploying Sentimark services using Helm charts ===${NC}"
echo "This script will:"
echo "1. Verify access to the AKS cluster"
echo "2. Create the $NAMESPACE namespace if it doesn't exist"
echo "3. Deploy services using Helm"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed.${NC}"
    echo "Please install it first: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed.${NC}"
    echo "Please install it first: https://kubernetes.io/docs/tasks/tools/"
    exit 1
fi

# Check if Helm is installed
if ! command -v helm &> /dev/null; then
    echo -e "${RED}Error: Helm is not installed.${NC}"
    echo "Please install it first: https://helm.sh/docs/intro/install/"
    exit 1
fi

# Check if logged in to Azure
echo "Checking Azure login status..."
az account show &> /dev/null || { 
    echo -e "${RED}Not logged in to Azure. Please run 'az login' first.${NC}" 
    exit 1
}

# Get AKS credentials
echo "Getting AKS credentials..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME --overwrite-existing || {
    echo -e "${RED}Failed to get AKS credentials.${NC}"
    echo -e "${YELLOW}Trying to verify AKS exists...${NC}"
    
    # Check if AKS exists
    if az aks show --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME &> /dev/null; then
        echo -e "${YELLOW}AKS cluster exists but credentials could not be obtained.${NC}"
        echo "This is likely due to the cluster having a private endpoint."
        echo -e "${YELLOW}Attempting to enable temporary public access...${NC}"
        
        # Ask for confirmation
        read -p "Do you want to enable temporary public access to the AKS API server? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Enable public access
            az aks update -g $RESOURCE_GROUP -n $CLUSTER_NAME --enable-apiserver-public-access -o none
            echo "Getting credentials again..."
            az aks get-credentials --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME --overwrite-existing
        else
            echo "You can use Azure Cloud Shell instead, which has direct access to private AKS clusters."
            exit 1
        fi
    else
        echo -e "${RED}AKS cluster not found.${NC}"
        exit 1
    fi
}

# Test connection to AKS
if ! kubectl get nodes &> /dev/null; then
    echo -e "${RED}Failed to connect to AKS cluster.${NC}"
    echo "Check DNS resolution for private AKS endpoint."
    echo "Recommendations:"
    echo "1. Use Azure Cloud Shell"
    echo "2. Set up Point-to-Site VPN to Azure"
    echo "3. Run the setup_vpn_access.sh script"
    exit 1
else
    echo -e "${GREEN}Successfully connected to AKS cluster.${NC}"
    kubectl get nodes
fi

# Create namespace if it doesn't exist
if ! kubectl get namespace $NAMESPACE &> /dev/null; then
    echo "Creating namespace $NAMESPACE..."
    kubectl create namespace $NAMESPACE
else
    echo "Namespace $NAMESPACE already exists."
fi

# Check for spot instance node pools
echo "Checking for spot instance node pools..."
SPOT_POOLS=$(kubectl get nodes --show-labels | grep -E "agentpool=dataspots|agentpool=lowspots" | wc -l)
if [ $SPOT_POOLS -eq 0 ]; then
    echo -e "${YELLOW}Warning: No spot instance node pools found.${NC}"
    echo "The Helm chart is configured to use spot instances."
    echo "You may need to modify the values file or create spot instance node pools."
    
    # Ask for confirmation
    read -p "Do you want to continue without spot instances? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Deployment aborted."
        exit 1
    fi
else
    echo -e "${GREEN}Found $SPOT_POOLS spot instance node pools.${NC}"
    kubectl get nodes --show-labels | grep -E "agentpool=dataspots|agentpool=lowspots"
fi

# Install or upgrade the Helm chart
echo "Deploying services using Helm..."
helm upgrade --install $RELEASE_NAME $HELM_DIR/sentimark-services \
    --namespace $NAMESPACE \
    --create-namespace \
    --values $VALUES_FILE

echo -e "${GREEN}Deployment completed!${NC}"
echo "To check the deployment status, run:"
echo "  kubectl get pods -n $NAMESPACE"
echo "  kubectl get services -n $NAMESPACE"
echo "  kubectl get ingress -n $NAMESPACE"

# Disable public access if it was temporarily enabled
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Do you want to disable public access to the AKS API server now? (y/n)${NC}"
    read -p "" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        az aks update -g $RESOURCE_GROUP -n $CLUSTER_NAME --disable-apiserver-public-access -o none
        echo -e "${GREEN}Public access disabled.${NC}"
    else
        echo -e "${YELLOW}Public access remains enabled. You should disable it when not needed:${NC}"
        echo "  az aks update -g $RESOURCE_GROUP -n $CLUSTER_NAME --disable-apiserver-public-access"
    fi
fi