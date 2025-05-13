#!/bin/bash
# Comprehensive Sentimark services deployment script - Version 2
# This script fixes deployment issues and ensures all services are properly deployed

set -e

# Variables
RESOURCE_GROUP="sentimark-sit-rg"
CLUSTER_NAME="sentimark-sit-aks"
NAMESPACE="sit"
RELEASE_NAME="sentimark"
SCRIPT_DIR="$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function for logging with timestamps
log() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo -e "${timestamp} - $1"
}

# Function to handle errors
handle_error() {
    log "${RED}ERROR: $1${NC}"
    exit 1
}

# Display banner
log "${BLUE}=====================================================${NC}"
log "${BLUE}     Sentimark Services Deployment - Fixed Script V2    ${NC}"
log "${BLUE}=====================================================${NC}"

# Check if we're logged into Azure
log "Checking Azure login status..."
if ! az account show --query name -o tsv &>/dev/null; then
    handle_error "Not logged in to Azure. Please run 'az login' first."
fi

# Check if AKS cluster exists
log "Verifying AKS cluster exists..."
if ! az aks show --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" --query name -o tsv &>/dev/null; then
    handle_error "AKS cluster '$CLUSTER_NAME' not found in resource group '$RESOURCE_GROUP'"
fi

# Check for required node pools
log "Checking for required node pools..."
nodepools=$(az aks nodepool list --resource-group "$RESOURCE_GROUP" --cluster-name "$CLUSTER_NAME" -o json | jq -r '.[].name')

if ! echo "$nodepools" | grep -q "dataspots"; then
    log "${YELLOW}Warning: dataspots node pool not found in cluster.${NC}"
    log "The Helm chart is configured to use spot instances for data-intensive workloads."
    log "This may affect the deployment."
else
    log "${GREEN}Found required dataspots node pool.${NC}"
fi

# Create values override for deployment
log "Creating values override for deployment..."
# Create a temporary values override file
VALUES_OVERRIDE="$SCRIPT_DIR/values.spot-override.yaml"
cat <<EOF > "$VALUES_OVERRIDE"
# Override to disable spot instance requirements
dataAcquisition:
  useSpotInstances: false
  nodeSelector: {}
  tolerations: []

dataMigration:
  useSpotInstances: false
  nodeSelector: {}
  tolerations: []

analyzer:
  useSpotInstances: false
  nodeSelector: {}
  tolerations: []
EOF
log "${GREEN}Created values override file: $VALUES_OVERRIDE${NC}"
log "This will be used in the deployment to disable spot instance requirements."

# Fix line endings in helm_deploy_fixed.sh
log "Ensuring correct line endings in deployment script..."
HELM_DEPLOY_SCRIPT="$SCRIPT_DIR/helm_deploy_fixed.sh"
tr -d '\r' < "$HELM_DEPLOY_SCRIPT" > "${HELM_DEPLOY_SCRIPT}.tmp"
chmod +x "${HELM_DEPLOY_SCRIPT}.tmp"
mv "${HELM_DEPLOY_SCRIPT}.tmp" "$HELM_DEPLOY_SCRIPT"
log "${GREEN}Processed line endings in $HELM_DEPLOY_SCRIPT${NC}"

# Deploy services using Helm
log "${BLUE}Deploying Sentimark services...${NC}"
log "This may take several minutes to complete."

# Run the Helm deployment with non-interactive mode and values override
log "Running fixed Helm deployment script with values override..."
bash "$HELM_DEPLOY_SCRIPT" \
    --release-name "$RELEASE_NAME" \
    --namespace "$NAMESPACE" \
    --chart-dir "/home/jonat/real_senti/infrastructure/helm/sentimark-services" \
    --non-interactive \
    --values-file "$VALUES_OVERRIDE"

DEPLOY_EXIT=$?
if [ $DEPLOY_EXIT -ne 0 ]; then
    handle_error "Deployment failed with exit code $DEPLOY_EXIT"
fi

# Verify deployment
log "${GREEN}Deployment completed successfully!${NC}"

# Create a deployment log
LOG_DIR="$SCRIPT_DIR/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/deployment_$(date +%Y%m%d_%H%M%S).json"

# Create detailed JSON log
cat > "$LOG_FILE" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "resource_group": "$RESOURCE_GROUP",
  "cluster_name": "$CLUSTER_NAME",
  "namespace": "$NAMESPACE",
  "release_name": "$RELEASE_NAME",
  "status": "completed",
  "spot_override_used": true,
  "script_version": "v2"
}
EOF

log "Deployment log saved to: $LOG_FILE"

# Summary
log "${GREEN}Deployment with spot instance override completed successfully!${NC}"
log "${BLUE}======== Next Steps =========${NC}"
log "1. Verify your deployment using Azure Portal or CLI."
log "2. Check service endpoints and logs."
log "3. For more information, see documentation in the docs directory."
log "${BLUE}=====================================================${NC}"
