#!/bin/bash
# Script to fix securityContext issues in Helm charts
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

# Function to extract the security context section
extract_securitycontext() {
  local template_file=$1
  local security_block=$(grep -n '^\s*securityContext:' "$template_file" | head -1 | cut -d: -f1)
  
  if [ -n "$security_block" ]; then
    # Find the end of the security context block
    local end_line=$(tail -n +$security_block "$template_file" | grep -n '^\s*[a-zA-Z]' | head -1 | cut -d: -f1)
    
    if [ -n "$end_line" ]; then
      # Extract the security context section
      local end_index=$((security_block + end_line - 1))
      sed -n "${security_block},${end_index}p" "$template_file"
      return 0
    fi
  fi
  
  return 1
}

# Function to get indentation
get_indentation() {
  local line=$1
  echo "$line" | sed 's/^\(\s*\).*/\1/'
}

# Function to fix a template file
fix_template() {
  local template_file=$1
  local basename=$(basename "$template_file")
  local backup_file="$BACKUP_DIR/$basename"
  
  log "Processing template: $basename"
  
  # Create backup
  cp "$template_file" "$backup_file"
  
  # Check if the file has pod-level securityContext
  if grep -q '^\s*template:' "$template_file" && grep -q '^\s*securityContext:' "$template_file"; then
    log "Found pod-level securityContext in $basename"
    
    # Create a temporary file
    tmp_file=$(mktemp)
    
    # Extract the securityContext block with proper indentation
    security_context_block=$(mktemp)
    {
      echo "# Pod-level securityContext moved to container-level by securitycontext_fix.sh"
      grep -A 10 '^\s*securityContext:' "$template_file" | sed '/^[[:space:]]*[^[:space:][:punct:]]/q' | sed '$d' | sed 's/^/#/'
    } > "$security_context_block"
    
    # Replace the securityContext block with comments
    awk '
      /^ *securityContext:/ {
        print "# Pod-level securityContext (moved to container level by securitycontext_fix.sh)";
        getline;
        while ($0 ~ /^[[:space:]]+[^[:space:]]/) {
          print "# " $0;
          if (getline <= 0) {
            break;
          }
        }
        print $0;
        next;
      }
      {print}
    ' "$template_file" > "$tmp_file"
    
    mv "$tmp_file" "$template_file"
    
    # Find all container definitions
    container_lines=$(grep -n '^\s*- name:' "$template_file" | cut -d: -f1)
    
    if [ -n "$container_lines" ]; then
      # For each container, insert the securityContext at the correct indentation
      for line in $container_lines; do
        # Get line with the container name
        name_line=$(sed -n "${line}p" "$template_file")
        
        # Get indentation of the name line
        indentation=$(get_indentation "$name_line")
        
        # Check if the container already has a securityContext
        next_line=$((line + 1))
        next_line_content=$(sed -n "${next_line}p" "$template_file")
        if [[ "$next_line_content" == *"securityContext:"* ]]; then
          log "Container at line $line already has securityContext - skipping"
          continue
        fi
        
        # Create the correctly indented securityContext block
        container_securitycontext=$(cat "$security_context_block" | sed "s/^/$indentation/" | sed 's/^#//')
        
        # Insert the securityContext after the container name
        local insert_tmp_file=$(mktemp)
        head -n "$line" "$template_file" > "$insert_tmp_file"
        echo "$container_securitycontext" >> "$insert_tmp_file"
        tail -n +$((line + 1)) "$template_file" >> "$insert_tmp_file"

        mv "$insert_tmp_file" "$template_file"
        
        log "Added container-level securityContext after line $line"
      done
      
      log "Fixed securityContext in $basename"
    else
      log "WARNING: Could not find container definitions in $basename"
    fi
  else
    log "No pod-level securityContext found in $basename"
  fi
  
  # Cleanup temporary files
  if [ -n "${security_context_block:-}" ] && [ -f "$security_context_block" ]; then
    rm -f "$security_context_block"
  fi
}

# Function to verify fixes
verify_fixes() {
  local template_file=$1
  local basename=$(basename "$template_file")
  
  log "Verifying fixes in: $basename"
  
  # Check for remaining uncommented pod-level securityContext
  pod_securitycontext=$(grep -n '^\s*securityContext:' "$template_file" | grep -v '^\s*#' | wc -l)
  
  # Check for container-level securityContext
  container_securitycontext=$(grep -n '^\s*- name:' "$template_file" | wc -l)
  container_with_securitycontext=$(grep -A1 '^\s*- name:' "$template_file" | grep -c 'securityContext:')
  
  # Print verification results
  log "Verification results for $basename:"
  log "  - Pod-level securityContext entries: $pod_securitycontext"
  log "  - Container definitions: $container_securitycontext"
  log "  - Containers with securityContext: $container_with_securitycontext"
  
  if [ "$pod_securitycontext" -gt 0 ]; then
    log "WARNING: Still found pod-level securityContext in $basename - manual review required"
    return 1
  elif [ "$container_securitycontext" -gt 0 ] && [ "$container_with_securitycontext" -eq 0 ]; then
    log "WARNING: No container-level securityContext found in $basename - manual review required"
    return 1
  fi
  
  log "Verification successful for $basename"
  return 0
}

# Function to run a Helm lint to verify the templates are valid
run_helm_lint() {
  log "Running Helm lint to verify templates..."
  
  # Run helm lint on the chart
  helm lint "$CHART_DIR" || {
    log "WARNING: Helm lint found issues with the chart"
    return 1
  }
  
  log "Helm lint passed - templates are valid"
  return 0
}

# Function to show a detailed diff of changes
show_changes() {
  local template_file=$1
  local backup_file="$BACKUP_DIR/$(basename "$template_file")"
  
  if [ -f "$backup_file" ]; then
    log "Changes made to $(basename "$template_file"):"
    diff -u "$backup_file" "$template_file" | grep -v '^---' | grep -v '^+++' || true
  fi
}

# Main function
main() {
  log "Starting securityContext fix for Helm charts in $TEMPLATES_DIR"
  
  # Find all deployment templates
  templates=$(find "$TEMPLATES_DIR" -name "*-deployment.yaml")
  
  if [ -z "$templates" ]; then
    log "No deployment templates found in $TEMPLATES_DIR"
    exit 1
  fi
  
  log "Found $(echo "$templates" | wc -l) deployment templates"
  
  # Process each template
  for template in $templates; do
    fix_template "$template"
  done
  
  # Verify fixes
  log "Verifying fixes..."
  failed_templates=0
  for template in $templates; do
    if ! verify_fixes "$template"; then
      failed_templates=$((failed_templates + 1))
      show_changes "$template"
    fi
  done
  
  # Run Helm lint to verify the templates are valid
  run_helm_lint
  
  # Final summary
  if [ "$failed_templates" -eq 0 ]; then
    log "All templates successfully fixed and verified"
  else
    log "WARNING: $failed_templates templates may require manual review"
  fi
  
  log "securityContext fixes complete. Backups saved to $BACKUP_DIR"
  log "Run Helm lint to verify the changes:"
  log "  helm lint $CHART_DIR"
  
  # Return success/failure status
  return "$failed_templates"
}

# Run main function
main "$@"