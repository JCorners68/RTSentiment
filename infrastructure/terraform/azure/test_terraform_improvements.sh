#!/bin/bash
# Test script for Terraform pipeline improvements
# This script tests the new features and improvements in the Terraform pipeline

set -e

# Color settings
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test directory
TEST_DIR="/tmp/terraform-test-$(date +%Y%m%d%H%M%S)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create test directory
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo -e "${BLUE}Starting tests for Terraform pipeline improvements${NC}"
echo -e "Test directory: $TEST_DIR"
echo -e "Script directory: $SCRIPT_DIR"
echo

# Function to run a test and report results
run_test() {
  local test_name="$1"
  local test_command="$2"
  local expected_exit_code="${3:-0}"
  
  echo -e "${YELLOW}Running test: $test_name${NC}"
  echo -e "Command: $test_command"
  
  # Run the command and capture output and exit code
  set +e
  eval "$test_command" > "$TEST_DIR/output.log" 2>&1
  local actual_exit_code=$?
  set -e
  
  # Check if exit code matches expected
  if [ "$actual_exit_code" -eq "$expected_exit_code" ]; then
    echo -e "${GREEN}✓ Test passed${NC}"
  else
    echo -e "${RED}✗ Test failed${NC}"
    echo -e "${RED}Expected exit code: $expected_exit_code, got: $actual_exit_code${NC}"
    echo -e "${YELLOW}Output:${NC}"
    cat "$TEST_DIR/output.log"
    echo
  fi
  
  # Check if output contains expected text if provided
  if [ -n "${4:-}" ]; then
    if grep -q "$4" "$TEST_DIR/output.log"; then
      echo -e "${GREEN}✓ Output contains expected text${NC}"
    else
      echo -e "${RED}✗ Output does not contain expected text: $4${NC}"
      echo -e "${YELLOW}Output:${NC}"
      cat "$TEST_DIR/output.log"
      echo
    fi
  fi
  
  echo
}

# Test 1: Help Command
run_test "Help Command" "$SCRIPT_DIR/run-terraform.sh --help" 0 "usage"

# Test 2: Debug Mode
run_test "Debug Mode" "$SCRIPT_DIR/run-terraform.sh --debug plan -target=non_existent_resource" 1 "Debug mode enabled"

# Test 3: Timeout Settings
run_test "Timeout Settings" "$SCRIPT_DIR/run-terraform.sh --operation-timeout=45 --lock-timeout=900 plan -no-color" 0 "Operation timeout: 45"

# Test 4: State Locking Module Structure
run_test "State Locking Module Structure" "ls -la $SCRIPT_DIR/modules/state-locking/*.tf | wc -l" 0 "3"

# Test 5: GitHub Actions Workflow Validation
run_test "GitHub Actions Workflow Validation" "grep 'concurrency' /home/jonat/real_senti/.github/workflows/terraform-cicd.yml" 0 "group"

# Test 6: Error Handling Improvement
run_test "Error Handling Improvement" "grep 'Enhanced error detection' $SCRIPT_DIR/run-terraform.sh" 0 "Enhanced error detection"

# Test 7: Documentation Existence
run_test "Documentation Existence" "grep 'Terraform Pipeline Improvements' /home/jonat/real_senti/docs/deployment/terraform_pipeline_improvements.md" 0 "Overview"

# Test 8: Lock Timeout Value
run_test "Lock Timeout Value" "grep 'TF_AZURE_STATE_LOCK_TIMEOUT' /home/jonat/real_senti/.github/workflows/terraform-cicd.yml" 0 "600"

# Summary
total_tests=8
passed_tests=$(grep -c "✓ Test passed" "$TEST_DIR/output.log" || echo 0)
failed_tests=$((total_tests - passed_tests))

echo -e "${BLUE}Test Summary:${NC}"
echo -e "${GREEN}Passed: $passed_tests${NC}"
echo -e "${RED}Failed: $failed_tests${NC}"
echo

if [ "$failed_tests" -eq 0 ]; then
  echo -e "${GREEN}All tests passed!${NC}"
  exit 0
else
  echo -e "${RED}Some tests failed.${NC}"
  exit 1
fi