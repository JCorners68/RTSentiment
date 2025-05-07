#!/bin/bash

# RT Sentiment Analysis - SIT Environment Verification Script
# This script verifies the SIT environment deployment on Azure

echo "Verifying RT Sentiment Analysis SIT environment deployment in westus region..."

# Run configuration consistency check
echo "Running configuration consistency check..."
"${BASH_SOURCE%/*}/check_config_consistency.sh"
if [ $? -ne 0 ]; then
  echo "Configuration consistency check failed. Verification may produce inconsistent results."
  echo "Please fix configuration issues before proceeding with the deployment."
fi
echo "Configuration consistency check completed."

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
CONFIG_DIR="${SCRIPT_DIR}/config"
LOGS_DIR="${SCRIPT_DIR}/logs"

# Create directories if they don't exist
mkdir -p "${CONFIG_DIR}"
mkdir -p "${LOGS_DIR}"

# Check resource group and cluster deployment
if [ -f "${CONFIG_DIR}/cluster_info.txt" ]; then
    echo "✅ Cluster info found:"
    cat "${CONFIG_DIR}/cluster_info.txt"
else
    echo "❌ Cluster info file not found!"
    exit 1
fi

# Check storage connection
if [ -f "${CONFIG_DIR}/storage_connection.txt" ]; then
    echo "✅ Storage connection configured"
    # Don't print the connection string as it contains secrets
    echo "Connection string saved in ${CONFIG_DIR}/storage_connection.txt"
else
    echo "❌ Storage connection file not found!"
fi

# Check latest deployment log
LATEST_LOG=$(ls -t ${LOGS_DIR}/deployment_*.json 2>/dev/null | head -1)
if [ -n "${LATEST_LOG}" ]; then
    echo "✅ Deployment log found:"
    cat "${LATEST_LOG}"
else
    echo "❓ No deployment logs found."
fi

# Check kubeconfig
if [ -f "${CONFIG_DIR}/kubeconfig" ]; then
    echo "✅ Kubernetes configuration found"
    echo "To use this configuration, run:"
    echo "export KUBECONFIG=\"${CONFIG_DIR}/kubeconfig\""
    
    # Verify if kubectl is available
    if command -v kubectl &> /dev/null; then
        echo "✅ kubectl is available"
        export KUBECONFIG="${CONFIG_DIR}/kubeconfig"
        echo "Testing connection to Kubernetes cluster..."
        if kubectl cluster-info; then
            echo "✅ Successfully connected to Kubernetes cluster"
            
            # Check for node pools including spot instances
            echo "Checking node pools..."
            kubectl get nodes --show-labels | grep -E "agentpool=dataspots|agentpool=lowspots"
            
            # Show running pods
            echo "Checking running pods..."
            kubectl get pods -A
        else
            echo "❌ Failed to connect to Kubernetes cluster"
            echo
            echo "This is likely due to private AKS endpoint DNS resolution issues."
            echo "To verify the cluster, use Azure Cloud Shell:"
            echo "1. Open https://portal.azure.com"
            echo "2. Click the Cloud Shell icon in the top navigation bar"
            echo "3. Run these commands to verify the cluster:"
            echo "   az aks show --resource-group ${RG_NAME} --name ${AKS_NAME} --query provisioningState -o tsv"
            echo "   az aks nodepool list --resource-group ${RG_NAME} --cluster-name ${AKS_NAME} -o table"
            echo "   az aks get-credentials --resource-group ${RG_NAME} --name ${AKS_NAME}"
            echo "   kubectl get nodes"
            echo "   kubectl get pods -A"
            
            # Fallback to Azure CLI verification without kubectl
            if command -v az &> /dev/null; then
                echo
                echo "Attempting to verify using Azure CLI instead..."
                echo "Checking AKS cluster status:"
                az aks show --resource-group ${RG_NAME} --name ${AKS_NAME} --query provisioningState -o tsv
                
                echo "Checking node pools (including spot instances):"
                az aks nodepool list --resource-group ${RG_NAME} --cluster-name ${AKS_NAME} -o table
            fi
        fi
    else
        echo "❌ kubectl is not installed. You'll need to install it to interact with the cluster."
        echo "Installation instructions: https://kubernetes.io/docs/tasks/tools/install-kubectl/"
    fi
else
    echo "❌ Kubernetes configuration file not found!"
fi

# Summary
echo 
echo "SIT Environment Deployment Summary:"
echo "===================================="
# Get values from config files for consistent output
LOCATION="westus"  # Default to westus
RG_NAME="sentimark-sit-rg"
AKS_NAME="sentimark-sit-aks"
STORAGE_NAME="sentimarksitstorage"

# Extract actual values from cluster_info.txt if available
if [ -f "${CONFIG_DIR}/cluster_info.txt" ]; then
    LOCATION=$(grep "Location:" "${CONFIG_DIR}/cluster_info.txt" | cut -d' ' -f2)
    RG_NAME=$(grep "Resource Group:" "${CONFIG_DIR}/cluster_info.txt" | cut -d' ' -f3)
    AKS_NAME=$(grep "AKS Cluster Name:" "${CONFIG_DIR}/cluster_info.txt" | cut -d' ' -f4)
    STORAGE_NAME=$(grep "Storage Account:" "${CONFIG_DIR}/cluster_info.txt" | cut -d' ' -f3)
fi

echo "Resource Group: ${RG_NAME} (in ${LOCATION})"
echo "AKS Cluster: ${AKS_NAME}"
echo "Storage Account: ${STORAGE_NAME}"
echo
echo "To deploy services, you'll need to:"
echo "1. Install kubectl if not already installed"
echo "2. Set KUBECONFIG environment variable: export KUBECONFIG=\"${CONFIG_DIR}/kubeconfig\""
echo "3. Run the deploy_services.sh script"
echo
echo "Alternatively, you can use the Azure Portal to manage your resources:"
echo "https://portal.azure.com/#resource/subscriptions/644936a7-e58a-4ccb-a882-0005f213f5bd/resourceGroups/sentimark-sit-rg/overview"