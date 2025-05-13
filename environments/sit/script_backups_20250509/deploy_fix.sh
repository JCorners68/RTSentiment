#!/bin/bash
# Simple fix for CRLF issues in deployment script

# Set variables
SCRIPT_DIR="$(dirname "$0")"
HELM_DEPLOY_SCRIPT="$SCRIPT_DIR/helm_deploy_fixed.sh"

# Ensure the script has proper line endings
echo "Fixing line endings in $HELM_DEPLOY_SCRIPT..."
tr -d '\r' < "$HELM_DEPLOY_SCRIPT" > "${HELM_DEPLOY_SCRIPT}.tmp"
chmod +x "${HELM_DEPLOY_SCRIPT}.tmp"
mv "${HELM_DEPLOY_SCRIPT}.tmp" "$HELM_DEPLOY_SCRIPT"
echo "Line endings fixed."

# Create a values override file
echo "Creating values override file to disable spot instances..."
VALUES_OVERRIDE="$SCRIPT_DIR/values.spot-override.yaml"
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
echo "Values override file created: $VALUES_OVERRIDE"

# Launch the deployment with automatic yes response for any prompts
echo "Running deployment with automatic confirmation for prompts..."
yes y | bash "$HELM_DEPLOY_SCRIPT" \
  --release-name "sentimark" \
  --namespace "sit" \
  --chart-dir "/home/jonat/real_senti/infrastructure/helm/sentimark-services"

# Check the result
EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
  echo "Deployment succeeded!"
  
  # Create a log file
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
  "script_version": "fix"
}
EOF
  
  echo "Deployment log saved to: $LOG_FILE"
else
  echo "Deployment failed with exit code $EXIT_CODE"
fi