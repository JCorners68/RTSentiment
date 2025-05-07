# Terraform Azure Deployment - Final Fixes

## Summary of All Fixes

The following critical issues in the Terraform configuration have been fixed:

1. **AKS Cluster CPU Quota Issue**
   - Changed node count from 3 to 2
   - Reduced VM size from Standard_D4s_v3 to Standard_D2s_v3
   - This brings the total vCPU usage down from 12 vCPUs to 4 vCPUs, well within quota limits

2. **Application Insights workspace_id Issue**
   - Added explicit workspace_id parameter to the Application Insights resource
   - This prevents the error where the workspace_id couldn't be removed after being set

3. **Local-Exec Provisioners**
   - Replaced az CLI local-exec provisioners with proper Terraform resources
   - Added Data Lake Gen2 Filesystem resources with proper dependencies
   - Added time_sleep resource to wait for RBAC propagation

4. **Docker Hub Authentication**
   - Added Docker Hub authentication to avoid rate limiting
   - Made Docker credentials configurable via variables
   - Kept container deployment resources but made them conditionally deployable
   - Added ability to provide Docker Hub credentials in tfvars file

5. **Improved Error Handling**
   - Added fallback resources for manual steps if automated deployment fails
   - Added detailed instructions for manual steps if needed

## Specific Changes Made

### 1. AKS Cluster Configuration
```terraform
default_node_pool {
  name                         = "default"
  node_count                   = 2  # Reduced from 3 to fit within CPU quota
  vm_size                      = "Standard_D2s_v3"  # Smaller VM size with fewer CPUs
  os_disk_size_gb              = 100
  proximity_placement_group_id = azurerm_proximity_placement_group.ppg.id
  # Removed zones as they're not supported in westus region
  only_critical_addons_enabled = false
}
```

### 2. Application Insights Configuration
```terraform
resource "azurerm_application_insights" "insights" {
  name                = var.app_insights_name
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.workspace.id
  
  tags = {
    environment = var.environment
    CostCenter  = "Sentimark"
  }
}
```

### 3. Data Lake Gen2 Filesystem Creation
```terraform
resource "azurerm_storage_data_lake_gen2_filesystem" "warehouse" {
  name               = "warehouse"
  storage_account_id = azurerm_storage_account.iceberg_storage.id
  
  depends_on = [
    azurerm_storage_account.iceberg_storage,
    azurerm_role_assignment.identity_storage_blob_contributor,
    time_sleep.wait_for_rbac_propagation
  ]
}

resource "azurerm_storage_data_lake_gen2_filesystem" "metadata" {
  name               = "metadata"
  storage_account_id = azurerm_storage_account.iceberg_storage.id
  
  depends_on = [
    azurerm_storage_account.iceberg_storage,
    azurerm_role_assignment.identity_storage_blob_contributor,
    time_sleep.wait_for_rbac_propagation
  ]
}

# Add delay for RBAC propagation
resource "time_sleep" "wait_for_rbac_propagation" {
  depends_on      = [azurerm_role_assignment.identity_storage_blob_contributor]
  create_duration = "60s"
}
```

### 4. Docker Hub Authentication
```terraform
# Container group for Iceberg REST Catalog
resource "azurerm_container_group" "iceberg_rest_catalog" {
  count               = var.deploy_container ? 1 : 0
  name                = "${var.base_name}-iceberg-rest-catalog"
  location            = var.location
  resource_group_name = var.resource_group_name
  ip_address_type     = "Private"
  subnet_ids          = var.subnet_ids
  os_type             = "Linux"
  restart_policy      = "Always"

  # Docker Hub authentication to avoid rate limiting
  dynamic "image_registry_credential" {
    for_each = var.docker_username != "" && var.docker_password != "" ? [1] : []
    content {
      server   = "index.docker.io"
      username = var.docker_username
      password = var.docker_password
    }
  }

  container {
    name   = "iceberg-rest"
    image  = "tabulario/iceberg-rest:0.5.0"
    cpu    = "1"
    memory = "1.5"
    
    # Container configuration...
  }
}
```

### 5. Variables for Docker Authentication
```terraform
variable "docker_username" {
  description = "Docker Hub username for authenticated pulls (to avoid rate limiting)"
  type        = string
  default     = ""
}

variable "docker_password" {
  description = "Docker Hub password or access token for authenticated pulls"
  type        = string
  default     = ""
  sensitive   = true
}

variable "deploy_container" {
  description = "Whether to deploy the Iceberg REST catalog container"
  type        = bool
  default     = true
}
```

## Next Steps

1. Create a new Terraform plan with these fixes:
```bash
cd /home/jonat/real_senti/infrastructure/terraform/azure
./run-terraform.sh plan -out=tfplan.sit.final -var-file=terraform.sit.tfvars
```

2. Apply the plan:
```bash
./run-terraform.sh apply tfplan.sit.final
```

3. If you want to use Docker Hub authentication, edit the terraform.sit.tfvars file to add your Docker Hub credentials:
```
docker_username = "your_dockerhub_username"
docker_password = "your_dockerhub_access_token"
```

4. If any deployment issues remain, use the manual steps provided in the fallback resources.

## Manual Steps (if needed)

If automatic deployment of any resources fails, you can use these manual steps:

### Create Data Lake Gen2 Filesystems
```bash
az storage fs create --account-name [storage-account-name] --name warehouse --auth-mode login
az storage fs create --account-name [storage-account-name] --name metadata --auth-mode login
```

### Deploy Iceberg REST Catalog Container
```bash
az container create --resource-group [resource-group-name] \
  --name sentimark-iceberg-rest-catalog \
  --image tabulario/iceberg-rest:0.5.0 \
  --cpu 1 --memory 1.5 \
  --ip-address Private \
  --subnet-ids '[subnet-id]' \
  --registry-username [your-dockerhub-username] \
  --registry-password [your-dockerhub-password] \
  --environment-variables 'AWS_REGION=us-east-1' 'CATALOG_WAREHOUSE=s3a://warehouse' \
  'CATALOG_IO__IMPL=org.apache.iceberg.azure.adls.AzureDataLakeFileIO' \
  'CATALOG_S3_ENDPOINT=https://[storage-account-name].dfs.core.windows.net' \
  'CATALOG_S3_PATH_STYLE_ACCESS=true' \
  --secure-environment-variables 'AWS_ACCESS_KEY_ID=[storage-account-name]' \
  'AWS_SECRET_ACCESS_KEY=[storage-account-key]' \
  'AZURE_STORAGE_ACCOUNT=[storage-account-name]' \
  'AZURE_STORAGE_ACCESS_KEY=[storage-account-key]'
```