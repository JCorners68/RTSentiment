#!/bin/bash
# Validates Helm charts for schema compliance and security issues
# Usage: ./validate_charts.sh [chart_dir]

set -euo pipefail

# Default chart directory
CHART_DIR=${1:-"/home/jonat/real_senti/infrastructure/helm/sentimark-services"}
OUTPUT_DIR="/home/jonat/real_senti/scan-results/$(date +%Y%m%d_%H%M%S)"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Validating Helm chart: $CHART_DIR"
echo "Results will be saved to: $OUTPUT_DIR"

# Step 1: Run helm lint
echo "Running helm lint..."
helm lint "$CHART_DIR" > "$OUTPUT_DIR/helm_lint.txt" || {
  echo "Helm lint failed!"
  cat "$OUTPUT_DIR/helm_lint.txt"
  exit 1
}

# Step 2: Generate template
echo "Generating Helm template..."
helm template "$CHART_DIR" > "$OUTPUT_DIR/helm_template.yaml" 2> "$OUTPUT_DIR/helm_template_errors.txt" || {
  echo "Helm template generation failed!"
  cat "$OUTPUT_DIR/helm_template_errors.txt"
  exit 1
}

# Step 3: Run security scan if kubesec is available
if command -v kubesec &> /dev/null; then
  echo "Running security scan with kubesec..."
  kubesec scan "$OUTPUT_DIR/helm_template.yaml" > "$OUTPUT_DIR/kubesec_results.json" || {
    echo "Security scan failed!"
    cat "$OUTPUT_DIR/kubesec_results.json"
    exit 1
  }
else
  echo "kubesec not found. Skipping security scan."
  echo "Install with: curl -s https://raw.githubusercontent.com/controlplaneio/kubesec/master/install.sh | sh"
fi

# Step 4: Check for securityContext at pod level
echo "Checking for pod-level securityContext issues..."
grep -n "securityContext:" "$OUTPUT_DIR/helm_template.yaml" | grep -B 5 "template:" > "$OUTPUT_DIR/securitycontext_issues.txt" || true

# Step 5: Summarize findings
echo "Validation complete. Results saved to: $OUTPUT_DIR"
echo "Summary:"
echo "----------------------------------------"
grep -A 2 "CHART VALIDATION" "$OUTPUT_DIR/helm_lint.txt" || true
echo "----------------------------------------"
if [ -s "$OUTPUT_DIR/securitycontext_issues.txt" ]; then
  echo "Found potential pod-level securityContext issues:"
  cat "$OUTPUT_DIR/securitycontext_issues.txt"
else
  echo "No pod-level securityContext issues found."
fi
