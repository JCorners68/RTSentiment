# Spot Instances Configuration for SIT Environment

## Overview

The SIT environment has been configured to use Azure Spot Virtual Machines for significant cost savings. This document explains the configuration, benefits, and considerations.

## Configuration Details

### Node Pools Using Spot Instances

The following node pools are configured to use spot instances:

1. **Data Processing Node Pool (`datanodes`)**
   - VM Size: Standard_D2s_v3 (2 vCPUs)
   - Priority: Spot
   - Eviction Policy: Delete
   - Maximum Spot Price: Market price (up to on-demand price)
   - Taints: 
     - `workload=dataprocessing:NoSchedule`
     - `kubernetes.azure.com/scalesetpriority=spot:NoSchedule`

2. **Low-Latency Node Pool (`lowlatency`)**
   - VM Size: Standard_F2s_v2 (2 vCPUs)
   - Priority: Spot
   - Eviction Policy: Delete
   - Maximum Spot Price: Market price (up to on-demand price)
   - Taints:
     - `workload=lowlatency:NoSchedule`
     - `kubernetes.azure.com/scalesetpriority=spot:NoSchedule`

### Default Node Pool (System Components)

The default node pool that runs critical system components is kept as a regular (non-spot) instance to ensure system stability. This is a best practice to prevent evictions from affecting critical system components like CoreDNS, which could impact the entire cluster.

## Benefits

1. **Cost Savings**: Up to 90% cost reduction compared to standard on-demand VMs
2. **Same VM Sizes and Performance**: Spot VMs offer the same performance as regular VMs
3. **Optimized for SIT Environment**: Perfect for testing environments where occasional interruptions are acceptable

## Considerations and Best Practices

### Handling Evictions

Spot VMs can be evicted when Azure needs the capacity back. To handle this:

1. **Pod Disruption Budgets**: Consider configuring PDBs for critical workloads
2. **Node Taints and Tolerations**: Only pods with appropriate tolerations will be scheduled on spot nodes
3. **Stateless Applications**: Prefer stateless applications on spot nodes

### Workload Configuration

To deploy workloads on spot nodes, add the following tolerations to your pod spec:

```yaml
tolerations:
- key: "kubernetes.azure.com/scalesetpriority"
  operator: "Equal"
  value: "spot"
  effect: "NoSchedule"
# Add additional tolerations for specific node pools as needed
- key: "workload"
  operator: "Equal" 
  value: "dataprocessing"  # or "lowlatency" for the other node pool
  effect: "NoSchedule"
```

### Node Selectors

To explicitly target specific node pools, add node selectors:

```yaml
nodeSelector:
  agentpool: datanodes  # or "lowlatency" for the low-latency node pool
```

## Cost Analysis

Based on current Azure pricing:

| VM Size | On-Demand Price | Spot Price (Est.) | Savings per VM |
|---------|----------------|-------------------|----------------|
| Standard_D2s_v3 | ~$0.11/hour | ~$0.01-0.03/hour | ~70-90% |
| Standard_F2s_v2 | ~$0.10/hour | ~$0.01-0.03/hour | ~70-90% |

Estimated monthly savings for SIT environment: **$150-$200**

## Quota Management

If you encounter Spot VM quota issues:

1. Go to the Azure Portal
2. Navigate to Subscriptions → Your Subscription → Usage + quotas
3. Filter by "spot" to see spot VM quotas
4. Request quota increases specifically for spot VMs if needed

## Verification

After applying this configuration, you can verify spot instances are working by:

1. Running: `kubectl get nodes -o custom-columns=NAME:.metadata.name,KIND:.metadata.labels.agentpool,PRIORITY:.metadata.labels.kubernetes\\.azure\\.com/scalesetpriority`
2. Looking for "spot" in the PRIORITY column for the data and low-latency nodes

## Conclusion

Using spot instances for the SIT environment is an excellent way to reduce costs while maintaining the necessary resources for testing. By keeping the system node pool as a regular instance and using spot instances for workload-specific node pools, we achieve a balance of reliability and cost efficiency.