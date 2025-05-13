#!/bin/bash
# Sentimark SIT Deployment Script
# This script handles:
# 1. Line ending fixes (CRLF to LF)
# 2. Spot instance configuration
# 3. Helm chart deployment to AKS

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

# Banner
log "======================================================"
log "    Sentimark Services Deployment - SIT Environment    "
log "======================================================"
log "This script will:"
log "1. Fix CRLF line endings in scripts"
log "2. Create values override to disable spot instance requirements"
log "3. Deploy Helm charts to the AKS cluster"

# Step 1: Fix line endings in the script
log "Step 1: Fixing CRLF line endings in deployment script"
tr -d '\r' < "$HELM_DEPLOY_SCRIPT" > "${HELM_DEPLOY_SCRIPT}.tmp"
chmod +x "${HELM_DEPLOY_SCRIPT}.tmp"
mv "${HELM_DEPLOY_SCRIPT}.tmp" "$HELM_DEPLOY_SCRIPT"
log "Line endings fixed successfully"

# Step 2: Create values override file to disable spot instance requirements
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

# Step 3: Clean up redundant scripts
log "Step 3: Cleaning up redundant deployment scripts"
# List of scripts to clean up (keep this one and helm_deploy_fixed.sh)
REDUNDANT_SCRIPTS=(
  "$SCRIPT_DIR/deploy_fix.sh"
  "$SCRIPT_DIR/deploy_services_fixed.sh"
  "$SCRIPT_DIR/deploy_services_fixed_v2.sh"
  "$SCRIPT_DIR/deploy_solution.sh"
)

# Create a backup directory
BACKUP_DIR="$SCRIPT_DIR/script_backups_$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Move redundant scripts to backup
for script in "${REDUNDANT_SCRIPTS[@]}"; do
  if [ -f "$script" ]; then
    log "Moving $script to backup"
    mv "$script" "$BACKUP_DIR/"
  fi
done
log "Redundant scripts backed up to: $BACKUP_DIR"

# Step 4: Deploy using values override and automatic yes responses
log "Step 4: Running deployment with values override"
log "This will deploy the Sentimark services to the SIT environment"
log "Command: bash $HELM_DEPLOY_SCRIPT --release-name $RELEASE_NAME --namespace $NAMESPACE --chart-dir $CHART_DIR --values-file $VALUES_OVERRIDE"

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
  "script_version": "consolidated"
}
EOF
  
  log "Deployment log saved to: $LOG_FILE"
  
  # Provide next steps
  log "==========================================="
  log "Deployment completed successfully!"
  log ""
  log "For more information, run:"
  log "az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command \"helm list -n sit\""
  log "az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command \"kubectl get pods -n sit\""
  log "==========================================="
else
  log "ERROR: Deployment failed with exit code $EXIT_CODE"
  log "Check the logs for more details"
fi