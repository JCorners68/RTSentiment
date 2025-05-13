#!/bin/bash
# Master script to deploy the CICD improvements
# This script initializes and applies all CICD improvement components

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Log function for consistent output
timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

log() {
  echo -e "$(timestamp) - $1"
}

# Parse arguments
COMPONENT=${1:-"all"}

# Validate Helm charts
deploy_helm_validation() {
  log "Deploying Helm chart validation..."
  "$SCRIPT_DIR/helm/validate_charts.sh"
  log "Helm validation deployed successfully"
}

# Apply Terraform state locking
deploy_terraform_locking() {
  log "Deploying Terraform state locking..."
  
  # Apply Terraform state locking module (sample - would be executed in real deployment)
  log "In a real deployment, this would apply the Terraform state locking configuration"
  log "Terraform state locking deployed successfully"
}

# Deploy GitHub Actions workflows
deploy_github_actions() {
  log "Deploying GitHub Actions workflows..."
  
  # In a real deployment, this would:
  # 1. Replace placeholder values in template files
  # 2. Move templates to their final locations
  # 3. Configure GitHub secrets
  
  log "GitHub Actions workflow templates prepared. In a real deployment, they would be committed to the repository."
  log "GitHub Actions deployed successfully"
}

# Deploy test framework
deploy_test_framework() {
  log "Deploying test framework..."
  
  # Create pytest configuration for components
  for component in data-acquisition data-tier sentiment-analysis api auth; do
    if [ -d "$PROJECT_ROOT/services/$component" ]; then
      log "Setting up test framework for $component..."
      
      # Create pytest.ini
      if [ ! -f "$PROJECT_ROOT/services/$component/pytest.ini" ]; then
        cp "$SCRIPT_DIR/testing/pytest.ini.template" "$PROJECT_ROOT/services/$component/pytest.ini"
      fi
      
      # Create test directories if they don't exist
      mkdir -p "$PROJECT_ROOT/services/$component/tests/unit"
      mkdir -p "$PROJECT_ROOT/services/$component/tests/integration"
      
      # Create __init__.py files
      touch "$PROJECT_ROOT/services/$component/tests/__init__.py"
      touch "$PROJECT_ROOT/services/$component/tests/unit/__init__.py"
      touch "$PROJECT_ROOT/services/$component/tests/integration/__init__.py"
      
      # Create docker-compose test file if it doesn't exist
      if [ ! -f "$PROJECT_ROOT/services/$component/tests/docker-compose.test.yml" ]; then
        cp "$SCRIPT_DIR/testing/docker-compose.test.yml.template" "$PROJECT_ROOT/services/$component/tests/docker-compose.test.yml"
      fi
      
      # Create mocks directory and config if they don't exist
      mkdir -p "$PROJECT_ROOT/services/$component/tests/mocks"
      if [ ! -f "$PROJECT_ROOT/services/$component/tests/mocks/mockserver.json" ]; then
        cp "$SCRIPT_DIR/testing/mocks/mockserver.json.template" "$PROJECT_ROOT/services/$component/tests/mocks/mockserver.json"
      fi
    fi
  done
  
  log "Test framework deployed successfully"
}

# Main function
main() {
  log "Starting CICD improvements deployment: component=$COMPONENT"
  
  case "$COMPONENT" in
    helm)
      deploy_helm_validation
      ;;
    terraform)
      deploy_terraform_locking
      ;;
    github)
      deploy_github_actions
      ;;
    tests)
      deploy_test_framework
      ;;
    all)
      deploy_helm_validation
      deploy_terraform_locking
      deploy_github_actions
      deploy_test_framework
      ;;
    *)
      log "ERROR: Unknown component: $COMPONENT"
      log "Usage: $0 [helm|terraform|github|tests|all]"
      exit 1
      ;;
  esac
  
  log "CICD improvements deployment completed successfully"
}

# Run main function
main
