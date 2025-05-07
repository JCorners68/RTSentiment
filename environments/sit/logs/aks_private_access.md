# Accessing Private AKS Clusters

This guide describes the recommended approach for interacting with private AKS clusters without requiring DNS resolution or VPN connections from your local machine.

## Why az aks command invoke?

Azure provides a powerful feature that allows you to execute commands inside your AKS cluster directly through the Azure API. This approach:

1. **Maintains complete isolation** from your local Windows environment
2. **Eliminates DNS resolution issues** with private AKS endpoints
3. **Avoids complex VPN configurations** and split-tunnel complexity
4. **Works with minimal setup** - just requires Azure CLI
5. **Provides secure access** through Azure RBAC, no need to expose your cluster publicly

## Setup

1. Ensure you have Azure CLI installed and are logged in:
   ```bash
   az login
   ```

2. Make the scripts executable:
   ```bash
   chmod +x aks_command.sh helm_deploy.sh
   ```

## Usage Examples

### Basic kubectl commands:

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

### Helm operations:

```bash
# List all Helm releases
./aks_command.sh helm list -A

# Deploy the Sentimark services using our script
./helm_deploy.sh
```

## How It Works

The `az aks command invoke` feature works by:

1. Establishing a secure connection to your AKS cluster through the Azure API
2. Running the command in a temporary pod in the kube-system namespace
3. Streaming the results back to your terminal

This approach doesn't require:
- DNS resolution for the private AKS endpoint
- Direct network connectivity to the AKS API server
- VPN connections or network configuration changes

## Advanced Use Cases

### Working with files:

For operations that require files (like applying manifests), there are several options:

1. **Use ConfigMaps or Secrets** to store the file content
2. **Create a jumpbox pod** in the cluster for more complex operations
3. **Set up a private Azure Container Registry** for Helm charts and container images

Our `helm_deploy.sh` script demonstrates the jumpbox pod approach.

## Alternative Approaches

If you need broader network connectivity to Azure resources (beyond just AKS), consider:

1. **Running a VPN client inside WSL2**: Maintains isolation from Windows while providing full connectivity to Azure VNet
2. **Using a jumpbox VM in Azure**: SSH into a VM in the same VNet as your AKS cluster
3. **Azure Bastion**: Connect to VMs in your VNet using the Azure Portal

## Troubleshooting

If you encounter issues with `az aks command invoke`:

1. Ensure you have the proper RBAC permissions (Contributor or Owner role)
2. Verify that you're using the latest version of Azure CLI
3. Check if the AKS cluster has the Command feature enabled
4. For timeout issues, consider specifying a longer timeout: `--timeout 5m`