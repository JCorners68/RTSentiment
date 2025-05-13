#!/usr/bin/env python
"""
Test runner for the Kanban CLI application.

This script allows running all tests or specific test categories, with
particular focus on evidence tests, which are part of the priority feature.
"""
import os
import sys
import unittest
import argparse
from pathlib import Path

# Add the parent directory to the path
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

def run_unit_tests():
    """Run all unit tests."""
    print("Running unit tests...")
    
    # Find all unit test modules
    unit_dir = Path(__file__).resolve().parent / 'unit'
    test_loader = unittest.TestLoader()
    suite = test_loader.discover(unit_dir, pattern='test_*.py')
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_integration_tests():
    """Run all integration tests."""
    print("Running integration tests...")
    
    # Find all integration test modules
    integration_dir = Path(__file__).resolve().parent / 'integration'
    test_loader = unittest.TestLoader()
    suite = test_loader.discover(integration_dir, pattern='test_*.py')
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def run_evidence_tests():
    """Run tests specifically for the Evidence Management System (priority feature)."""
    print("Running Evidence Management System tests (priority feature)...")
    
    test_loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add evidence-related unit tests
    unit_dir = Path(__file__).resolve().parent / 'unit'
    for module_name in ['test_validation', 'test_storage', 'test_commands']:
        module_path = unit_dir / f"{module_name}.py"
        if module_path.exists():
            module_tests = test_loader.loadTestsFromName(f"tests.unit.{module_name}")
            
            # Filter for evidence-related test classes
            for test_case in module_tests:
                for test in test_case:
                    # Include test cases that have 'evidence' in their name (case insensitive)
                    if 'evidence' in test.id().lower():
                        suite.addTest(test)
    
    # Add evidence-related integration tests
    integration_dir = Path(__file__).resolve().parent / 'integration'
    integration_tests = test_loader.loadTestsFromName("tests.integration.test_workflow")
    for test_case in integration_tests:
        for test in test_case:
            # Include test cases that have 'evidence' in their name (case insensitive)
            if 'evidence' in test.id().lower():
                suite.addTest(test)
    
    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

def main():
    """Main entry point for the test runner."""
    parser = argparse.ArgumentParser(description='Run Kanban CLI tests')
    parser.add_argument('--unit', action='store_true', help='Run only unit tests')
    parser.add_argument('--integration', action='store_true', help='Run only integration tests')
    parser.add_argument('--evidence', action='store_true', help='Run only evidence-related tests (priority feature)')
    
    args = parser.parse_args()
    
    # Track test success
    success = True
    
    # Run specified tests or all tests if no flags are provided
    if args.unit:
        success &= run_unit_tests()
    elif args.integration:
        success &= run_integration_tests()
    elif args.evidence:
        success &= run_evidence_tests()
    else:
        # Run all tests
        success &= run_unit_tests()
        success &= run_integration_tests()
    
    # Return exit code
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
