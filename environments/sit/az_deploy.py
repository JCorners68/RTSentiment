#!/usr/bin/env python3

import os
import sys
import time
import json
from datetime import datetime
from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.storage import StorageManagementClient

# Get credentials from environment variables
subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
tenant_id = os.environ.get("AZURE_TENANT_ID")
client_id = os.environ.get("AZURE_CLIENT_ID")
client_secret = os.environ.get("AZURE_CLIENT_SECRET")
resource_group = os.environ.get("AZURE_RESOURCE_GROUP")
location = os.environ.get("AZURE_LOCATION")
aks_cluster = os.environ.get("AZURE_AKS_CLUSTER")
script_dir = os.environ.get("SCRIPT_DIR")

print(f"Deploying SIT environment to Azure...")
print(f"Subscription: {subscription_id}")
print(f"Resource Group: {resource_group}")
print(f"Location: {location}")
print(f"AKS Cluster: {aks_cluster}")

# Create credential object
credential = ClientSecretCredential(
    tenant_id=tenant_id,
    client_id=client_id,
    client_secret=client_secret
)

# Create clients
resource_client = ResourceManagementClient(credential, subscription_id)
aks_client = ContainerServiceClient(credential, subscription_id)
storage_client = StorageManagementClient(credential, subscription_id)

# 1. Create or update the resource group
print(f"Creating or checking resource group {resource_group}...")
try:
    # Check if resource group exists first
    rg = resource_client.resource_groups.get(resource_group)
    print(f"Resource group {resource_group} already exists in {rg.location}")
    # Update our location to match existing resource group
    location = rg.location
except Exception as e:
    print(f"Resource group does not exist, creating in {location}...")
    resource_client.resource_groups.create_or_update(
        resource_group,
        {"location": location}
    )

# 2. Create or get AKS cluster
print(f"Checking for existing AKS cluster {aks_cluster}...")

try:
    # Check if cluster already exists
    existing_cluster = aks_client.managed_clusters.get(resource_group, aks_cluster)
    print(f"AKS cluster {aks_cluster} already exists.")
    print(f"Using existing AKS cluster: {existing_cluster.name}")
    aks_result = existing_cluster
except Exception as e:
    # Cluster doesn't exist, create it
    print(f"Creating AKS cluster {aks_cluster}...")
    print("This will take several minutes...")
    try:
        aks_op = aks_client.managed_clusters.begin_create_or_update(
            resource_group,
            aks_cluster,
            {
                "location": location,
                "identity": {
                    "type": "SystemAssigned"
                },
                "agent_pool_profiles": [
                    {
                        "name": "agentpool",
                        "count": 1,
                        "vm_size": "Standard_B2s",
                        "mode": "System"
                    },
                    {
                        "name": "datanodes",
                        "count": 1,
                        "vm_size": "Standard_B2s",
                        "mode": "User"
                    }
                ],
                "dns_prefix": aks_cluster
            }
        )
        aks_result = aks_op.result()
        print(f"AKS cluster created: {aks_result.name}")
    except Exception as e:
        print(f"Error creating AKS cluster: {str(e)}")
        sys.exit(1)

# 3. Create or get Storage Account
storage_name = "sentimarksitstorage"
print(f"Checking for existing storage account {storage_name}...")

try:
    # Check if storage account already exists
    existing_storage = storage_client.storage_accounts.get_properties(resource_group, storage_name)
    print(f"Storage account {storage_name} already exists.")
    storage_result = existing_storage
except Exception as e:
    # Storage account doesn't exist, create it
    print(f"Creating storage account {storage_name}...")
    try:
        storage_op = storage_client.storage_accounts.begin_create(
            resource_group,
            storage_name,
            {
                "location": location,
                "kind": "StorageV2",
                "sku": {
                    "name": "Standard_LRS"
                }
            }
        )
        storage_result = storage_op.result()
        print(f"Storage account created: {storage_result.name}")
    except Exception as e:
        print(f"Error creating storage account: {str(e)}")
        sys.exit(1)

# Get storage keys and save connection string regardless of whether account was created or already existed
try:
    keys = storage_client.storage_accounts.list_keys(resource_group, storage_name)
    storage_key = keys.keys[0].value
    storage_connection = f"DefaultEndpointsProtocol=https;AccountName={storage_name};AccountKey={storage_key};EndpointSuffix=core.windows.net"
    
    # Save connection string to a file
    connection_file = os.path.join(script_dir, "config", "storage_connection.txt")
    with open(connection_file, "w") as f:
        f.write(storage_connection)
    print(f"Storage connection string saved to {connection_file}")
except Exception as e:
    print(f"Error getting storage keys: {str(e)}")

# 4. Get AKS Credentials
print("Getting AKS credentials...")
try:
    credentials = aks_client.managed_clusters.list_cluster_admin_credentials(
        resource_group,
        aks_cluster
    )
    # Save kubeconfig
    kubeconfig_path = os.path.join(script_dir, "config", "kubeconfig")
    with open(kubeconfig_path, "wb") as f:
        f.write(credentials.kubeconfigs[0].value)
    os.chmod(kubeconfig_path, 0o600)
    print(f"Kubeconfig saved to {kubeconfig_path}")
except Exception as e:
    print(f"Error getting AKS credentials: {str(e)}")

# 5. Save cluster information
cluster_info_path = os.path.join(script_dir, "config", "cluster_info.txt")
with open(cluster_info_path, "w") as f:
    f.write(f"AKS Cluster Name: {aks_cluster}\n")
    f.write(f"Resource Group: {resource_group}\n")
    f.write(f"Environment: SIT\n")
    f.write(f"Location: {location}\n")
    f.write(f"Deployed on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    f.write(f"Subscription ID: {subscription_id}\n")
    f.write(f"Tenant ID: {tenant_id}\n")
    f.write(f"Storage Account: {storage_name}\n")

# 6. Save deployment status to log file
log_file = os.path.join(script_dir, "logs", f"deployment_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
os.makedirs(os.path.dirname(log_file), exist_ok=True)

deployment_log = {
    "timestamp": datetime.now().isoformat(),
    "resource_group": resource_group,
    "location": location,
    "aks_cluster": aks_cluster,
    "storage_account": storage_name,
    "status": "completed"
}

with open(log_file, "w") as f:
    json.dump(deployment_log, f, indent=2)

# 7. Output deployment information
print("\nDeployment completed!")
print(f"Resource Group: {resource_group}")
print(f"AKS Cluster: {aks_cluster}")
print(f"Storage Account: {storage_name}")
print(f"Kubeconfig: {kubeconfig_path}")
print(f"Deployment log: {log_file}")
print("\nTo deploy services, run:")
print(f"export KUBECONFIG={kubeconfig_path}")
print("./deploy_services.sh")
