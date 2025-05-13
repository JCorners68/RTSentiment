#!/bin/bash
# Comprehensive Sentimark services deployment script
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

# Function to run AKS commands
run_aks_command() {
    local command="$1"
    local description="$2"
    local silent="$3"
    
    if [ -z "$silent" ] || [ "$silent" != "silent" ]; then
        log "Running: $description..."
    fi
    
    local result=$(az aks command invoke \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CLUSTER_NAME" \
        --command "$command" \
        --output json 2>&1)
    
    # Check for errors in az command itself
    if [ $? -ne 0 ]; then
        log "${RED}Command failed: $description${NC}"
        echo "$result"
        return 1
    fi
    
    # Extract exit code from JSON response
    local exit_code=$(echo "$result" | jq -r '.exitCode // 1' 2>/dev/null)
    if [[ ! "$exit_code" =~ ^[0-9]+$ ]]; then
        exit_code=1
    fi
    
    # Extract logs from JSON response
    local logs=$(echo "$result" | jq -r '.logs // ""' 2>/dev/null)
    
    if [ "$exit_code" -ne 0 ]; then
        if [ -z "$silent" ] || [ "$silent" != "silent" ]; then
            log "${RED}Command failed with exit code $exit_code: $description${NC}"
            echo "$logs"
        fi
        return 1
    else
        if [ -z "$silent" ] || [ "$silent" != "silent" ]; then
            echo "$logs"
        fi
        return 0
    fi
}

# Display banner
log "${BLUE}=====================================================${NC}"
log "${BLUE}     Sentimark Services Deployment - Fixed Script     ${NC}"
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

# Step 1: Check for existing deployments
log "Checking for existing Helm deployments..."
if run_aks_command "helm list -n $NAMESPACE" "Listing Helm releases" "silent" &>/dev/null; then
    exists=$(run_aks_command "helm list -n $NAMESPACE -q | grep -w $RELEASE_NAME || echo ''" "Checking release existence" "silent")
    
    if [ -n "$exists" ]; then
        log "${YELLOW}Found existing release: $RELEASE_NAME${NC}"
        log "Getting release details..."
        run_aks_command "helm get all $RELEASE_NAME -n $NAMESPACE" "Release details"
        
        log "Checking chart version..."
        chart_name=$(run_aks_command "helm list -n $NAMESPACE -o json | jq -r '.[] | select(.name==\"$RELEASE_NAME\") | .chart'" "Getting chart name" "silent")
        
        if [[ "$chart_name" == *"test"* ]]; then
            log "${YELLOW}Found test chart deployment ($chart_name). This will be uninstalled.${NC}"
            read -p "Do you want to uninstall the test deployment? (y/n): " uninstall_test
            if [[ "$uninstall_test" =~ ^[Yy]$ ]]; then
                log "Uninstalling test deployment..."
                run_aks_command "helm uninstall $RELEASE_NAME -n $NAMESPACE" "Uninstalling test deployment" || handle_error "Failed to uninstall test deployment"
            else
                log "${YELLOW}Keeping existing test deployment. Will attempt to upgrade to actual services.${NC}"
            fi
        else
            log "${GREEN}Found actual services deployment ($chart_name).${NC}"
            read -p "Do you want to redeploy/upgrade the services? (y/n): " upgrade_services
            if [[ ! "$upgrade_services" =~ ^[Yy]$ ]]; then
                log "Exiting without changes."
                exit 0
            fi
        fi
    else
        log "${GREEN}No existing release found. Will perform fresh installation.${NC}"
    fi
else
    log "${GREEN}No existing Helm deployments found in namespace $NAMESPACE.${NC}"
fi

# Step 2: Check for necessary node pools
log "Checking for required node pools..."
nodepools=$(az aks nodepool list --resource-group "$RESOURCE_GROUP" --cluster-name "$CLUSTER_NAME" -o json | jq -r '.[].name')

if ! echo "$nodepools" | grep -q "dataspots"; then
    log "${YELLOW}Warning: dataspots node pool not found in cluster.${NC}"
    log "The Helm chart is configured to use spot instances for data-intensive workloads."
    read -p "Do you want to create the missing node pool? (y/n): " create_nodepool
    
    if [[ "$create_nodepool" =~ ^[Yy]$ ]]; then
        log "Creating dataspots node pool. This will take a few minutes..."
        az aks nodepool add \
            --resource-group "$RESOURCE_GROUP" \
            --cluster-name "$CLUSTER_NAME" \
            --name dataspots \
            --node-count 1 \
            --node-vm-size Standard_D4s_v3 \
            --priority Spot \
            --eviction-policy Delete \
            --spot-max-price -1 \
            --labels workload=data \
            --node-taints "kubernetes.azure.com/scalesetpriority=spot:NoSchedule" \
            --zones 1 2 3 || handle_error "Failed to create dataspots node pool"
        log "${GREEN}Successfully created dataspots node pool.${NC}"
    else
        log "${YELLOW}Continuing without spot instance node pool.${NC}"
        log "Note: Some services may not deploy correctly if they require spot instances."
        
        read -p "Do you want to disable spot instance requirements in values.yaml? (y/n): " disable_spots
        if [[ "$disable_spots" =~ ^[Yy]$ ]]; then
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
        fi
    fi
else
    log "${GREEN}Found required dataspots node pool.${NC}"
fi

# Step 3: Prepare for deployment
log "Preparing for service deployment..."

# Determine if we need to use values override
VALUES_ARGS=""
if [ -f "$SCRIPT_DIR/values.spot-override.yaml" ]; then
    VALUES_ARGS="--values $SCRIPT_DIR/values.spot-override.yaml"
    log "Using values override to disable spot instance requirements."
fi

# Determine if using install or upgrade
action="install"
if run_aks_command "helm list -n $NAMESPACE -q | grep -w $RELEASE_NAME || echo ''" "Checking release existence" "silent" | grep -q "$RELEASE_NAME"; then
    action="upgrade"
    log "Will perform upgrade of existing deployment."
else
    log "Will perform fresh installation."
fi

# Step 4: Deploy the services
log "${BLUE}Deploying Sentimark services...${NC}"
log "This may take several minutes to complete."

DEPLOY_COMMAND="helm $action $RELEASE_NAME /tmp/chart-package.tgz \
    --namespace $NAMESPACE \
    --create-namespace \
    --wait --timeout 10m \
    $VALUES_ARGS"

# Use the fixed Helm deployment script for the actual deployment
HELM_DEPLOY_SCRIPT="$SCRIPT_DIR/helm_deploy_fixed.sh"
if [ ! -f "$HELM_DEPLOY_SCRIPT" ]; then
    handle_error "Fixed deployment script not found: $HELM_DEPLOY_SCRIPT"
fi

log "Running fixed Helm deployment script..."
# Ensure the script is using LF line endings
if command -v file &> /dev/null && file "$HELM_DEPLOY_SCRIPT" | grep -q "CRLF"; then
    log "${YELLOW}Warning: Helm deploy script has CRLF line endings. Converting to LF...${NC}"
    tr -d '\r' < "$HELM_DEPLOY_SCRIPT" > "${HELM_DEPLOY_SCRIPT}.tmp"
    chmod +x "${HELM_DEPLOY_SCRIPT}.tmp"
    mv "${HELM_DEPLOY_SCRIPT}.tmp" "$HELM_DEPLOY_SCRIPT"
    log "${GREEN}Converted line endings from CRLF to LF${NC}"
fi

# Run the script using bash explicitly with the proper arguments
# Use yes to automatically answer 'y' to any prompts
yes y | bash "$HELM_DEPLOY_SCRIPT" \
    --release-name "$RELEASE_NAME" \
    --namespace "$NAMESPACE" \
    --chart-dir "/home/jonat/real_senti/infrastructure/helm/sentimark-services" || handle_error "Deployment failed"

# Step 5: Verify deployment
log "Verifying deployment..."

# Wait for all pods to be ready
log "Waiting for all pods to be ready (timeout: 5 minutes)..."
run_aks_command "
    kubectl wait --for=condition=ready pods --all -n $NAMESPACE --timeout=300s
" "Waiting for pods" || log "${YELLOW}Warning: Not all pods are ready. Continuing with verification...${NC}"

log "Checking deployed pods..."
run_aks_command "kubectl get pods -n $NAMESPACE -o wide" "Pod status"

log "Checking deployed services..."
run_aks_command "kubectl get services -n $NAMESPACE" "Service status"

log "Checking deployments..."
run_aks_command "kubectl get deployments -n $NAMESPACE" "Deployment status"

# Print deployment summary
log "Helm release status:"
run_aks_command "helm list -n $NAMESPACE" "Helm status"

# Step 6: Save deployment log
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
  "spot_node_pool_created": $(if [[ "$create_nodepool" =~ ^[Yy]$ ]]; then echo "true"; else echo "false"; fi),
  "spot_override_used": $(if [ -f "$SCRIPT_DIR/values.spot-override.yaml" ]; then echo "true"; else echo "false"; fi)
}
EOF

log "Deployment log saved to: $LOG_FILE"

# Step 7: Display summary and next steps
log "${GREEN}Deployment completed!${NC}"
log "${BLUE}======== Next Steps ========${NC}"
log "1. Verify all services are running correctly:"
log "   az aks command invoke -g $RESOURCE_GROUP -n $CLUSTER_NAME --command \"kubectl get pods -n $NAMESPACE\""
log ""
log "2. Check service endpoints:"
log "   az aks command invoke -g $RESOURCE_GROUP -n $CLUSTER_NAME --command \"kubectl get services -n $NAMESPACE\""
log ""
log "3. View service logs:"
log "   az aks command invoke -g $RESOURCE_GROUP -n $CLUSTER_NAME --command \"kubectl logs deployment/<deployment-name> -n $NAMESPACE\""
log ""
log "4. For more information, see:"
log "   /home/jonat/real_senti/docs/deployment/helm_with_private_aks.md"
log ""
log "${BLUE}=====================================================${NC}"