#!/bin/bash
# Quick verification script for Sentimark service deployment

set -e

# Variables
RESOURCE_GROUP="sentimark-sit-rg"
CLUSTER_NAME="sentimark-sit-aks"
NAMESPACE="sit"
RELEASE_NAME="sentimark"

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
    
    log "Checking: $description..."
    
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
    
    # Extract logs from JSON response
    local logs=$(echo "$result" | jq -r '.logs // ""' 2>/dev/null)
    echo "$logs"
    return 0
}

# Display banner
log "${BLUE}=====================================================${NC}"
log "${BLUE}     Sentimark Deployment Status Check                ${NC}"
log "${BLUE}=====================================================${NC}"

# Check if we're logged into Azure
log "Checking Azure login status..."
if ! az account show --query name -o tsv &>/dev/null; then
    handle_error "Not logged in to Azure. Please run 'az login' first."
fi

# Check Helm release
log "${BLUE}Helm Release Status:${NC}"
run_aks_command "helm list -n $NAMESPACE" "Helm releases"

# Check pod status
log "${BLUE}Pod Status:${NC}"
run_aks_command "kubectl get pods -n $NAMESPACE" "Pods"
run_aks_command "
    # Count ready pods
    TOTAL_PODS=\$(kubectl get pods -n $NAMESPACE --no-headers | wc -l)
    READY_PODS=\$(kubectl get pods -n $NAMESPACE --no-headers | grep '1/1\|2/2\|3/3\|4/4' | wc -l)
    echo \"Ready pods: \$READY_PODS/\$TOTAL_PODS\"
    
    # List non-ready pods
    NOT_READY=\$(kubectl get pods -n $NAMESPACE --no-headers | grep -v '1/1\|2/2\|3/3\|4/4' || echo 'All pods ready')
    if [ \"\$NOT_READY\" != 'All pods ready' ]; then
        echo \"Non-ready pods:\"
        echo \"\$NOT_READY\"
    fi
" "Ready status"

# Check service status
log "${BLUE}Service Status:${NC}"
run_aks_command "kubectl get services -n $NAMESPACE" "Services"

# Check deployment status
log "${BLUE}Deployment Status:${NC}"
run_aks_command "kubectl get deployments -n $NAMESPACE" "Deployments"

# Check events for any issues
log "${BLUE}Recent Events:${NC}"
run_aks_command "kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -10" "Recent events"

# Display final status
log "${GREEN}Status check completed.${NC}"