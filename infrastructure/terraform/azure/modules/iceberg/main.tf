# Sentimark - Iceberg on Azure Module
# This module sets up Azure Data Lake Storage Gen2 for Apache Iceberg tables

# Storage account for Iceberg tables
resource "azurerm_storage_account" "iceberg_storage" {
  name                     = var.storage_account_name
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true # Hierarchical Namespace for ADLS Gen2
  
  blob_properties {
    versioning_enabled = false # Need to be false when is_hns_enabled = true
    
    delete_retention_policy {
      days = 7
    }
  }
  
  network_rules {
    default_action = "Deny"
    ip_rules       = var.allowed_ips
    virtual_network_subnet_ids = var.subnet_ids
    bypass         = ["AzureServices", "Logging", "Metrics"]
  }
  
  tags = merge(var.tags, {
    service = "iceberg"
    data_tier = "true"
  })
}

# Add role assignment for the terraform service principal with Owner permissions
resource "azurerm_role_assignment" "terraform_sp_storage_blob_owner" {
  scope                = azurerm_storage_account.iceberg_storage.id
  role_definition_name = "Storage Blob Data Owner"  # Owner for full permissions
  principal_id         = "5c765214-89b0-4a9b-9e8f-ff6e763d1828" # Service Principal Object ID
}

# Also add Storage Account Contributor role for management plane operations
resource "azurerm_role_assignment" "terraform_sp_storage_contributor" {
  scope                = azurerm_storage_account.iceberg_storage.id
  role_definition_name = "Storage Account Contributor"
  principal_id         = "5c765214-89b0-4a9b-9e8f-ff6e763d1828" # Service Principal Object ID
}

# Add longer delay for RBAC propagation
resource "time_sleep" "wait_for_rbac_propagation" {
  depends_on      = [
    azurerm_role_assignment.identity_storage_blob_contributor,
    azurerm_role_assignment.terraform_sp_storage_blob_owner,
    azurerm_role_assignment.terraform_sp_storage_contributor
  ]
  create_duration = "300s"  # Increased to 5 minutes for better propagation
}

# Use azurerm_resource_group_template_deployment for Data Lake Gen2 filesystems
# This works better with RBAC as it uses Azure Resource Manager directly
resource "azurerm_resource_group_template_deployment" "warehouse_filesystem" {
  name                = "warehouse-filesystem-deployment"
  resource_group_name = var.resource_group_name
  deployment_mode     = "Incremental"
  parameters_content = jsonencode({
    "storageAccountName" = {
      value = azurerm_storage_account.iceberg_storage.name
    },
    "filesystemName" = {
      value = "warehouse"
    }
  })

  template_content = <<TEMPLATE
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "storageAccountName": {
      "type": "string"
    },
    "filesystemName": {
      "type": "string"
    }
  },
  "resources": [
    {
      "type": "Microsoft.Storage/storageAccounts/blobServices/containers",
      "apiVersion": "2021-04-01",
      "name": "[concat(parameters('storageAccountName'), '/default/', parameters('filesystemName'))]",
      "properties": {
        "publicAccess": "None"
      }
    }
  ]
}
TEMPLATE

  depends_on = [
    azurerm_storage_account.iceberg_storage,
    time_sleep.wait_for_rbac_propagation
  ]
}

resource "azurerm_resource_group_template_deployment" "metadata_filesystem" {
  name                = "metadata-filesystem-deployment"
  resource_group_name = var.resource_group_name
  deployment_mode     = "Incremental"
  parameters_content = jsonencode({
    "storageAccountName" = {
      value = azurerm_storage_account.iceberg_storage.name
    },
    "filesystemName" = {
      value = "metadata"
    }
  })

  template_content = <<TEMPLATE
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "storageAccountName": {
      "type": "string"
    },
    "filesystemName": {
      "type": "string"
    }
  },
  "resources": [
    {
      "type": "Microsoft.Storage/storageAccounts/blobServices/containers",
      "apiVersion": "2021-04-01",
      "name": "[concat(parameters('storageAccountName'), '/default/', parameters('filesystemName'))]",
      "properties": {
        "publicAccess": "None"
      }
    }
  ]
}
TEMPLATE

  depends_on = [
    azurerm_storage_account.iceberg_storage,
    time_sleep.wait_for_rbac_propagation
  ]
}

# Fallback instructions for manual filesystem creation
resource "null_resource" "create_filesystems_reminder" {
  count = 0  # Disabled by default since we're using the proper resources
  
  provisioner "local-exec" {
    command = <<EOT
      echo "=== MANUAL FILESYSTEM CREATION REMINDER ==="
      echo "If the automatic filesystem creation fails, manually create them with:"
      echo "az storage fs create --account-name ${azurerm_storage_account.iceberg_storage.name} --name warehouse --auth-mode login"
      echo "az storage fs create --account-name ${azurerm_storage_account.iceberg_storage.name} --name metadata --auth-mode login"
      echo "=== END REMINDER ==="
    EOT
  }
  
}

# Assign necessary roles for Spark/Iceberg access
resource "azurerm_role_assignment" "storage_blob_data_contributor" {
  scope                = azurerm_storage_account.iceberg_storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = var.service_principal_id
}

# Managed Identity for AKS to access Iceberg storage
resource "azurerm_user_assigned_identity" "iceberg_identity" {
  name                = "${var.base_name}-iceberg-identity"
  resource_group_name = var.resource_group_name
  location            = var.location
  
  tags = var.tags
}

# Grant identity access to storage
resource "azurerm_role_assignment" "identity_storage_blob_contributor" {
  scope                = azurerm_storage_account.iceberg_storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.iceberg_identity.principal_id
}

# Azure Key Vault for Iceberg credentials
resource "azurerm_key_vault" "iceberg_vault" {
  name                       = "${var.base_name}-iceberg-kv"
  location                   = var.location
  resource_group_name        = var.resource_group_name
  tenant_id                  = var.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
  purge_protection_enabled   = true
  
  access_policy {
    tenant_id = var.tenant_id
    object_id = var.service_principal_id
    
    secret_permissions = [
      "Get", "List", "Set", "Delete", "Backup", "Restore", "Recover"
    ]
  }
  
  # Add access policy for the deploying service principal
  access_policy {
    tenant_id = var.tenant_id
    object_id = "5c765214-89b0-4a9b-9e8f-ff6e763d1828" # Service Principal Object ID
    
    secret_permissions = [
      "Get", "List", "Set", "Delete", "Backup", "Restore", "Recover", "Purge"
    ]
  }
  
  tags = var.tags
}

# Store storage account keys in Key Vault
resource "azurerm_key_vault_secret" "storage_account_key" {
  name         = "iceberg-storage-account-key"
  value        = azurerm_storage_account.iceberg_storage.primary_access_key
  key_vault_id = azurerm_key_vault.iceberg_vault.id
}

# Ensure subnets have proper delegation for container instances
resource "azurerm_subnet_network_security_group_association" "container_subnet_nsg" {
  count                     = length(var.subnet_ids) > 0 && var.deploy_container ? 1 : 0
  subnet_id                 = element(var.subnet_ids, 0)
  network_security_group_id = azurerm_network_security_group.container_nsg[0].id
}

resource "azurerm_network_security_group" "container_nsg" {
  count               = var.deploy_container ? 1 : 0
  name                = "${var.base_name}-container-nsg"
  location            = var.location
  resource_group_name = var.resource_group_name

  security_rule {
    name                       = "AllowContainerGroupCommunication"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "8181"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

# Since we can't modify the subnet delegation directly (it would be managed elsewhere),
# we'll use a null_resource to provide guidance for delegating the subnet
resource "null_resource" "subnet_delegation_instructions" {
  count = var.deploy_container ? 1 : 0
  
  provisioner "local-exec" {
    command = <<EOT
      echo "=== SUBNET DELEGATION INSTRUCTIONS ==="
      echo "To fix the 'SubnetMissingRequiredDelegation' error, run the following Azure CLI command:"
      echo ""
      echo "for subnet_id in ${join(" ", var.subnet_ids)}; do"
      echo "  SUBNET_NAME=\$(echo \$subnet_id | cut -d'/' -f11)"
      echo "  VNET_NAME=\$(echo \$subnet_id | cut -d'/' -f9)"
      echo "  RESOURCE_GROUP=\$(echo \$subnet_id | cut -d'/' -f5)"
      echo "  az network vnet subnet update --name \$SUBNET_NAME --vnet-name \$VNET_NAME --resource-group \$RESOURCE_GROUP --delegations Microsoft.ContainerInstance/containerGroups"
      echo "done"
      echo ""
      echo "=== END INSTRUCTIONS ==="
    EOT
  }
}

# Container group for Iceberg REST Catalog - make deployment conditional on container size
resource "azurerm_container_group" "iceberg_rest_catalog" {
  count               = var.deploy_container ? 1 : 0
  name                = "${var.base_name}-iceberg-rest-catalog"
  location            = var.location
  resource_group_name = var.resource_group_name
  ip_address_type     = "Private"
  subnet_ids          = var.subnet_ids
  os_type             = "Linux"
  restart_policy      = "Always"
  
  depends_on = [
    null_resource.subnet_delegation_instructions,
    azurerm_subnet_network_security_group_association.container_subnet_nsg,
    azurerm_storage_account.iceberg_storage
  ]

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

    environment_variables = {
      "AWS_REGION"                 = "us-east-1"
      "CATALOG_WAREHOUSE"          = "s3a://warehouse"
      "CATALOG_IO__IMPL"           = "org.apache.iceberg.azure.adls.AzureDataLakeFileIO"
      "CATALOG_S3_ENDPOINT"        = "https://${azurerm_storage_account.iceberg_storage.name}.dfs.core.windows.net"
      "CATALOG_S3_PATH_STYLE_ACCESS" = "true"
    }

    secure_environment_variables = {
      "AWS_ACCESS_KEY_ID"       = azurerm_storage_account.iceberg_storage.name
      "AWS_SECRET_ACCESS_KEY"   = azurerm_storage_account.iceberg_storage.primary_access_key
      "AZURE_STORAGE_ACCOUNT"   = azurerm_storage_account.iceberg_storage.name
      "AZURE_STORAGE_ACCESS_KEY" = azurerm_storage_account.iceberg_storage.primary_access_key
    }

    ports {
      port     = 8181
      protocol = "TCP"
    }
  }

  tags = var.tags
}

# Fallback manual container deployment instructions if container deployment is disabled
resource "null_resource" "container_reminder" {
  count = var.deploy_container ? 0 : 1
  
  provisioner "local-exec" {
    command = <<EOT
      echo "=== CONTAINER DEPLOYMENT REMINDER ==="
      echo "The Iceberg REST catalog container group was not deployed automatically."
      echo "To deploy it manually later, run:"
      echo "az container create --resource-group ${var.resource_group_name} \\"
      echo "  --name ${var.base_name}-iceberg-rest-catalog \\"
      echo "  --image tabulario/iceberg-rest:0.5.0 \\"
      echo "  --cpu 1 --memory 1.5 \\"
      echo "  --ip-address Private \\"
      echo "  --subnet-ids '${join("','", var.subnet_ids)}' \\"
      echo "  --registry-username YOUR_DOCKER_USERNAME \\"
      echo "  --registry-password YOUR_DOCKER_PASSWORD \\"
      echo "  --environment-variables 'AWS_REGION=us-east-1' 'CATALOG_WAREHOUSE=s3a://warehouse' \\"
      echo "  'CATALOG_IO__IMPL=org.apache.iceberg.azure.adls.AzureDataLakeFileIO' \\"
      echo "  'CATALOG_S3_ENDPOINT=https://${azurerm_storage_account.iceberg_storage.name}.dfs.core.windows.net' \\"
      echo "  'CATALOG_S3_PATH_STYLE_ACCESS=true' \\"
      echo "  --secure-environment-variables 'AWS_ACCESS_KEY_ID=${azurerm_storage_account.iceberg_storage.name}' \\"
      echo "  'AWS_SECRET_ACCESS_KEY=${azurerm_storage_account.iceberg_storage.primary_access_key}' \\"
      echo "  'AZURE_STORAGE_ACCOUNT=${azurerm_storage_account.iceberg_storage.name}' \\"
      echo "  'AZURE_STORAGE_ACCESS_KEY=${azurerm_storage_account.iceberg_storage.primary_access_key}'"
      echo "=== END REMINDER ==="
    EOT
  }
  
}