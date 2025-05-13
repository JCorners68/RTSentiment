#!/bin/bash
# clean_securitycontext.sh
# Script to clean up commented securityContext sections in Helm deployment templates
# for the Sentimark services

set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

HELM_TEMPLATES_DIR="/home/jonat/real_senti/infrastructure/helm/sentimark-services/templates"
BACKUP_DIR="${HELM_TEMPLATES_DIR}/backups-$(date +%Y%m%d-%H%M%S)"

# Create backup directory
mkdir -p "$BACKUP_DIR"
echo -e "${GREEN}Created backup directory: ${BACKUP_DIR}${NC}"

# Function to clean up security context in a file
clean_security_context() {
    local file="$1"
    local basename=$(basename "$file")
    
    echo -e "${YELLOW}Processing $basename...${NC}"
    
    # Create backup
    cp "$file" "$BACKUP_DIR/$basename"
    
    # Use sed to replace the commented securityContext sections with a consistent format
    sed -i '
      # Find pod-level securityContext lines and replace with a consistent single-line comment
      /# Pod-level security context/,/fsGroup/c\
      # Pod-level security context (fsGroup settings moved to volumes when needed)
    ' "$file"
    
    echo -e "${GREEN}Cleaned securityContext in $basename${NC}"
}

# Process all deployment files
FILES=(
    "${HELM_TEMPLATES_DIR}/api-deployment.yaml"
    "${HELM_TEMPLATES_DIR}/auth-deployment.yaml"
    "${HELM_TEMPLATES_DIR}/data-acquisition-deployment.yaml"
    "${HELM_TEMPLATES_DIR}/data-migration-deployment.yaml"
    "${HELM_TEMPLATES_DIR}/data-tier-deployment.yaml"
    "${HELM_TEMPLATES_DIR}/sentiment-analysis-deployment.yaml"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        clean_security_context "$file"
    else
        echo -e "${RED}File not found: $file${NC}"
    fi
done

echo -e "${GREEN}All files processed. Backups stored in: ${BACKUP_DIR}${NC}"

# Run helm lint to verify the changes don't break the chart
echo -e "${YELLOW}Running helm lint to verify chart integrity...${NC}"
cd "$(dirname "${HELM_TEMPLATES_DIR}")"
helm lint . || {
    echo -e "${RED}Helm lint failed. Please check the templates for errors.${NC}"
    exit 1
}

echo -e "${GREEN}Security context cleanup completed successfully.${NC}"