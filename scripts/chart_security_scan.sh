#!/bin/bash
# Helm Chart Security Scanning Script
# This script performs security scanning of Helm charts using multiple tools

set -e

# Variables
CHART_DIR=""
OUTPUT_DIR="./scan-results"
SCAN_DATE=$(date +%Y%m%d_%H%M%S)
VERBOSE=false
FAIL_ON_ERROR=false

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function for logging with timestamps
log() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo -e "${timestamp} - $1"
}

# Function to handle errors
handle_error() {
    ERROR_MSG="$1"
    log "${RED}Error: $ERROR_MSG${NC}"
    
    if [ "$FAIL_ON_ERROR" = true ]; then
        exit 1
    fi
}

# Function to display usage
usage() {
    echo "Usage: $0 [options] --chart-dir CHART_DIR"
    echo ""
    echo "Options:"
    echo "  --chart-dir CHART_DIR     Path to the Helm chart directory (required)"
    echo "  --output-dir OUTPUT_DIR   Directory to store scan results (default: ./scan-results)"
    echo "  --verbose                 Enable verbose output"
    echo "  --fail-on-error           Exit with error code on any security issue"
    echo "  --help                    Display this help message"
    echo ""
    echo "Example:"
    echo "  $0 --chart-dir ./infrastructure/helm/sentimark-services --verbose"
    echo ""
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --chart-dir)
            CHART_DIR="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --fail-on-error)
            FAIL_ON_ERROR=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Check required arguments
if [ -z "$CHART_DIR" ]; then
    echo "Error: --chart-dir is required"
    usage
fi

# Check if chart directory exists
if [ ! -d "$CHART_DIR" ]; then
    echo "Error: Chart directory $CHART_DIR does not exist"
    exit 1
fi

# Display banner
log "${BLUE}=====================================================${NC}"
log "${BLUE}      Helm Chart Security Scanning                    ${NC}"
log "${BLUE}=====================================================${NC}"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"
SCAN_OUTPUT_DIR="$OUTPUT_DIR/$SCAN_DATE"
mkdir -p "$SCAN_OUTPUT_DIR"

log "Scan results will be saved to: $SCAN_OUTPUT_DIR"

# Check for required tools
MISSING_TOOLS=()

# Check for Helm
if ! command -v helm &> /dev/null; then
    MISSING_TOOLS+=("helm")
fi

# Check for jq
if ! command -v jq &> /dev/null; then
    MISSING_TOOLS+=("jq")
fi

# Check for Docker (needed for some scanning tools)
if ! command -v docker &> /dev/null; then
    MISSING_TOOLS+=("docker")
fi

# Inform if any tools are missing
if [ ${#MISSING_TOOLS[@]} -gt 0 ]; then
    log "${YELLOW}Warning: The following required tools are missing:${NC}"
    for tool in "${MISSING_TOOLS[@]}"; do
        log "  - $tool"
    done
    log "Some scanning features may not be available"
fi

# Phase 1: Helm Lint
log "Phase 1: Running Helm lint..."
HELM_LINT_FILE="$SCAN_OUTPUT_DIR/helm_lint.txt"

if command -v helm &> /dev/null; then
    helm lint "$CHART_DIR" > "$HELM_LINT_FILE" 2>&1
    HELM_LINT_EXIT_CODE=$?
    
    if [ $HELM_LINT_EXIT_CODE -ne 0 ]; then
        log "${RED}✗ Helm lint found issues:${NC}"
        if [ "$VERBOSE" = true ]; then
            cat "$HELM_LINT_FILE"
        else
            grep -E "ERROR|Warning" "$HELM_LINT_FILE" || true
        fi
        handle_error "Helm lint failed with exit code $HELM_LINT_EXIT_CODE"
    else
        log "${GREEN}✓ Helm lint passed${NC}"
    fi
else
    log "${YELLOW}⚠ Skipping Helm lint - helm command not found${NC}"
fi

# Phase 2: Template Validation
log "Phase 2: Validating templates..."
TEMPLATE_FILE="$SCAN_OUTPUT_DIR/helm_template.yaml"
TEMPLATE_ERROR_FILE="$SCAN_OUTPUT_DIR/helm_template_errors.txt"

if command -v helm &> /dev/null; then
    helm template "$CHART_DIR" > "$TEMPLATE_FILE" 2> "$TEMPLATE_ERROR_FILE"
    TEMPLATE_EXIT_CODE=$?
    
    if [ $TEMPLATE_EXIT_CODE -ne 0 ]; then
        log "${RED}✗ Helm template validation failed:${NC}"
        cat "$TEMPLATE_ERROR_FILE"
        handle_error "Helm template failed with exit code $TEMPLATE_EXIT_CODE"
    else
        TEMPLATE_LINES=$(wc -l < "$TEMPLATE_FILE")
        log "${GREEN}✓ Helm template validation passed ($TEMPLATE_LINES lines)${NC}"
    fi
else
    log "${YELLOW}⚠ Skipping template validation - helm command not found${NC}"
fi

# Phase 3: Kubesec scanning
log "Phase 3: Running kubesec security scanner..."
KUBESEC_OUTPUT_FILE="$SCAN_OUTPUT_DIR/kubesec_results.json"

if command -v docker &> /dev/null && [ -f "$TEMPLATE_FILE" ]; then
    # Check if the file is not empty
    if [ -s "$TEMPLATE_FILE" ]; then
        log "Running kubesec scan using Docker..."
        docker run --rm -v "$(pwd)/$TEMPLATE_FILE:/tmp/template.yaml" kubesec/kubesec:v2 scan /tmp/template.yaml > "$KUBESEC_OUTPUT_FILE" 2>&1
        KUBESEC_EXIT_CODE=$?
        
        if [ $KUBESEC_EXIT_CODE -ne 0 ]; then
            log "${RED}✗ kubesec scan failed:${NC}"
            cat "$KUBESEC_OUTPUT_FILE"
            handle_error "Kubesec scan failed with exit code $KUBESEC_EXIT_CODE"
        else
            if command -v jq &> /dev/null; then
                CRITICAL_COUNT=$(jq '[.[] | select(.scoring.critical | length > 0)] | length' "$KUBESEC_OUTPUT_FILE")
                WARNING_COUNT=$(jq '[.[] | select(.scoring.advise | length > 0)] | length' "$KUBESEC_OUTPUT_FILE")
                
                if [ "$CRITICAL_COUNT" -gt 0 ]; then
                    log "${RED}✗ Kubesec found $CRITICAL_COUNT templates with critical issues${NC}"
                    if [ "$VERBOSE" = true ]; then
                        jq '[.[] | select(.scoring.critical | length > 0)] | .[].scoring.critical' "$KUBESEC_OUTPUT_FILE"
                    fi
                    handle_error "Kubesec found critical security issues"
                else
                    log "${GREEN}✓ Kubesec scan passed with no critical issues${NC}"
                    if [ "$WARNING_COUNT" -gt 0 ]; then
                        log "${YELLOW}⚠ Kubesec found $WARNING_COUNT templates with warnings${NC}"
                        if [ "$VERBOSE" = true ]; then
                            jq '[.[] | select(.scoring.advise | length > 0)] | .[].scoring.advise' "$KUBESEC_OUTPUT_FILE"
                        fi
                    fi
                fi
            else
                log "${YELLOW}⚠ jq not found, unable to parse kubesec results${NC}"
                if [ "$VERBOSE" = true ]; then
                    cat "$KUBESEC_OUTPUT_FILE"
                fi
            fi
        fi
    else
        log "${YELLOW}⚠ Template file is empty, skipping kubesec scan${NC}"
    fi
else
    log "${YELLOW}⚠ Skipping kubesec scan - docker command not found or template file not available${NC}"
fi

# Phase 4: Chart Testing (ct)
log "Phase 4: Running chart-testing validation..."
CT_OUTPUT_FILE="$SCAN_OUTPUT_DIR/chart_testing.txt"

if command -v docker &> /dev/null; then
    log "Running chart-testing linting using Docker..."
    docker run --rm -v "$(dirname "$CHART_DIR"):/charts" quay.io/helmpack/chart-testing:latest ct lint --charts "/charts/$(basename "$CHART_DIR")" > "$CT_OUTPUT_FILE" 2>&1 || true
    
    if grep -q "Error" "$CT_OUTPUT_FILE"; then
        log "${RED}✗ Chart-testing found issues:${NC}"
        if [ "$VERBOSE" = true ]; then
            cat "$CT_OUTPUT_FILE"
        else
            grep -E "Error|Lint" "$CT_OUTPUT_FILE" || true
        fi
        handle_error "Chart-testing validation failed"
    else
        log "${GREEN}✓ Chart-testing validation passed${NC}"
    fi
else
    log "${YELLOW}⚠ Skipping chart-testing - docker command not found${NC}"
fi

# Phase 5: Chart schema validation
log "Phase 5: Running chart schema validation..."
SCHEMA_OUTPUT_FILE="$SCAN_OUTPUT_DIR/schema_validation.txt"

if command -v helm &> /dev/null && [ -f "$CHART_DIR/values.schema.json" ]; then
    log "Checking values against schema..."
    SCHEMA_VALID=true
    
    if command -v jq &> /dev/null; then
        # Extract default values
        DEFAULT_VALUES=$(helm inspect values "$CHART_DIR")
        echo "$DEFAULT_VALUES" > "$SCAN_OUTPUT_DIR/values.yaml"
        
        # Validate default values against schema
        jq -n --arg yaml "$DEFAULT_VALUES" 'import "yaml" as yaml; yaml::decode($yaml)' | \
        jq --slurpfile schema "$CHART_DIR/values.schema.json" 'import "jschema" as schema; schema::validate($schema[0])' > "$SCHEMA_OUTPUT_FILE" 2>&1 || SCHEMA_VALID=false
        
        if [ "$SCHEMA_VALID" = true ]; then
            log "${GREEN}✓ Default values conform to schema${NC}"
        else
            log "${RED}✗ Default values do not conform to schema:${NC}"
            cat "$SCHEMA_OUTPUT_FILE"
            handle_error "Values schema validation failed"
        fi
    else
        log "${YELLOW}⚠ jq not found, skipping schema validation${NC}"
    fi
else
    log "${YELLOW}⚠ Skipping schema validation - schema not found or helm not available${NC}"
fi

# Phase 6: Custom best practices checks
log "Phase 6: Running custom best practices checks..."
BEST_PRACTICES_FILE="$SCAN_OUTPUT_DIR/best_practices.txt"

{
    echo "Best Practices Checks:"
    echo "======================="
    
    # Check 1: Resource limits
    if [ -f "$TEMPLATE_FILE" ]; then
        PODS_WITHOUT_LIMITS=$(grep -A 10 "kind: Deployment\|kind: StatefulSet\|kind: DaemonSet" "$TEMPLATE_FILE" | grep -c "resources:" || echo "0")
        echo "Resources specified for pods: $PODS_WITHOUT_LIMITS found"
        
        if [ "$PODS_WITHOUT_LIMITS" -eq 0 ]; then
            echo "❌ FAIL: No resource limits/requests found in templates"
        else
            echo "✅ PASS: Resource specifications found"
        fi
    fi
    
    # Check 2: Network policies
    if [ -f "$TEMPLATE_FILE" ]; then
        NETWORK_POLICIES=$(grep -c "kind: NetworkPolicy" "$TEMPLATE_FILE" || echo "0")
        echo "Network policies: $NETWORK_POLICIES found"
        
        if [ "$NETWORK_POLICIES" -eq 0 ]; then
            echo "⚠️ WARNING: No network policies found"
        else
            echo "✅ PASS: Network policies defined"
        fi
    fi
    
    # Check 3: Probe checks
    if [ -f "$TEMPLATE_FILE" ]; then
        LIVENESS_PROBES=$(grep -c "livenessProbe:" "$TEMPLATE_FILE" || echo "0")
        READINESS_PROBES=$(grep -c "readinessProbe:" "$TEMPLATE_FILE" || echo "0")
        
        echo "Liveness probes: $LIVENESS_PROBES found"
        echo "Readiness probes: $READINESS_PROBES found"
        
        if [ "$LIVENESS_PROBES" -eq 0 ] || [ "$READINESS_PROBES" -eq 0 ]; then
            echo "⚠️ WARNING: Missing health probes"
        else
            echo "✅ PASS: Health probes defined"
        fi
    fi
    
    # Check 4: Security context
    if [ -f "$TEMPLATE_FILE" ]; then
        SECURITY_CONTEXTS=$(grep -c "securityContext:" "$TEMPLATE_FILE" || echo "0")
        
        echo "Security contexts: $SECURITY_CONTEXTS found"
        
        if [ "$SECURITY_CONTEXTS" -eq 0 ]; then
            echo "⚠️ WARNING: No security contexts defined"
        else
            echo "✅ PASS: Security contexts found"
        fi
    fi
    
    echo ""
    echo "Complete check details are in the template file: $TEMPLATE_FILE"

} > "$BEST_PRACTICES_FILE"

log "Best practices check completed"
if [ "$VERBOSE" = true ]; then
    cat "$BEST_PRACTICES_FILE"
fi

# Phase 7: Generate summary report
log "Phase 7: Generating summary report..."
SUMMARY_FILE="$SCAN_OUTPUT_DIR/summary.json"

# Count issues
CRITICAL_ISSUES=0
WARNING_ISSUES=0

# Count critical issues from kubesec
if [ -f "$KUBESEC_OUTPUT_FILE" ] && command -v jq &> /dev/null; then
    CRITICAL_FROM_KUBESEC=$(jq '[.[] | select(.scoring.critical | length > 0)] | length' "$KUBESEC_OUTPUT_FILE")
    WARNING_FROM_KUBESEC=$(jq '[.[] | select(.scoring.advise | length > 0)] | length' "$KUBESEC_OUTPUT_FILE")
    
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + CRITICAL_FROM_KUBESEC))
    WARNING_ISSUES=$((WARNING_ISSUES + WARNING_FROM_KUBESEC))
fi

# Count issues from helm lint
if [ -f "$HELM_LINT_FILE" ]; then
    CRITICAL_FROM_LINT=$(grep -c "ERROR" "$HELM_LINT_FILE" || echo "0")
    WARNING_FROM_LINT=$(grep -c "Warning" "$HELM_LINT_FILE" || echo "0")
    
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + CRITICAL_FROM_LINT))
    WARNING_ISSUES=$((WARNING_ISSUES + WARNING_FROM_LINT))
fi

# Count issues from best practices
if [ -f "$BEST_PRACTICES_FILE" ]; then
    CRITICAL_FROM_BP=$(grep -c "❌ FAIL" "$BEST_PRACTICES_FILE" || echo "0")
    WARNING_FROM_BP=$(grep -c "⚠️ WARNING" "$BEST_PRACTICES_FILE" || echo "0")
    
    CRITICAL_ISSUES=$((CRITICAL_ISSUES + CRITICAL_FROM_BP))
    WARNING_ISSUES=$((WARNING_ISSUES + WARNING_FROM_BP))
fi

# Create summary JSON
{
    echo "{"
    echo "  \"timestamp\": \"$(date -Iseconds)\","
    echo "  \"chart\": \"$(basename "$CHART_DIR")\","
    echo "  \"scan_location\": \"$SCAN_OUTPUT_DIR\","
    echo "  \"status\": \"$([ $CRITICAL_ISSUES -eq 0 ] && echo "passed" || echo "failed")\","
    echo "  \"summary\": {"
    echo "    \"critical_issues\": $CRITICAL_ISSUES,"
    echo "    \"warning_issues\": $WARNING_ISSUES"
    echo "  },"
    echo "  \"tools\": ["
    echo "    {"
    echo "      \"name\": \"helm_lint\","
    echo "      \"status\": \"$([ $CRITICAL_FROM_LINT -eq 0 ] && echo "passed" || echo "failed")\","
    echo "      \"critical_issues\": $CRITICAL_FROM_LINT,"
    echo "      \"warning_issues\": $WARNING_FROM_LINT"
    echo "    },"
    echo "    {"
    echo "      \"name\": \"kubesec\","
    echo "      \"status\": \"$([ $CRITICAL_FROM_KUBESEC -eq 0 ] && echo "passed" || echo "failed")\","
    echo "      \"critical_issues\": $CRITICAL_FROM_KUBESEC,"
    echo "      \"warning_issues\": $WARNING_FROM_KUBESEC"
    echo "    },"
    echo "    {"
    echo "      \"name\": \"best_practices\","
    echo "      \"status\": \"$([ $CRITICAL_FROM_BP -eq 0 ] && echo "passed" || echo "failed")\","
    echo "      \"critical_issues\": $CRITICAL_FROM_BP,"
    echo "      \"warning_issues\": $WARNING_FROM_BP"
    echo "    }"
    echo "  ]"
    echo "}"
} > "$SUMMARY_FILE"

# Create HTML report
HTML_REPORT="$SCAN_OUTPUT_DIR/report.html"

{
    echo "<!DOCTYPE html>"
    echo "<html>"
    echo "<head>"
    echo "  <title>Helm Chart Security Scan Report</title>"
    echo "  <style>"
    echo "    body { font-family: Arial, sans-serif; margin: 20px; }"
    echo "    h1 { color: #333; }"
    echo "    .summary { background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }"
    echo "    .passed { color: green; }"
    echo "    .failed { color: red; }"
    echo "    .warning { color: orange; }"
    echo "    table { border-collapse: collapse; width: 100%; }"
    echo "    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }"
    echo "    th { background-color: #f2f2f2; }"
    echo "    tr:nth-child(even) { background-color: #f9f9f9; }"
    echo "  </style>"
    echo "</head>"
    echo "<body>"
    echo "  <h1>Helm Chart Security Scan Report</h1>"
    echo "  <div class=\"summary\">"
    echo "    <h2>Summary</h2>"
    echo "    <p><strong>Chart:</strong> $(basename "$CHART_DIR")</p>"
    echo "    <p><strong>Scan Date:</strong> $(date)</p>"
    echo "    <p><strong>Status:</strong> <span class=\"$([ $CRITICAL_ISSUES -eq 0 ] && echo "passed" || echo "failed")\">$([ $CRITICAL_ISSUES -eq 0 ] && echo "PASSED" || echo "FAILED")</span></p>"
    echo "    <p><strong>Critical Issues:</strong> <span class=\"$([ $CRITICAL_ISSUES -eq 0 ] && echo "passed" || echo "failed")\">$CRITICAL_ISSUES</span></p>"
    echo "    <p><strong>Warning Issues:</strong> <span class=\"warning\">$WARNING_ISSUES</span></p>"
    echo "  </div>"
    echo ""
    echo "  <h2>Tool Results</h2>"
    echo "  <table>"
    echo "    <tr>"
    echo "      <th>Tool</th>"
    echo "      <th>Status</th>"
    echo "      <th>Critical Issues</th>"
    echo "      <th>Warning Issues</th>"
    echo "    </tr>"
    echo "    <tr>"
    echo "      <td>Helm Lint</td>"
    echo "      <td class=\"$([ $CRITICAL_FROM_LINT -eq 0 ] && echo "passed" || echo "failed")\">$([ $CRITICAL_FROM_LINT -eq 0 ] && echo "PASSED" || echo "FAILED")</td>"
    echo "      <td>$CRITICAL_FROM_LINT</td>"
    echo "      <td>$WARNING_FROM_LINT</td>"
    echo "    </tr>"
    echo "    <tr>"
    echo "      <td>Kubesec</td>"
    echo "      <td class=\"$([ $CRITICAL_FROM_KUBESEC -eq 0 ] && echo "passed" || echo "failed")\">$([ $CRITICAL_FROM_KUBESEC -eq 0 ] && echo "PASSED" || echo "FAILED")</td>"
    echo "      <td>$CRITICAL_FROM_KUBESEC</td>"
    echo "      <td>$WARNING_FROM_KUBESEC</td>"
    echo "    </tr>"
    echo "    <tr>"
    echo "      <td>Best Practices</td>"
    echo "      <td class=\"$([ $CRITICAL_FROM_BP -eq 0 ] && echo "passed" || echo "failed")\">$([ $CRITICAL_FROM_BP -eq 0 ] && echo "PASSED" || echo "FAILED")</td>"
    echo "      <td>$CRITICAL_FROM_BP</td>"
    echo "      <td>$WARNING_FROM_BP</td>"
    echo "    </tr>"
    echo "  </table>"
    echo ""
    echo "  <h2>Scan Details</h2>"
    echo "  <p>Full scan results can be found in the following location:</p>"
    echo "  <code>$SCAN_OUTPUT_DIR</code>"
    echo "</body>"
    echo "</html>"
} > "$HTML_REPORT"

# Display final summary
log "${BLUE}=====================================================${NC}"
if [ $CRITICAL_ISSUES -eq 0 ]; then
    log "${GREEN}✓ Security scan completed successfully${NC}"
else
    log "${RED}✗ Security scan completed with $CRITICAL_ISSUES critical issues${NC}"
fi
log "${BLUE}=====================================================${NC}"
log "Critical issues: $CRITICAL_ISSUES"
log "Warning issues: $WARNING_ISSUES"
log "Scan results saved to: $SCAN_OUTPUT_DIR"
log "HTML report: $HTML_REPORT"

# Exit with appropriate code
if [ $CRITICAL_ISSUES -gt 0 ] && [ "$FAIL_ON_ERROR" = true ]; then
    exit 1
else
    exit 0
fi