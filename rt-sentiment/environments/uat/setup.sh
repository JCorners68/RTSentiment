#!/bin/bash

# RT Sentiment Analysis - UAT Environment Setup Script
# This script sets up the User Acceptance Testing (UAT) environment in Azure.
# Subscription ID: 644936a7-e58a-4ccb-a882-0005f213f5bd
# Tenant ID: 1ced8c49-a03c-439c-9ff1-0c23f5128720

# Display a message at the start
echo "Setting up RT Sentiment Analysis UAT environment..."
echo "Using subscription: 644936a7-e58a-4ccb-a882-0005f213f5bd"
echo "Using tenant: 1ced8c49-a03c-439c-9ff1-0c23f5128720"

# Create the necessary directories if they don't exist
mkdir -p config
mkdir -p tests
mkdir -p logs

# Set Azure-specific variables
RESOURCE_GROUP="rt-sentiment-uat"
LOCATION="westus"  # Changed to US West for low latency
CONTAINER_REGISTRY="rtsentiregistry"
AKS_CLUSTER="rt-sentiment-aks"
PPG_NAME="rt-sentiment-ppg"  # Proximity Placement Group for low latency
STORAGE_ACCOUNT="rtsentistorage"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Azure CLI is not installed. Please install Azure CLI first."
    exit 1
fi

# Ensure Azure CLI is logged in
echo "Checking Azure CLI login status..."
az account show &> /dev/null
if [ $? -ne 0 ]; then
    echo "Not logged in to Azure CLI. Please run 'az login --tenant 1ced8c49-a03c-439c-9ff1-0c23f5128720' first."
    exit 1
fi

# Set subscription
echo "Setting subscription to 644936a7-e58a-4ccb-a882-0005f213f5bd..."
az account set --subscription 644936a7-e58a-4ccb-a882-0005f213f5bd --tenant 1ced8c49-a03c-439c-9ff1-0c23f5128720

# Create resource group if it doesn't exist
echo "Creating resource group if it doesn't exist..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Proximity Placement Group for low latency
echo "Creating Proximity Placement Group for low latency..."
az ppg create \
    --name $PPG_NAME \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --type Standard

# Create Azure Container Registry if it doesn't exist
echo "Creating Azure Container Registry if it doesn't exist..."
az acr create \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_REGISTRY \
    --sku Premium \
    --location $LOCATION

# Create Storage Account if it doesn't exist
echo "Creating Storage Account if it doesn't exist..."
az storage account create \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS \
    --kind StorageV2

# Create AKS cluster if it doesn't exist with PPG for low latency
echo "Creating AKS cluster with Proximity Placement Group for low latency..."
az aks create \
    --resource-group $RESOURCE_GROUP \
    --name $AKS_CLUSTER \
    --node-count 3 \
    --enable-addons monitoring \
    --generate-ssh-keys \
    --location $LOCATION \
    --ppg $PPG_NAME \
    --node-vm-size Standard_D4s_v3 \
    --node-osdisk-size 100

# Get AKS credentials
echo "Getting AKS credentials..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER

# Assign ACR Pull role to AKS
echo "Assigning ACR Pull role to AKS..."
AKS_IDENTITY=$(az aks show -g $RESOURCE_GROUP -n $AKS_CLUSTER --query identityProfile.kubeletidentity.objectId -o tsv)
ACR_ID=$(az acr show -n $CONTAINER_REGISTRY -g $RESOURCE_GROUP --query id -o tsv)
az role assignment create \
    --assignee $AKS_IDENTITY \
    --role AcrPull \
    --scope $ACR_ID

# Pull Docker images from GitHub Container Registry and push to Azure Container Registry
echo "Pushing Docker images to Azure Container Registry..."
ACR_LOGIN_SERVER=$(az acr show -n $CONTAINER_REGISTRY -g $RESOURCE_GROUP --query loginServer -o tsv)

# Login to GitHub Container Registry and Azure Container Registry
echo "Logging into container registries..."
# Note: These would be dynamically populated in a real scenario
GITHUB_PAT=${GITHUB_PAT:-"your_github_pat"}
GITHUB_USER=${GITHUB_USER:-"your_github_username"}
GITHUB_REPO=${GITHUB_REPO:-"your_github_repo"}

# Login to GitHub Container Registry
echo "Logging into GitHub Container Registry..."
echo $GITHUB_PAT | docker login ghcr.io -u $GITHUB_USER --password-stdin

# Login to Azure Container Registry
echo "Logging into Azure Container Registry..."
az acr login --name $CONTAINER_REGISTRY

# Pull image from GitHub, tag for ACR, and push
echo "Pulling data-acquisition image from GitHub Container Registry..."
docker pull ghcr.io/$GITHUB_REPO/data-acquisition:latest
docker tag ghcr.io/$GITHUB_REPO/data-acquisition:latest $ACR_LOGIN_SERVER/data-acquisition:latest
docker push $ACR_LOGIN_SERVER/data-acquisition:latest

# Deploy services to AKS using kubectl
echo "Deploying services to AKS..."
# Get kubeconfig credentials for kubectl
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_CLUSTER --overwrite-existing

# Apply kubernetes manifests using kubectl
kubectl apply -f ../../infrastructure/kubernetes/base/data-acquisition.yaml

# Create Azure Front Door for global distribution with low latency
echo "Setting up Azure Front Door for global distribution with low latency..."
az network front-door create \
    --resource-group $RESOURCE_GROUP \
    --name "rt-sentiment-fd" \
    --accepted-protocols Http Https \
    --backend-address "data-acquisition.uat.example.com"

# Set up Application Insights for monitoring
echo "Setting up Application Insights for monitoring..."
az monitor app-insights component create \
    --app rt-sentiment-insights \
    --location $LOCATION \
    --resource-group $RESOURCE_GROUP \
    --application-type web

# Display success message
echo "UAT environment setup complete."
echo "Data Acquisition Service is available at: https://data-acquisition.uat.example.com"
echo "Azure Front Door endpoint: https://rt-sentiment-fd.azurefd.net"
echo "Low latency infrastructure is configured using Proximity Placement Group: $PPG_NAME"