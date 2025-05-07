# Accessing Private AKS Clusters

This guide describes the recommended approach for interacting with private AKS clusters without requiring DNS resolution or VPN connections from your local machine.

## Overview

The Sentimark SIT environment uses a private AKS cluster to enhance security. However, this presents challenges when accessing the cluster from development machines due to DNS resolution issues with the private endpoint (`rt-sentiment-pu1l2xsk.e0a6a092-8322-4fa7-84a5-8b90d32afcb2.privatelink.westus.azmk8s.io`).

## Solution: az aks command invoke

Azure provides a powerful feature that allows you to execute commands inside your AKS cluster directly through the Azure API. This approach:

1. **Maintains complete isolation** from your local Windows environment
2. **Eliminates DNS resolution issues** with private AKS endpoints
3. **Avoids complex VPN configurations** and split-tunnel complexity
4. **Works with minimal setup** - just requires Azure CLI
5. **Provides secure access** through Azure RBAC, no need to expose your cluster publicly

## Prerequisites

- Azure CLI installed and configured
- Appropriate RBAC permissions on the AKS cluster (Contributor or Owner role)

## Setup Instructions

1. Ensure you have Azure CLI installed and are logged in:
   ```bash
   az login
   ```

2. Make the provided scripts executable:
   ```bash
   cd /home/jonat/real_senti/environments/sit
   chmod +x aks_command.sh helm_deploy.sh
   ```

## Usage Examples

### Basic kubectl commands

Run the `aks_command.sh` script followed by the kubectl command you want to execute:

```bash
# List nodes in the cluster
./aks_command.sh kubectl get nodes

# Get all pods across all namespaces
./aks_command.sh kubectl get pods -A

# Deploy a manifest
./aks_command.sh kubectl apply -f /path/to/manifest.yaml

# Get detailed info about the cluster
./aks_command.sh kubectl cluster-info dump
```

### Helm operations

For Helm deployments, use the `helm_deploy.sh` script:

```bash
# Deploy using the Helm charts
./helm_deploy.sh
```

This script follows idempotence principles by:
- Using temporary files that are cleaned up after execution
- Not creating persistent resources in the cluster
- Properly logging all actions and results

## How It Works

The `az aks command invoke` feature works by:

1. Establishing a secure connection to your AKS cluster through the Azure API
2. Running the command in a temporary pod in the kube-system namespace
3. Streaming the results back to your terminal

This approach doesn't require:
- DNS resolution for the private AKS endpoint
- Direct network connectivity to the AKS API server
- VPN connections or network configuration changes

## Troubleshooting

If you encounter issues with `az aks command invoke`:

1. Ensure you have the proper RBAC permissions (Contributor or Owner role)
2. Verify that you're using the latest version of Azure CLI:
   ```bash
   az --version
   az upgrade
   ```
3. For timeout issues, consider specifying a longer timeout:
   ```bash
   az aks command invoke --timeout 5m --resource-group sentimark-sit-rg --name sentimark-sit-aks --command "kubectl get pods -A"
   ```
4. If you're seeing permission errors, verify your Azure role assignments:
   ```bash
   az role assignment list --assignee <your-email> --resource-group sentimark-sit-rg
   ```

## Alternative Approaches

For situations where `az aks command invoke` is not suitable:

1. **Azure Cloud Shell**: Has built-in access to private AKS endpoints
2. **VPN to Azure**: Connect to the Azure VNet where the AKS cluster is deployed
3. **Jump Box VM**: Deploy a VM in the same VNet and connect to it via SSH

## References

- [Azure AKS Documentation](https://docs.microsoft.com/en-us/azure/aks/)
- [az aks command invoke](https://docs.microsoft.com/en-us/cli/azure/aks/command?view=azure-cli-latest#az-aks-command-invoke)
- [Private AKS Clusters](https://docs.microsoft.com/en-us/azure/aks/private-clusters)