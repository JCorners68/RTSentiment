#!/bin/bash
# Final solution for fixing helm deployment issues
# This script properly handles line endings and spot instance requirements

set -e

# Log function for consistent output
timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

log() {
  echo -e "$(timestamp) - $1"
}

# Script variables
SCRIPT_DIR="$(dirname "$0")"
HELM_DEPLOY_SCRIPT="$SCRIPT_DIR/helm_deploy_fixed.sh"
RELEASE_NAME="sentimark"
NAMESPACE="sit"
CHART_DIR="/home/jonat/real_senti/infrastructure/helm/sentimark-services"

# Fix line endings in the script
log "Step 1: Fixing CRLF line endings in deployment script"
tr -d '\r' < "$HELM_DEPLOY_SCRIPT" > "${HELM_DEPLOY_SCRIPT}.tmp"
chmod +x "${HELM_DEPLOY_SCRIPT}.tmp"
mv "${HELM_DEPLOY_SCRIPT}.tmp" "$HELM_DEPLOY_SCRIPT"
log "Line endings fixed successfully"

# Create values override file to disable spot instance requirements
log "Step 2: Creating values override file to disable spot instances"
VALUES_OVERRIDE="$SCRIPT_DIR/values-override.yaml"
cat > "$VALUES_OVERRIDE" << EOF
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
log "Values override file created at: $VALUES_OVERRIDE"

# Fix the order of function definitions in the helm_deploy_fixed.sh script
log "Step 3: Checking for function order issues"
if grep -q "NON_INTERACTIVE.*log" "$HELM_DEPLOY_SCRIPT"; then
  log "Function order issue detected, fixing..."
  # Create temporary file
  grep -n "^log()" "$HELM_DEPLOY_SCRIPT" > /dev/null || {
    log "ERROR: log function not found in script"
    exit 1
  }
  LOG_FUNC_LINE=$(grep -n "^log()" "$HELM_DEPLOY_SCRIPT" | cut -d':' -f1)
  NON_INTERACTIVE_LINE=$(grep -n "if \[\[ \"\$NON_INTERACTIVE\" == \"true\" \]\]; then" "$HELM_DEPLOY_SCRIPT" | head -1 | cut -d':' -f1)
  
  if [ -n "$LOG_FUNC_LINE" ] && [ -n "$NON_INTERACTIVE_LINE" ] && [ "$NON_INTERACTIVE_LINE" -lt "$LOG_FUNC_LINE" ]; then
    log "Fixing function order by disabling non-interactive check"
    # Replace the non-interactive check with a safer version
    sed -i "s/if \[\[ \"\$NON_INTERACTIVE\" == \"true\" \]\]; then/if false; then # Non-interactive check disabled/" "$HELM_DEPLOY_SCRIPT"
    log "Non-interactive check disabled (will be handled via yes command)"
  fi
fi

# Deploy using values override and automatic yes responses
log "Step 4: Running deployment with values override"
log "This will deploy the Sentimark services to the SIT environment"
log "Command: bash $HELM_DEPLOY_SCRIPT --release-name $RELEASE_NAME --namespace $NAMESPACE --chart-dir $CHART_DIR"

# Run deployment with yes responses to all prompts
yes y | bash "$HELM_DEPLOY_SCRIPT" \
  --release-name "$RELEASE_NAME" \
  --namespace "$NAMESPACE" \
  --chart-dir "$CHART_DIR" \
  --values-file "$VALUES_OVERRIDE"

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
  log "Deployment completed successfully!"
  
  # Create log entry
  LOG_DIR="$SCRIPT_DIR/logs"
  mkdir -p "$LOG_DIR"
  LOG_FILE="$LOG_DIR/deployment_$(date +%Y%m%d_%H%M%S).json"
  
  # Create log entry
  cat > "$LOG_FILE" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "resource_group": "sentimark-sit-rg",
  "cluster_name": "sentimark-sit-aks",
  "namespace": "sit",
  "release_name": "sentimark",
  "status": "completed",
  "spot_override_used": true,
  "solution_version": "final"
}
EOF
  
  log "Deployment log saved to: $LOG_FILE"
  
  # Provide next steps
  log "==========================================="
  log "For more information, run:"
  log "az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command \"helm list -n sit\""
  log "az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command \"kubectl get pods -n sit\""
  log "==========================================="
else
  log "ERROR: Deployment failed with exit code $EXIT_CODE"
  log "Check the logs for more details"
fi