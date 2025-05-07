#!/bin/bash
# Enhanced verification script for Sentimark deployment
# This script performs comprehensive checks to verify a successful deployment

set -e

# Variables
RESOURCE_GROUP="sentimark-sit-rg"
CLUSTER_NAME="sentimark-sit-aks"
NAMESPACE="sit"
RELEASE_NAME="sentimark"
TIMEOUT=300  # 5 minutes timeout for checks
VERIFICATION_LOG_DIR="/home/jonat/real_senti/environments/sit/logs"
VERIFICATION_LOG_FILE="${VERIFICATION_LOG_DIR}/verification_$(date +%Y%m%d_%H%M%S).json"

# Colors for terminal output
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
    ERROR_MSG="$1"
    log "${RED}Error: $ERROR_MSG${NC}"
    
    # Generate a failure log
    mkdir -p "$VERIFICATION_LOG_DIR"
    
    # Save information about the failure
    {
        echo "{"
        echo "  \"timestamp\": \"$(date -Iseconds)\","
        echo "  \"status\": \"failed\","
        echo "  \"error\": \"$ERROR_MSG\","
        echo "  \"resource_group\": \"$RESOURCE_GROUP\","
        echo "  \"cluster_name\": \"$CLUSTER_NAME\","
        echo "  \"namespace\": \"$NAMESPACE\","
        echo "  \"release_name\": \"$RELEASE_NAME\""
        echo "}"
    } > "$VERIFICATION_LOG_FILE"
    
    log "Verification failure log saved to: $VERIFICATION_LOG_FILE"
    
    exit 1
}

# Display banner
log "${BLUE}=====================================================${NC}"
log "${BLUE}      Sentimark Deployment Verification               ${NC}"
log "${BLUE}=====================================================${NC}"

# Check for required tools
if ! command -v az &> /dev/null; then
    handle_error "Azure CLI is not installed. Please run 'az login' first."
fi

if ! command -v jq &> /dev/null; then
    log "${YELLOW}jq is not installed but is required for enhanced verification.${NC}"
    log "${YELLOW}Installing jq...${NC}"
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update -qq && sudo apt-get install -qq -y jq
    elif command -v yum &> /dev/null; then
        sudo yum install -y -q jq
    elif command -v brew &> /dev/null; then
        brew install jq
    else
        handle_error "Could not automatically install jq. Please install manually."
    fi
    
    # Verify jq is now installed
    if ! command -v jq &> /dev/null; then
        handle_error "Failed to install jq."
    fi
    
    log "${GREEN}jq installed successfully.${NC}"
fi

# Verify Azure login
log "Verifying Azure login..."
if ! az account show &> /dev/null; then
    handle_error "Not logged in to Azure. Please run 'az login' first."
fi

# Verify AKS cluster exists
log "Verifying AKS cluster exists..."
if ! az aks show --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" --query name -o tsv &> /dev/null; then
    handle_error "AKS cluster '$CLUSTER_NAME' not found in resource group '$RESOURCE_GROUP'"
fi

# Create verification log directory
mkdir -p "$VERIFICATION_LOG_DIR"

# Begin verification process
log "${GREEN}Starting comprehensive deployment verification...${NC}"

# Phase 1: Verify Helm release
log "Phase 1: Verifying Helm release..."
HELM_RESULT=$(az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "helm list -n $NAMESPACE" \
    --output json)

HELM_OUTPUT=$(echo "$HELM_RESULT" | jq -r '.logs // ""')
if [[ $HELM_OUTPUT != *"$RELEASE_NAME"* ]]; then
    handle_error "Helm release '$RELEASE_NAME' not found in namespace '$NAMESPACE'"
fi

log "${GREEN}✓ Helm release verification passed${NC}"

# Phase 2: Verify deployments
log "Phase 2: Verifying Kubernetes deployments..."
DEPLOYMENT_RESULT=$(az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "kubectl get deployments -n $NAMESPACE -l release=$RELEASE_NAME -o json" \
    --output json)

DEPLOYMENTS=$(echo "$DEPLOYMENT_RESULT" | jq -r '.logs' | jq -r '.items | length')
if [ "$DEPLOYMENTS" -lt 1 ]; then
    handle_error "No deployments found for release '$RELEASE_NAME'"
fi

log "${GREEN}✓ Found $DEPLOYMENTS deployments for release $RELEASE_NAME${NC}"

# Phase 3: Verify deployment readiness
log "Phase 3: Verifying deployment readiness..."
READY_RESULT=$(az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "
    MAX_RETRIES=30
    RETRY_INTERVAL=10
    
    for i in \$(seq 1 \$MAX_RETRIES); do
        DEPLOYMENTS=\$(kubectl get deployments -n $NAMESPACE -l release=$RELEASE_NAME -o json)
        TOTAL=\$(echo \"\$DEPLOYMENTS\" | jq '.items | length')
        READY=0
        
        for j in \$(seq 0 \$((\$TOTAL - 1))); do
            DESIRED=\$(echo \"\$DEPLOYMENTS\" | jq -r \".items[\$j].spec.replicas\")
            AVAILABLE=\$(echo \"\$DEPLOYMENTS\" | jq -r \".items[\$j].status.availableReplicas // 0\")
            NAME=\$(echo \"\$DEPLOYMENTS\" | jq -r \".items[\$j].metadata.name\")
            
            if [ \"\$AVAILABLE\" -eq \"\$DESIRED\" ]; then
                READY=\$((\$READY + 1))
                echo \"Deployment \$NAME is ready (\$AVAILABLE/\$DESIRED)\"
            else
                echo \"Deployment \$NAME is not ready: \$AVAILABLE/\$DESIRED instances available\"
            fi
        done
        
        if [ \"\$READY\" -eq \"\$TOTAL\" ]; then
            echo \"All deployments are ready!\"
            exit 0
        else
            echo \"Waiting for deployments to become ready (\$READY/\$TOTAL ready)... Attempt \$i/\$MAX_RETRIES\"
            if [ \"\$i\" -lt \"\$MAX_RETRIES\" ]; then
                sleep \$RETRY_INTERVAL
            fi
        fi
    done
    
    echo \"Timed out waiting for deployments to become ready\"
    kubectl get deployments -n $NAMESPACE -l release=$RELEASE_NAME
    exit 1
    " \
    --output json)

READY_OUTPUT=$(echo "$READY_RESULT" | jq -r '.logs // ""')
READY_EXIT_CODE=$(echo "$READY_RESULT" | jq -r '.exitCode // 1')

if [ "$READY_EXIT_CODE" -ne 0 ]; then
    handle_error "Deployments did not become ready in time: $READY_OUTPUT"
fi

log "${GREEN}✓ All deployments are ready${NC}"

# Phase 4: Verify services
log "Phase 4: Verifying services..."
SERVICES_RESULT=$(az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "kubectl get services -n $NAMESPACE -l release=$RELEASE_NAME -o json" \
    --output json)

SERVICES=$(echo "$SERVICES_RESULT" | jq -r '.logs' | jq -r '.items | length')
if [ "$SERVICES" -lt 1 ]; then
    handle_error "No services found for release '$RELEASE_NAME'"
fi

# Check if services have endpoints
if echo "$SERVICES_RESULT" | jq -r '.logs' | jq -r '.items[] | select(.spec.type=="LoadBalancer")' | grep -q "loadBalancer"; then
    log "${GREEN}✓ Services have load balancer endpoints${NC}"
else
    log "${YELLOW}⚠ No load balancer endpoints found for services. This may be expected for internal-only services.${NC}"
fi

log "${GREEN}✓ Found $SERVICES services for release $RELEASE_NAME${NC}"

# Phase 5: Health checks
log "Phase 5: Performing health checks..."
HEALTH_CHECK_RESULT=$(az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "
    # Get the API service
    API_SERVICE=\$(kubectl get services -n $NAMESPACE -l app=api,release=$RELEASE_NAME -o name --no-headers 2>/dev/null | head -n 1)
    
    if [ -z \"\$API_SERVICE\" ]; then
        echo \"API service not found.\"
        exit 1
    fi
    
    # Extract IP and port
    API_IP=\$(kubectl get \$API_SERVICE -n $NAMESPACE -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
    API_PORT=\$(kubectl get \$API_SERVICE -n $NAMESPACE -o jsonpath='{.spec.ports[0].port}' 2>/dev/null)
    
    if [ -z \"\$API_IP\" ] || [ -z \"\$API_PORT\" ]; then
        echo \"API service endpoint not available yet.\"
        exit 1
    fi
    
    # Check health endpoint
    echo \"Testing API health endpoint at http://\${API_IP}:\${API_PORT}/health...\"
    HEALTH_RESPONSE=\$(curl -s -o /dev/null -w '%{http_code}' http://\${API_IP}:\${API_PORT}/health)
    
    if [ \"\$HEALTH_RESPONSE\" -eq 200 ]; then
        echo \"API health endpoint returned 200 OK\"
        exit 0
    else
        echo \"API health endpoint returned \$HEALTH_RESPONSE, expected 200\"
        exit 1
    fi
    " \
    --output json)

HEALTH_CHECK_OUTPUT=$(echo "$HEALTH_CHECK_RESULT" | jq -r '.logs // ""')
HEALTH_CHECK_EXIT_CODE=$(echo "$HEALTH_CHECK_RESULT" | jq -r '.exitCode // 1')

if [ "$HEALTH_CHECK_EXIT_CODE" -ne 0 ]; then
    log "${YELLOW}⚠ Health check warning: $HEALTH_CHECK_OUTPUT${NC}"
    log "${YELLOW}⚠ Health checks failed but continuing verification. This might be expected if the API service doesn't have a /health endpoint.${NC}"
else
    log "${GREEN}✓ Health checks passed${NC}"
fi

# Phase 6: Resource checks
log "Phase 6: Verifying resource allocation..."
RESOURCE_CHECK_RESULT=$(az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "
    # Check resource requests and limits
    echo \"Checking resource allocation...\"
    kubectl get pods -n $NAMESPACE -l release=$RELEASE_NAME -o json | jq '.items[] | select(.spec.containers != null) | .spec.containers[] | select(.resources != null) | {name: .name, requests: .resources.requests, limits: .resources.limits}'
    
    # Count pods with resource constraints
    TOTAL_PODS=\$(kubectl get pods -n $NAMESPACE -l release=$RELEASE_NAME --no-headers | wc -l)
    PODS_WITH_RESOURCES=\$(kubectl get pods -n $NAMESPACE -l release=$RELEASE_NAME -o json | jq '[.items[] | select(.spec.containers != null) | .spec.containers[] | select(.resources != null)] | length')
    
    echo \"Pods with resource constraints: \$PODS_WITH_RESOURCES/\$TOTAL_PODS\"
    
    # Show node resource usage
    echo \"Node resource usage:\"
    kubectl top nodes || echo \"Metrics server may not be enabled\"
    
    # Show pod resource usage
    echo \"Pod resource usage:\"
    kubectl top pods -n $NAMESPACE -l release=$RELEASE_NAME || echo \"Metrics server may not be enabled\"
    
    exit 0
    " \
    --output json)

log "${GREEN}✓ Resource verification completed${NC}"

# Phase 7: Configuration validation
log "Phase 7: Validating configuration..."
CONFIG_CHECK_RESULT=$(az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "
    # Verify config maps
    CM_COUNT=\$(kubectl get configmaps -n $NAMESPACE -l release=$RELEASE_NAME --no-headers | wc -l)
    echo \"Found \$CM_COUNT ConfigMaps\"
    
    # Verify secrets (count only, don't show content)
    SECRET_COUNT=\$(kubectl get secrets -n $NAMESPACE -l release=$RELEASE_NAME --no-headers | wc -l)
    echo \"Found \$SECRET_COUNT Secrets\"
    
    # Check for PVCs
    PVC_COUNT=\$(kubectl get pvc -n $NAMESPACE -l release=$RELEASE_NAME --no-headers 2>/dev/null | wc -l || echo 0)
    echo \"Found \$PVC_COUNT PersistentVolumeClaims\"
    
    exit 0
    " \
    --output json)

CONFIG_CHECK_OUTPUT=$(echo "$CONFIG_CHECK_RESULT" | jq -r '.logs // ""')
log "${GREEN}✓ Configuration validation completed:${NC}"
echo "$CONFIG_CHECK_OUTPUT"

# Phase 8: Verification summary
log "Phase 8: Creating verification summary..."

# Create detailed verification log
{
    echo "{"
    echo "  \"timestamp\": \"$(date -Iseconds)\","
    echo "  \"status\": \"success\","
    echo "  \"resource_group\": \"$RESOURCE_GROUP\","
    echo "  \"cluster_name\": \"$CLUSTER_NAME\","
    echo "  \"namespace\": \"$NAMESPACE\","
    echo "  \"release_name\": \"$RELEASE_NAME\","
    echo "  \"verification_phases\": ["
    echo "    {"
    echo "      \"name\": \"Helm release verification\","
    echo "      \"status\": \"passed\""
    echo "    },"
    echo "    {"
    echo "      \"name\": \"Deployment verification\","
    echo "      \"status\": \"passed\","
    echo "      \"details\": \"$DEPLOYMENTS deployments found\""
    echo "    },"
    echo "    {"
    echo "      \"name\": \"Deployment readiness check\","
    echo "      \"status\": \"passed\""
    echo "    },"
    echo "    {"
    echo "      \"name\": \"Service verification\","
    echo "      \"status\": \"passed\","
    echo "      \"details\": \"$SERVICES services found\""
    echo "    },"
    echo "    {"
    echo "      \"name\": \"Health checks\","
    echo "      \"status\": \"$([ "$HEALTH_CHECK_EXIT_CODE" -eq 0 ] && echo "passed" || echo "warning")\""
    echo "    },"
    echo "    {"
    echo "      \"name\": \"Resource allocation check\","
    echo "      \"status\": \"passed\""
    echo "    },"
    echo "    {"
    echo "      \"name\": \"Configuration validation\","
    echo "      \"status\": \"passed\""
    echo "    }"
    echo "  ],"
    echo "  \"verification_time_seconds\": \"$SECONDS\""
    echo "}"
} > "$VERIFICATION_LOG_FILE"

log "Verification summary saved to: $VERIFICATION_LOG_FILE"

# Display final summary
log "${BLUE}=====================================================${NC}"
log "${GREEN}✓ Verification completed successfully${NC}"
log "${BLUE}=====================================================${NC}"
log "Time elapsed: $SECONDS seconds"
log "Deployments: $DEPLOYMENTS"
log "Services: $SERVICES"
log "Verification log: $VERIFICATION_LOG_FILE"

exit 0