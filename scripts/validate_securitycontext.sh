#!/bin/bash
# validate_securitycontext.sh
# Script to validate security context settings in Helm deployment templates

set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

HELM_TEMPLATES_DIR="/home/jonat/real_senti/infrastructure/helm/sentimark-services/templates"
VALIDATION_RESULTS="security_context_validation_$(date +%Y%m%d-%H%M%S).log"

echo -e "${BLUE}Starting security context validation...${NC}"
echo "Security Context Validation Results - $(date)" > "$VALIDATION_RESULTS"
echo "==============================================" >> "$VALIDATION_RESULTS"

# Function to validate security context settings in a file
validate_security_context() {
    local file="$1"
    local basename=$(basename "$file")
    
    echo -e "${YELLOW}Validating $basename...${NC}"
    echo -e "\nFile: $basename" >> "$VALIDATION_RESULTS"
    echo "--------------------" >> "$VALIDATION_RESULTS"
    
    # Check if container-level security context is present
    if grep -q "# Container-level security context" "$file"; then
        echo -e "✅ Container-level security context comment found" >> "$VALIDATION_RESULTS"
    else
        echo -e "❌ Missing container-level security context comment" >> "$VALIDATION_RESULTS"
    fi
    
    # Check if all required security settings are present at container level
    local container_level_settings=(
        "runAsNonRoot"
        "runAsUser"
        "runAsGroup"
        "allowPrivilegeEscalation"
        "capabilities"
        "drop"
        "readOnlyRootFilesystem"
    )
    
    for setting in "${container_level_settings[@]}"; do
        if grep -q "$setting" "$file"; then
            echo -e "✅ Container setting found: $setting" >> "$VALIDATION_RESULTS"
        else
            echo -e "❌ Missing container setting: $setting" >> "$VALIDATION_RESULTS"
        fi
    done
    
    # Check for proper pod-level handling
    if grep -q "# Pod-level security context" "$file"; then
        echo -e "✅ Pod-level security context comment found" >> "$VALIDATION_RESULTS"
    else
        echo -e "❌ Missing pod-level security context comment" >> "$VALIDATION_RESULTS"
    fi
    
    # Check if the file has volumes
    if grep -q "volumes:" "$file"; then
        echo -e "📦 File has volumes section" >> "$VALIDATION_RESULTS"
        
        # If volumes are present, fsGroup should be set at pod level
        if grep -q "fsGroup:" "$file" && ! grep -q "#.*fsGroup:" "$file"; then
            echo -e "✅ fsGroup correctly set for volume access" >> "$VALIDATION_RESULTS"
        else
            echo -e "❌ fsGroup missing but volumes are present" >> "$VALIDATION_RESULTS"
        fi
    else
        echo -e "📄 File does not have volumes section" >> "$VALIDATION_RESULTS"
        
        # If no volumes, fsGroup should not be set or should be commented out
        if grep -q "fsGroup:" "$file" && ! grep -q "#.*fsGroup:" "$file"; then
            echo -e "❌ fsGroup set but no volumes are present" >> "$VALIDATION_RESULTS"
        else
            echo -e "✅ Correctly no fsGroup set (no volumes)" >> "$VALIDATION_RESULTS"
        fi
    fi
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
        validate_security_context "$file"
    else
        echo -e "${RED}File not found: $file${NC}" | tee -a "$VALIDATION_RESULTS"
    fi
done

# Run helm lint to verify chart syntax
echo -e "${YELLOW}Running helm lint to verify chart syntax...${NC}"
cd "$(dirname "${HELM_TEMPLATES_DIR}")"
helm lint . > helm_lint_results.log 2>&1
HELM_LINT_EXIT_CODE=$?

if [ $HELM_LINT_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}Helm lint passed${NC}"
    echo -e "\nHelm Lint: PASSED" >> "$VALIDATION_RESULTS"
else
    echo -e "${RED}Helm lint failed. Check helm_lint_results.log for details${NC}"
    echo -e "\nHelm Lint: FAILED - See helm_lint_results.log" >> "$VALIDATION_RESULTS"
fi

# Run template rendering to verify values interpolation
echo -e "${YELLOW}Testing template rendering...${NC}"
helm template . > helm_template_results.yaml 2>helm_template_errors.log
HELM_TEMPLATE_EXIT_CODE=$?

if [ $HELM_TEMPLATE_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}Helm template rendering passed${NC}"
    echo -e "\nHelm Template Rendering: PASSED" >> "$VALIDATION_RESULTS"
else
    echo -e "${RED}Helm template rendering failed. Check helm_template_errors.log for details${NC}"
    echo -e "\nHelm Template Rendering: FAILED - See helm_template_errors.log" >> "$VALIDATION_RESULTS"
fi

echo -e "${GREEN}Validation completed. Results saved to: ${VALIDATION_RESULTS}${NC}"
echo -e "Summary of findings:" | tee -a "$VALIDATION_RESULTS"
grep -E "^❌" "$VALIDATION_RESULTS" || echo -e "${GREEN}No issues found!${NC}" | tee -a "$VALIDATION_RESULTS"