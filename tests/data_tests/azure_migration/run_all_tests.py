#!/usr/bin/env python3
"""
Master UAT test script for Phase 4 Azure migration.

This script runs all the Phase 4 test steps in sequence:
1. Azure Blob Storage setup
2. Dremio JDBC connection with Azure
3. Parquet to Iceberg migration
4. Migration validation
"""
import os
import sys
import json
import time
import logging
import argparse
import subprocess
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime


def setup_logging(verbose: bool = False) -> None:
    """
    Set up logging configuration.
    
    Args:
        verbose: Whether to enable verbose logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load configuration from {config_path}: {str(e)}")
        sys.exit(1)


def run_test_script(script_path: str, args: List[str]) -> Tuple[bool, str]:
    """
    Run a test script and return the result.
    
    Args:
        script_path: Path to the test script
        args: Command line arguments
        
    Returns:
        Tuple[bool, str]: (success, output)
    """
    cmd = [sys.executable, script_path] + args
    logging.info(f"Running: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        output = []
        for line in process.stdout:
            line = line.rstrip()
            output.append(line)
            print(line)
            
        process.wait()
        success = process.returncode == 0
        
        if success:
            logging.info(f"✅ Test script {os.path.basename(script_path)} completed successfully")
        else:
            logging.error(f"❌ Test script {os.path.basename(script_path)} failed with code {process.returncode}")
            
        return success, "\n".join(output)
        
    except Exception as e:
        logging.error(f"Failed to run test script {script_path}: {str(e)}")
        return False, str(e)


def create_report_dir(output_dir: str) -> str:
    """
    Create a report directory for this test run.
    
    Args:
        output_dir: Base output directory
        
    Returns:
        str: Path to the report directory
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = os.path.join(output_dir, f"test_run_{timestamp}")
    
    try:
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
            logging.info(f"Created report directory: {report_dir}")
    except Exception as e:
        logging.error(f"Failed to create report directory {report_dir}: {str(e)}")
        sys.exit(1)
        
    return report_dir


def save_test_report(
    report_dir: str,
    test_results: Dict[str, Dict[str, Any]]
) -> str:
    """
    Save a consolidated test report.
    
    Args:
        report_dir: Path to the report directory
        test_results: Dictionary of test results
        
    Returns:
        str: Path to the report file
    """
    report_file = os.path.join(report_dir, "test_report.json")
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "overall_success": all(result["success"] for result in test_results.values()),
        "tests": test_results
    }
    
    try:
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        logging.info(f"Saved test report to: {report_file}")
    except Exception as e:
        logging.error(f"Failed to save test report: {str(e)}")
        
    return report_file


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Master UAT test script for Phase 4 Azure migration')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--ticker', help='Ticker to migrate (migrates all tickers if not specified)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--skip-steps', type=str, help='Comma-separated list of steps to skip (1-4)')
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Determine the config path
    if not os.path.isabs(args.config):
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), args.config))
    else:
        config_path = args.config
        
    # Load configuration
    config = load_config(config_path)
    
    # Create report directory
    output_dir = config["test"]["output_dir"]
    report_dir = create_report_dir(output_dir)
    
    # Update config to use the report directory for output
    config["test"]["output_dir"] = report_dir
    
    # Save updated config
    updated_config_path = os.path.join(report_dir, "config.json")
    with open(updated_config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    # Determine which steps to skip
    skip_steps = []
    if args.skip_steps:
        skip_steps = [int(step.strip()) for step in args.skip_steps.split(",")]
    
    # Track test results
    test_results = {}
    
    # Step 1: Azure Blob Storage setup
    if 1 not in skip_steps:
        logging.info("\n=== Step 1: Azure Blob Storage setup ===")
        script_path = os.path.join(os.path.dirname(__file__), "test_azure_setup.py")
        script_args = ["--config", updated_config_path]
        if args.verbose:
            script_args.append("--verbose")
            
        success, output = run_test_script(script_path, script_args)
        test_results["azure_setup"] = {
            "success": success,
            "output": output
        }
        
        if not success and not args.skip_steps:
            logging.error("Azure Blob Storage setup failed. Stopping tests.")
            save_test_report(report_dir, test_results)
            sys.exit(1)
    
    # Step 2: Dremio JDBC connection with Azure
    if 2 not in skip_steps:
        logging.info("\n=== Step 2: Dremio JDBC connection with Azure ===")
        script_path = os.path.join(os.path.dirname(__file__), "test_dremio_azure_connection.py")
        script_args = ["--config", updated_config_path]
        if args.verbose:
            script_args.append("--verbose")
            
        success, output = run_test_script(script_path, script_args)
        test_results["dremio_connection"] = {
            "success": success,
            "output": output
        }
        
        if not success and not args.skip_steps:
            logging.error("Dremio JDBC connection test failed. Stopping tests.")
            save_test_report(report_dir, test_results)
            sys.exit(1)
    
    # Step 3: Parquet to Iceberg migration
    if 3 not in skip_steps:
        logging.info("\n=== Step 3: Parquet to Iceberg migration ===")
        script_path = os.path.join(os.path.dirname(__file__), "test_parquet_migration.py")
        script_args = ["--config", updated_config_path]
        if args.ticker:
            script_args.extend(["--ticker", args.ticker])
        if args.verbose:
            script_args.append("--verbose")
            
        success, output = run_test_script(script_path, script_args)
        test_results["parquet_migration"] = {
            "success": success,
            "output": output
        }
        
        if not success and not args.skip_steps:
            logging.error("Parquet migration test failed. Stopping tests.")
            save_test_report(report_dir, test_results)
            sys.exit(1)
    
    # Step 4: Migration validation
    if 4 not in skip_steps and args.ticker:
        logging.info("\n=== Step 4: Migration validation ===")
        script_path = os.path.join(os.path.dirname(__file__), "test_validation.py")
        
        # Determine the Parquet file path
        parquet_file = os.path.join(config["test"]["parquet_dir"], f"{args.ticker}_sentiment.parquet")
        
        script_args = ["--config", updated_config_path, "--parquet-file", parquet_file]
        if args.verbose:
            script_args.append("--verbose")
            
        success, output = run_test_script(script_path, script_args)
        test_results["migration_validation"] = {
            "success": success,
            "output": output
        }
    
    # Save consolidated test report
    report_file = save_test_report(report_dir, test_results)
    
    # Print overall results
    overall_success = all(result["success"] for result in test_results.values())
    
    if overall_success:
        print("\n✅ All UAT tests passed successfully!")
        print(f"\nTest report saved to: {report_file}")
        print("\nTo complete verification, please check the following:")
        print("1. Review the test reports in the output directory")
        print("2. Log in to Dremio UI and verify the migrated data")
        print("3. Run sample queries in Dremio to verify the data is correct")
        sys.exit(0)
    else:
        print("\n❌ Some UAT tests failed. Please check the test report and logs.")
        print(f"\nTest report saved to: {report_file}")
        sys.exit(1)


if __name__ == '__main__':
    main()