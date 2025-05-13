#!/bin/bash
# Script to fix common Helm YAML syntax issues

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

# Fix YAML syntax issues for a single file
fix_file() {
  local file=$1
  log "${BLUE}Processing file: ${file}${NC}"
  
  # Create backup
  local backup_file="${file}.bak.${TIMESTAMP}"
  cp "$file" "$backup_file" || error_exit "Failed to create backup of $file"
  
  # Create temporary file
  local tmp_file=$(mktemp)
  
  # Fix common YAML syntax issues
  sed -E '
    # Fix env entries indentation
    s/([[:space:]]+)-([[:space:]]+)name:/\1- name:/g;
    # Fix containerPort entries
    s/([[:space:]]+)-([[:space:]]+)containerPort:/\1- containerPort:/g;
    # Fix drop entries in capabilities
    s/([[:space:]]+)-([[:space:]]+)([A-Z]+)([[:space:]]*$)/\1- \3\4/g;
    # Fix quotes in list entries
    s/([[:space:]]+)-([[:space:]]+)([^[:space:]]+:)/\1- \3/g;
    # Fix resource separators
    s/^([[:space:]]*)-([[:space:]]*)--([[:space:]]*$)/---/g;
  ' "$file" > "$tmp_file"

  # Apply changes
  mv "$tmp_file" "$file"
  ' "$file" > "$tmp_file"
  
  # Apply changes
  mv "$tmp_file" "$file"
  log "${GREEN}Successfully fixed YAML syntax in $file${NC}"
}

# Main function
main() {
  local templates_dir="/home/jonat/real_senti/infrastructure/helm/sentimark-services/templates"
  
  log "${GREEN}Starting Helm YAML syntax fix script${NC}"
  
  # Process all YAML files in the templates directory
  if [ $# -eq 0 ]; then
    # No arguments, process all files
    for file in "$templates_dir"/*.yaml; do
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
  
  log "${GREEN}Helm YAML syntax fix script completed${NC}"
  
  # Run helm lint to verify changes
  log "${BLUE}Running helm lint to verify changes${NC}"
  cd "$(dirname "$templates_dir")" && helm lint .
}

# Display help if requested
if [ ${1+x} ] && { [ "$1" == "-h" ] || [ "$1" == "--help" ]; }; then
  echo "Usage: $0 [file_paths...]"
  echo "  - If no files provided, fixes all *.yaml files in templates directory"
  echo "  - Otherwise fixes only the specified files"
  exit 0
fi

# Run main function
main "$@"