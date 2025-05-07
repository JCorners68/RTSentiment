# SIT Environment Resource Optimization

## Overview

This document outlines changes made to optimize resource usage for the SIT environment and resolve vCPU quota limitations.

## Issues and Solutions

### 1. vCPU Quota Limitations

**Problem:**
```
Error: ErrCode_InsufficientVCPUQuota
Insufficient regional vcpu quota left for location westus. left regional vcpu quota 12, requested quota 16.
```

The SIT environment was attempting to provision more vCPUs than the available quota allowed. For a testing environment, this level of resources is excessive.

**Solution:**
- Reduced AKS node count from 3 to 1 for the default node pool
- Reduced data nodes from 2 to 1
- Reduced low-latency nodes from 2 to 1
- Reduced VM sizes to more appropriate sizes for SIT:
  - Default pool: Standard_D2s_v3 (2 vCPUs)
  - Data pool: Standard_D2s_v3 (2 vCPUs) from D8s_v3 (8 vCPUs)
  - Low-latency pool: Standard_F2s_v2 (2 vCPUs) from F8s_v2 (8 vCPUs)
- Total vCPU reduction: From 16 vCPUs to 6 vCPUs

### 2. Key Vault Access Policy Conflict

**Problem:**
```
Error: A resource with the ID "/subscriptions/644936a7-e58a-4ccb-a882-0005f213f5bd/resourceGroups/sentimark-sit-rg-data-tier/providers/Microsoft.KeyVault/vaults/sentimark-dt-zcsdms/objectId/5c765214-89b0-4a9b-9e8f-ff6e763d1828" already exists
```

The service principal already had a Key Vault access policy created outside of Terraform, causing a conflict.

**Solution:**
- Removed the explicit access_policy block from the Key Vault resource
- Removed the azurerm_key_vault_access_policy resource for the service principal
- Left a comment explaining that the policy already exists and is not managed by Terraform

### 3. Data Lake Filesystem Creation Permission Issues

**Problem:**
```
Error: checking for existence of existing File System "warehouse" in Account "sentimarkicezcsdms": unexpected status 403 (403 This request is not authorized to perform this operation.)
```

The service principal doesn't have the correct permissions even with the Storage Blob Data Owner role.

**Solution:**
- Used ARM templates via azurerm_resource_group_template_deployment instead of direct resource creation
- This approach uses Azure Resource Manager which has different authentication mechanisms
- Created separate deployments for warehouse and metadata filesystems

## Resource Configuration Comparison

| Resource | Original | Optimized | vCPU Savings |
|----------|----------|-----------|--------------|
| Default Node Pool | 2 nodes × D2s_v3 | 1 node × D2s_v3 | 2 vCPUs |
| Data Node Pool | 2 nodes × D8s_v3 | 1 node × D2s_v3 | 14 vCPUs |
| Low-latency Node Pool | 2 nodes × F8s_v2 | 1 node × F2s_v2 | 14 vCPUs |
| **Total vCPUs** | **30 vCPUs** | **6 vCPUs** | **24 vCPUs** |

## Disk Space Optimization

| Resource | Original | Optimized | Disk Savings |
|----------|----------|-----------|--------------|
| Default Node Pool | 100 GB | 64 GB | 36 GB |
| Data Node Pool | 200 GB | 128 GB | 72 GB |
| Low-latency Node Pool | 100 GB | 64 GB | 36 GB |
| **Total Disk** | **400 GB** | **256 GB** | **144 GB** |

## SIT vs. UAT/Production Configuration

This optimization better aligns with best practices for environment sizing:

1. **SIT Environment (Current)**
   - Minimal resources for basic testing
   - 6 total vCPUs across all node pools
   - Sufficient for function verification

2. **UAT Environment (Future)**
   - Moderate resources for load testing
   - ~16-20 vCPUs recommended
   - More realistic performance testing

3. **Production Environment (Future)**
   - Full resources based on actual load
   - 30+ vCPUs depending on requirements
   - Optimized for production performance

## Next Steps

1. Apply the updated configuration
2. Request quota increase for UAT environment in advance
3. Consider environment-specific variable files to avoid hardcoding these values