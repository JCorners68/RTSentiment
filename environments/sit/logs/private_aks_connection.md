# Connecting to Private AKS Cluster in SIT Environment

## DNS Resolution Issue

The AKS cluster in the SIT environment is deployed with private endpoint access, which means:

- The Kubernetes API server has a private FQDN: `rt-sentiment-pu1l2xsk.e0a6a092-8322-4fa7-84a5-8b90d32afcb2.privatelink.westus.azmk8s.io`
- This hostname resolves only within the Azure VNet or when properly connected through VPN/ExpressRoute

## Connection Methods

### Option 1: Access via Jump Box (Recommended)

1. SSH into a jump box VM within the Azure VNet
2. Run kubectl commands from the jump box
3. The jump box will have proper DNS resolution for the private AKS endpoint

Example:
```bash
# Copy kubeconfig to jump box
scp /home/jonat/real_senti/environments/sit/config/kubeconfig azure-user@jump-box-ip:~/kubeconfig

# SSH to jump box
ssh azure-user@jump-box-ip

# Use kubectl on jump box
export KUBECONFIG=~/kubeconfig
kubectl get nodes
```

### Option 2: VPN Connection

1. Configure Azure Point-to-Site VPN or Site-to-Site VPN
2. Ensure DNS settings are configured to resolve Azure private endpoints
3. Connect to VPN before running kubectl commands

### Option 3: DNS Configuration (For Development)

If you need to access the cluster from your development machine, modify DNS settings:

1. Find the private IP of the AKS API server
```bash
az network private-endpoint show --name aks-pe --resource-group sentimark-sit-rg --query 'customDnsConfigs[0].ipAddresses[0]' -o tsv
```

2. Add entry to your hosts file
```
<private-ip> rt-sentiment-pu1l2xsk.e0a6a092-8322-4fa7-84a5-8b90d32afcb2.privatelink.westus.azmk8s.io
```

## AKS Status Verification

When direct kubectl access isn't available, you can still verify cluster status via Azure CLI:

```bash
# Check cluster status
az aks show --resource-group sentimark-sit-rg --name sentimark-sit-aks --query provisioningState

# List node pools
az aks nodepool list --resource-group sentimark-sit-rg --cluster-name sentimark-sit-aks -o table

# Get node count
az aks show --resource-group sentimark-sit-rg --name sentimark-sit-aks --query agentPoolProfiles[*].count
```

## Spot Instance Node Pools

The SIT environment uses spot instance node pools for cost savings:

1. `dataspots`: Spot instances for data processing workloads (Standard_D2s_v3)
2. `lowspots`: Spot instances for low-latency workloads (Standard_F2s_v2)

To deploy workloads to these node pools, use the following tolerations and node affinity:

```yaml
tolerations:
- key: "kubernetes.azure.com/scalesetpriority"
  operator: "Equal"
  value: "spot"
  effect: "NoSchedule"
- key: "workload"  # Choose either "dataprocessing" or "lowlatency" based on pool
  operator: "Equal"
  value: "dataprocessing"  # or "lowlatency"
  effect: "NoSchedule"
```