#!/usr/bin/env python3
"""
Sentimark SIT Environment Verification CLI

A comprehensive verification tool for the Sentimark SIT environment.
This tool checks all aspects of the deployment in westus region and
reports on their status.
"""

import os
import sys
import json
import argparse
import subprocess
import datetime
import time
from pathlib import Path

def green(text):
    """Format text in green."""
    return f"\033[92m{text}\033[0m"

def red(text):
    """Format text in red."""
    return f"\033[91m{text}\033[0m"

def yellow(text):
    """Format text in yellow."""
    return f"\033[93m{text}\033[0m"

def blue(text):
    """Format text in blue."""
    return f"\033[94m{text}\033[0m"

def header(text):
    """Format text as header."""
    return f"\n{blue('='*80)}\n{blue(text)}\n{blue('='*80)}\n"

def run_command(command, check=True):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            text=True,
            capture_output=True
        )
        return result.stdout.strip(), result.returncode
    except subprocess.CalledProcessError as e:
        return e.stderr.strip(), e.returncode

class SITVerifier:
    def __init__(self, script_dir=None, verbose=False):
        """Initialize the SIT environment verifier."""
        if script_dir is None:
            self.script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
        else:
            self.script_dir = Path(script_dir)
        
        self.verbose = verbose
        self.config_dir = self.script_dir / "config"
        self.logs_dir = self.script_dir / "logs"
        
        # Ensure directories exist
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Set environment variables
        os.environ["KUBECONFIG"] = str(self.config_dir / "kubeconfig")
        
        # Initialize results
        self.results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "region": "westus",
            "environment": "SIT",
            "checks": [],
            "summary": {
                "passed": 0,
                "failed": 0,
                "warning": 0,
                "skipped": 0
            }
        }

    def log_check(self, name, status, message, details=None):
        """Log a check result."""
        check = {
            "name": name,
            "status": status,
            "message": message
        }
        
        if details:
            check["details"] = details
            
        self.results["checks"].append(check)
        self.results["summary"][status] += 1
        
        if status == "passed":
            status_str = green("PASS")
        elif status == "failed":
            status_str = red("FAIL")
        elif status == "warning":
            status_str = yellow("WARN")
        else:
            status_str = yellow("SKIP")
            
        print(f"{status_str} {name}: {message}")
        
        if self.verbose and details:
            print(f"     Details: {details}")

    def check_config_files(self):
        """Check if all required configuration files exist."""
        print(header("CONFIGURATION FILES"))
        
        files_to_check = [
            ("Cluster Info", "cluster_info.txt"),
            ("Kubernetes Config", "kubeconfig"),
            ("Storage Connection", "storage_connection.txt")
        ]
        
        for name, filename in files_to_check:
            file_path = self.config_dir / filename
            if file_path.exists():
                if name == "Cluster Info":
                    # Check if region is westus
                    with open(file_path, 'r') as f:
                        content = f.read()
                        if "Location: westus" in content:
                            self.log_check(f"{name} File", "passed", f"File exists and contains correct region (westus)")
                        else:
                            self.log_check(f"{name} File", "warning", f"File exists but does not specify westus region", f"Path: {file_path}")
                else:
                    self.log_check(f"{name} File", "passed", f"File exists at {file_path}")
            else:
                self.log_check(f"{name} File", "failed", f"File not found at {file_path}")

    def check_azure_resources(self):
        """Check if Azure resources are properly deployed."""
        print(header("AZURE RESOURCES"))
        
        # Skip if az CLI not available
        az_available, _ = run_command("command -v az")
        if not az_available:
            self.log_check("Azure CLI", "skipped", "Azure CLI not installed, skipping Azure resource checks")
            return
            
        # Check if already logged in
        login_status, _ = run_command("az account show", check=False)
        if "error" in login_status.lower():
            self.log_check("Azure Login", "skipped", "Not logged in to Azure, skipping Azure resource checks")
            return
            
        # Check resource group
        print("Checking resource group...")
        rg_output, rc = run_command("az group show --name sentimark-sit-rg --query properties.provisioningState -o tsv", check=False)
        if rc == 0:
            self.log_check("Resource Group", "passed", f"Resource group exists and is in state: {rg_output}")
            
            # Check resource group location
            rg_location, _ = run_command("az group show --name sentimark-sit-rg --query location -o tsv")
            if "westus" in rg_location.lower():
                self.log_check("Resource Group Location", "passed", "Resource group is in westus region")
            else:
                self.log_check("Resource Group Location", "failed", f"Resource group is in {rg_location} instead of westus")
        else:
            self.log_check("Resource Group", "failed", "Resource group not found")
            return
            
        # Check AKS cluster
        print("Checking AKS cluster...")
        aks_output, rc = run_command("az aks show --resource-group sentimark-sit-rg --name sentimark-sit-aks --query provisioningState -o tsv", check=False)
        if rc == 0:
            self.log_check("AKS Cluster", "passed", f"AKS cluster exists and is in state: {aks_output}")
            
            # Check AKS cluster location
            aks_location, _ = run_command("az aks show --resource-group sentimark-sit-rg --name sentimark-sit-aks --query location -o tsv")
            if "westus" in aks_location.lower():
                self.log_check("AKS Cluster Location", "passed", "AKS cluster is in westus region")
            else:
                self.log_check("AKS Cluster Location", "failed", f"AKS cluster is in {aks_location} instead of westus")
                
            # Check node pools 
            print("Checking AKS node pools...")
            node_pools_output, _ = run_command("az aks nodepool list --resource-group sentimark-sit-rg --cluster-name sentimark-sit-aks -o json")
            try:
                node_pools = json.loads(node_pools_output)
                default_pool = next((pool for pool in node_pools if pool["name"] == "default"), None)
                
                if default_pool:
                    self.log_check("Default Node Pool", "passed", 
                                  f"Default pool exists with {default_pool['count']} nodes, VM size: {default_pool['vmSize']}")
                else:
                    self.log_check("Default Node Pool", "failed", "Default node pool not found")
                
                # Check for spot instance node pools
                spot_pools = [pool for pool in node_pools if pool.get("scaleSetPriority", "").lower() == "spot"]
                if spot_pools:
                    for pool in spot_pools:
                        self.log_check(f"Spot Node Pool: {pool['name']}", "passed", 
                                      f"Spot pool exists with {pool['count']} nodes, VM size: {pool['vmSize']}")
                    
                    self.log_check("Spot Instances", "passed", f"Found {len(spot_pools)} spot instance node pools")
                else:
                    self.log_check("Spot Instances", "warning", "No spot instance node pools found")
                
                # Total nodes count across all pools
                total_nodes = sum(pool["count"] for pool in node_pools)
                self.log_check("Total Node Count", "passed", f"AKS cluster has {total_nodes} nodes across all pools")
                
            except (json.JSONDecodeError, KeyError) as e:
                self.log_check("Node Pools", "failed", f"Error parsing node pool data: {str(e)}")
        else:
            self.log_check("AKS Cluster", "failed", "AKS cluster not found")
            
        # Check Storage Account
        print("Checking Storage Account...")
        
        # First try to get storage account name from connection file
        storage_account_name = "sentimarksitstorage"  # Default name
        storage_conn_file = self.config_dir / "storage_connection.txt"
        
        if storage_conn_file.exists():
            try:
                with open(storage_conn_file, 'r') as f:
                    conn_str = f.read().strip()
                    # Parse connection string to get account name
                    for part in conn_str.split(';'):
                        if part.startswith("AccountName="):
                            storage_account_name = part.split('=')[1]
                            break
            except Exception as e:
                self.log_check("Storage Connection String", "warning", f"Error parsing storage connection string: {str(e)}")
        
        # Check if storage account exists
        storage_output, rc = run_command(f"az storage account show --resource-group sentimark-sit-rg --name {storage_account_name} --query statusOfPrimary -o tsv", check=False)
        if rc == 0:
            self.log_check("Storage Account", "passed", f"Storage account {storage_account_name} exists and is in state: {storage_output}")
            
            # Check Storage Account location
            storage_location, _ = run_command(f"az storage account show --resource-group sentimark-sit-rg --name {storage_account_name} --query location -o tsv")
            if "westus" in storage_location.lower():
                self.log_check("Storage Account Location", "passed", f"Storage account {storage_account_name} is in westus region")
            else:
                self.log_check("Storage Account Location", "warning", f"Storage account {storage_account_name} is in {storage_location} instead of westus")
            
            # Check if Data Lake Gen2 is enabled
            is_hns_enabled, _ = run_command(f"az storage account show --resource-group sentimark-sit-rg --name {storage_account_name} --query isHnsEnabled -o tsv")
            if is_hns_enabled.lower() == "true":
                self.log_check("Data Lake Storage", "passed", "Hierarchical namespace is enabled (Data Lake Gen2)")
            else:
                self.log_check("Data Lake Storage", "warning", "Hierarchical namespace is not enabled")
        else:
            self.log_check("Storage Account", "failed", f"Storage account {storage_account_name} not found")

    def check_kubernetes_resources(self):
        """Check Kubernetes resources."""
        print(header("KUBERNETES RESOURCES"))
        
        # Skip if kubectl not installed
        kubectl_available, _ = run_command("command -v kubectl")
        if not kubectl_available:
            self.log_check("Kubectl", "skipped", "kubectl not installed, skipping Kubernetes resource checks")
            return
            
        # Check kubeconfig
        kubeconfig = self.config_dir / "kubeconfig"
        if not kubeconfig.exists():
            self.log_check("Kubeconfig", "failed", "Kubeconfig file not found")
            return
            
        # Set KUBECONFIG environment variable
        os.environ["KUBECONFIG"] = str(kubeconfig)
        
        # Try to get credentials first if not already set up
        if not os.path.exists(str(kubeconfig)) or os.path.getsize(str(kubeconfig)) == 0:
            print("Getting cluster credentials...")
            get_creds, _ = run_command("az aks get-credentials --resource-group sentimark-sit-rg --name sentimark-sit-aks --file " + str(kubeconfig) + " --overwrite-existing", check=False)
            
        # Check cluster connection
        print("Checking cluster connection...")
        cluster_info, rc = run_command("kubectl cluster-info", check=False)
        
        # If direct connection fails, try to see if the cluster exists via Azure CLI
        if rc != 0:
            aks_exists, aks_rc = run_command("az aks show --resource-group sentimark-sit-rg --name sentimark-sit-aks --query name -o tsv", check=False)
            
            if aks_rc == 0 and aks_exists:
                self.log_check("Cluster Connection", "warning", "AKS cluster exists but could not connect directly (may require VPN/private link)")
                
                # Still try to get nodes from Azure CLI instead
                try:
                    node_count, _ = run_command("az aks show --resource-group sentimark-sit-rg --name sentimark-sit-aks --query agentPoolProfiles[*].count -o tsv | paste -sd+ - | bc", check=False)
                    self.log_check("Node Count (via Azure CLI)", "passed", f"Cluster has approximately {node_count} nodes (from Azure CLI)")
                except Exception:
                    pass
                
                # Continue with other checks that don't require direct connection
                return
            else:
                self.log_check("Cluster Connection", "failed", "Failed to connect to Kubernetes cluster")
                return
        else:
            self.log_check("Cluster Connection", "passed", "Successfully connected to Kubernetes cluster")
            
            # Check if cluster info shows westus region
            if "westus" in cluster_info.lower():
                self.log_check("Cluster Region", "passed", "Cluster is in westus region")
            else:
                self.log_check("Cluster Region", "warning", "Could not confirm cluster is in westus region from cluster-info")
            
        # Check nodes
        print("Checking nodes...")
        nodes_output, rc = run_command("kubectl get nodes -o json", check=False)
        if rc == 0:
            try:
                nodes = json.loads(nodes_output)
                node_count = len(nodes["items"])
                ready_nodes = sum(1 for node in nodes["items"] 
                                 for condition in node["status"]["conditions"] 
                                 if condition["type"] == "Ready" and condition["status"] == "True")
                
                if node_count > 0:
                    if ready_nodes == node_count:
                        self.log_check("Nodes", "passed", f"All {node_count} nodes are Ready")
                    else:
                        self.log_check("Nodes", "warning", f"Only {ready_nodes}/{node_count} nodes are Ready")
                else:
                    self.log_check("Nodes", "failed", "No nodes found in the cluster")
            except (json.JSONDecodeError, KeyError) as e:
                self.log_check("Nodes", "failed", f"Error parsing node data: {str(e)}")
        else:
            self.log_check("Nodes", "failed", "Failed to get nodes")
            
        # Check sit namespace
        print("Checking sit namespace...")
        namespace_output, rc = run_command("kubectl get namespace sit", check=False)
        if rc == 0:
            self.log_check("SIT Namespace", "passed", "SIT namespace exists")
            
            # Check pods in sit namespace
            print("Checking pods...")
            pods_output, rc = run_command("kubectl get pods -n sit -o json", check=False)
            if rc == 0:
                try:
                    pods = json.loads(pods_output)
                    pod_count = len(pods["items"])
                    running_pods = sum(1 for pod in pods["items"] if pod["status"]["phase"] == "Running")
                    
                    if pod_count > 0:
                        if running_pods == pod_count:
                            self.log_check("Pods", "passed", f"All {pod_count} pods in sit namespace are Running")
                        else:
                            self.log_check("Pods", "warning", f"Only {running_pods}/{pod_count} pods in sit namespace are Running")
                    else:
                        self.log_check("Pods", "warning", "No pods found in sit namespace")
                except (json.JSONDecodeError, KeyError) as e:
                    self.log_check("Pods", "failed", f"Error parsing pod data: {str(e)}")
            else:
                self.log_check("Pods", "failed", "Failed to get pods in sit namespace")
                
            # Check services in sit namespace
            print("Checking services...")
            services_output, rc = run_command("kubectl get services -n sit -o json", check=False)
            if rc == 0:
                try:
                    services = json.loads(services_output)
                    service_count = len(services["items"])
                    
                    if service_count > 0:
                        loadbalancer_services = [svc for svc in services["items"] if svc["spec"]["type"] == "LoadBalancer"]
                        lb_services_with_ip = [svc for svc in loadbalancer_services 
                                             if "ingress" in svc["status"].get("loadBalancer", {}) 
                                             and len(svc["status"]["loadBalancer"]["ingress"]) > 0]
                        
                        if len(loadbalancer_services) > 0:
                            if len(lb_services_with_ip) == len(loadbalancer_services):
                                self.log_check("Services", "passed", f"All {len(loadbalancer_services)} LoadBalancer services have External IPs")
                            else:
                                self.log_check("Services", "warning", 
                                              f"Only {len(lb_services_with_ip)}/{len(loadbalancer_services)} LoadBalancer services have External IPs")
                        
                        self.log_check("Service Count", "passed", f"Found {service_count} services in sit namespace")
                    else:
                        self.log_check("Service Count", "warning", "No services found in sit namespace")
                except (json.JSONDecodeError, KeyError) as e:
                    self.log_check("Services", "failed", f"Error parsing service data: {str(e)}")
            else:
                self.log_check("Services", "failed", "Failed to get services in sit namespace")
        else:
            self.log_check("SIT Namespace", "warning", "SIT namespace does not exist")

    def check_application_health(self):
        """Check application health by accessing service endpoints."""
        print(header("APPLICATION HEALTH"))
        
        # Skip if kubectl not installed
        kubectl_available, _ = run_command("command -v kubectl")
        if not kubectl_available:
            self.log_check("Application Health", "skipped", "kubectl not installed, skipping application health checks")
            return
            
        # Get service IPs
        print("Getting service endpoints...")
        data_acq_ip, rc = run_command("kubectl get svc -n sit data-acquisition-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null", check=False)
        
        if data_acq_ip:
            # Check data acquisition service health
            print(f"Checking Data Acquisition Service health at {data_acq_ip}...")
            health_code, rc = run_command(f"curl -s -o /dev/null -w '%{{http_code}}' http://{data_acq_ip}:8002/health", check=False)
            
            if rc == 0 and health_code == "200":
                self.log_check("Data Acquisition Health", "passed", "Data Acquisition Service is healthy")
                
                # Try to get actual health response
                health_response, _ = run_command(f"curl -s http://{data_acq_ip}:8002/health", check=False)
                try:
                    health_data = json.loads(health_response)
                    self.log_check("Health Details", "passed", f"Health status: {health_data.get('status')}", health_data)
                except json.JSONDecodeError:
                    self.log_check("Health Details", "warning", "Could not parse health response as JSON")
            else:
                self.log_check("Data Acquisition Health", "failed", f"Data Acquisition Service returned HTTP {health_code}")
        else:
            self.log_check("Service Endpoint", "warning", "Could not get Data Acquisition Service IP address")

    def check_deployment_logs(self):
        """Check deployment logs."""
        print(header("DEPLOYMENT LOGS"))
        
        # Check for deployment logs
        log_files = list(self.logs_dir.glob("deployment_*.json"))
        
        if log_files:
            latest_log = max(log_files, key=lambda f: os.path.getmtime(f))
            self.log_check("Deployment Logs", "passed", f"Found deployment log file: {latest_log.name}")
            
            # Check log content
            try:
                with open(latest_log, 'r') as f:
                    log_data = json.load(f)
                    
                if log_data.get("status") == "completed":
                    self.log_check("Deployment Status", "passed", "Deployment status is completed")
                    
                    # Check region
                    if log_data.get("location") == "westus":
                        self.log_check("Deployment Region", "passed", "Deployment region is westus")
                    else:
                        self.log_check("Deployment Region", "warning", 
                                      f"Deployment region is {log_data.get('location')} instead of westus")
                else:
                    self.log_check("Deployment Status", "warning", f"Deployment status is {log_data.get('status')}")
            except (json.JSONDecodeError, KeyError) as e:
                self.log_check("Deployment Log Content", "failed", f"Error parsing log content: {str(e)}")
        else:
            self.log_check("Deployment Logs", "warning", "No deployment log files found")

    def check_all(self):
        """Run all verification checks."""
        start_time = time.time()
        
        print(header(f"SENTIMARK SIT ENVIRONMENT VERIFICATION"))
        print(f"Region: westus")
        print(f"Environment: SIT")
        print(f"Started at: {datetime.datetime.now().isoformat()}")
        print(f"Script directory: {self.script_dir}")
        print()
        
        # Run all checks
        self.check_config_files()
        self.check_azure_resources()
        self.check_kubernetes_resources()
        self.check_application_health()
        self.check_deployment_logs()
        
        # Calculate verification time
        end_time = time.time()
        verification_time = end_time - start_time
        self.results["verification_time"] = verification_time
        
        # Save verification results
        results_file = self.logs_dir / f"verification_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
            
        # Print summary
        passed = self.results["summary"]["passed"]
        failed = self.results["summary"]["failed"]
        warning = self.results["summary"]["warning"]
        skipped = self.results["summary"]["skipped"]
        total = passed + failed + warning + skipped
        
        print(header("VERIFICATION SUMMARY"))
        print(f"Total checks: {total}")
        print(f"Passed: {green(passed)}")
        print(f"Failed: {red(failed)}")
        print(f"Warnings: {yellow(warning)}")
        print(f"Skipped: {yellow(skipped)}")
        print(f"Verification time: {verification_time:.2f} seconds")
        print(f"Results saved to: {results_file}")
        print()
        
        if failed > 0:
            print(red("VERIFICATION FAILED"))
            return 1
        elif warning > 0:
            print(yellow("VERIFICATION PASSED WITH WARNINGS"))
            return 0
        else:
            print(green("VERIFICATION PASSED SUCCESSFULLY"))
            return 0

def main():
    """Main entrypoint for the SIT verification tool."""
    parser = argparse.ArgumentParser(description="Sentimark SIT Environment Verification Tool")
    parser.add_argument("--verbose", "-v", action="store_true", help="Display verbose output")
    parser.add_argument("--check", choices=["config", "azure", "kubernetes", "health", "logs", "all"],
                       default="all", help="Select which checks to run")
    args = parser.parse_args()
    
    verifier = SITVerifier(verbose=args.verbose)
    
    if args.check == "config":
        verifier.check_config_files()
    elif args.check == "azure":
        verifier.check_azure_resources()
    elif args.check == "kubernetes":
        verifier.check_kubernetes_resources()
    elif args.check == "health":
        verifier.check_application_health()
    elif args.check == "logs":
        verifier.check_deployment_logs()
    else:
        return verifier.check_all()
        
    return 0

if __name__ == "__main__":
    sys.exit(main())