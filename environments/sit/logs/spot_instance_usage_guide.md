# Using Azure Spot Instances in AKS for Sentimark SIT Environment

## Overview

The Sentimark SIT environment uses Azure Spot Instances for cost optimization. This document explains how to leverage these spot instances effectively and how to ensure application resilience.

## Spot Instance Pools

The following spot instance node pools are configured:

| Pool Name | VM Size | Purpose | Taints |
|-----------|---------|---------|--------|
| dataspots | Standard_D2s_v3 | Data processing workloads | `workload=dataprocessing:NoSchedule`, `kubernetes.azure.com/scalesetpriority=spot:NoSchedule` |
| lowspots | Standard_F2s_v2 | Low-latency workloads | `workload=lowlatency:NoSchedule`, `kubernetes.azure.com/scalesetpriority=spot:NoSchedule` |

## Deploying Applications to Spot Instances

To schedule pods on spot instances, configure your deployments with:

1. **Tolerations** for the node taints:

```yaml
tolerations:
- key: "kubernetes.azure.com/scalesetpriority"
  operator: "Equal"
  value: "spot"
  effect: "NoSchedule"
- key: "workload"
  operator: "Equal"
  value: "dataprocessing"  # or "lowlatency" depending on target pool
  effect: "NoSchedule"
```

2. **Node affinity** to prefer the specific node pool:

```yaml
affinity:
  nodeAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: agentpool
          operator: In
          values:
          - dataspots  # or lowspots depending on target pool
```

## Handling Spot Instance Evictions

Applications deployed on spot instances must handle potential evictions:

1. **Pod Disruption Budgets (PDB)**: Define PDBs to ensure service continuity:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: my-app-pdb
spec:
  minAvailable: 1  # or use maxUnavailable
  selector:
    matchLabels:
      app: my-app
```

2. **Graceful Termination**: Implement proper shutdown handling:

```yaml
spec:
  containers:
  - name: my-app
    # ...
    lifecycle:
      preStop:
        exec:
          command: ["sh", "-c", "sleep 10 && /app/cleanup.sh"]
    terminationGracePeriodSeconds: 60
```

3. **State Persistence**: For stateful workloads:
   - Use durable storage (Azure Disks, Azure Files)
   - Implement checkpointing and state recovery
   - Consider using StatefulSets with PersistentVolumeClaims

## Example Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-processor
  namespace: sit
spec:
  replicas: 2
  selector:
    matchLabels:
      app: data-processor
  template:
    metadata:
      labels:
        app: data-processor
    spec:
      terminationGracePeriodSeconds: 60
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: agentpool
                operator: In
                values:
                - dataspots
      tolerations:
      - key: "kubernetes.azure.com/scalesetpriority"
        operator: "Equal"
        value: "spot"
        effect: "NoSchedule"
      - key: "workload"
        operator: "Equal"
        value: "dataprocessing"
        effect: "NoSchedule"
      containers:
      - name: data-processor
        image: sentimark/data-processor:latest
        resources:
          requests:
            cpu: "0.5"
            memory: "1Gi"
          limits:
            cpu: "1"
            memory: "2Gi"
```

## Monitoring Spot Instance Nodes

Monitor spot instance nodes:

```bash
# List all nodes with labels and taints
kubectl get nodes --show-labels
kubectl describe nodes | grep -A5 Taints

# Watch for node events (including preemption)
kubectl get events --field-selector involvedObject.kind=Node -w
```

## Cost Savings Expectations

Our configured spot instances provide:

- 60-80% cost savings compared to regular on-demand VMs
- Standard_D2s_v3 (dataspots): ~$0.068/hour vs $0.227/hour (on-demand)
- Standard_F2s_v2 (lowspots): ~$0.043/hour vs $0.143/hour (on-demand)

These figures are approximate and will vary based on region and market demand.