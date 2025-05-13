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

# Function to fix securityContext in a template
fix_securitycontext() {
  local template_file=$1
  local basename=$(basename "$template_file")
  
  log "Processing template: $basename"
  
  # Create backup
  cp "$template_file" "$BACKUP_DIR/$basename"
  
  # Temporary file for modifications
  local tmp_file=$(mktemp)
  
  # Identify if the template has a pod-level securityContext
  local has_pod_securitycontext=false
  if grep -q '^\s*securityContext:' "$template_file"; then
    has_pod_securitycontext=true
    log "Found pod-level securityContext in $basename"
  else
    log "No pod-level securityContext found in $basename"
  fi
  
  # Make the modifications based on YAML structure instead of regex
  awk -v has_pod_securitycontext="$has_pod_securitycontext" '
    BEGIN {
      in_pod_spec = 0
      in_security_context = 0
      pod_security_found = 0
      security_content = ""
      
      # Function to detect indentation level
      function get_indent(line) {
        match(line, /^[ \t]*/)
        return substr(line, 1, RLENGTH)
      }
    }
    
    # Detecting pod spec
    /^[[:space:]]*spec:/ && !in_pod_spec {
      in_pod_spec = 1
      indent_level = get_indent($0)
      print
      next
    }
    
    # Detecting securityContext in pod spec
    in_pod_spec && /^[[:space:]]*securityContext:/ && has_pod_securitycontext == "true" {
      in_security_context = 1
      pod_security_found = 1
      security_indent = get_indent($0)
      base_indent = security_indent
      
      # Comment out this line
      print "#" $0
      
      # Capture the securityContext content for later use
      security_content = security_content base_indent "securityContext:\n"
      next
    }
    
    # Capture securityContext content
    in_security_context && /^[[:space:]]/ {
      line_indent = get_indent($0)
      
      # If indent is less than or same as base, we are out of the securityContext block
      if (length(line_indent) <= length(base_indent) && $0 ~ /[^[:space:]]/) {
        in_security_context = 0
        print
        next
      }
      
      # Comment out this securityContext line
      print "#" $0
      
      # Capture content for later use (removing the leading spaces to match container indent)
      relative_indent = substr(line_indent, length(base_indent) + 1)
      content_line = relative_indent $0
      gsub(/^[[:space:]]*/, "", content_line)
      security_content = security_content "  " content_line "\n"
      next
    }
    
    # Add securityContext to containers
    /^[[:space:]]*- name:/ && pod_security_found {
      # Print the container name line
      print
      
      # Get the container indent
      container_indent = get_indent($0)
      
      # Check if the next line is already a securityContext
      getline next_line
      if (next_line ~ /securityContext:/) {
        # Already has securityContext, just print it
        print next_line
      } else {
        # Add container securityContext here
        print container_indent "securityContext:"
        
        # Add captured securityContext content with proper indentation
        # We need to add 2 spaces of indentation for container-level securityContext
        split(security_content, content_lines, "\n")
        for (i in content_lines) {
          if (content_lines[i] != "") {
            print container_indent "  " content_lines[i]
          }
        }
        
        # Print the line we read ahead
        print next_line
      }
      next
    }
    
    # Default action: print the line
    {
      print
    }
  ' "$template_file" > "$tmp_file"
  
  # Replace the original file with the modified version
  mv "$tmp_file" "$template_file"
  
  # Check if we made any changes
  if cmp -s "$template_file" "$BACKUP_DIR/$basename"; then
    log "No changes made to $basename"
  else
    log "Successfully updated $basename"
  fi
}

# Function to verify the Helm charts
verify_helm_charts() {
  log "Verifying Helm charts with 'helm lint'..."
  
  # Run helm lint to verify the templates
  if helm lint "$CHART_DIR"; then
    log "Helm lint successful - charts are valid"
    return 0
  else
    log "Helm lint found issues - manual verification required"
    return 1
  fi
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
    fix_securitycontext "$template"
  done
  
  # Verify the Helm charts
  verify_helm_charts
  
  log "securityContext fixes complete. Backups saved to $BACKUP_DIR"
}

# Run main function
main "$@"