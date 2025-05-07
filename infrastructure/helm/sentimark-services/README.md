# Sentimark Services Helm Chart

This Helm chart deploys all services for the Sentimark project with optimized configurations for different environments, including spot instance support for cost optimization.

## Features

- **Spot Instance Support**: Run workloads on Azure Spot instances to reduce costs by 60-80%
- **Configurable Services**: Deploy and configure multiple services with a single values file
- **Pod Disruption Budgets**: Ensure high availability during node maintenance or spot instance preemption
- **Security Contexts**: Secure-by-default configuration with least privilege principles
- **Probes**: Comprehensive liveness, readiness, and startup probes for all services
- **Resource Management**: Configurable resource requests and limits for all containers

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- AKS cluster with spot instance node pools configured

## Spot Instance Configuration

This chart is designed to leverage Azure Spot instances configured with the following node pools:

- **dataspots**: Standard_D2s_v3 VMs for data processing workloads
- **lowspots**: Standard_F2s_v2 VMs for low-latency workloads

Pods are scheduled on these spot instances using node selectors and tolerations:

```yaml
nodeSelector:
  agentpool: dataspots  # or lowspots

tolerations:
- key: "kubernetes.azure.com/scalesetpriority"
  operator: "Equal"
  value: "spot"
  effect: "NoSchedule"
- key: "workload"
  operator: "Equal"
  value: "dataprocessing"  # or "lowlatency"
  effect: "NoSchedule"
```

## Installation

```bash
# Add the repository
helm repo add sentimark https://sentimark.com/charts

# Install the chart with default configuration
helm install sit sentimark/sentimark-services

# Install with custom values
helm install sit sentimark/sentimark-services -f my-values.yaml
```

## Configuration

The following table lists the configurable parameters of the Sentimark Services chart. For a complete list, see the [values.yaml](values.yaml) file.

| Parameter | Description | Default |
| --------- | ----------- | ------- |
| `global.environment` | Deployment environment | `sit` |
| `global.registry.server` | Container registry server | `rtsentiregistry.azurecr.io` |
| `global.spotInstances.enabled` | Enable spot instances | `true` |
| `dataAcquisition.enabled` | Enable data acquisition service | `true` |
| `dataAcquisition.replicaCount` | Number of replicas | `3` |
| `dataAcquisition.spotInstance.enabled` | Deploy on spot instances | `true` |
| `dataAcquisition.spotInstance.nodeSelector.agentpool` | Node pool to use | `dataspots` |
| `dataMigration.enabled` | Enable data migration service | `true` |
| `dataMigration.replicaCount` | Number of replicas | `1` |
| `dataMigration.cronJob.enabled` | Enable scheduled migration jobs | `true` |
| `dataMigration.cronJob.schedule` | Cron schedule for migration jobs | `"0 0 * * *"` |

## Accessing the Services

The services are deployed with ClusterIP by default. To access them externally, you can:

1. Enable the ingress by setting `dataAcquisition.ingress.enabled=true`
2. Use port-forwarding:
   ```bash
   kubectl port-forward svc/data-acquisition 8002:80
   ```

## Troubleshooting

### DNS Resolution with Private AKS Endpoints

If you experience DNS resolution errors with private AKS endpoints:

```
dial tcp: lookup rt-sentiment-pu1l2xsk.privatelink.westus.azmk8s.io: no such host
```

Use one of these approaches:

1. Run `./setup_vpn_access.sh` to temporarily enable public access (for development only)
2. Use Azure Cloud Shell which has direct access to private endpoints
3. Set up a proper Point-to-Site VPN following the instructions in `setup_vpn_access.sh`

### Handling Spot Instance Evictions

When running on spot instances, be aware that nodes may be evicted with short notice:

1. Ensure your applications handle shutdowns gracefully
2. Set up proper Pod Disruption Budgets (already configured by default)
3. Implement proper state persistence for stateful workloads