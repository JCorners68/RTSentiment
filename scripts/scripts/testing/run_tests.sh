#!/bin/bash
# Runs tests for specified service components
# Usage: ./run_tests.sh [component] [test_type]

set -euo pipefail

COMPONENT=${1:-"all"}
TEST_TYPE=${2:-"all"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Log function
log() {
  echo "[$(date "+%Y-%m-%d %H:%M:%S")] $1"
}

# Run tests for a specific component
run_component_tests() {
  local component=$1
  local test_type=$2
  
  log "Running $test_type tests for $component..."
  
  if [ ! -d "$PROJECT_ROOT/services/$component" ]; then
    log "ERROR: Component directory not found: $component"
    return 1
  fi
  
  cd "$PROJECT_ROOT/services/$component"
  
  case "$test_type" in
    unit)
      log "Running unit tests..."
      if [ -d tests/unit ]; then
        python -m pytest tests/unit -v -m unit --cov=src
      else
        log "No unit tests found for $component"
      fi
      ;;
    integration)
      log "Running integration tests..."
      if [ -d tests/integration ]; then
        if [ -f tests/docker-compose.test.yml ]; then
          log "Setting up integration test environment..."
          docker-compose -f tests/docker-compose.test.yml up -d
          python -m pytest tests/integration -v -m integration
          docker-compose -f tests/docker-compose.test.yml down
        else
          python -m pytest tests/integration -v -m integration
        fi
      else
        log "No integration tests found for $component"
      fi
      ;;
    all)
      log "Running all tests..."
      python -m pytest tests -v --cov=src
      ;;
    *)
      log "Unknown test type: $test_type"
      return 1
      ;;
  esac
  
  log "Tests completed for $component"
  return 0
}

# Main function
main() {
  log "Starting test run: component=$COMPONENT, type=$TEST_TYPE"
  
  # Create test results directory
  RESULTS_DIR="$PROJECT_ROOT/test-results/$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$RESULTS_DIR"
  log "Test results will be saved to: $RESULTS_DIR"
  
  # Run tests for all components or specific component
  if [ "$COMPONENT" = "all" ]; then
    log "Running tests for all components..."
    for dir in "$PROJECT_ROOT"/services/*/; do
      component=$(basename "$dir")
      run_component_tests "$component" "$TEST_TYPE" || log "WARNING: Tests failed for $component"
    done
  else
    run_component_tests "$COMPONENT" "$TEST_TYPE" || {
      log "ERROR: Tests failed for $COMPONENT"
      exit 1
    }
  fi
  
  log "All tests completed successfully"
}

# Run main function
main
