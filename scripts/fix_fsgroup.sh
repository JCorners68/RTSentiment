#!/bin/bash
# fix_fsgroup.sh
# Script to properly configure fsGroup settings at the pod level for Helm deployment templates
# This ensures fsGroup is only applied when volumes are present

set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

HELM_TEMPLATES_DIR="/home/jonat/real_senti/infrastructure/helm/sentimark-services/templates"
BACKUP_DIR="${HELM_TEMPLATES_DIR}/fsgroup-backups-$(date +%Y%m%d-%H%M%S)"

# Create backup directory
mkdir -p "$BACKUP_DIR"
echo -e "${GREEN}Created backup directory: ${BACKUP_DIR}${NC}"

# Function to fix fsGroup settings in a file
fix_fsgroup() {
    local file="$1"
    local service_name="$2"
    local basename=$(basename "$file")
    
    echo -e "${YELLOW}Processing $basename for $service_name...${NC}"
    
    # Create backup
    cp "$file" "$BACKUP_DIR/$basename"
    
    # Check if the file has volumes section
    if grep -q "volumes:" "$file"; then
        echo -e "${YELLOW}Volumes found in $basename, adding fsGroup setting...${NC}"
        
        # Add fsGroup setting to the pod security context
        sed -i "/# Pod-level security context/,+1c\\
      # Pod-level security context (fsGroup required for volume access)\\
      securityContext:\\
        fsGroup: {{ .Values.$service_name.securityContext.fsGroup }}" "$file"
        
        echo -e "${GREEN}Added fsGroup to $basename${NC}"
    else
        echo -e "${YELLOW}No volumes found in $basename, leaving pod securityContext commented out${NC}"
    fi
}

# Map of files to their service value names
declare -A FILE_TO_SERVICE=(
    ["api-deployment.yaml"]="api"
    ["auth-deployment.yaml"]="auth"
    ["data-acquisition-deployment.yaml"]="dataAcquisition"
    ["data-migration-deployment.yaml"]="dataMigration"
    ["data-tier-deployment.yaml"]="dataTier"
    ["sentiment-analysis-deployment.yaml"]="sentimentAnalysis"
)

# Process all deployment files
for file_basename in "${!FILE_TO_SERVICE[@]}"; do
    file="${HELM_TEMPLATES_DIR}/$file_basename"
    service="${FILE_TO_SERVICE[$file_basename]}"
    
    if [ -f "$file" ]; then
        fix_fsgroup "$file" "$service"
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

echo -e "${GREEN}fsGroup fixes applied successfully.${NC}"