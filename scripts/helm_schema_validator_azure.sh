#!/bin/bash
# helm_schema_validator.sh - Comprehensive Helm Chart Schema Validation Script
#
# This script validates Helm charts against their values.schema.json definitions,
# ensuring compliance with schema standards before deployment. It also performs
# additional validation to ensure all templates render correctly and follow
# Kubernetes security best practices.
#
# Features:
# - Schema validation using values.schema.json
# - Template rendering verification
# - Kubernetes resource validation
# - Security context placement checking
# - Common misconfigurations detection
# - CI/CD integration support
#
# Azure Pipelines Usage:
# 
# To use this script in Azure Pipelines, add the following to your pipeline YAML:
#
# - task: Bash@3
#   displayName: 'Validate Helm Charts'
#   inputs:
#     targetType: 'filePath'
#     filePath: './scripts/helm_schema_validator.sh'
#     arguments: '--chart-dir $(Build.SourcesDirectory)/path/to/chart --ci'
#
# The script automatically detects the Azure Pipelines environment and:
# - Installs required dependencies
# - Uses appropriate directories for outputs
# - Reports results to the pipeline
# 
# You can customize behavior using the following pipeline variables:
# - HELM_CHART_DIR: Custom path to the Helm chart
# - HELM_VALUES_FILE: Custom path to the values file
#
# Author: Sentimark Team

set -euo pipefail

# Set colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default paths and directories - Azure DevOps aware
if [ -n "${BUILD_SOURCESDIRECTORY:-}" ]; then
  REPO_ROOT="${BUILD_SOURCESDIRECTORY}"
else
  REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

# Support for Azure Pipeline variables
if [ -n "${SYSTEM_TEAMFOUNDATIONCOLLECTIONURI:-}" ]; then
  echo "Running in Azure Pipelines environment"
  CI_MODE=true
  
  # Set Azure-specific variables
  if [ -n "${HELM_CHART_DIR:-}" ]; then
    CHART_DIR="${HELM_CHART_DIR}"
  else
    CHART_DIR="${REPO_ROOT}/infrastructure/helm/sentimark-services"
  fi
  
  if [ -n "${HELM_VALUES_FILE:-}" ]; then
    VALUES_FILE="${HELM_VALUES_FILE}"
  fi
else
  CHART_DIR="${REPO_ROOT}/infrastructure/helm/sentimark-services"
  CI_MODE=false
fi

# Set default values
VALUES_FILE=""
TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/helm-validator.XXXXXX")
QUIET_MODE=false
CHECK_SECURITY_CONTEXTS=true

# Set output directory based on environment
if [ -n "${BUILD_ARTIFACTSTAGINGDIRECTORY:-}" ]; then
  OUTPUT_DIR="${BUILD_ARTIFACTSTAGINGDIRECTORY}/helm-validation"
else
  OUTPUT_DIR="${REPO_ROOT}/scan-results/$(date +%Y%m%d_%H%M%S)"
fi

LOG_FILE="${OUTPUT_DIR}/validation.log"

# Set exit code for CI/CD integration
EXIT_CODE=0

# Ensure temp directory is cleaned up on exit
trap 'rm -rf "${TEMP_DIR}"' EXIT

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Initialize log file
touch "${LOG_FILE}"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    --chart-dir)
      CHART_DIR="$2"
      shift 2
      ;;
    --values)
      VALUES_FILE="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --ci)
      CI_MODE=true
      shift
      ;;
    --quiet)
      QUIET_MODE=true
      shift
      ;;
    --skip-security-context)
      CHECK_SECURITY_CONTEXTS=false
      shift
      ;;
    --help)
      echo "Usage: $0 [options] [chart_dir] [values_file]"
      echo ""
      echo "Options:"
      echo "  --chart-dir DIR       Path to the Helm chart directory"
      echo "  --values FILE         Path to the values file to validate"
      echo "  --output-dir DIR      Path to the output directory"
      echo "  --ci                  Run in CI mode (exit with non-zero code on failure)"
      echo "  --quiet               Reduce output verbosity"
      echo "  --skip-security-context Don't validate securityContext placement"
      echo "  --help                Display this help message"
      echo ""
      exit 0
      ;;
    *)
      # Positional arguments handling
      if [[ -d "$key" ]]; then
        CHART_DIR="$key"
      elif [[ -f "$key" ]]; then
        VALUES_FILE="$key"
      else
        echo -e "${RED}Invalid argument: $key${NC}" >&2
        exit 1
      fi
      shift
      ;;
  esac
done

# Set values file if not specified
if [ -z "$VALUES_FILE" ]; then
  VALUES_FILE="${CHART_DIR}/values.yaml"
fi

# Log function with standardized format and Azure DevOps integration
log() {
  local level="$1"
  local message="$2"
  local color=""
  
  case "${level}" in
    "INFO")
      color="${BLUE}"
      ;;
    "SUCCESS")
      color="${GREEN}"
      ;;
    "WARNING")
      color="${YELLOW}"
      # Send Azure Pipeline warning if in Azure environment
      if [ -n "${SYSTEM_TEAMFOUNDATIONCOLLECTIONURI:-}" ]; then
        echo "##vso[task.logissue type=warning]${message}"
      fi
      ;;
    "ERROR")
      color="${RED}"
      EXIT_CODE=1
      # Send Azure Pipeline error if in Azure environment
      if [ -n "${SYSTEM_TEAMFOUNDATIONCOLLECTIONURI:-}" ]; then
        echo "##vso[task.logissue type=error]${message}"
      fi
      ;;
    *)
      color="${NC}"
      ;;
  esac
  
  # Output to console unless in quiet mode (and not error)
  if [[ "$QUIET_MODE" == "false" || "$level" == "ERROR" ]]; then
    echo -e "${color}[${level}] ${message}${NC}"
  fi
  
  # Always log to file
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] ${message}" >> "${LOG_FILE}"
}

# Print header function for sections
print_header() {
  if [[ "$QUIET_MODE" == "false" ]]; then
    echo -e "\n${BLUE}${BOLD}=== $1 ===${NC}"
  fi
  echo -e "\n=== $1 ===" >> "${LOG_FILE}"
}

# Function to check if a command exists
check_command() {
  if ! command -v "$1" &> /dev/null; then
    log "WARNING" "Required command not found: $1"
    return 1
  fi
  return 0
}

# Function to install missing dependencies
ensure_dependencies() {
  print_header "Installing Dependencies"
  local missing_deps=false
  local install_output=""
  
  # Check for required tools and install if missing
  for cmd in helm jq yq yamllint jsonschema kubesec kubectl; do
    if ! check_command "$cmd"; then
      log "INFO" "Installing missing dependency: $cmd"
      missing_deps=true
      
      # Install the dependency based on the command name
      case $cmd in
        helm)
          install_output=$(curl -fsSL https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 | bash 2>&1) || true
          log "INFO" "Helm installation: $install_output"
          ;;
        jq)
          install_output=$(apt-get update -qq && apt-get install -y jq 2>&1) || true
          log "INFO" "jq installation: $install_output"
          ;;
        yq)
          install_output=$(wget -qO /usr/local/bin/yq https://github.com/mikefarah/yq/releases/latest/download/yq_linux_amd64 && chmod +x /usr/local/bin/yq 2>&1) || true
          log "INFO" "yq installation: $install_output"
          ;;
        yamllint)
          install_output=$(apt-get update -qq && apt-get install -y yamllint 2>&1) || true
          log "INFO" "yamllint installation: $install_output"
          ;;
        jsonschema)
          install_output=$(pip install jsonschema 2>&1) || true
          log "INFO" "jsonschema installation: $install_output"
          ;;
        kubesec)
          install_output=$(curl -s https://raw.githubusercontent.com/controlplaneio/kubesec/master/install.sh | sh 2>&1) || true
          log "INFO" "kubesec installation: $install_output"
          ;;
        kubectl)
          install_output=$(apt-get update -qq && apt-get install -y kubectl 2>&1) || true
          log "INFO" "kubectl installation: $install_output"
          ;;
      esac
      
      # Verify installation
      if check_command "$cmd"; then
        log "SUCCESS" "Successfully installed: $cmd"
      else
        log "WARNING" "Failed to install: $cmd - some features may be limited"
      fi
    else
      log "INFO" "Command already available: $cmd"
    fi
  done
  
  if [ "$missing_deps" = true ]; then
    log "INFO" "Dependency installation complete"
  else
    log "INFO" "All dependencies are already installed"
  fi
  
  return 0
}

# Validate prerequisites
validate_prerequisites() {
  print_header "Checking Prerequisites"
  
  local prerequisites_ok=true
  
  # In Azure Pipelines, try to install missing dependencies
  if [ -n "${SYSTEM_TEAMFOUNDATIONCOLLECTIONURI:-}" ]; then
    ensure_dependencies
  fi
  
  # Check for required tools
  for cmd in helm jq; do
    if ! check_command "$cmd"; then
      prerequisites_ok=false
    else
      log "INFO" "Found required command: $cmd"
    fi
  done
  
  # Check for optional but useful tools
  for cmd in yq yamllint jsonschema kubesec kubectl; do
    if ! check_command "$cmd"; then
      log "INFO" "Optional command not found: $cmd (some features will be limited)"
    else
      log "INFO" "Found optional command: $cmd"
    fi
  done
  
  # Check chart directory and values file
  if [[ ! -d "${CHART_DIR}" ]]; then
    log "ERROR" "Chart directory not found: ${CHART_DIR}"
    prerequisites_ok=false
  fi
  
  if [[ ! -f "${VALUES_FILE}" ]]; then
    log "ERROR" "Values file not found: ${VALUES_FILE}"
    prerequisites_ok=false
  fi
  
  # Check for Chart.yaml
  if [[ ! -f "${CHART_DIR}/Chart.yaml" ]]; then
    log "ERROR" "Chart.yaml not found in ${CHART_DIR}"
    prerequisites_ok=false
  fi
  
  # Check for templates directory
  if [[ ! -d "${CHART_DIR}/templates" ]]; then
    log "ERROR" "templates directory not found in ${CHART_DIR}"
    prerequisites_ok=false
  fi
  
  if [[ "${prerequisites_ok}" == "true" ]]; then
    log "SUCCESS" "Prerequisites check passed"
    return 0
  else
    log "ERROR" "Prerequisites check failed"
    return 1
  fi
}

# Validate values.schema.json
validate_schema_file() {
  print_header "Validating Schema Definition"
  
  local schema_file="${CHART_DIR}/values.schema.json"
  
  # Check if schema file exists
  if [[ ! -f "${schema_file}" ]]; then
    log "WARNING" "No values.schema.json found in chart - charts should have schemas for validation"
    return 1
  fi
  
  log "INFO" "Found values.schema.json at ${schema_file}"
  
  # Check if schema is valid JSON
  if ! jq empty "${schema_file}" 2> "${TEMP_DIR}/schema_errors.txt"; then
    log "ERROR" "values.schema.json contains invalid JSON:"
    cat "${TEMP_DIR}/schema_errors.txt" >> "${LOG_FILE}"
    return 1
  fi
  
  # Check schema version
  local schema_version=$(jq -r '."$schema" // empty' "${schema_file}")
  if [[ -z "${schema_version}" ]]; then
    log "WARNING" "Schema does not specify \$schema property, recommended to use http://json-schema.org/draft-07/schema#"
  else
    log "INFO" "Schema uses version: ${schema_version}"
  fi
  
  # Check required fields
  local required_fields=$(jq -r '.required // [] | length' "${schema_file}")
  # Force numeric conversion
  required_fields=$((${required_fields:-0}+0))

  if [ "${required_fields}" -eq 0 ]; then
    log "WARNING" "Schema does not have any required fields. Consider adding required fields for validation."
  else
    log "INFO" "Schema has ${required_fields} required fields"
  fi
  
  # Check property descriptions
  local total_properties=$(jq '[.. | objects | select(has("type"))] | length' "${schema_file}")
  local described_properties=$(jq '[.. | objects | select(has("description"))] | length' "${schema_file}")

  # Ensure variables are treated as integers
  total_properties=${total_properties:-0}
  described_properties=${described_properties:-0}

  local description_percentage=0
  if [[ ${total_properties} -gt 0 ]]; then
    description_percentage=$(( described_properties * 100 / total_properties ))
  fi
  
  log "INFO" "Schema documents ${described_properties}/${total_properties} properties (${description_percentage}%)"
  
  if [[ ${description_percentage} -lt 80 ]]; then
    log "WARNING" "Schema documentation is below 80% coverage. Consider adding more descriptions."
  else
    log "SUCCESS" "Schema documentation coverage is good (${description_percentage}%)"
  fi
  
  log "SUCCESS" "Schema file validation passed"
  return 0
}

# Validate values against schema with improved fallback logic
validate_values_against_schema() {
  print_header "Validating Values Against Schema"
  
  local schema_file="${CHART_DIR}/values.schema.json"
  
  # Check if schema file exists
  if [[ ! -f "${schema_file}" ]]; then
    log "WARNING" "Cannot validate values without values.schema.json"
    return 1
  fi
  
  # Check if jsonschema is available
  if check_command "jsonschema"; then
    log "INFO" "Using jsonschema for validation"
    
    # Convert YAML to JSON for validation
    if check_command "yq"; then
      yq eval -o=json "${VALUES_FILE}" > "${TEMP_DIR}/values.json"
      
      # Validate using jsonschema
      if ! jsonschema -i "${TEMP_DIR}/values.json" "${schema_file}" > "${TEMP_DIR}/validation_output.txt" 2>&1; then
        log "ERROR" "Values file does not conform to schema:"
        cat "${TEMP_DIR}/validation_output.txt" >> "${LOG_FILE}"
        return 1
      else
        log "SUCCESS" "Values file conforms to schema"
      fi
    else
      log "WARNING" "yq not found, falling back to manual validation"
      # Basic validation using awk when specialized tools are missing
      if [ -f "${schema_file}" ]; then
        log "INFO" "Schema file exists but cannot perform full validation without required tools"
        # Basic syntax check (limited validation)
        if grep -q "^[[:space:]]*[{[]" "${VALUES_FILE}" && grep -q "[]}][[:space:]]*$" "${VALUES_FILE}"; then
          log "INFO" "Values file appears to be valid YAML/JSON (basic check only)"
        else
          log "ERROR" "Values file appears to be invalid YAML/JSON"
          log "ERROR" "Full validation requires yq and jsonschema tools"
          return 1
        fi
      fi
    fi
  else
    log "WARNING" "jsonschema not found - limited schema validation will be performed"
    
    # Basic validation using awk when specialized tools are missing
    if [ -f "${schema_file}" ]; then
      log "INFO" "Schema file exists but cannot perform full validation without required tools"
      # Basic syntax check (limited validation)
      if grep -q "^[[:space:]]*[{[]" "${VALUES_FILE}" && grep -q "[]}][[:space:]]*$" "${VALUES_FILE}"; then
        log "INFO" "Values file appears to be valid YAML/JSON (basic check only)"
      else
        log "ERROR" "Values file appears to be invalid YAML/JSON"
        log "ERROR" "Full validation requires yq and jsonschema tools"
        return 1
      fi
    fi
  fi
  
  return 0
}

# Validate templates render correctly
validate_template_rendering() {
  print_header "Validating Template Rendering"
  
  log "INFO" "Rendering chart templates with helm template"
  
  # Use a test release name for rendering
  local release_name="schema-validator-test"
  local template_file="${OUTPUT_DIR}/rendered_templates.yaml"
  
  # Render templates and capture any errors
  if ! helm template "${release_name}" "${CHART_DIR}" --values "${VALUES_FILE}" > "${template_file}" 2> "${TEMP_DIR}/template_errors.txt"; then
    log "ERROR" "Failed to render templates:"
    cat "${TEMP_DIR}/template_errors.txt" >> "${LOG_FILE}"
    return 1
  fi
  
  # Check if template file is empty
  if [[ ! -s "${template_file}" ]]; then
    log "ERROR" "Helm template rendered empty output"
    return 1
  fi
  
  # Count resources
  local resource_count=$(grep -c "^kind:" "${template_file}" || echo 0)
  log "INFO" "Successfully rendered ${resource_count} resources"
  
  # Validate YAML syntax
  if check_command "yamllint"; then
    log "INFO" "Validating YAML syntax with yamllint"
    
    if ! yamllint -d "{extends: relaxed, rules: {line-length: {max: 150}}}" "${template_file}" > "${TEMP_DIR}/yamllint_output.txt" 2>&1; then
      local error_count=$(grep -c "error:" "${TEMP_DIR}/yamllint_output.txt" || echo 0)
      
      if [ "${error_count}" -gt 0 ]; then
        log "ERROR" "YAML syntax validation failed with ${error_count} errors"
        grep "error:" "${TEMP_DIR}/yamllint_output.txt" | head -n 5 >> "${LOG_FILE}"
        
        if [ "${error_count}" -gt 5 ]; then
          log "INFO" "More errors omitted, see ${TEMP_DIR}/yamllint_output.txt"
        fi
        
        return 1
      else
        local warning_count=$(grep -c "warning:" "${TEMP_DIR}/yamllint_output.txt" || echo 0)
        if [ "${warning_count}" -gt 0 ]; then
          log "WARNING" "YAML syntax has ${warning_count} warnings"
        else
          log "SUCCESS" "YAML syntax validation passed"
        fi
      fi
    else
      log "SUCCESS" "YAML syntax validation passed"
    fi
  else
    log "WARNING" "yamllint not found, skipping YAML syntax validation"
  fi
  
  log "SUCCESS" "Template rendering validation passed"
  return 0
}

# Validate security contexts with AKS-specific checks
validate_security_contexts() {
  if [[ "${CHECK_SECURITY_CONTEXTS}" != "true" ]]; then
    log "INFO" "Skipping security context validation as requested"
    return 0
  fi
  
  print_header "Validating SecurityContext Placement"
  
  local template_file="${OUTPUT_DIR}/rendered_templates.yaml"
  local sc_issues_file="${OUTPUT_DIR}/security_context_issues.txt"
  
  if [[ ! -f "${template_file}" ]]; then
    log "ERROR" "Template file not found. Run validate_template_rendering first."
    return 1
  fi
  
  log "INFO" "Checking for proper securityContext placement"
  
  # Look for securityContext in template
  local sc_count=$(grep -c "securityContext:" "${template_file}" 2>/dev/null || echo "0")

  # Convert to pure integer
  sc_count=$(echo "$sc_count" | tr -d '[:space:]')
  sc_count=${sc_count:-0}

  if [ "${sc_count}" -eq 0 ]; then
    log "WARNING" "No securityContext settings found in templates. Consider adding them for security."
    return 0
  fi

  log "INFO" "Found ${sc_count} securityContext declarations"
  
  # Check for container-specific securityContext properties at pod level
  # These properties should be at container level, not pod level
  local container_specific_props="runAsNonRoot|runAsUser|allowPrivilegeEscalation|readOnlyRootFilesystem|capabilities"
  local misplaced_contexts=0
  
  # Create a temporary file to store results
  echo "Security Context Issues:" > "${sc_issues_file}"
  echo "=======================" >> "${sc_issues_file}"
  echo "" >> "${sc_issues_file}"
  
  # Check for pod-level securityContext with container-level settings
  for prop in runAsNonRoot runAsUser allowPrivilegeEscalation readOnlyRootFilesystem capabilities; do
    # Find lines with securityContext and the property, but not within a container
    grep -n -B 10 -A 2 "securityContext:" "${template_file}" | 
      grep -n "${prop}:" | 
      grep -v -B 15 "containers:" > "${TEMP_DIR}/context_check.txt" || true
    
    if [ -s "${TEMP_DIR}/context_check.txt" ]; then
      echo "Found ${prop} at pod level (should be at container level):" >> "${sc_issues_file}"
      cat "${TEMP_DIR}/context_check.txt" >> "${sc_issues_file}"
      echo "" >> "${sc_issues_file}"
      # Initialize if not yet set
      misplaced_contexts=${misplaced_contexts:-0}
      misplaced_contexts=$((misplaced_contexts + 1))
    fi
  done
  
  # Ensure clean integer
  misplaced_contexts=${misplaced_contexts:-0}
  misplaced_contexts=$(echo "$misplaced_contexts" | tr -d '[:space:]')
  if [ "${misplaced_contexts}" -gt 0 ]; then
    log "ERROR" "Found ${misplaced_contexts} container-specific securityContext settings at pod level"
    log "ERROR" "These should be moved to container level. See ${sc_issues_file} for details."
    return 1
  else
    log "SUCCESS" "All securityContext settings are properly placed"
  fi
  
  # Check if fsGroup is at pod-level (where it should be)
  if grep -q "securityContext:" "${template_file}" && 
     ! grep -q "fsGroup:" "${template_file}"; then
    log "WARNING" "No fsGroup setting found in securityContext. Consider adding for volume access."
  fi
  
  # Check for missing container security contexts
  local container_count=$(grep -c "containers:" "${template_file}" || echo 0)
  local container_sc_count=$(grep -A 5 "containers:" "${template_file}" | grep -c "securityContext:" || echo 0)
  
  # Set default values if empty
  container_sc_count=${container_sc_count:-0}
  container_count=${container_count:-0}

  # Remove any leading/trailing whitespace
  container_sc_count=$(echo "$container_sc_count" | tr -d '[:space:]')
  container_count=$(echo "$container_count" | tr -d '[:space:]')

  if [ "${container_sc_count}" -lt "${container_count}" ]; then
    log "WARNING" "Not all containers have securityContext settings. Consider adding them for all containers."
  else
    log "SUCCESS" "All containers have securityContext settings"
  fi
  
  # AKS-specific security checks
  log "INFO" "Running AKS-specific security checks"
  
  # Check for Azure-recommended security settings
  if ! grep -q "runAsNonRoot: true" "${template_file}"; then
    log "WARNING" "AKS best practice: runAsNonRoot should be set to true"
  fi
  
  # Check for Azure Policy compliance
  if grep -q "hostPath:" "${template_file}"; then
    log "WARNING" "AKS Azure Policy often restricts hostPath volumes"
  fi
  
  # Check for pod seccomp profile
  if ! grep -q "seccompProfile:" "${template_file}"; then
    log "WARNING" "AKS best practice: seccompProfile should be defined"
  fi
  
  # Check for container resource limits
  if ! grep -q "resources:" "${template_file}"; then
    log "WARNING" "AKS best practice: resources should be defined for all containers"
  fi
  
  # Check for proper network policy
  if grep -q "hostNetwork: true" "${template_file}"; then
    log "WARNING" "AKS best practice: hostNetwork should be avoided unless absolutely necessary"
  }
  
  return 0
}

# Run additional security checks on rendered templates
run_security_checks() {
  print_header "Running Security Checks"
  
  local template_file="${OUTPUT_DIR}/rendered_templates.yaml"
  
  if [[ ! -f "${template_file}" ]]; then
    log "ERROR" "Template file not found. Run validate_template_rendering first."
    return 1
  fi
  
  # Basic security checks
  log "INFO" "Running basic security checks"
  
  # Check resource limits
  local containers_with_limits=$(grep -A 10 "containers:" "${template_file}" | grep -c "resources:" || echo 0)
  local container_count=$(grep -c "containers:" "${template_file}" || echo 0)

  # Set default values if empty
  containers_with_limits=${containers_with_limits:-0}
  container_count=${container_count:-0}

  # Remove any leading/trailing whitespace
  containers_with_limits=$(echo "$containers_with_limits" | tr -d '[:space:]')
  container_count=$(echo "$container_count" | tr -d '[:space:]')

  if [ "${containers_with_limits}" -lt "${container_count}" ]; then
    # Format numbers consistently without leading zeroes
    containers_with_limits=$(echo "$containers_with_limits" | sed 's/^0*//')
    container_count=$(echo "$container_count" | sed 's/^0*//')

    # Handle empty strings after removing zeroes
    containers_with_limits=${containers_with_limits:-0}
    container_count=${container_count:-0}

    log "WARNING" "Not all containers have resource limits. Found ${containers_with_limits}/${container_count}."
  else
    log "SUCCESS" "All containers have resource specifications"
  fi
  
  # Check for privileged mode
  if grep -q "privileged: true" "${template_file}"; then
    log "ERROR" "Found containers running in privileged mode"
  else
    log "SUCCESS" "No containers running in privileged mode"
  fi
  
  # Check for host networking
  if grep -q "hostNetwork: true" "${template_file}"; then
    log "WARNING" "Found pods using host networking"
  else
    log "SUCCESS" "No pods using host networking"
  fi
  
  # Azure-specific security checks
  log "INFO" "Running Azure-specific security checks"
  
  # Check for Microsoft-recommended security settings
  if grep -q "allowPrivilegeEscalation: true" "${template_file}"; then
    log "WARNING" "AKS best practice: allowPrivilegeEscalation should be set to false"
  }
  
  # Check for Azure-specific security settings
  if grep -q "hostIPC: true" "${template_file}" || grep -q "hostPID: true" "${template_file}"; then
    log "WARNING" "AKS best practice: hostIPC and hostPID should be avoided"
  }
  
  # Check for proper volume mounts
  if grep -q "readOnly: false" "${template_file}" && grep -q "mountPath: /" "${template_file}"; then
    log "WARNING" "AKS best practice: root filesystem should be mounted read-only"
  }
  
  # Run kubesec if available
  if check_command "kubesec"; then
    log "INFO" "Running kubesec for security scanning"
    local kubesec_output="${OUTPUT_DIR}/kubesec_results.json"
    
    if ! kubesec scan "${template_file}" > "${kubesec_output}" 2> "${TEMP_DIR}/kubesec_errors.txt"; then
      log "ERROR" "Kubesec scan failed:"
      cat "${TEMP_DIR}/kubesec_errors.txt" >> "${LOG_FILE}"
      return 1
    fi
    
    # Parse kubesec results
    if check_command "jq"; then
      local critical_count=$(jq '[.[] | select(.scoring.critical | length > 0)] | length' "${kubesec_output}")
      local warning_count=$(jq '[.[] | select(.scoring.advise | length > 0)] | length' "${kubesec_output}")

      # Set default values if empty
      critical_count=${critical_count:-0}
      warning_count=${warning_count:-0}

      # Remove any leading/trailing whitespace
      critical_count=$(echo "$critical_count" | tr -d '[:space:]')
      warning_count=$(echo "$warning_count" | tr -d '[:space:]')

      if [ "${critical_count}" -gt 0 ]; then
        log "ERROR" "Kubesec found ${critical_count} critical security issues"
        jq -r '.[] | select(.scoring.critical | length > 0) | "Resource: \(.object.metadata.name) - \(.scoring.critical | length) issues"' "${kubesec_output}" >> "${LOG_FILE}"
      else
        log "SUCCESS" "Kubesec found no critical security issues"
      fi

      if [ "${warning_count}" -gt 0 ]; then
        log "WARNING" "Kubesec found ${warning_count} potential improvements"
      fi
    else
      log "WARNING" "jq not found, cannot parse kubesec results"
    fi
  else
    log "WARNING" "kubesec not found, skipping detailed security scan"
  fi
  
  return 0
}

# Generate validation report
generate_validation_report() {
  print_header "Generating Validation Report"
  
  local report_file="${OUTPUT_DIR}/validation_report.md"
  local error_count=$(grep -c "\[ERROR\]" "${LOG_FILE}" || echo 0)
  local warning_count=$(grep -c "\[WARNING\]" "${LOG_FILE}" || echo 0)

  # Set default values if empty
  error_count=${error_count:-0}
  warning_count=${warning_count:-0}
  
  log "INFO" "Creating validation report at ${report_file}"
  
  # Get chart information
  local chart_name
  local chart_version
  
  if command -v yq &> /dev/null; then
    chart_name=$(yq eval '.name' "${CHART_DIR}/Chart.yaml" 2>/dev/null || echo "Unknown Chart")
    chart_version=$(yq eval '.version' "${CHART_DIR}/Chart.yaml" 2>/dev/null || echo "Unknown Version")
  else
    chart_name=$(grep -m 1 "^name:" "${CHART_DIR}/Chart.yaml" | cut -d ':' -f 2- | tr -d ' ' 2>/dev/null || echo "Unknown Chart")
    chart_version=$(grep -m 1 "^version:" "${CHART_DIR}/Chart.yaml" | cut -d ':' -f 2- | tr -d ' ' 2>/dev/null || echo "Unknown Version")
  fi
  
  # Create report
  cat > "${report_file}" << EOF
# Helm Chart Validation Report

**Chart:** ${chart_name}
**Version:** ${chart_version}
**Date:** $(date +"%Y-%m-%d %H:%M:%S")
**Status:** $(if [ "${error_count}" -eq 0 ]; then echo "✅ PASSED"; else echo "❌ FAILED"; fi)

## Validation Summary

- **Errors:** ${error_count}
- **Warnings:** ${warning_count}
- **Values File:** \`$(basename "${VALUES_FILE}")\`
- **Output Directory:** \`${OUTPUT_DIR}\`

## Validation Steps

| Step | Status | Details |
|------|--------|---------|
EOF

  # Function to get status for each step
  get_step_status() {
    local step=$1
    local section_errors=$(grep "\[ERROR\]" "${LOG_FILE}" | grep -c "${step}" || echo 0)
    local section_warnings=$(grep "\[WARNING\]" "${LOG_FILE}" | grep -c "${step}" || echo 0)

    # Set default values if empty
    section_errors=${section_errors:-0}
    section_warnings=${section_warnings:-0}

    # Remove any leading/trailing whitespace
    section_errors=$(echo "$section_errors" | tr -d '[:space:]')
    section_warnings=$(echo "$section_warnings" | tr -d '[:space:]')

    if [ "${section_errors}" -gt 0 ]; then
      echo "❌ FAILED (${section_errors} errors)"
    elif [ "${section_warnings}" -gt 0 ]; then
      echo "⚠️ WARNINGS (${section_warnings} warnings)"
    else
      echo "✅ PASSED"
    fi
  }

  # Add results for each step
  echo "| Prerequisites | $(get_step_status "Prerequisites") | Verified required tools and files |" >> "${report_file}"
  echo "| Schema Definition | $(get_step_status "Schema Definition") | Validated values.schema.json structure |" >> "${report_file}"
  echo "| Values Validation | $(get_step_status "Values Against Schema") | Checked values against schema |" >> "${report_file}"
  echo "| Template Rendering | $(get_step_status "Template Rendering") | Rendered and verified templates |" >> "${report_file}"
  echo "| SecurityContext | $(get_step_status "SecurityContext") | Verified proper placement of security settings |" >> "${report_file}"
  echo "| Security Checks | $(get_step_status "Security Checks") | Scanned for security best practices |" >> "${report_file}"

  # Add detailed findings
  cat >> "${report_file}" << EOF

## Detailed Findings

### Errors

EOF

  # Convert error_count to integer to avoid errors
  error_count=${error_count:-0}

  if [ "${error_count}" -gt 0 ]; then
    grep "\[ERROR\]" "${LOG_FILE}" | sed 's/.*\[ERROR\] /- /' >> "${report_file}"
  else
    echo "No errors found." >> "${report_file}"
  fi

  cat >> "${report_file}" << EOF

### Warnings

EOF

  # Set default values if empty
  warning_count=${warning_count:-0}

  # Remove any leading/trailing whitespace
  warning_count=$(echo "$warning_count" | tr -d '[:space:]')

  if [ "${warning_count}" -gt 0 ]; then
    grep "\[WARNING\]" "${LOG_FILE}" | sed 's/.*\[WARNING\] /- /' >> "${report_file}"
  else
    echo "No warnings found." >> "${report_file}"
  fi

  cat >> "${report_file}" << EOF

## Recommendations

1. $(if [ "${error_count}" -gt 0 ]; then echo "Fix all errors before deploying to any environment"; else echo "Review warnings and address them where appropriate"; fi)
2. $(if grep -q "securityContext" "${LOG_FILE}"; then echo "Ensure all container-specific securityContext properties are at container level, not pod level"; else echo "Add appropriate securityContext settings to all containers"; fi)
3. $(if grep -q "resource" "${LOG_FILE}"; then echo "Set appropriate resource limits and requests for all containers"; else echo "Continue monitoring resource usage after deployment"; fi)
4. $(if grep -q "values.schema.json" "${LOG_FILE}"; then echo "Update schema to cover all chart values with proper validation"; else echo "Add schema validation for any new parameters"; fi)
5. Integrate this validation script into your CI/CD pipeline to catch issues early

## Azure-Specific Recommendations

1. Implement Azure Policy for AKS to enforce security requirements
2. Use Azure Monitor to track container resource utilization
3. Consider using Azure Container Insights for runtime security monitoring
4. Enable AKS Defender for Containers for threat protection
5. Implement Azure RBAC for Kubernetes to manage access control

## Reference

For more information on Helm chart best practices, see:
- [Helm Best Practices](https://helm.sh/docs/chart_best_practices/)
- [Kubernetes Security Best Practices](https://kubernetes.io/docs/concepts/security/security-checklist/)
- [Microsoft Azure Kubernetes Best Practices](https://docs.microsoft.com/en-us/azure/aks/best-practices)
- [AKS Security Guidelines](https://learn.microsoft.com/en-us/azure/aks/security-hardening)

Report generated by helm_schema_validator.sh
EOF

  log "SUCCESS" "Validation report generated: ${report_file}"
  return 0
}

# Report results to Azure Pipelines
report_to_azure_pipelines() {
  if [ -n "${SYSTEM_TEAMFOUNDATIONCOLLECTIONURI:-}" ]; then
    local error_count=$(grep -c "\[ERROR\]" "${LOG_FILE}" || echo 0)
    local warning_count=$(grep -c "\[WARNING\]" "${LOG_FILE}" || echo 0)

    # Set default values
    error_count=${error_count:-0}
    warning_count=${warning_count:-0}

    if [ "${EXIT_CODE}" -ne 0 ]; then
      echo "##vso[task.logissue type=error]Helm validation failed with ${error_count} errors"
      echo "##vso[task.complete result=Failed;]Helm validation failed"
    else
      if [ "${warning_count}" -gt 0 ]; then
        echo "##vso[task.logissue type=warning]Helm validation passed with ${warning_count} warnings"
      fi
      echo "##vso[task.complete result=Succeeded;]Helm validation succeeded"
    fi
    
    # Publish report as artifact
    if [ -f "${OUTPUT_DIR}/validation_report.md" ]; then
      echo "##vso[artifact.upload artifactname=HelmValidationReport;]${OUTPUT_DIR}/validation_report.md"
    fi
    
    # Publish all validation results as artifact
    if [ -d "${OUTPUT_DIR}" ]; then
      echo "##vso[artifact.upload artifactname=HelmValidationResults;]${OUTPUT_DIR}"
    }
  fi
}

# Main function
main() {
  echo -e "${BLUE}${BOLD}Sentimark Helm Chart Schema Validator${NC}"
  echo -e "Chart: ${CHART_DIR}"
  echo -e "Values: ${VALUES_FILE}"
  echo -e "Output: ${OUTPUT_DIR}\n"
  
  # Run validation steps
  validate_prerequisites || EXIT_CODE=1
  validate_schema_file || EXIT_CODE=1
  validate_values_against_schema || EXIT_CODE=1
  validate_template_rendering || EXIT_CODE=1
  validate_security_contexts || EXIT_CODE=1
  run_security_checks || EXIT_CODE=1
  generate_validation_report
  
  # Final summary
  print_header "Validation Summary"
  
  local error_count=$(grep -c "\[ERROR\]" "${LOG_FILE}" || echo 0)
  local warning_count=$(grep -c "\[WARNING\]" "${LOG_FILE}" || echo 0)

  # Set default values if empty
  error_count=${error_count:-0}
  warning_count=${warning_count:-0}

  # Remove any leading/trailing whitespace
  error_count=$(echo "$error_count" | tr -d '[:space:]')
  warning_count=$(echo "$warning_count" | tr -d '[:space:]')

  if [ "${error_count}" -eq 0 ]; then
    log "SUCCESS" "Validation completed with no errors and ${warning_count} warnings"
  else
    log "ERROR" "Validation completed with ${error_count} errors and ${warning_count} warnings"
    log "ERROR" "Review ${OUTPUT_DIR}/validation_report.md for details"
  fi
  
  log "INFO" "Output saved to: ${OUTPUT_DIR}"
  
  # Report results to Azure Pipelines
  report_to_azure_pipelines
  
  # Exit with proper code for CI/CD integration
  if [[ "${CI_MODE}" == "true" ]]; then
    exit "${EXIT_CODE}"
  else
    exit 0
  fi
}

# Run main function
main