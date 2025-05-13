#!/bin/bash
# Script to fix securityContext fields in Helm charts
# Moves securityContext from pod-level to container-level

set -euo pipefail

# Set colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Timestamp for backups
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Log function for consistent output
log() {
  echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${1}"
}

# Error handling function
error_exit() {
  log "${RED}ERROR: ${1}${NC}" >&2
  exit 1
}

# Fix securityContext for a single file
fix_file() {
  local file=$1
  log "${BLUE}Processing file: ${file}${NC}"
  
  # Create backup
  local backup_dir=$(dirname "$file")/templates_backup_${TIMESTAMP}
  mkdir -p "$backup_dir"
  local backup_file="${backup_dir}/$(basename "$file")"
  cp "$file" "$backup_file" || error_exit "Failed to create backup of $file"
  
  # Create temporary file
  local tmp_file=$(mktemp)
  
  # Process the file line by line with specific fixes for securityContext
  awk '
    # Flags to track context in the file
    BEGIN {
      in_container = 0;
      found_security_context = 0;
      commented_pod_level = 0;
      in_cronjob = 0;
      container_indent = "        "; # Default container indentation (8 spaces)
      security_indent = "          "; # Default securityContext indentation (10 spaces)
      caps_indent = "            ";  # Default capabilities indentation (12 spaces)
    }

    # Detect CronJob section which needs different indentation
    /kind: CronJob/ { in_cronjob = 1; print; next; }

    # Detect container section and set appropriate indentation based on context
    /containers:/ {
      in_container = 1;
      if (in_cronjob) {
        # CronJob containers have deeper indentation
        container_indent = "            "; # 12 spaces for CronJob
        security_indent = "              "; # 14 spaces for CronJob securityContext
        caps_indent = "                "; # 16 spaces for CronJob capabilities
      } else {
        # Regular deployment containers
        container_indent = "        "; # 8 spaces for regular deployment
        security_indent = "          "; # 10 spaces for regular securityContext
        caps_indent = "            "; # 12 spaces for regular capabilities
      }
      print;
      next;
    }

    # Handle pod-level securityContext (occurs before container section)
    /securityContext:/ && !in_container {
      # Comment out the line
      commented_pod_level = 1;
      print "      # " $0;
      next;
    }

    # Comment out fsGroup under pod-level securityContext
    /fsGroup:/ && commented_pod_level && !in_container {
      print "        # " $0;
      next;
    }

    # Handle container-level securityContext
    /securityContext:/ && in_container {
      found_security_context = 1;
      # Use the appropriate indentation based on context
      print container_indent "securityContext:";
      next;
    }

    # Handle capabilities section
    /capabilities:/ && in_container && found_security_context {
      print security_indent "capabilities:";
      next;
    }

    # Handle drop array under capabilities
    /drop:/ && in_container && found_security_context {
      print security_indent "  drop:";
      next;
    }

    # For any line after securityContext within container context, fix indentation
    /runAs|allow|readOnly/ && in_container && found_security_context {
      # Use the appropriate indentation for securityContext properties
      gsub(/^[ ]+/, security_indent);
      print;
      next;
    }

    # For capabilities entries (items beginning with dash)
    /^[ ]*-/ && in_container && found_security_context {
      # Use the appropriate indentation for capabilities entries
      gsub(/^[ ]*-/, caps_indent "- ");
      print;
      next;
    }

    # Just print other lines unchanged
    { print }
  ' "$file" > "$tmp_file"
  
  # Apply changes
  mv "$tmp_file" "$file"
  log "${GREEN}Successfully updated securityContext in $file${NC}"
}

# Main function
main() {
  local templates_dir="/home/jonat/real_senti/infrastructure/helm/sentimark-services/templates"
  
  log "${GREEN}Starting securityContext fix script${NC}"
  
  # Process all deployment YAML files in the templates directory
  if [ $# -eq 0 ]; then
    # No arguments, process all files
    for file in "$templates_dir"/*-deployment.yaml; do
      if [ -f "$file" ]; then
        fix_file "$file"
      fi
    done
  else
    # Process specific files provided as arguments
    for file in "$@"; do
      if [ -f "$file" ]; then
        fix_file "$file"
      else
        log "${YELLOW}File not found: $file${NC}"
      fi
    done
  fi
  
  log "${GREEN}securityContext fix script completed${NC}"
}

# Display help if requested
if [ ${1+x} ] && { [ "$1" == "-h" ] || [ "$1" == "--help" ]; }; then
  echo "Usage: $0 [file_paths...]"
  echo "  - If no files provided, fixes all *-deployment.yaml files in templates directory"
  echo "  - Otherwise fixes only the specified files"
  exit 0
fi

# Run main function
main "$@"