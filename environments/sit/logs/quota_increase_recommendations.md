# Azure Quota Increase Recommendations

## Current Limitations

Based on our SIT deployment experience, we've identified the following quota limitations that need to be addressed for both enhanced SIT performance and UAT deployment:

1. **vCPU Quota**: Currently limited to 10 vCPUs in the StandardDSv3Family in westus region
2. **GPU Resources**: No GPU quota available (required for UAT but not SIT)
3. **Storage Account IOPS**: Limited throughput for the Data Lake Gen2 storage

## Quota Increase Recommendations

### For SIT Environment Improvement

| Resource Type | Current Quota | Recommended Quota | Justification |
|--------------|--------------|------------------|--------------|
| StandardDSv3Family vCPUs | 10 | 16 | Support full node pool deployment with 2-3 nodes |
| Storage Account Premium Performance | Standard | Premium | Improved IOPS for Data Lake Gen2 storage |
| Container Registry Storage | 10 GB | 20 GB | Support for multiple service container images |
| Standard SSD Managed Disks | 2 TB | 4 TB | Support for increased data volume in AKS nodes |

### For UAT Environment (New Requirements)

| Resource Type | Current Quota | Recommended Quota | Justification |
|--------------|--------------|------------------|--------------|
| StandardDSv3Family vCPUs | 10 | 24 | Support for increased node count in UAT |
| NCasT4_v3-series VMs | 0 | 4 | NVIDIA T4 GPUs for FinBERT model acceleration |
| GPU Enabled VMs | 0 | 4 | Required for ML workloads in UAT |
| Standard SSD Managed Disks | 2 TB | 8 TB | Increased storage for UAT data volume |
| Premium SSD Managed Disks | 0 | 2 TB | High-performance storage for ML model data |
| Total Regional vCPUs | 20 | 48 | Accommodate all SIT and UAT resources |

## Optimal Memory vs CPU Configurations

### General Workloads (Data Tier & API Services)

The optimal memory-to-CPU ratio for general workloads is **4-8 GB RAM per vCPU**. For the data tier specifically, we recommend:

| VM Size | vCPUs | Memory | Ratio | Recommended Use |
|---------|------|--------|-------|-----------------|
| Standard_D2s_v3 | 2 | 8 GiB | 4:1 | Default nodes, API services |
| Standard_D4s_v3 | 4 | 16 GiB | 4:1 | Data tier services with moderate workloads |
| Standard_E4s_v3 | 4 | 32 GiB | 8:1 | Memory-intensive data processing |
| Standard_D8s_v3 | 8 | 32 GiB | 4:1 | Concurrent data processing |

### GPU Workloads (UAT Only)

For FinBERT model execution, the optimal configurations are:

| VM Size | GPUs | vCPUs | Memory | Recommended Use |
|---------|------|-------|--------|-----------------|
| Standard_NC4as_T4_v3 | 1 | 4 | 28 GiB | Single model inference |
| Standard_NC8as_T4_v3 | 1 | 8 | 56 GiB | Model inference with higher throughput |
| Standard_NC16as_T4_v3 | 1 | 16 | 110 GiB | Model fine-tuning and high-volume inference |

The NVIDIA T4 GPU is optimal for our use case because:
1. It provides 16GB GDDR6 memory, sufficient for FinBERT model
2. It supports mixed-precision inference (FP16/INT8)
3. It's more cost-effective than V100 GPUs

## Implementation Recommendations

### SIT Improvements (Without GPU)

For improved SIT performance, we recommend:

1. **Node Pool Configuration**:
   ```terraform
   default_node_pool {
     name           = "default"
     node_count     = 2
     vm_size        = "Standard_D4s_v3"  # 4 vCPU, 16 GB RAM
     os_disk_size_gb = 128
   }
   
   # Add dedicated data tier node
   resource "azurerm_kubernetes_cluster_node_pool" "data_tier" {
     name                  = "datatier"
     kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
     vm_size               = "Standard_E4s_v3"  # 4 vCPU, 32 GB RAM (memory optimized)
     node_count            = 1
     os_disk_size_gb       = 256
   }
   ```

2. **Storage Configuration**:
   ```terraform
   resource "azurerm_storage_account" "iceberg_storage" {
     # Existing configuration...
     account_tier             = "Premium"  # Upgrade to Premium
     account_replication_type = "LRS"
     is_hns_enabled           = true
   }
   ```

### UAT Implementation (With GPU)

For UAT with GPU support, we recommend:

1. **Add GPU Node Pool**:
   ```terraform
   resource "azurerm_kubernetes_cluster_node_pool" "gpu_nodes" {
     name                  = "gpunodes"
     kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
     vm_size               = "Standard_NC4as_T4_v3"  # T4 GPU-enabled VM
     node_count            = 1
     os_disk_size_gb       = 256
     
     # GPU nodes need specific taints to prevent non-GPU workloads
     node_taints = ["sku=gpu:NoSchedule"]
   }
   ```

2. **Configure GPU in Kubernetes**:
   ```yaml
   # In Kubernetes deployment for data-acquisition
   spec:
     nodeSelector:
       agentpool: gpunodes
     tolerations:
     - key: "sku"
       operator: "Equal"
       value: "gpu"
       effect: "NoSchedule"
     containers:
     - name: data-acquisition
       resources:
         limits:
           nvidia.com/gpu: 1
   ```

3. **Environment Variables for GPU**:
   ```yaml
   env:
   - name: USE_CUDA
     value: "yes"
   - name: CUDA_DEVICE
     value: "0"
   ```

## Quota Increase Process

1. **Request Timing**: Request quota increases at least 2-3 weeks before needed
2. **Request Process**:
   - Navigate to Azure Portal
   - Select Subscription
   - Go to Usage + quotas
   - Select "Request Increase" for each resource
   - Provide business justification

3. **Approval Timeline**:
   - Standard vCPU increases: 1-3 business days
   - GPU resources: 3-7 business days
   - Premium storage: 1-2 business days

4. **Alternative Options**:
   - If quota increase is not approved in time, consider:
     - Using multiple smaller VMs instead of larger ones
     - Deploying across multiple regions
     - Using burstable B-series VMs for non-critical workloads

## Cost Implications

| Recommendation | Estimated Additional Monthly Cost |
|----------------|----------------------------------|
| SIT vCPU increase (6 additional) | ~$175-225 |
| Premium Storage Upgrade | ~$50-75 |
| UAT GPU Node (NC4as_T4_v3) | ~$350-450 |
| Additional Storage | ~$100-150 |

*Note: Costs are approximate and may vary based on usage patterns and Azure pricing changes.*