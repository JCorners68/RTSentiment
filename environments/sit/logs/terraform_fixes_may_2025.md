# Terraform Deployment Error Fixes - May 2025 Updates

## Overview
This document summarizes the fixes implemented to address the deployment errors in the SIT environment's Terraform configuration identified in May 2025.

## Issues Fixed

### 1. AKS Availability Zone Issue in westus Region
**Problem:** Availability zones are not supported in the westus region, causing deployment failures with error: `AvailabilityZoneNotSupported: The zone(s) '2' for resource 'default' is not supported.`

**Solution:**
- Explicitly set `zones = []` in the AKS node pool configurations
- Added clear comments about westus region limitations
- Updated main cluster configuration to use a variable for kubernetes_version
- Updated `terraform.sit.tfvars` to ensure `enable_aks_availability_zones = false`

**Files Modified:**
- `/infrastructure/terraform/azure/main.tf`
- `/infrastructure/terraform/azure/node_pools.tf`
- `/infrastructure/terraform/azure/terraform.sit.tfvars`

### 2. Deprecated Azure Front Door Resource
**Problem:** The deployment failed with error: `Creation of new Frontdoors are not allowed as the resource has been deprecated`

**Solution:**
- Replaced the deprecated `azurerm_frontdoor` resource with the modern `azurerm_cdn_frontdoor_profile` resources
- Added conditional deployment using `count` based on variable `enable_cdn_frontdoor`
- Updated output variables to handle the new resource

**Files Modified:**
- `/infrastructure/terraform/azure/main.tf`
- `/infrastructure/terraform/azure/outputs.tf`
- `/infrastructure/terraform/azure/terraform.sit.tfvars`

### 3. App Configuration Key RBAC Propagation Timeout
**Problem:** App Configuration Key creation was failing with error: `waiting for App Configuration Key read permission to be propagated: context canceled`

**Solution:**
- Increased RBAC propagation wait time from 180s to 300s
- Updated variable `app_config_read_delay_seconds` to 300 in terraform.sit.tfvars
- Refactored app configuration keys creation to use `for_each` with delays between each key
- Added comments explaining the RBAC propagation timing issue

**Files Modified:**
- `/infrastructure/terraform/azure/modules/app-config/main.tf`
- `/infrastructure/terraform/azure/terraform.sit.tfvars`

### 4. Policy Assignment Authorization Issue
**Problem:** Service principal lacked permission for policy assignments: `AuthorizationFailed: The client does not have authorization to perform action 'Microsoft.Authorization/policyAssignments/write'`

**Solution:**
- Disabled policy assignments in SIT environment by setting `enable_policy_assignments = false`
- Added `count` conditional to all policy assignment resources
- Updated policy assignment output to handle disabled assignments
- Added variable to the cost management module

**Files Modified:**
- `/infrastructure/terraform/azure/terraform.sit.tfvars`
- `/infrastructure/terraform/azure/cost_management/azure_cost_optimization_and_governance.tf`

### 5. Monitor Activity Log Alert Location Issue
**Problem:** Activity Log Alert creation failed with error: `LocationNotAvailableForResourceType: The provided location 'westus' is not available for resource type 'microsoft.insights/activityLogAlerts'`

**Solution:**
- Confirmed that Activity Log Alerts use "global" location setting
- Added clarifying comment to prevent future confusion

**Files Modified:**
- `/infrastructure/terraform/azure/modules/app-config/main.tf`

### 6. Storage Data Lake Gen2 Filesystem Authorization Issue
**Problem:** Data Lake Gen2 filesystem creation failed with error: `This request is not authorized to perform this operation`

**Solution:**
- Added additional role assignments for the terraform service principal:
  - Storage Blob Data Owner (data plane operations)
  - Storage Account Contributor (management plane operations)
- Increased RBAC propagation wait time from 180s to 300s
- Added dependency on role assignments for resource creation

**Files Modified:**
- `/infrastructure/terraform/azure/modules/iceberg/main.tf`

### 7. Container Instance Subnet Delegation Issue
**Problem:** Container Group deployment failed with error: `SubnetMissingRequiredDelegation: Subnet missing required delegation 'Microsoft.ContainerInstance'`

**Solution:**
- Added proper subnet delegation in the data_tier.tf file
- Added NSG rule for container communication
- Created guidance for manual delegation via null_resource
- Disabled container deployment in SIT environment by setting `deploy_container = false`

**Files Modified:**
- `/infrastructure/terraform/azure/modules/iceberg/main.tf`
- `/infrastructure/terraform/azure/terraform.sit.tfvars`

### 8. Deployment and Verification Pipeline Consistency
**Problem:** Inconsistencies between deployment scripts, Terraform variables, and verification scripts led to confusion and errors.

**Solution:**
- Created `/environments/sit/check_config_consistency.sh` script to validate consistency
- Added config check to deployment script with abort if inconsistent
- Added config check to verification script with warning if inconsistent
- Added Python test for config consistency
- Updated verification scripts to use dynamic values from configuration
  
**Files Modified:**
- `/environments/sit/deploy_azure_sit.sh`
- `/environments/sit/verify_deployment.sh`
- `/environments/sit/tests/run_verification.py`
- Created `/environments/sit/check_config_consistency.sh`
- Created `/environments/sit/tests/test_config_consistency.py`

## Conclusion
These fixes address all identified deployment errors and should result in a successful deployment of the SIT environment. The changes maintain a consistent configuration across all tools and scripts, while also ensuring compatibility with the westus region's limitations.

Key benefits:
- Increased robustness through consistency checking
- Better error handling and debugging
- Reduced resource usage appropriate for a testing environment
- Workarounds for regional limitations

## Next Steps

1. Run the deployment with these fixes:
```bash
cd /home/jonat/real_senti/environments/sit
./deploy_azure_sit.sh
```

2. After deployment, verify the resources:
```bash
cd /home/jonat/real_senti/environments/sit
./verify_deployment.sh
```

3. Run the Python-based verification:
```bash
cd /home/jonat/real_senti/environments/sit/tests
python run_verification.py
```

4. If any specific resource still has issues, consider:
   - Checking logs in `/home/jonat/real_senti/environments/sit/logs`
   - Running `./check_config_consistency.sh` for detailed configuration analysis
   - Using the Azure Portal for manual verification and troubleshooting

5. Apply similar fixes to UAT and production environments as needed.