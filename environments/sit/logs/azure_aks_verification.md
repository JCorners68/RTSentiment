# Verifying AKS Deployment via Azure Cloud Shell

To verify the SIT environment deployment quickly, use Azure Cloud Shell in the portal:

1. Open the [Azure Portal](https://portal.azure.com)
2. Click the Cloud Shell icon in the top navigation bar
3. Select "Bash" environment
4. Run these commands to verify the deployment:

```bash
# Verify resource group
az group show --name sentimark-sit-rg --query properties.provisioningState -o tsv

# Verify AKS cluster
az aks show --resource-group sentimark-sit-rg --name sentimark-sit-aks --query provisioningState -o tsv

# Verify node pools (including spot instances)
az aks nodepool list --resource-group sentimark-sit-rg --cluster-name sentimark-sit-aks -o table

# Connect to the cluster
az aks get-credentials --resource-group sentimark-sit-rg --name sentimark-sit-aks

# List Kubernetes nodes 
kubectl get nodes

# Check the workloads
kubectl get pods -A
```

The Cloud Shell has direct access to the private AKS endpoint, so you won't encounter DNS resolution issues.