# Spot Instance Deployment Guide

This guide documents the implementation and usage of Azure Spot Instances for the Sentimark SIT environment, providing significant cost savings for non-production workloads.

## Overview

Azure Spot Virtual Machines (VMs) provide access to unused Azure capacity at significant discounts. Spot VMs are ideal for interruptible workloads, offering up to 80% cost savings compared to on-demand VMs. The Sentimark SIT environment leverages spot instances for data processing and low-latency workloads.

## Implementation Details

### Node Pools Configuration

The SIT environment utilizes three node pools:

| Pool Name | VM Size | Role | Spot Instance | Taints |
|-----------|---------|------|--------------|--------|
| default | Standard_D2s_v3 | System | No | None |
| dataspots | Standard_D2s_v3 | Data Processing | Yes | `kubernetes.azure.com/scalesetpriority=spot:NoSchedule`<br>`workload=dataprocessing:NoSchedule` |
| lowspots | Standard_F2s_v2 | Low Latency | Yes | `kubernetes.azure.com/scalesetpriority=spot:NoSchedule`<br>`workload=lowlatency:NoSchedule` |

### Terraform Configuration

Spot instances are configured in the Terraform files:

**File: `/home/jonat/real_senti/infrastructure/terraform/azure/node_pools.tf`**

```terraform
resource "azurerm_kubernetes_cluster_node_pool" "data_nodes_spot" {
  name                  = "dataspots"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = "Standard_D2s_v3"
  priority              = "Spot"
  eviction_policy       = "Delete"
  spot_max_price        = -1  # Pay the current spot price up to on-demand price
  node_count            = 1
  
  node_taints = [
    "workload=dataprocessing:NoSchedule",
    "kubernetes.azure.com/scalesetpriority=spot:NoSchedule"
  ]
  
  count = var.enable_spot_instances ? 1 : 0
}

resource "azurerm_kubernetes_cluster_node_pool" "low_latency_spot" {
  name                  = "lowspots"
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size               = "Standard_F2s_v2"
  priority              = "Spot"
  eviction_policy       = "Delete"
  spot_max_price        = -1
  node_count            = 1
  
  node_taints = [
    "workload=lowlatency:NoSchedule",
    "kubernetes.azure.com/scalesetpriority=spot:NoSchedule"
  ]
  
  count = var.enable_spot_instances && var.use_low_latency_pool ? 1 : 0
}
```

**File: `/home/jonat/real_senti/infrastructure/terraform/azure/variables.tf`**

```terraform
variable "enable_spot_instances" {
  description = "Whether to use spot instances for node pools (for cost savings)"
  type        = bool
  default     = false
}

variable "use_low_latency_pool" {
  description = "Whether to create the low-latency node pool"
  type        = bool
  default     = false
}
```

**File: `/home/jonat/real_senti/infrastructure/terraform/azure/terraform.sit.tfvars`**

```terraform
# Spot instance configuration
enable_spot_instances = true   # Enable spot instances for cost savings
use_low_latency_pool = true    # Enable both node pools
```

## Using Spot Instances in Kubernetes Deployments

To schedule pods on spot instance nodes, you must configure tolerations and node selectors in your Kubernetes manifests.

### Example Deployment for Data Processing Workloads

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-acquisition
spec:
  replicas: 3
  selector:
    matchLabels:
      app: data-acquisition
  template:
    metadata:
      labels:
        app: data-acquisition
    spec:
      # Use node selector for spot instances
      nodeSelector:
        agentpool: dataspots
      
      # Add tolerations for spot instances
      tolerations:
      - key: "kubernetes.azure.com/scalesetpriority"
        operator: "Equal"
        value: "spot"
        effect: "NoSchedule"
      - key: "workload"
        operator: "Equal"
        value: "dataprocessing"
        effect: "NoSchedule"
      
      # Pod Disruption Budget for high availability
      terminationGracePeriodSeconds: 60
      containers:
      - name: data-acquisition
        image: rtsentiregistry.azurecr.io/data-acquisition:latest
        # Add lifecycle hooks for graceful termination
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 10; /app/shutdown.sh || true"]
```

### Helm Chart Configuration

Our Helm charts are already configured to use spot instances when available. See the configuration in:
- `/home/jonat/real_senti/infrastructure/helm/sentimark-services/values.yaml`
- `/home/jonat/real_senti/infrastructure/helm/sentimark-services/templates/_helpers.tpl`

## Handling Spot Instance Evictions

Spot instances can be evicted with only 30 seconds notice when Azure needs the capacity back. To handle this gracefully:

1. **Pod Disruption Budgets (PDB)**: Define PDBs to ensure service continuity
2. **Graceful Termination**: Implement proper shutdown handling with sufficient `terminationGracePeriodSeconds`
3. **Lifecycle Hooks**: Use `preStop` hooks to clean up resources
4. **State Persistence**: For stateful workloads, use persistent storage and checkpointing

## Cost Savings

The current configuration provides approximately:

- 60-80% cost savings compared to regular on-demand VMs
- Standard_D2s_v3 (dataspots): ~$0.068/hour vs $0.227/hour (on-demand)
- Standard_F2s_v2 (lowspots): ~$0.043/hour vs $0.143/hour (on-demand)

These figures are approximate and vary based on region and market demand.

## Monitoring Spot Instances

To monitor your spot instance nodes:

```bash
# Using az aks command invoke
./aks_command.sh kubectl get nodes --show-labels | grep -E "agentpool=dataspots|agentpool=lowspots"

# Check for eviction events
./aks_command.sh kubectl get events --field-selector involvedObject.kind=Node -w
```

## Troubleshooting

### Common Issues

1. **Pods not scheduling on spot instances**:
   - Verify that the tolerations and node selectors match the node taints
   - Check if the spot nodes are available and ready

2. **Frequent evictions**:
   - Consider using on-demand instances for critical workloads
   - Implement better handling of preemption signals

3. **Spot instances not being created**:
   - Check quota limits in your Azure subscription
   - Verify that the VM size requested is available as spot in your region

## References

- [Azure Spot Virtual Machines Documentation](https://docs.microsoft.com/en-us/azure/virtual-machines/spot-vms)
- [Kubernetes Pod Disruption Budgets](https://kubernetes.io/docs/tasks/run-application/configure-pdb/)
- [Kubernetes Node Taints and Tolerations](https://kubernetes.io/docs/concepts/scheduling-eviction/taint-and-toleration/)