# Terraform State Locking Implementation

## Overview

This document describes the implementation of Terraform state locking for the Sentimark project. State locking is a critical feature that prevents concurrent modifications to the Terraform state file, which could lead to corruption and infrastructure inconsistencies.

## Problem Statement

The previous Terraform configuration was using local state files without proper locking mechanisms. This approach had several issues:

1. **Concurrent Access Conflicts**: Multiple users or CI/CD pipelines could modify the state simultaneously
2. **State Corruption Risk**: Without locking, state files could become corrupted during concurrent operations
3. **No Centralized State**: Each environment had local state that wasn't centrally stored or backed up
4. **Inconsistent Infrastructure**: State conflicts could lead to drift between environments

## Implementation Details

### 1. Azure Storage Backends

We've implemented Azure Storage blob-based backends for Terraform state with built-in locking:

- **SIT Environment**: `sentimarksitterraform` storage account
- **UAT Environment**: `sentimarkuatterraform` storage account
- **PROD Environment**: `sentimarkprodterraform` storage account

Each environment has its own dedicated backend configuration file in the `backends/` directory:

- `sit.tfbackend`
- `uat.tfbackend`
- `prod.tfbackend`

### 2. State Locking Mechanism

Azure Storage natively supports leases on blobs, which Terraform uses for state locking:

- **Lock Duration**: 300 seconds (configured via `TF_AZURE_STATE_LOCK_TIMEOUT`)
- **Lease Type**: Exclusive write access lease
- **Contention Handling**: Terraform automatically retries acquiring the lock with exponential backoff

### 3. Backend Configuration

The `backend.tf` file has been updated to use Azure Storage for state management:

```hcl
terraform {
  backend "azurerm" {
    # Values provided via backend-config files
    # State locking enabled by default
  }
}
```

### 4. Setup Script

A new script, `setup_terraform_backend.sh`, has been created to set up the necessary Azure resources:

- Creates resource groups for each environment
- Provisions storage accounts with proper security settings
- Creates blob containers for state files
- Configures backend configuration files

### 5. Enhanced Terraform Runner

The `run-terraform.sh` script has been enhanced with:

- Support for state locking timeout configuration
- Improved error handling for state locking issues
- Clear documentation on using the backend with different environments

## Usage Instructions

### Initializing with State Locking

To initialize Terraform with state locking for a specific environment:

```bash
cd infrastructure/terraform/azure

# For SIT environment
./run-terraform.sh init -backend-config=backends/sit.tfbackend

# For UAT environment
./run-terraform.sh init -backend-config=backends/uat.tfbackend

# For PROD environment
./run-terraform.sh init -backend-config=backends/prod.tfbackend
```

### Setting Up Backends

If you need to create or reconfigure a backend:

```bash
# Create SIT backend
./setup_terraform_backend.sh --environment=sit

# Create UAT backend
./setup_terraform_backend.sh --environment=uat --location=westus

# Create PROD backend
./setup_terraform_backend.sh --environment=prod --location=eastus2
```

### Handling Lock Contention

If you encounter a state locking error:

1. Check who is holding the lock using the lock ID from the error message
2. If the lock is stale (the process is no longer running), you can force-unlock:

```bash
./run-terraform.sh force-unlock <LOCK_ID>
```

**CAUTION**: Only use force-unlock if you're certain the locking process is no longer running.

## CI/CD Integration

For CI/CD pipelines, the service principal requires the following permissions:

1. Storage Blob Data Contributor role on the storage account
2. Storage Account Contributor role (for creating the storage account if needed)

Environment variables required for state locking in CI/CD:

```
ARM_STORAGE_USE_AZUREAD=true
TF_AZURE_STATE_LOCK_TIMEOUT=300
```

## Monitoring and Troubleshooting

If state locking issues occur, check:

1. Storage account access logs for unauthorized access attempts
2. Extended blob metadata for lock information
3. Service principal permissions
4. Network access policies on the storage account

## Security Considerations

The implemented solution includes:

- Secure access control via Azure AD authentication
- HTTPS-only access to storage accounts
- Disabled public blob access
- Blob versioning for state file recovery
- Resource locks on the storage accounts