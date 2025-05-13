# CLI Kanban Verification Guide

This document outlines the verification procedures for CLI Kanban, providing a comprehensive guide to testing and validating the system's functionality, robustness, and reliability.

## 1. Verification Approach

CLI Kanban employs a multi-layered verification approach to ensure all components work correctly:

1. **Unit Testing**: Validates individual components in isolation
2. **Integration Testing**: Tests interactions between components
3. **End-to-End Testing**: Verifies complete user workflows
4. **Edge Case Testing**: Validates system behavior under unusual or error conditions
5. **Performance Testing**: Measures performance under various loads
6. **Cross-Platform Testing**: Ensures functionality across supported environments

## 2. Test Environment Setup

Before running verification tests, set up a clean test environment:

```bash
# Create a dedicated test directory
mkdir -p ~/kanban_test
cd ~/kanban_test

# Initialize a clean environment
python -m src.main init --clean

# Verify environment variables
python -m src.main config check-env
```

## 3. End-to-End Test Workflows

### 3.1. Project Management Workflow

This workflow validates the core project management capabilities:

```bash
# Run the complete project workflow test
python -m tests.e2e.test_complete_workflow

# Alternatively, run a manual workflow:
# 1. Create an epic
python -m src.main kanban epic create --title "Test Epic" --description "End-to-end test epic" --status "Open"

# 2. Create tasks for the epic (using the epic ID from previous output)
python -m src.main kanban task add --title "Design Task" --description "Design component" --status "Ready" --priority "High" --epic EPC-123

python -m src.main kanban task add --title "Implement Task" --description "Implement component" --status "Backlog" --priority "Medium" --epic EPC-123

python -m src.main kanban task add --title "Test Task" --description "Test component" --status "Backlog" --priority "Medium" --epic EPC-123

# 3. View the board
python -m src.main kanban board show

# 4. Move tasks through workflow
python -m src.main kanban board move TSK-001 "In Progress"
python -m src.main kanban board move TSK-001 "Done"
python -m src.main kanban board move TSK-002 "In Progress"
python -m src.main kanban board move TSK-002 "Done"
python -m src.main kanban board move TSK-003 "In Progress"
python -m src.main kanban board move TSK-003 "Done"

# 5. Close the epic
python -m src.main kanban epic update EPC-123 --status "Closed"

# 6. Verify board state
python -m src.main kanban board show
```

### 3.2. Evidence Management Workflow

This workflow validates the evidence management capabilities:

```bash
# Create a task for evidence
python -m src.main kanban task add --title "Evidence Test Task" --description "For testing evidence" --status "In Progress"

# Add evidence for the task
python -m src.main kanban evidence add --title "Test Evidence" --description "Evidence for testing" --category "Requirement" --task TSK-001

# Add attachment to evidence
python -m src.main kanban evidence attach EVD-001 test_document.txt --description "Test attachment"

# View evidence details
python -m src.main kanban evidence get EVD-001 --with-attachments

# Tag evidence
python -m src.main kanban evidence tag EVD-001 "important,design,reference"

# Search for evidence
python -m src.main kanban evidence search --category "Requirement" --tag "important"
```

### 3.3. API Server Workflow

This workflow validates the API server functionality:

```bash
# Start the API server
python -m src.server.control start

# Test API endpoints (using curl)
curl http://localhost:3000/health
curl -H "x-webhook-secret: your-secret-here" http://localhost:3000/api/kanban/tasks
curl -H "x-webhook-secret: your-secret-here" http://localhost:3000/api/kanban/epics

# Test creating a task via API
curl -X POST -H "x-webhook-secret: your-secret-here" -H "Content-Type: application/json" \
  -d '{"title":"API Task","description":"Created via API","status":"Backlog"}' \
  http://localhost:3000/api/kanban/task

# Stop the API server
python -m src.server.control stop
```

## 4. Edge Case Testing

Edge case tests validate system behavior under unusual or error conditions:

```bash
# Run complete edge case test suite
python -m tests.edge_cases

# Alternatively, test specific edge cases:
# Test concurrent file access
python -m tests.edge_cases StorageEdgeCaseTest.test_concurrent_file_access

# Test corrupted data file handling
python -m tests.edge_cases StorageEdgeCaseTest.test_corrupted_data_file

# Test handling of nonexistent resources
python -m tests.edge_cases CommandEdgeCaseTest.test_nonexistent_task_id

# Test invalid input validation
python -m tests.edge_cases ValidationEdgeCaseTest.test_invalid_task_status

# Test configuration issues
python -m tests.edge_cases ConfigurationEdgeCaseTest.test_invalid_config_file
```

## 5. Cross-Platform Verification

Verify CLI Kanban functionality across different operating systems:

### 5.1. Windows Verification

```powershell
# Initialize system on Windows
python -m src.main init

# Run basic workflow to verify Windows compatibility
python -m src.main kanban task add --title "Windows Test" --description "Testing on Windows" --status "Backlog"
python -m src.main kanban task list
```

### 5.2. Linux Verification

```bash
# Initialize system on Linux
python -m src.main init

# Run basic workflow to verify Linux compatibility
python -m src.main kanban task add --title "Linux Test" --description "Testing on Linux" --status "Backlog"
python -m src.main kanban task list
```

### 5.3. macOS Verification

```bash
# Initialize system on macOS
python -m src.main init

# Run basic workflow to verify macOS compatibility
python -m src.main kanban task add --title "macOS Test" --description "Testing on macOS" --status "Backlog"
python -m src.main kanban task list
```

## 6. File Permission and Line Ending Verification

Ensure scripts have the correct permissions and line endings:

```bash
# Run the permissions fix script
./scripts/fix_permissions.sh --verbose

# Verify script permissions
ls -la scripts/*.sh
ls -la tests/e2e/*.py

# Check for CRLF line endings
find . -name "*.py" -exec file {} \; | grep CRLF
find . -name "*.sh" -exec file {} \; | grep CRLF
```

## 7. Configuration Validation

Verify the configuration system:

```bash
# Validate configuration
python -m src.main config validate

# Check environment
python -m src.main config check-env

# Test configuration repair
python -m src.main config repair

# Test with intentionally corrupted configuration
sed -i 's/version: "0.1.0"/# version removed/' config.yaml
python -m src.main config validate
python -m src.main config repair --force
python -m src.main config validate
```

## 8. UI Refinement Verification

Verify the user interface in different scenarios:

```bash
# Test with no tasks
rm -f data/tasks.yaml
python -m src.main kanban board show

# Test with many tasks (generate test data)
python -m tests.generate_test_data --tasks 50
python -m src.main kanban board show

# Test UI with narrow terminal
export COLUMNS=60
python -m src.main kanban board show
unset COLUMNS

# Test color output in different terminals
TERM=xterm-color python -m src.main kanban board show
TERM=xterm-mono python -m src.main kanban board show
```

## 9. Performance Verification

Verify system performance under various conditions:

```bash
# Generate large test dataset
python -m tests.generate_test_data --tasks 1000 --epics 100 --evidence 500

# Measure task listing performance
time python -m src.main kanban task list

# Measure board display performance
time python -m src.main kanban board show

# Measure search performance
time python -m src.main kanban evidence search --category "Requirement"
```

## 10. Verification Checklist

Use this checklist to ensure all aspects have been verified:

- [ ] All unit tests pass (`python -m tests.run_tests --unit`)
- [ ] All integration tests pass (`python -m tests.run_tests --integration`)
- [ ] End-to-end workflow tests pass (`python -m tests.e2e.test_complete_workflow`)
- [ ] Edge case tests pass (`python -m tests.edge_cases`)
- [ ] Server API endpoints work as expected
- [ ] System works on all supported platforms (Windows, Linux, macOS)
- [ ] Scripts have correct permissions and line endings
- [ ] Configuration validation and repair functions correctly
- [ ] UI adapts to different terminal sizes and capabilities
- [ ] Performance meets requirements under various load conditions
- [ ] All documented commands work as described

## 11. Verification Report

Generate a verification report after completing all tests:

```bash
# Generate verification report
python -m src.tools.generate_verification_report
```

The report includes:
- Test coverage summary
- Platform compatibility results
- Performance metrics
- Edge case handling assessment
- Recommendations for future improvements

## 12. Troubleshooting Common Verification Issues

### Issue: Missing Dependencies
If tests fail due to missing dependencies, verify your environment:
```bash
pip install -r requirements.txt
python -m src.utils.dependency_check
```

### Issue: Configuration Problems
If tests fail due to configuration issues:
```bash
python -m src.main config repair --force
```

### Issue: Permission Denied
If tests fail due to permission issues:
```bash
./scripts/fix_permissions.sh --verbose
```

### Issue: Inconsistent Test Results
If you encounter inconsistent test results:
```bash
# Clean test environment
rm -rf data/*
python -m src.main init --clean
```

## 13. Continuous Verification

For ongoing verification during development:

1. Run unit tests before committing changes:
   ```bash
   python -m tests.run_tests --unit
   ```

2. Run integration tests for affected components:
   ```bash
   python -m tests.run_tests --integration
   ```

3. Run edge case tests for modified functionality:
   ```bash
   python -m tests.edge_cases
   ```

4. Verify cross-platform compatibility for significant changes:
   ```bash
   ./scripts/verify_cross_platform.sh
   ```

This verification guide provides a comprehensive approach to validating CLI Kanban functionality. By following these procedures, you can ensure the system works correctly across various scenarios and environments.