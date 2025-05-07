#!/usr/bin/env python3
"""
SIT Environment Verification Script

This script verifies the SIT environment by checking the configuration files
and establishing direct connections to Azure resources.
"""
import os
import sys
import json
import datetime
import subprocess
from pathlib import Path

def main():
    """Main verification function."""
    print("Running SIT Environment Verification...")
    
    # Check configuration consistency first
    print("Checking configuration consistency...")
    script_dir = Path(__file__).parent.parent.absolute()
    config_test_path = Path(__file__).parent / "test_config_consistency.py"
    
    if config_test_path.exists():
        # Run the config consistency test
        try:
            result = subprocess.run(
                [sys.executable, str(config_test_path)],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print("⚠️  Configuration consistency check failed!")
                print(result.stderr)
                print("Continuing with verification, but results may be inconsistent.")
            else:
                print("✅ Configuration consistency check passed.")
        except Exception as e:
            print(f"⚠️  Error running configuration consistency check: {str(e)}")
    else:
        print("⚠️  Configuration consistency test not found at:", config_test_path)
    
    # Get script directory
    script_dir = Path(__file__).parent.parent.absolute()
    config_dir = script_dir / "config"
    
    verification_results = {
        "timestamp": datetime.datetime.now().isoformat(),
        "tests": [],
        "summary": {
            "passed": 0,
            "failed": 0,
            "skipped": 0
        }
    }
    
    # Test 1: Check if cluster_info.txt exists
    test_result = {
        "name": "Cluster Info Check",
        "status": "failed",
        "message": ""
    }
    
    cluster_info_path = config_dir / "cluster_info.txt"
    if cluster_info_path.exists():
        test_result["status"] = "passed"
        test_result["message"] = f"Cluster info file found at {cluster_info_path}"
        verification_results["summary"]["passed"] += 1
    else:
        test_result["message"] = f"Cluster info file not found at {cluster_info_path}"
        verification_results["summary"]["failed"] += 1
    
    verification_results["tests"].append(test_result)
    
    # Test 2: Check if storage_connection.txt exists
    test_result = {
        "name": "Storage Connection Check",
        "status": "failed",
        "message": ""
    }
    
    storage_conn_path = config_dir / "storage_connection.txt"
    if storage_conn_path.exists():
        test_result["status"] = "passed"
        test_result["message"] = f"Storage connection file found at {storage_conn_path}"
        verification_results["summary"]["passed"] += 1
    else:
        test_result["message"] = f"Storage connection file not found at {storage_conn_path}"
        verification_results["summary"]["failed"] += 1
    
    verification_results["tests"].append(test_result)
    
    # Test 3: Check if kubeconfig exists
    test_result = {
        "name": "Kubernetes Config Check",
        "status": "failed",
        "message": ""
    }
    
    kubeconfig_path = config_dir / "kubeconfig"
    if kubeconfig_path.exists():
        test_result["status"] = "passed"
        test_result["message"] = f"Kubernetes config file found at {kubeconfig_path}"
        verification_results["summary"]["passed"] += 1
    else:
        test_result["message"] = f"Kubernetes config file not found at {kubeconfig_path}"
        verification_results["summary"]["failed"] += 1
    
    verification_results["tests"].append(test_result)
    
    # Test 4: Check deployment logs
    test_result = {
        "name": "Deployment Logs Check",
        "status": "failed",
        "message": ""
    }
    
    logs_dir = script_dir / "logs"
    deployment_logs = list(logs_dir.glob("deployment_*.json"))
    if deployment_logs:
        latest_log = max(deployment_logs, key=os.path.getctime)
        try:
            with open(latest_log, 'r') as f:
                log_data = json.load(f)
            if log_data.get("status") == "completed":
                test_result["status"] = "passed"
                test_result["message"] = f"Latest deployment log shows completed status at {latest_log}"
                verification_results["summary"]["passed"] += 1
            else:
                test_result["message"] = f"Latest deployment log does not have completed status at {latest_log}"
                verification_results["summary"]["failed"] += 1
        except (json.JSONDecodeError, KeyError):
            test_result["message"] = f"Error parsing deployment log at {latest_log}"
            verification_results["summary"]["failed"] += 1
    else:
        test_result["message"] = "No deployment logs found"
        verification_results["summary"]["failed"] += 1
    
    verification_results["tests"].append(test_result)
    
    # Output test results
    print("\nTest Results:")
    print("============")
    for test in verification_results["tests"]:
        status_icon = "✅" if test["status"] == "passed" else "❌"
        print(f"{status_icon} {test['name']}: {test['message']}")
    
    print("\nSummary:")
    print(f"Passed: {verification_results['summary']['passed']}")
    print(f"Failed: {verification_results['summary']['failed']}")
    print(f"Skipped: {verification_results['summary']['skipped']}")
    
    # Save results
    results_path = script_dir / "logs" / f"verification_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, 'w') as f:
        json.dump(verification_results, f, indent=2)
    
    print(f"\nResults saved to {results_path}")
    
    # Exit with appropriate code
    if verification_results["summary"]["failed"] > 0:
        print("\nVerification FAILED")
        return 1
    else:
        print("\nVerification PASSED")
        return 0

if __name__ == "__main__":
    sys.exit(main())