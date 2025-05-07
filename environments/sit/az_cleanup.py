#!/usr/bin/env python3

import os
import sys
from azure.identity import ClientSecretCredential
from azure.mgmt.resource import ResourceManagementClient

# Get credentials from environment variables
subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID")
tenant_id = os.environ.get("AZURE_TENANT_ID")
client_id = os.environ.get("AZURE_CLIENT_ID")
client_secret = os.environ.get("AZURE_CLIENT_SECRET")
resource_group = os.environ.get("AZURE_RESOURCE_GROUP")

print(f"Deleting resource group {resource_group}...")

# Create credential object
credential = ClientSecretCredential(
    tenant_id=tenant_id,
    client_id=client_id,
    client_secret=client_secret
)

# Create resource client
resource_client = ResourceManagementClient(credential, subscription_id)

# Check if resource group exists
try:
    rg = resource_client.resource_groups.get(resource_group)
    print(f"Resource group {resource_group} found in {rg.location}")
    
    # Delete resource group
    print(f"Starting deletion of resource group {resource_group}...")
    delete_operation = resource_client.resource_groups.begin_delete(resource_group)
    
    # This will block until the deletion is complete
    # Set wait to False if you want to return immediately
    print("Deletion started. This may take several minutes...")
    delete_operation.wait()
    
    print(f"Resource group {resource_group} deleted successfully")
except Exception as e:
    print(f"Error: {str(e)}")
    sys.exit(1)

# Clean up local configuration files
print("Cleaning up local configuration files...")
