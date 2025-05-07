#!/usr/bin/env python3
"""
SIT Environment Configuration Consistency Test

This script verifies that all configuration files use consistent settings
for resource names, regions, and other critical parameters.
"""
import unittest
import os
import re
from pathlib import Path


class ConfigConsistencyTest(unittest.TestCase):
    """Test suite for verifying configuration consistency."""

    def setUp(self):
        """Set up the test environment by locating configuration files."""
        self.script_dir = Path(__file__).parent.parent.absolute()
        self.repo_root = self.script_dir.parent.parent.absolute()
        
        self.deploy_script_path = self.script_dir / "deploy_azure_sit.sh"
        self.verify_script_path = self.script_dir / "verify_deployment.sh"
        self.python_verify_script_path = self.script_dir / "sentimark_sit_verify.py"
        self.terraform_vars_path = self.repo_root / "infrastructure" / "terraform" / "azure" / "terraform.sit.tfvars"
        
        # Check if files exist
        for path in [self.deploy_script_path, self.terraform_vars_path, self.python_verify_script_path]:
            self.assertTrue(
                path.exists(), 
                f"Required file not found: {path}"
            )

    def extract_from_shell_script(self, file_path, variable_name):
        """Extract a variable value from a shell script."""
        with open(file_path, 'r') as f:
            content = f.read()
            
        pattern = rf'{variable_name}="([^"]+)"'
        match = re.search(pattern, content)
        if match:
            return match.group(1)
        return None

    def extract_from_terraform_vars(self, file_path, variable_name):
        """Extract a variable value from a Terraform variables file."""
        with open(file_path, 'r') as f:
            content = f.read()
            
        pattern = rf'{variable_name}\s*=\s*"([^"]+)"'
        match = re.search(pattern, content)
        if match:
            return match.group(1)
        return None

    def extract_from_python_script(self, file_path, variable_name):
        """Extract a variable value from a Python script."""
        with open(file_path, 'r') as f:
            content = f.read()
            
        pattern = rf'"{variable_name}"\s*:\s*"([^"]+)"'
        match = re.search(pattern, content)
        if match:
            return match.group(1)
        
        # Try alternate format
        pattern = rf'{variable_name}\s*=\s*"([^"]+)"'
        match = re.search(pattern, content)
        if match:
            return match.group(1)
        
        return None

    def test_region_consistency(self):
        """Test that region is consistent across all files."""
        deploy_region = self.extract_from_shell_script(self.deploy_script_path, "LOCATION")
        tf_region = self.extract_from_terraform_vars(self.terraform_vars_path, "location")
        
        # Extract from Python verification file
        py_region = "westus"  # Default
        with open(self.python_verify_script_path, 'r') as f:
            content = f.read()
            region_match = re.search(r'"region"\s*:\s*"([^"]+)"', content)
            if region_match:
                py_region = region_match.group(1)
        
        self.assertIsNotNone(deploy_region, "Region not found in deployment script")
        self.assertIsNotNone(tf_region, "Region not found in Terraform variables")
        
        self.assertEqual(
            deploy_region, tf_region, 
            f"Region mismatch: deploy script ({deploy_region}) vs Terraform vars ({tf_region})"
        )
        self.assertEqual(
            deploy_region, py_region, 
            f"Region mismatch: deploy script ({deploy_region}) vs Python verify ({py_region})"
        )

    def test_resource_group_consistency(self):
        """Test that resource group name is consistent across files."""
        deploy_rg = self.extract_from_shell_script(self.deploy_script_path, "RESOURCE_GROUP")
        tf_rg = self.extract_from_terraform_vars(self.terraform_vars_path, "resource_group_name")
        
        self.assertIsNotNone(deploy_rg, "Resource group not found in deployment script")
        self.assertIsNotNone(tf_rg, "Resource group not found in Terraform variables")
        
        self.assertEqual(
            deploy_rg, tf_rg, 
            f"Resource group mismatch: deploy script ({deploy_rg}) vs Terraform vars ({tf_rg})"
        )

    def test_aks_cluster_consistency(self):
        """Test that AKS cluster name is consistent across files."""
        deploy_aks = self.extract_from_shell_script(self.deploy_script_path, "AKS_CLUSTER")
        tf_aks = self.extract_from_terraform_vars(self.terraform_vars_path, "aks_cluster_name")
        
        self.assertIsNotNone(deploy_aks, "AKS cluster name not found in deployment script")
        self.assertIsNotNone(tf_aks, "AKS cluster name not found in Terraform variables")
        
        self.assertEqual(
            deploy_aks, tf_aks, 
            f"AKS cluster name mismatch: deploy script ({deploy_aks}) vs Terraform vars ({tf_aks})"
        )

    def test_terraform_variables_best_practices(self):
        """Test that Terraform variables follow best practices for SIT environment."""
        with open(self.terraform_vars_path, 'r') as f:
            content = f.read()
            
        # Check availability zones are disabled
        self.assertIn('enable_aks_availability_zones = false', content, 
                      "AKS availability zones should be disabled in westus region")
                      
        # Check policy assignments are disabled
        self.assertIn('enable_policy_assignments = false', content, 
                     "Policy assignments should be disabled for SIT environment")
                     
        # Check container deployment is disabled
        self.assertIn('deploy_container = false', content, 
                     "Container deployment should be disabled for SIT environment")


if __name__ == "__main__":
    unittest.main()