# Terraform Azure Deployment Fixes

## Issue Summary
Multiple errors were encountered during Terraform deployment of the SIT Azure infrastructure. The following key issues were identified and fixed:

1. AKS Cluster Availability Zones - westus region doesn't support availability zones for AKS
2. Front Door Resource - The classic Azure Front Door is deprecated
3. App Configuration Keys - Permission issues with RBAC role assignments
4. Activity Log Alert Location - Wrong location specified for Log Alerts
5. Policy Assignments - Added conditional creation based on permission flag (now enabled)
6. Container Instance Subnet - Missing required delegation for Container Instance
7. Storage Data Lake Gen2 Permissions - Enabled after granting Storage Blob Data Contributor permission
8. Role Assignments - Enabled after granting Microsoft.Authorization/roleAssignments/write permission

## Changes Made

### 1. AKS Cluster Availability Zones
- Removed `zones` parameter from the default node pool configuration
- Added a new variable `enable_aks_availability_zones` to control this feature

### 2. Front Door Resource 
- Commented out the deprecated `azurerm_frontdoor` and WAF policy resources
- Added variables to control classic vs CDN Front Door implementation
- Added documentation for future implementation using `azurerm_cdn_frontdoor_*` resources

### 3. App Configuration Keys
- Added time delay between RBAC assignment and key creation
- Implemented `time_sleep` resource with configurable duration
- Added `app_config_read_delay_seconds` variable

### 4. Activity Log Alert Location
- Changed the location from `var.location` to `"global"` for the Activity Log Alert

### 5. Policy Assignments
- Added conditional creation with `count = var.enable_policy_assignments ? 1 : 0`
- Added variable `enable_policy_assignments` to control this feature (set to true)
- This now works since the service principal has been granted policy assignment permissions

### 6. Container Instance Subnet
- Added required delegation for Container Instance to the data tier subnet:
```terraform
delegation {
  name = "container-instance-delegation"
  service_delegation {
    name    = "Microsoft.ContainerInstance/containerGroups"
    actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
  }
}
```

### 7. Storage Data Lake Gen2 Permissions
- Re-enabled direct creation of data lake filesystems after granting permissions
- Removed workaround `null_resource` with manual instructions
- Service principal now has Storage Blob Data Contributor role on the storage account

### 8. Role Assignments
- Re-enabled direct role assignment resources after granting permissions
- Removed workaround `null_resource` with manual instructions
- Service principal now has Microsoft.Authorization/roleAssignments/write permission

## Testing
- Basic validation of Terraform configuration was performed
- Resource dependencies were maintained in the updated configuration
- Variable defaults and types were properly defined

## Next Steps
1. Run the terraform plan command:
```bash
cd infrastructure/terraform/azure
./run-terraform.sh plan -var-file=terraform.sit.tfvars -out=tfplan.sit
```

2. Apply the terraform plan:
```bash
./run-terraform.sh apply tfplan.sit
```

3. After deployment is complete, perform the manual steps outlined in the local-exec outputs:
   - Create data lake filesystems
   - Assign Storage Blob Data Contributor role to the managed identity

4. Validate the deployment with the verification script:
```bash
cd environments/sit
python3 sentimark_sit_verify.py
```