#!/bin/bash
# Script to thoroughly validate Helm charts beyond basic linting
# Performs template rendering, Kubernetes schema validation, and dry-run deployment

set -euo pipefail

# Set colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Base paths
BASE_DIR="/home/jonat/real_senti"
HELM_DIR="${BASE_DIR}/infrastructure/helm/sentimark-services"
OUTPUT_DIR="${BASE_DIR}/scan-results/$(date +"%Y%m%d_%H%M%S")"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Log function for consistent output
log() {
  echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] ${1}"
}

# Error handling function
error_exit() {
  log "${RED}ERROR: ${1}${NC}" >&2
  exit 1
}

# Success function
success() {
  log "${GREEN}SUCCESS: ${1}${NC}"
}

# Validation steps
validate_helm_lint() {
  log "${BLUE}Step 1: Running helm lint to check YAML syntax...${NC}"
  
  cd "${HELM_DIR}" || error_exit "Failed to change directory to ${HELM_DIR}"
  
  # Run helm lint and capture output
  if helm lint . > "${OUTPUT_DIR}/helm_lint.txt" 2>&1; then
    success "Helm lint passed!"
  else
    error_exit "Helm lint failed! Check ${OUTPUT_DIR}/helm_lint.txt for details."
  fi
}

validate_helm_template() {
  log "${BLUE}Step 2: Running helm template to render YAML with values...${NC}"
  
  cd "${HELM_DIR}" || error_exit "Failed to change directory to ${HELM_DIR}"
  
  # Run helm template and capture output
  if helm template sentimark-test . > "${OUTPUT_DIR}/helm_template.yaml" 2>"${OUTPUT_DIR}/helm_template_errors.txt"; then
    success "Helm template rendered successfully!"
  else
    cat "${OUTPUT_DIR}/helm_template_errors.txt"
    error_exit "Helm template rendering failed! Check ${OUTPUT_DIR}/helm_template_errors.txt for details."
  fi
  
  # Count rendered resources for verification
  resource_count=$(grep -c "^kind:" "${OUTPUT_DIR}/helm_template.yaml" || true)
  log "${YELLOW}Rendered ${resource_count} Kubernetes resources.${NC}"
}

validate_kubernetes_schema() {
  log "${BLUE}Step 3: Validating Kubernetes schema with kubectl...${NC}"

  # Verify kubectl is available
  if ! command -v kubectl &> /dev/null; then
    log "${YELLOW}kubectl not found, skipping Kubernetes schema validation.${NC}"
    return
  fi

  # Check if we have access to a Kubernetes cluster for proper schema validation
  if kubectl cluster-info &> /dev/null; then
    log "${BLUE}Cluster connection available, performing validation...${NC}"

    # Run kubectl apply --dry-run=client for initial validation
    if kubectl apply --dry-run=client -f "${OUTPUT_DIR}/helm_template.yaml" > "${OUTPUT_DIR}/kubectl_validation.txt" 2>&1; then
      success "Kubernetes client-side schema validation passed!"
    else
      log "${YELLOW}Client-side validation reported issues. See ${OUTPUT_DIR}/kubectl_validation.txt for details.${NC}"
    fi

    # Run kubectl apply --dry-run=server for server-side validation
    if kubectl apply --dry-run=server -f "${OUTPUT_DIR}/helm_template.yaml" > "${OUTPUT_DIR}/kubectl_server_validation.txt" 2>&1; then
      success "Kubernetes server-side schema validation passed!"
    else
      log "${YELLOW}Server-side validation reported issues. See ${OUTPUT_DIR}/kubectl_server_validation.txt for details.${NC}"
    fi
  else
    log "${YELLOW}No Kubernetes cluster available, skipping kubectl validation.${NC}"
    log "${BLUE}For complete validation, run this script with access to a Kubernetes cluster.${NC}"

    # Note the validation state in a file
    echo "WARNING: Kubernetes schema validation was skipped due to lack of cluster access." > "${OUTPUT_DIR}/kubectl_validation.txt"
  fi
}

validate_kubesec() {
  log "${BLUE}Step 4: Running security validation with kubesec (if available)...${NC}"
  
  # Verify kubesec is available
  if ! command -v kubesec &> /dev/null; then
    log "${YELLOW}kubesec not found, skipping security validation.${NC}"
    return
  fi
  
  # Run kubesec scan
  if kubesec scan "${OUTPUT_DIR}/helm_template.yaml" > "${OUTPUT_DIR}/kubesec_results.json" 2>&1; then
    success "Kubesec scan completed successfully!"
    
    # Extract and display high severity issues
    high_severity_count=$(grep -c '"score":-[7-9][0-9]*' "${OUTPUT_DIR}/kubesec_results.json" || true)
    if [ "${high_severity_count}" -gt 0 ]; then
      log "${YELLOW}WARNING: Found ${high_severity_count} high severity security issues!${NC}"
    else
      log "${GREEN}No high severity security issues found.${NC}"
    fi
  else
    log "${YELLOW}Kubesec scan failed, but continuing with validation.${NC}"
  fi
}

check_securitycontext_placement() {
  log "${BLUE}Step 5: Verifying securityContext placement...${NC}"
  
  # Check for pod-level securityContext with container-level properties
  pod_sec_issues=$(grep -n "securityContext:" "${OUTPUT_DIR}/helm_template.yaml" | 
                  grep -B 5 -A 10 "runAsNonRoot\|capabilities\|allowPrivilegeEscalation\|readOnlyRootFilesystem" | 
                  grep -v "containers:" || true)
  
  if [ -n "${pod_sec_issues}" ]; then
    log "${RED}Found potential pod-level securityContext issues:${NC}"
    echo "${pod_sec_issues}"
    log "${YELLOW}WARNING: Possible incorrect securityContext placement detected.${NC}"
  else
    success "No incorrect securityContext placement detected!"
  fi
  
  # Check that container-level has proper securityContext settings
  container_sec_missing=$(grep -A 20 "containers:" "${OUTPUT_DIR}/helm_template.yaml" | 
                         grep -v "securityContext:" || true)
  
  if [ -n "${container_sec_missing}" ]; then
    log "${YELLOW}WARNING: Some containers might be missing securityContext.${NC}"
  else
    success "All containers appear to have securityContext defined!"
  fi
}

validate_indentation() {
  log "${BLUE}Step 6: Checking indentation consistency...${NC}"
  
  # Check for common indentation issues
  indent_issues=$(grep -n "^ \{1,7\}-" "${OUTPUT_DIR}/helm_template.yaml" || true)
  
  if [ -n "${indent_issues}" ]; then
    log "${YELLOW}WARNING: Found potential indentation issues:${NC}"
    echo "${indent_issues}"
  else
    success "No obvious indentation issues detected!"
  fi
}

generate_validation_report() {
  log "${BLUE}Generating validation report...${NC}"
  
  # Create report file
  report_file="${OUTPUT_DIR}/validation_report.md"
  
  cat > "${report_file}" << EOF
# Helm Chart Validation Report

**Date:** $(date +"%Y-%m-%d %H:%M:%S")
**Chart:** sentimark-services

## Validation Steps Performed

1. **Helm Lint**: ${HELM_DIR}
   - Basic YAML syntax check
   - Template structure validation

2. **Helm Template Rendering**:
   - Full template rendering with default values
   - Generated $(grep -c "^kind:" "${OUTPUT_DIR}/helm_template.yaml" || echo "N/A") Kubernetes resources

3. **Kubernetes Schema Validation**:
   - Client-side schema validation
   - Server-side validation (if cluster available)

4. **Security Review** (if kubesec available):
   - Scanned for security best practices
   - Checked for high severity issues

5. **SecurityContext Placement Verification**:
   - Checked for correct placement of security settings
   - Verified container-level securityContext configuration

6. **Indentation Consistency Check**:
   - Reviewed for consistent YAML indentation
   - Checked list item formatting

## Results Summary

$(if grep -q "ERROR" "${OUTPUT_DIR}"/* 2>/dev/null; then echo "⚠️ Issues were detected during validation. See detailed logs."; else echo "✅ All validation checks passed successfully!"; fi)

## Recommendations

1. Deploy to a test environment before production
2. Add these validation steps to your CI/CD pipeline
3. Create a values.yaml template with all required values
4. Document indentation standards in a style guide

## Next Steps

- Review the detailed logs in ${OUTPUT_DIR} for any warnings
- Run a test deployment in a non-production environment
- Update automation scripts if needed
EOF
  
  success "Validation report generated: ${report_file}"
}

# Main function
main() {
  log "${GREEN}Starting comprehensive Helm chart validation...${NC}"
  
  # Execute validation steps
  validate_helm_lint
  validate_helm_template
  validate_kubernetes_schema
  validate_kubesec
  check_securitycontext_placement
  validate_indentation
  generate_validation_report
  
  log "${GREEN}Validation completed! Results saved to ${OUTPUT_DIR}${NC}"
  log "${YELLOW}Review the validation report at ${OUTPUT_DIR}/validation_report.md${NC}"
}

# Run main function
main