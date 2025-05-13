#!/bin/bash
# Simple script to fix securityContext issues in Helm charts
# Moves securityContext from pod-level to container-level where needed

set -euo pipefail

# Log function for consistent output
timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

log() {
  echo -e "$(timestamp) - $1"
}

# Variables
CHART_DIR="/home/jonat/real_senti/infrastructure/helm/sentimark-services"
TEMPLATES_DIR="$CHART_DIR/templates"
BACKUP_DIR="$CHART_DIR/templates_backup_$(date +%Y%m%d_%H%M%S)"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Process a template file
process_template() {
  local template_file=$1
  local basename=$(basename "$template_file")
  
  log "Processing template: $basename"
  
  # Create backup
  cp "$template_file" "$BACKUP_DIR/$basename"
  
  # Update securityContext to ensure both pod and container level contexts exist and are properly commented
  # This is a simple search and replace to uncomment container securityContext and comment pod securityContext
  
  # First, uncomment container-level securityContext if commented
  sed -i 's/^#\s*securityContext:/securityContext:/' "$template_file"
  
  # Then, comment out pod-level securityContext (under spec: and before containers:)
  sed -i '/^\s*spec:/,/^\s*containers:/ s/^\(\s*\)securityContext:/\1# securityContext:/' "$template_file"
  
  # Make sure fsGroup is present at both levels
  # First at pod level (commented)
  sed -i '/^\s*# securityContext:/,/^\s*[a-zA-Z]/ s/^\(\s*\)fsGroup:/\1# fsGroup:/' "$template_file"
  
  log "Updated $basename"
}

# Verify templates with helm lint
verify_templates() {
  log "Verifying templates with helm lint..."
  
  helm lint "$CHART_DIR" || {
    log "WARNING: helm lint found issues with the templates"
    log "You may need to manually review the templates"
    return 1
  }
  
  log "Templates verified successfully"
  return 0
}

# Main function
main() {
  log "Starting securityContext fix for Helm charts in $TEMPLATES_DIR"
  
  # Find all deployment templates
  local templates=$(find "$TEMPLATES_DIR" -name "*-deployment.yaml")
  
  if [ -z "$templates" ]; then
    log "No deployment templates found in $TEMPLATES_DIR"
    exit 1
  fi
  
  log "Found $(echo "$templates" | wc -l) deployment templates"
  
  # Process each template
  for template in $templates; do
    process_template "$template"
  done
  
  # Verify templates
  verify_templates
  
  log "Script completed. Backups saved to $BACKUP_DIR"
}

# Run main function
main "$@"