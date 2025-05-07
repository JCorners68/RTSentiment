#!/bin/bash
# Deploy Sentimark services using Helm through az aks command invoke
# This script uses full Helm capabilities while maintaining compatibility with private AKS clusters

set -e

# Variables
RESOURCE_GROUP="sentimark-sit-rg"
CLUSTER_NAME="sentimark-sit-aks"
RELEASE_NAME="sentimark"
NAMESPACE="sit"
CHART_DIR="/home/jonat/real_senti/infrastructure/helm/sentimark-services"
START_TIME=$(date +%s)

# Chart Repository Configuration (uncomment and configure when repository is available)
# REPO_NAME="sentimark"
# REPO_URL="https://example.azurecr.io/helm/v1/repo"
# CHART_NAME="sentimark-services"
# CHART_VERSION="0.1.0"

# Use local chart (if repository not configured)
USE_LOCAL_CHART=true

# Use simplified test chart instead of actual chart (useful for testing)
USE_TEST_CHART=false

# Maximum file size for transfer (in MB)
MAX_TRANSFER_SIZE_MB=20

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --test-chart)
            USE_TEST_CHART=true
            shift
            ;;
        --chart-dir)
            CHART_DIR="$2"
            shift 2
            ;;
        --release-name)
            RELEASE_NAME="$2"
            shift 2
            ;;
        --namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        *)
            # Unknown option
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Function for logging with timestamps
log() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo -e "${timestamp} - $1"
}

# Function to handle errors with pre-emptive cleanup
handle_error() {
    ERROR_MSG="$1"
    log "${RED}Error: $ERROR_MSG${NC}"
    
    # Perform emergency cleanup for common error cases
    if [[ "$ERROR_MSG" == *"Helm deployment failed"* ]]; then
        # Attempt to clean up any failed Helm releases
        log "Attempting to clean up failed Helm releases..."
        az aks command invoke \
            --resource-group "$RESOURCE_GROUP" \
            --name "$CLUSTER_NAME" \
            --command "helm list -n $NAMESPACE --failed -q 2>/dev/null | xargs -r helm uninstall -n $NAMESPACE 2>/dev/null || true" \
            --output none || true
    fi
    
    # Generate a failure log
    FAILURE_LOG_DIR="/home/jonat/real_senti/environments/sit/logs"
    mkdir -p "$FAILURE_LOG_DIR"
    FAILURE_LOG_FILE="$FAILURE_LOG_DIR/failure_$(date +%Y%m%d_%H%M%S).json"
    
    # Save information about the failure
    {
        echo "{"
        echo "  \"timestamp\": \"$(date -Iseconds)\","
        echo "  \"error\": \"$ERROR_MSG\","
        echo "  \"resource_group\": \"$RESOURCE_GROUP\","
        echo "  \"cluster_name\": \"$CLUSTER_NAME\","
        echo "  \"namespace\": \"$NAMESPACE\","
        echo "  \"failed_command\": \"Last executed command failed\""
        echo "}"
    } > "$FAILURE_LOG_FILE"
    
    log "Failure log saved to: $FAILURE_LOG_FILE"
    
    exit 1
}

# Display banner
log "${BLUE}=====================================================${NC}"
log "${BLUE}     Deploy to Private AKS Using Helm via az CLI      ${NC}"
log "${BLUE}=====================================================${NC}"

# Check for required tools
if ! command -v az &> /dev/null; then
    handle_error "Azure CLI is not installed"
fi

# Check if jq is installed (REQUIRED for JSON parsing)
if ! command -v jq &> /dev/null; then
    log "${YELLOW}jq is not installed but is REQUIRED for this script.${NC}"
    log "${YELLOW}Attempting to install jq automatically...${NC}"
    
    JQ_INSTALLED=false
    
    # Try to install jq automatically
    if command -v apt-get &> /dev/null; then
        # Debian/Ubuntu
        log "Installing jq using apt-get..."
        if sudo apt-get update -qq && sudo apt-get install -qq -y jq; then
            JQ_INSTALLED=true
        fi
    elif command -v yum &> /dev/null; then
        # RHEL/CentOS/Fedora
        log "Installing jq using yum..."
        if sudo yum install -y -q jq; then
            JQ_INSTALLED=true
        fi
    elif command -v brew &> /dev/null; then
        # macOS with Homebrew
        log "Installing jq using brew..."
        if brew install jq; then
            JQ_INSTALLED=true
        fi
    fi
    
    # Verify jq is now installed
    if command -v jq &> /dev/null; then
        log "${GREEN}jq was successfully installed.${NC}"
        JQ_INSTALLED=true
    fi
    
    # Handle case where installation failed
    if [ "$JQ_INSTALLED" = false ]; then
        log "${RED}Failed to install jq automatically.${NC}"
        log "${RED}Please install jq manually and try again:${NC}"
        log "  For Debian/Ubuntu: sudo apt update && sudo apt install -y jq"
        log "  For RHEL/CentOS: sudo yum install -y jq"
        log "  For macOS: brew install jq"
        handle_error "jq is required for this script"
    fi
fi

# Extra verification that jq works correctly
if ! echo '{"test":123}' | jq -r '.test' &>/dev/null; then
    log "${RED}jq is installed but not functioning correctly.${NC}"
    handle_error "jq is not functioning correctly"
fi

log "${GREEN}jq is installed and functioning correctly.${NC}"

# Check for Helm CLI (critical for proper chart packaging)
if ! command -v helm &> /dev/null; then
    log "${YELLOW}Helm CLI is not installed on this machine.${NC}"
    log "${YELLOW}This is highly recommended for proper chart packaging!${NC}"
    log "Attempting to install Helm automatically..."
    
    HELM_INSTALLED=false
    
    # Try to install Helm automatically
    if command -v curl &> /dev/null; then
        log "Downloading and installing Helm..."
        curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 -o get_helm.sh
        chmod +x get_helm.sh
        if ./get_helm.sh; then
            HELM_INSTALLED=true
            rm -f get_helm.sh
        else
            rm -f get_helm.sh
        fi
    fi
    
    # Verify Helm is now installed
    if command -v helm &> /dev/null; then
        log "${GREEN}Helm was successfully installed.${NC}"
        HELM_INSTALLED=true
    fi
    
    # Warning if installation failed
    if [ "$HELM_INSTALLED" = false ]; then
        log "${YELLOW}Could not install Helm automatically.${NC}"
        log "${YELLOW}Will use fallback method with tar for packaging.${NC}"
        log "${YELLOW}For optimal results, please install Helm manually:${NC}"
        log "  curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash"
    fi
fi

# Helper function to safely extract exit code from JSON
extract_exit_code() {
    local json_data="$1"
    local exit_code
    
    # Try to extract using jq
    exit_code=$(echo "$json_data" | jq -r '.exitCode // 1' 2>/dev/null)
    
    # Verify the result is an integer
    if [[ "$exit_code" =~ ^[0-9]+$ ]]; then
        echo "$exit_code"
    else
        # Fallback to a default error code if we couldn't extract a valid integer
        echo "1"
    fi
}

# Helper function to safely extract logs from JSON
extract_logs() {
    local json_data="$1"
    local logs
    
    # Try to extract using jq
    logs=$(echo "$json_data" | jq -r '.logs // ""' 2>/dev/null)
    
    # Return the logs or a default message
    if [ -n "$logs" ]; then
        echo "$logs"
    else
        echo "No logs available or could not extract logs from response."
    fi
}

# Check if logged in to Azure
log "Checking Azure login status..."
az account show &> /dev/null || handle_error "Not logged in to Azure. Please run 'az login' first."

# Verify AKS cluster exists
log "Verifying AKS cluster exists..."
az aks show --resource-group "$RESOURCE_GROUP" --name "$CLUSTER_NAME" --query name -o tsv &> /dev/null || 
    handle_error "AKS cluster '$CLUSTER_NAME' not found in resource group '$RESOURCE_GROUP'"

# Check if we have a local chart if USE_LOCAL_CHART is true
if [ "$USE_LOCAL_CHART" = true ] && [ ! -d "$CHART_DIR" ]; then
    handle_error "Helm chart not found at $CHART_DIR"
fi

# Check if values.yaml exists
VALUES_FILE="$CHART_DIR/values.yaml"
if [ ! -f "$VALUES_FILE" ]; then
    handle_error "values.yaml not found at $VALUES_FILE"
fi

# Lint the chart if Helm is available
if command -v helm &> /dev/null; then
    log "Linting the Helm chart..."
    if ! helm lint "$CHART_DIR"; then
        log "${YELLOW}Warning: The chart has linting issues but we'll continue.${NC}"
    else
        log "${GREEN}Chart linting successful!${NC}"
    fi
fi

# Create namespace if it doesn't exist (idempotent operation)
log "Creating namespace $NAMESPACE if it doesn't exist..."
az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -" || 
    handle_error "Failed to create namespace"

# Check for spot instance node pools
log "Verifying AKS cluster has spot instance node pools..."
NODE_POOLS_OUTPUT=$(az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "kubectl get nodes --show-labels | grep -E 'dataspots|lowspots'" \
    --output json)

if [[ $(echo "$NODE_POOLS_OUTPUT" | jq -r '.logs // ""' | grep -c "dataspots") -eq 0 ]]; then
    log "${YELLOW}Warning: dataspots node pool not found in cluster.${NC}"
    log "The Helm chart is configured to use spot instances."
    log "You may need to update values.yaml or create the required node pools."
    
    # Ask for confirmation
    read -p "Continue with deployment anyway? (y/n): " CONTINUE
    if [[ ! $CONTINUE =~ ^[Yy]$ ]]; then
        log "Deployment aborted."
        exit 1
    fi
else
    log "${GREEN}Found spot instance node pools.${NC}"
fi

# Check if Helm is available in the AKS command environment
log "Checking if Helm is available in the AKS command environment..."
HELM_CHECK=$(az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "command -v helm || echo 'helm not found'" \
    --output json)

if [[ $(echo "$HELM_CHECK" | jq -r '.logs // ""' | grep -c "helm not found") -gt 0 ]]; then
    log "${YELLOW}Warning: Helm not found in AKS command environment.${NC}"
    log "Will use kubectl with helm docker image for deployment."
    USE_HELM_POD=true
else
    log "${GREEN}Helm is available in the AKS command environment.${NC}"
    USE_HELM_POD=false
fi

# Create a temporary directory for chart packaging
TEMP_DIR=$(mktemp -d)
log "Created temporary directory: $TEMP_DIR"

# Enhanced cleanup function with pre-emptive cleanup
cleanup() {
    EXIT_CODE=$?
    log "Cleaning up temporary files and resources..."
    
    # Always clean up local temporary files
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
        log "Removed local temporary directory: $TEMP_DIR"
    fi
    
    # Clean up remote temporary files with best-effort approach
    az aks command invoke \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CLUSTER_NAME" \
        --command "rm -rf /tmp/test-chart /tmp/helm-* /tmp/chart-* 2>/dev/null || true" \
        --output none || true
    
    # Clean up any helm-deploy-* pods that might have been created
    az aks command invoke \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CLUSTER_NAME" \
        --command "kubectl get pods -n default -l app=helm-deploy --no-headers 2>/dev/null | awk '{print \$1}' | xargs -r kubectl delete pod -n default --grace-period=0 --force 2>/dev/null || true" \
        --output none || true
    
    log "Cleanup completed"
    
    # Preserve the original exit code
    return $EXIT_CODE
}

# Register cleanup function for multiple signals
trap cleanup EXIT INT TERM HUP

# Define test chart templates for --test-chart mode
create_test_chart() {
    local chart_dir="$1"
    
    log "Creating test chart in $chart_dir..."
    mkdir -p "$chart_dir/templates"
    
    # Create Chart.yaml
    cat > "$chart_dir/Chart.yaml" << EOF
apiVersion: v2
name: sentimark-test
description: A test chart for Sentimark
type: application
version: 0.1.0
appVersion: 1.0.0
EOF
    
    # Create deployment.yaml
    cat > "$chart_dir/templates/deployment.yaml" << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-deployment
  labels:
    app: sentimark-test
spec:
  replicas: 1
  selector:
    matchLabels:
      app: sentimark-test
  template:
    metadata:
      labels:
        app: sentimark-test
    spec:
      containers:
      - name: nginx
        image: nginx:stable
        ports:
        - containerPort: 80
EOF
    
    # Create service.yaml
    cat > "$chart_dir/templates/service.yaml" << EOF
apiVersion: v1
kind: Service
metadata:
  name: test-service
  labels:
    app: sentimark-test
spec:
  type: ClusterIP
  ports:
  - port: 80
    targetPort: 80
    protocol: TCP
    name: http
  selector:
    app: sentimark-test
EOF
    
    # Create minimal values.yaml
    cat > "$chart_dir/values.yaml" << EOF
# Default values for test chart
replicaCount: 1
image:
  repository: nginx
  tag: stable
EOF
}

# Check if using local chart
if [ "$USE_LOCAL_CHART" = true ]; then
    # Verify chart directory exists
    if [ ! -d "$CHART_DIR" ]; then
        handle_error "Chart directory not found: $CHART_DIR"
    fi
    
    # Check if values.yaml exists
    VALUES_FILE="$CHART_DIR/values.yaml"
    if [ ! -f "$VALUES_FILE" ]; then
        handle_error "values.yaml not found at $VALUES_FILE"
    fi
    
    # Check if this is a test chart deployment
    if [ "$USE_TEST_CHART" = true ]; then
        # Create a test chart instead of using the real chart
        TEST_CHART_DIR="$TEMP_DIR/test-chart"
        create_test_chart "$TEST_CHART_DIR"
        
        # Override chart directory for packaging
        PACKAGE_DIR="$TEST_CHART_DIR"
        log "Using test chart for deployment"
    else
        # Use the real chart for deployment
        PACKAGE_DIR="$CHART_DIR"
        log "Using actual chart from $CHART_DIR for deployment"
    fi
    
    # Package the chart with better error handling and dependency resolution
    log "Packaging Helm chart..."
    if command -v helm &> /dev/null; then
        # Use helm for packaging - this is the preferred method
        log "${GREEN}Using Helm CLI for chart packaging (recommended)${NC}"
        
        # First check for dependencies
        if [ -f "$PACKAGE_DIR/Chart.yaml" ] && grep -q "dependencies:" "$PACKAGE_DIR/Chart.yaml"; then
            log "Chart has dependencies, running helm dependency build..."
            (cd "$PACKAGE_DIR" && helm dependency build) || 
                handle_error "Failed to build chart dependencies"
        fi
        
        # Then package the chart
        helm package "$PACKAGE_DIR" --destination "$TEMP_DIR" || 
            handle_error "Failed to package Helm chart with helm command"
        
        CHART_PACKAGE=$(find "$TEMP_DIR" -name "*.tgz" | head -n 1)
        if [ -z "$CHART_PACKAGE" ]; then
            handle_error "Helm package command did not produce a .tgz file"
        fi
        
        CHART_FILENAME=$(basename "$CHART_PACKAGE")
        log "Created chart package with helm: $CHART_FILENAME"
    else
        # Fallback to tar if helm is not available
        log "${YELLOW}Warning: helm not found locally. Using tar for packaging.${NC}"
        log "${YELLOW}This may not work correctly for complex charts.${NC}"
        
        CHART_FILENAME="chart.tgz"
        CHART_PACKAGE="$TEMP_DIR/$CHART_FILENAME"
        
        # For actual chart, use proper directory structure
        if [ "$USE_TEST_CHART" = true ]; then
            # Package the test chart
            tar -czf "$CHART_PACKAGE" -C "$TEMP_DIR" "test-chart" || 
                handle_error "Failed to create test chart archive"
        else
            # Package the real chart with correct structure
            tar -czf "$CHART_PACKAGE" -C "$(dirname "$CHART_DIR")" "$(basename "$CHART_DIR")" || 
                handle_error "Failed to create chart archive"
        fi
        
        log "Created chart package with tar: $CHART_FILENAME"
    fi
    
    # Check the structure of the packaged chart
    log "Examining packaged chart..."
    if command -v tar &> /dev/null; then
        tar -tvf "$CHART_PACKAGE" | head -10
    fi
    
    # Check if the package size is too large
    PACKAGE_SIZE_KB=$(du -k "$CHART_PACKAGE" | cut -f1)
    PACKAGE_SIZE_MB=$(echo "scale=2; $PACKAGE_SIZE_KB/1024" | bc)
    MAX_SIZE_KB=$((MAX_TRANSFER_SIZE_MB * 1024))
    
    log "Chart package size: ${PACKAGE_SIZE_MB}MB (maximum allowed: ${MAX_TRANSFER_SIZE_MB}MB)"
    
    if [ "$PACKAGE_SIZE_KB" -gt "$MAX_SIZE_KB" ]; then
        log "${RED}Chart package size exceeds the maximum allowed size for transfer.${NC}"
        log "${RED}Consider reducing the chart size or transferring it to AKS through another method.${NC}"
        handle_error "Chart package too large for transfer: ${PACKAGE_SIZE_MB}MB (max: ${MAX_TRANSFER_SIZE_MB}MB)"
    fi
    
    # Read values.yaml content and properly handle line endings
    log "Processing values.yaml for transfer..."
    # Convert CRLF to LF and then base64 encode for safe transfer
    VALUES_B64=$(tr -d '\r' < "$VALUES_FILE" | base64 -w 0)
    log "Values.yaml processed and encoded for transfer."
    
    # Base64 encode the chart package for transfer
    log "Encoding chart package for transfer..."
    CHART_B64=$(base64 -w 0 "$CHART_PACKAGE")
fi

log "Deploying Helm chart using az aks command invoke..."
log "This may take a few minutes..."

# Check if Helm is available in the AKS command environment
log "Checking if Helm is available in the AKS command environment..."
HELM_CHECK=$(az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "command -v helm || echo 'helm not found'" \
    --output json)

# Parse result using helper function
HELM_CHECK_OUTPUT=$(extract_logs "$HELM_CHECK")

if [[ "$HELM_CHECK_OUTPUT" == *"helm not found"* ]]; then
    log "${YELLOW}Helm not found in AKS command environment.${NC}"
    log "Will use a temporary pod with Helm for deployment."
    USE_HELM_POD=true
else
    log "${GREEN}Helm is available in the AKS command environment.${NC}"
    USE_HELM_POD=false
fi

# Define any additional set arguments for Helm (empty by default)
HELM_SET_ARGS=""

# Create deployment command based on strategy (pod or direct)
if [ "$USE_HELM_POD" = true ]; then
    # Use temporary pod with Helm installed
    log "Creating deployment command using temporary Helm pod..."
    
    # Generate a unique pod name with timestamp
    HELM_POD_NAME="helm-deploy-$(date +%s)"
    
    # Create pod definition with app=helm-deploy label for cleanup
    POD_YAML="apiVersion: v1
kind: Pod
metadata:
  name: $HELM_POD_NAME
  namespace: default
  labels:
    app: helm-deploy
spec:
  containers:
  - name: helm
    image: alpine/helm:latest
    command: ['sleep', '600']
  restartPolicy: Never"
    
    # Create a more robust and verbose pod-based deployment command
    DEPLOY_COMMAND=$(cat <<EOF
#!/bin/bash
set -e

echo 'DEBUG: Starting pod-based Helm deployment...'
echo 'Creating temporary Helm pod...'
cat << 'EOT_POD_YAML' | kubectl apply -f -
$POD_YAML
EOT_POD_YAML

echo 'Waiting for Helm pod to be ready...'
kubectl wait --for=condition=Ready pod/$HELM_POD_NAME -n default --timeout=60s
if [ \$? -ne 0 ]; then
  echo "ERROR: Helm pod failed to reach ready state!"
  kubectl describe pod/$HELM_POD_NAME -n default
  exit 1
fi

echo 'DEBUG: Pod ready. Creating temporary directory in pod...'
kubectl exec $HELM_POD_NAME -n default -- mkdir -p /tmp/chart
kubectl exec $HELM_POD_NAME -n default -- mkdir -p /tmp/values

echo 'DEBUG: Transferring values.yaml via base64 decode...'
echo '${VALUES_B64}' | base64 -d > /tmp/helm-values.yaml
if [ \$? -ne 0 ]; then
  echo "ERROR: Failed to decode values.yaml locally!"
  exit 1
fi

echo 'DEBUG: Values file created locally. Copying to pod...'
ls -l /tmp/helm-values.yaml

# Copy values file to pod
kubectl cp /tmp/helm-values.yaml $HELM_POD_NAME:/tmp/values/values.yaml -n default
if [ \$? -ne 0 ]; then
  echo "ERROR: Failed to copy values.yaml to pod!"
  exit 1
fi

echo 'DEBUG: Values file copied to pod. Checking content in pod...'
kubectl exec $HELM_POD_NAME -n default -- ls -l /tmp/values/
kubectl exec $HELM_POD_NAME -n default -- head -n 20 /tmp/values/values.yaml

echo 'DEBUG: Transferring chart package...'
echo '$CHART_B64' | base64 -d > /tmp/chart-package.tgz
if [ \$? -ne 0 ]; then
  echo "ERROR: Failed to decode base64 chart package!"
  exit 1
fi

echo 'DEBUG: Chart package decoded. Size check:'
ls -l /tmp/chart-package.tgz

echo 'DEBUG: Copying chart to pod...'
kubectl cp /tmp/chart-package.tgz $HELM_POD_NAME:/tmp/chart/chart-package.tgz -n default
if [ \$? -ne 0 ]; then
  echo "ERROR: Failed to copy chart package to pod!"
  exit 1
fi

echo 'DEBUG: Chart copied to pod. Checking content in pod...'
kubectl exec $HELM_POD_NAME -n default -- ls -la /tmp/chart/
kubectl exec $HELM_POD_NAME -n default -- tar -tvf /tmp/chart/chart-package.tgz | head -n 5

echo 'Installing chart with Helm...'
kubectl exec $HELM_POD_NAME -n default -- helm upgrade --install $RELEASE_NAME /tmp/chart/chart-package.tgz \
    --namespace $NAMESPACE \
    --create-namespace \
    --values /tmp/values/values.yaml \
    $HELM_SET_ARGS \
    --debug \
    --wait --timeout 5m
HELM_EXIT=\$?

echo "DEBUG: Helm command completed with exit code: \$HELM_EXIT"

if [ \$HELM_EXIT -ne 0 ]; then
  echo "ERROR: Helm command failed with exit code \$HELM_EXIT"
  kubectl exec $HELM_POD_NAME -n default -- helm list -n $NAMESPACE
  exit \$HELM_EXIT
fi

echo 'Removing temporary pod...'
kubectl delete pod $HELM_POD_NAME -n default --wait=false

echo 'Helm deployment completed successfully'
EOF
)
else
    # Use Helm directly in the AKS command environment with verbose output
    log "Creating deployment command using direct Helm execution..."
    
    # Create a more robust remote shell script with proper error handling and debugging
    DEPLOY_COMMAND=$(cat << EOF
#!/bin/bash
set -e

echo 'DEBUG: Starting remote execution...'
echo 'Creating temporary directory...'
mkdir -p /tmp/chart-deploy

echo 'DEBUG: Created directory. Current working directory:'
pwd
ls -la /tmp/chart-deploy

echo 'Transferring values.yaml via base64 decode...'
echo '${VALUES_B64}' | base64 -d > /tmp/chart-deploy/values.yaml
if [ \$? -ne 0 ]; then
  echo "ERROR: Failed to decode and write values.yaml!"
  exit 1
fi

echo 'DEBUG: Values file transferred. Content preview:'
ls -la /tmp/chart-deploy/
head -n 20 /tmp/chart-deploy/values.yaml

echo 'Transferring chart package...'
EOF
)

    # Add chart base64 transfer mechanism - using a file-based approach
    # Generate a safe UUID to use in the remote filename
    CHART_UUID=$(cat /proc/sys/kernel/random/uuid | tr -d '-')
    
    # Create a more robust approach for transferring the chart package
    DEPLOY_COMMAND+=$(cat << EOT

echo 'Transferring chart package in chunks via base64...'
# Create temp file to store the base64 encoded data
cat > /tmp/chart-deploy/chart-b64.txt << 'CHART_B64_EOF'
EOT
)

    # Split the base64 content into chunks to avoid shell limitations
    # Use a heredoc instead of inline echo to avoid corrupting the base64 content
    echo "$CHART_B64" | sed -e 's/.\{1000\}/&\n/g' | while read -r CHUNK; do
        if [ -n "$CHUNK" ]; then
            DEPLOY_COMMAND+="$CHUNK"$'\n'
        fi
    done
    
    # Close the heredoc and add decoding logic
    DEPLOY_COMMAND+=$(cat << EOT
CHART_B64_EOF

# Now decode the base64 file
echo "DEBUG: Base64 file created. Size:"
ls -la /tmp/chart-deploy/chart-b64.txt
cat /tmp/chart-deploy/chart-b64.txt | base64 -d > /tmp/chart-deploy/chart-package.tgz
DECODE_RESULT=\$?

if [ \$DECODE_RESULT -ne 0 ]; then
  echo "ERROR: Failed to decode base64 chart package! Exit code: \$DECODE_RESULT"
  echo "DEBUG: First few lines of base64 file:"
  head -5 /tmp/chart-deploy/chart-b64.txt
  exit 1
fi

echo 'DEBUG: Chart package transferred. Details:'
ls -la /tmp/chart-deploy/
echo 'DEBUG: Chart structure:'
tar -tvf /tmp/chart-deploy/chart-package.tgz | head -n 10

echo 'Installing chart with Helm...'
helm upgrade --install $RELEASE_NAME /tmp/chart-deploy/chart-package.tgz \
    --namespace $NAMESPACE \
    --create-namespace \
    --values /tmp/chart-deploy/values.yaml \
    $HELM_SET_ARGS \
    --debug \
    --wait --timeout 5m
HELM_EXIT=\$?

echo "DEBUG: Helm command completed with exit code: \$HELM_EXIT"

if [ \$HELM_EXIT -ne 0 ]; then
  echo "ERROR: Helm command failed with exit code \$HELM_EXIT"
  helm list -n $NAMESPACE
  exit \$HELM_EXIT
fi

echo 'Cleaning up temporary files...'
rm -rf /tmp/chart-deploy

echo 'Helm deployment completed successfully'
EOT
)

fi

# Debug: Print the deployment command (commented out for production use)
log "DEBUG: Deployment command preview (first few lines):"
echo "$DEPLOY_COMMAND" | head -n 10
log "..."

# Save the command to a file for debugging
DEPLOY_CMD_FILE="$TEMP_DIR/deploy_command.sh"
echo "$DEPLOY_COMMAND" > "$DEPLOY_CMD_FILE"
log "Command saved to: $DEPLOY_CMD_FILE for inspection"

# Execute the deployment command with improved error handling
log "Executing deployment command..."
DEPLOY_RESULT=$(az aks command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER_NAME" \
    --command "$DEPLOY_COMMAND" \
    --output json)
AZ_EXIT_CODE=$?

# Check if az command was successful
if [ $AZ_EXIT_CODE -ne 0 ]; then
    log "${RED}Azure CLI command failed with exit code $AZ_EXIT_CODE${NC}"
    log "Command output: $DEPLOY_RESULT"
    handle_error "Azure CLI command failed"
fi

# Use the extract_exit_code helper function to safely get the exit code
DEPLOY_EXIT_CODE=$(extract_exit_code "$DEPLOY_RESULT")
if [[ $DEPLOY_EXIT_CODE -ne 0 ]]; then
    log "${RED}Deployment failed with exit code $DEPLOY_EXIT_CODE:${NC}"
    
    # Use the extract_logs helper function to safely get the logs
    DEPLOY_LOGS=$(extract_logs "$DEPLOY_RESULT")
    echo "$DEPLOY_LOGS"
    
    # Attempt to get more detailed error information
    log "Attempting to get more error details..."
    ERROR_DETAILS=$(az aks command invoke \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CLUSTER_NAME" \
        --command "kubectl get events -n $NAMESPACE --sort-by='.lastTimestamp' | tail -n 20" \
        --output json)
    
    # Extract and display the error details
    ERROR_LOGS=$(extract_logs "$ERROR_DETAILS")
    if [ -n "$ERROR_LOGS" ]; then
        log "Recent Kubernetes events:"
        echo "$ERROR_LOGS"
    fi
    
    # Check if any Helm releases are in failed state
    log "Checking for failed Helm releases..."
    FAILED_RELEASES=$(az aks command invoke \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CLUSTER_NAME" \
        --command "helm list -n $NAMESPACE --failed" \
        --output json)
    
    # Extract and display any failed releases
    FAILED_RELEASES_LOG=$(extract_logs "$FAILED_RELEASES")
    if [ -n "$FAILED_RELEASES_LOG" ] && [ "$FAILED_RELEASES_LOG" != "No failed releases found" ]; then
        log "Failed Helm releases:"
        echo "$FAILED_RELEASES_LOG"
    fi
    
    # Additional debugging: Check Helm release history if available
    HELM_HISTORY=$(az aks command invoke \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CLUSTER_NAME" \
        --command "helm history $RELEASE_NAME -n $NAMESPACE 2>/dev/null || echo 'No history available'" \
        --output json)
    
    HELM_HISTORY_LOG=$(extract_logs "$HELM_HISTORY")
    if [ -n "$HELM_HISTORY_LOG" ] && [ "$HELM_HISTORY_LOG" != "No history available" ]; then
        log "Helm release history:"
        echo "$HELM_HISTORY_LOG"
    fi
    
    handle_error "Helm deployment failed"
else
    log "${GREEN}Helm deployment completed successfully!${NC}"
    DEPLOY_LOGS=$(extract_logs "$DEPLOY_RESULT")
    echo "$DEPLOY_LOGS"
    
    # Verify the deployment immediately
    log "Verifying deployment..."
    HELM_LIST=$(az aks command invoke \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CLUSTER_NAME" \
        --command "helm list -n $NAMESPACE" \
        --output json)
    
    HELM_LIST_LOGS=$(extract_logs "$HELM_LIST")
    if [ -n "$HELM_LIST_LOGS" ]; then
        log "Helm releases in namespace $NAMESPACE:"
        echo "$HELM_LIST_LOGS"
    else
        log "${YELLOW}Warning: Could not verify Helm release${NC}"
    fi
    
    # Check the deployed pods
    log "Checking deployed pods..."
    PODS_CHECK=$(az aks command invoke \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CLUSTER_NAME" \
        --command "kubectl get pods -n $NAMESPACE" \
        --output json)
    
    PODS_CHECK_LOGS=$(extract_logs "$PODS_CHECK")
    if [ -n "$PODS_CHECK_LOGS" ]; then
        log "Pods in namespace $NAMESPACE:"
        echo "$PODS_CHECK_LOGS"
    else
        log "${YELLOW}Warning: Could not check deployed pods${NC}"
    fi
    
    # Check the deployed services
    log "Checking deployed services..."
    SERVICES_CHECK=$(az aks command invoke \
        --resource-group "$RESOURCE_GROUP" \
        --name "$CLUSTER_NAME" \
        --command "kubectl get services -n $NAMESPACE" \
        --output json)
    
    SERVICES_CHECK_LOGS=$(extract_logs "$SERVICES_CHECK")
    if [ -n "$SERVICES_CHECK_LOGS" ]; then
        log "Services in namespace $NAMESPACE:"
        echo "$SERVICES_CHECK_LOGS"
    else
        log "${YELLOW}Warning: Could not check deployed services${NC}"
    fi
fi

# Final verification already completed above, so we can skip redundant checks
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
log "${GREEN}Deployment completed in $DURATION seconds!${NC}"

# Create a detailed deployment log
LOG_DIR="/home/jonat/real_senti/environments/sit/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/deployment_$(date +%Y%m%d_%H%M%S).json"

# Gather additional information for the log
CHART_INFO=""
if [ "$USE_TEST_CHART" = true ]; then
    CHART_INFO="test chart (simplified nginx deployment)"
else
    CHART_INFO="$CHART_DIR (actual chart)"
fi

DEPLOYMENT_METHOD="helm_$([ "$USE_HELM_POD" = true ] && echo "pod" || echo "direct")"

# Create detailed JSON log with command status
cat > "$LOG_FILE" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "resource_group": "$RESOURCE_GROUP",
  "cluster_name": "$CLUSTER_NAME",
  "namespace": "$NAMESPACE",
  "release_name": "$RELEASE_NAME",
  "chart": "$CHART_INFO",
  "duration_seconds": $DURATION,
  "status": "completed",
  "location": "westus",
  "deployment_method": "$DEPLOYMENT_METHOD",
  "exit_code": $DEPLOY_EXIT_CODE,
  "jq_available": true,
  "chart_size_mb": "$PACKAGE_SIZE_MB"
}
EOF

log "Deployment log saved to: $LOG_FILE"

# Print usage instructions
log "${BLUE}======== Helm Release Commands ========${NC}"
log "Use these commands to manage your Helm release:"
log ""
log "${GREEN}Check release status:${NC}"
log "  az aks command invoke -g $RESOURCE_GROUP -n $CLUSTER_NAME --command \"helm list -n $NAMESPACE\""
log ""
log "${GREEN}View running pods:${NC}"
log "  az aks command invoke -g $RESOURCE_GROUP -n $CLUSTER_NAME --command \"kubectl get pods -n $NAMESPACE\""
log ""
log "${GREEN}Get release details:${NC}"
log "  az aks command invoke -g $RESOURCE_GROUP -n $CLUSTER_NAME --command \"helm get all $RELEASE_NAME -n $NAMESPACE\""
log ""
log "${GREEN}Rollback to previous release:${NC}"
log "  az aks command invoke -g $RESOURCE_GROUP -n $CLUSTER_NAME --command \"helm rollback $RELEASE_NAME [REVISION] -n $NAMESPACE\""
log ""
log "${GREEN}View release history:${NC}"
log "  az aks command invoke -g $RESOURCE_GROUP -n $CLUSTER_NAME --command \"helm history $RELEASE_NAME -n $NAMESPACE\""
log ""
log "${GREEN}Uninstall release:${NC}"
log "  az aks command invoke -g $RESOURCE_GROUP -n $CLUSTER_NAME --command \"helm uninstall $RELEASE_NAME -n $NAMESPACE\""
log ""
log "${BLUE}For more information on using Helm with private AKS clusters, see:${NC}"
log "  /home/jonat/real_senti/docs/deployment/helm_with_private_aks.md"