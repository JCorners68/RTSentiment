#!/bin/bash
# validate_helm_charts.sh - CI/CD script to validate Helm charts before deployment
#
# This script is designed to be run in CI/CD pipelines to validate Helm charts
# against their schema definitions, check for security issues, and ensure
# all templates render correctly before deployment.
#
# Usage: ./validate_helm_charts.sh [--charts-dir CHARTS_DIR] [--env ENV]

set -eo pipefail

# Default parameters
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHARTS_DIR="${REPO_ROOT}/infrastructure/helm"
VALIDATOR_SCRIPT="${REPO_ROOT}/scripts/helm_schema_validator.sh"
RESULTS_DIR="${REPO_ROOT}/scan-results"
ENVIRONMENT="dev"
VALIDATION_EXIT_CODE=0
EMAIL_NOTIFICATION=false
EMAIL_RECIPIENTS=""
FAIL_PIPELINE=true

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --charts-dir)
      CHARTS_DIR="$2"
      shift 2
      ;;
    --results-dir)
      RESULTS_DIR="$2"
      shift 2
      ;;
    --env)
      ENVIRONMENT="$2"
      shift 2
      ;;
    --notify)
      EMAIL_NOTIFICATION=true
      shift
      ;;
    --email)
      EMAIL_RECIPIENTS="$2"
      shift 2
      ;;
    --no-fail)
      FAIL_PIPELINE=false
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo ""
      echo "Options:"
      echo "  --charts-dir DIR     Directory containing Helm charts (default: ./infrastructure/helm)"
      echo "  --results-dir DIR    Directory to store validation results (default: ./scan-results)"
      echo "  --env ENV            Environment to validate for (dev, sit, uat, prod) (default: dev)"
      echo "  --notify             Send email notification on validation failure"
      echo "  --email RECIPIENTS   Comma-separated list of email recipients for notifications"
      echo "  --no-fail            Don't fail the pipeline on validation errors"
      echo "  --help               Display this help message"
      echo ""
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Create timestamp for this run
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RUN_RESULTS_DIR="${RESULTS_DIR}/${TIMESTAMP}"
mkdir -p "${RUN_RESULTS_DIR}"

# Function to log with timestamp
log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to log to both console and file
log_to_file() {
  local message="$1"
  local file="$2"
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${message}" | tee -a "${file}"
}

# Header function
print_header() {
  local message="$1"
  local file="$2"
  echo "" | tee -a "${file}"
  echo "===================================================" | tee -a "${file}"
  echo " ${message}" | tee -a "${file}"
  echo "===================================================" | tee -a "${file}"
  echo "" | tee -a "${file}"
}

# Check if validator script exists
if [[ ! -f "${VALIDATOR_SCRIPT}" ]]; then
  log "ERROR: Validator script not found at ${VALIDATOR_SCRIPT}"
  exit 1
fi

# Make sure validator script is executable
chmod +x "${VALIDATOR_SCRIPT}"

# Determine values file based on environment
get_values_file() {
  local chart_dir="$1"
  
  # Check for environment-specific values file
  if [[ -f "${chart_dir}/values-${ENVIRONMENT}.yaml" ]]; then
    echo "${chart_dir}/values-${ENVIRONMENT}.yaml"
  elif [[ -f "${chart_dir}/values.${ENVIRONMENT}.yaml" ]]; then
    echo "${chart_dir}/values.${ENVIRONMENT}.yaml"
  else
    # Fall back to default values file
    echo "${chart_dir}/values.yaml"
  fi
}

# Find all helm charts in the directory
find_helm_charts() {
  local charts_root="$1"
  local charts=()
  
  # Find directories containing Chart.yaml
  while IFS= read -r chart_yaml; do
    chart_dir="$(dirname "${chart_yaml}")"
    charts+=("${chart_dir}")
  done < <(find "${charts_root}" -name "Chart.yaml" -type f)
  
  echo "${charts[@]}"
}

# Main validation function
validate_charts() {
  local summary_file="${RUN_RESULTS_DIR}/validation_summary.md"
  local log_file="${RUN_RESULTS_DIR}/validation.log"
  
  # Initialize summary file
  cat > "${summary_file}" << EOF
# Helm Chart Validation Summary

**Date:** $(date +"%Y-%m-%d %H:%M:%S")
**Environment:** ${ENVIRONMENT}

## Results

| Chart | Status | Errors | Warnings | Details |
|-------|--------|--------|----------|---------|
EOF

  # Find all charts
  charts=($(find_helm_charts "${CHARTS_DIR}"))
  
  if [[ ${#charts[@]} -eq 0 ]]; then
    log_to_file "No Helm charts found in ${CHARTS_DIR}" "${log_file}"
    exit 1
  fi
  
  log_to_file "Found ${#charts[@]} charts to validate" "${log_file}"
  
  # Validate each chart
  for chart_dir in "${charts[@]}"; do
    chart_name=$(basename "${chart_dir}")
    print_header "Validating chart: ${chart_name}" "${log_file}"
    
    # Get appropriate values file
    values_file=$(get_values_file "${chart_dir}")
    log_to_file "Using values file: ${values_file}" "${log_file}"
    
    # Create chart-specific output directory
    chart_output_dir="${RUN_RESULTS_DIR}/${chart_name}"
    mkdir -p "${chart_output_dir}"
    
    # Run validation
    log_to_file "Running validation..." "${log_file}"
    
    if "${VALIDATOR_SCRIPT}" \
      --chart-dir "${chart_dir}" \
      --values "${values_file}" \
      --output-dir "${chart_output_dir}" \
      --ci > "${chart_output_dir}/validation_output.txt" 2>&1; then
      
      validation_status="✅ PASSED"
      log_to_file "Validation passed for ${chart_name}" "${log_file}"
    else
      validation_status="❌ FAILED"
      VALIDATION_EXIT_CODE=1
      log_to_file "Validation failed for ${chart_name}" "${log_file}"
    fi
    
    # Count errors and warnings
    error_count=$(grep -c "\[ERROR\]" "${chart_output_dir}/validation.log" || echo 0)
    warning_count=$(grep -c "\[WARNING\]" "${chart_output_dir}/validation.log" || echo 0)
    
    # Add to summary
    echo "| ${chart_name} | ${validation_status} | ${error_count} | ${warning_count} | [Details](${chart_name}/validation_report.md) |" >> "${summary_file}"
    
    # Copy validation output to main log
    cat "${chart_output_dir}/validation_output.txt" >> "${log_file}"
    
    log_to_file "Finished validating ${chart_name}" "${log_file}"
  done
  
  # Add summary footer
  cat >> "${summary_file}" << EOF

## Summary

Total charts validated: ${#charts[@]}
Charts with errors: $(grep -c "❌ FAILED" "${summary_file}" || echo 0)
Charts with warnings only: $(grep -c "⚠️ WARNINGS" "${summary_file}" || echo 0)

## Recommendation

$(if [[ ${VALIDATION_EXIT_CODE} -eq 0 ]]; then
  echo "All charts passed validation and are ready for deployment to ${ENVIRONMENT}."
else
  echo "Some charts failed validation. Fix errors before deploying to ${ENVIRONMENT}."
fi)

## Next Steps

1. Review detailed validation reports for each chart
2. Fix any errors found
3. Address warnings where possible
4. Run validation again to verify fixes

Report generated by CI/CD pipeline on $(date)
EOF

  # Output final result
  if [[ ${VALIDATION_EXIT_CODE} -eq 0 ]]; then
    print_header "VALIDATION SUCCESSFUL: All charts passed validation" "${log_file}"
  else
    print_header "VALIDATION FAILED: Some charts have errors" "${log_file}"
    
    # List failing charts
    grep "❌ FAILED" "${summary_file}" | sed 's/|//g' >> "${log_file}"
  fi
  
  # Provide location of results
  log_to_file "Validation results: ${RUN_RESULTS_DIR}" "${log_file}"
  log_to_file "Summary report: ${summary_file}" "${log_file}"
}

# Send notification (if enabled)
send_notification() {
  if [[ "${EMAIL_NOTIFICATION}" != "true" || -z "${EMAIL_RECIPIENTS}" ]]; then
    return 0
  fi
  
  local subject="Helm Chart Validation - "
  if [[ ${VALIDATION_EXIT_CODE} -eq 0 ]]; then
    subject="${subject}PASSED"
  else
    subject="${subject}FAILED"
  fi
  
  local summary_file="${RUN_RESULTS_DIR}/validation_summary.md"
  
  if command -v mail &> /dev/null; then
    log "Sending notification email to ${EMAIL_RECIPIENTS}"
    mail -s "${subject}" "${EMAIL_RECIPIENTS}" < "${summary_file}"
  else
    log "Email command not found, notification not sent"
  fi
}

# Main script execution
log "Starting Helm chart validation for ${ENVIRONMENT} environment"
validate_charts
send_notification

# Exit with appropriate code for CI/CD pipeline
if [[ "${FAIL_PIPELINE}" == "true" ]]; then
  exit ${VALIDATION_EXIT_CODE}
else
  exit 0
fi