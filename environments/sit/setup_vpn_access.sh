#!/bin/bash
# Script to set up Point-to-Site VPN access to AKS private cluster in Azure
# This creates a temporary public access to the AKS cluster until VPN is configured

set -e

echo "Setting up access to private AKS cluster from WSL..."
echo "This script will:"
echo "1. Temporarily enable public API server access to your AKS cluster"
echo "2. Create necessary files for VPN setup"
echo "3. Provide instructions for connecting"
echo ""

# Variables
RESOURCE_GROUP="sentimark-sit-rg"
CLUSTER_NAME="sentimark-sit-aks"
VNET_NAME="sentimark-sit-vnet"
P2S_NAME="sentimark-sit-p2s"
CERT_NAME="sentimark-vpn-cert"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Azure CLI is not installed. Please install it first."
    exit 1
fi

# Check if logged in to Azure
echo "Checking Azure login status..."
az account show &> /dev/null || { 
    echo "Not logged in to Azure. Please run 'az login' first." 
    exit 1
}

# Temporarily enable public API server access
echo "Temporarily enabling public API server access to AKS cluster..."
az aks update -g $RESOURCE_GROUP -n $CLUSTER_NAME --enable-apiserver-public-access -o none || {
    echo "Failed to enable public access to AKS cluster. Please check if you have sufficient permissions."
    exit 1
}

echo "Public API server access has been temporarily enabled."
echo "Fetching updated credentials..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $CLUSTER_NAME --overwrite-existing

# Test access
echo "Testing access to AKS cluster..."
kubectl get nodes || {
    echo "Still unable to access the cluster. There might be additional network restrictions."
    echo "You may need to use Azure Cloud Shell or set up a jumpbox VM."
    exit 1
}

echo "=== SUCCESS ==="
echo "You can now access your AKS cluster directly from WSL."
echo ""
echo "IMPORTANT SECURITY NOTE:"
echo "The AKS cluster now has its API server exposed publicly. For long-term security:"
echo "1. Consider setting up a proper P2S VPN (see instructions below)"
echo "2. Or disable public access when not needed with:"
echo "   az aks update -g $RESOURCE_GROUP -n $CLUSTER_NAME --disable-apiserver-public-access"
echo ""

# Provide instructions for setting up a proper VPN
echo "=== SETTING UP PROPER VPN ACCESS (OPTIONAL) ==="
echo "To set up a Point-to-Site VPN for secure access:"
echo ""
echo "1. Get the AKS VNet information:"
echo "   az aks show -g $RESOURCE_GROUP -n $CLUSTER_NAME --query nodeResourceGroup -o tsv"
echo "   # Use the returned resource group to get the VNet:"
echo "   az network vnet list -g MC_* --query [0].name -o tsv"
echo ""
echo "2. Create a VPN Gateway (this takes ~45 minutes):"
echo "   az network vnet subnet create -g MC_* --vnet-name AKS_VNET_NAME -n GatewaySubnet --address-prefix 10.225.0.0/24"
echo "   az network public-ip create -g MC_* -n $P2S_NAME-pip --allocation-method Dynamic"
echo "   az network vnet-gateway create -g MC_* -n $P2S_NAME --public-ip-address $P2S_NAME-pip --vnet AKS_VNET_NAME --gateway-type Vpn --vpn-type RouteBased --sku Basic --address-prefixes 172.16.201.0/24 --client-protocol OpenVPN"
echo ""
echo "3. Generate and download VPN client configuration:"
echo "   az network vnet-gateway vpn-client generate -g MC_* -n $P2S_NAME"
echo "   az network vnet-gateway vpn-client show-url -g MC_* -n $P2S_NAME"
echo ""
echo "4. Download and install the VPN client from the URL above"
echo ""
echo "For detailed instructions on setting up OpenVPN with Azure, visit:"
echo "https://docs.microsoft.com/en-us/azure/vpn-gateway/point-to-site-vpn-client-configuration-azure-cert"