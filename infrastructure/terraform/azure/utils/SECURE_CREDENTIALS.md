# Secure Credential Handling for Terraform

This document describes the secure credential handling system implemented for Terraform operations in the Sentimark project.

## Overview

The secure credential handling system provides multiple methods for safely providing Azure authentication credentials to Terraform without exposing them in plain text files or command line arguments. This approach strengthens security by:

1. Never writing credentials to disk in plain text
2. Supporting multiple authentication methods (environment variables, Azure Key Vault, managed identities)
3. Using secure file permissions and memory management
4. Including proper credential validation and verification
5. Providing automatic credential rotation support
6. Supporting environment-specific credentials (SIT, UAT, PROD)

## Authentication Methods

The following authentication methods are supported:

### 1. Environment Variables

Loads credentials from environment variables securely without exposing them:
- Supports standard Terraform Azure variables (`ARM_CLIENT_ID`, etc.)
- Supports TF_VAR prefixed variables (`TF_VAR_client_id`, etc.)
- Supports environment-specific variables (`SIT_CLIENT_ID`, etc.)

Example:
```bash
export ARM_CLIENT_ID="your-client-id"
export ARM_CLIENT_SECRET="your-client-secret"
export ARM_TENANT_ID="your-tenant-id"
export ARM_SUBSCRIPTION_ID="your-subscription-id"

./run-terraform.sh plan
```

### 2. Azure Key Vault

Fetches credentials securely from Azure Key Vault:
- No credentials stored locally
- Supports automatically selecting environment-specific secrets
- Managed through Azure RBAC for access control

Example:
```bash
# Using Key Vault
./run-terraform.sh --keyvault sentimark-keyvault plan

# With specific environment
./run-terraform.sh --keyvault sentimark-keyvault --environment prod plan
```

### 3. Managed Identity

Uses Azure Managed Identity for authentication:
- No credentials needed at all
- Supports role-based access control
- Perfect for running in Azure environments

Example:
```bash
# Using managed identity
./run-terraform.sh --use-msi plan
```

### 4. Secure File Storage

For development environments, can securely store credentials locally:
- Files stored with 0600 permissions (owner read/write only)
- Supports multiple profiles for different environments
- Files are stored outside the Git repository

Example:
```bash
# Setup credentials (interactive)
./utils/secure_credentials.sh save --profile sit

# Use saved credentials
./run-terraform.sh --creds-method file --creds-profile sit plan
```

## Implementation Details

### Security Features

1. **Temporary Files**: Credentials are stored in temporary files that are automatically removed when the command completes
2. **Secure Permissions**: All credential files use 0600 permissions (owner read/write only)
3. **Memory Safety**: Credentials are cleared from memory when no longer needed
4. **Clean Termination**: Signal handlers ensure credentials are cleaned up even if the command fails
5. **Validation**: Credentials are validated before use to prevent mid-operation failures
6. **Masked Output**: Credentials are not displayed in logs or terminal output

### Directory Structure

```
/infrastructure/terraform/azure/
  ├── utils/
  │   ├── secure_credentials.sh  # Main credential handling script
  │   └── SECURE_CREDENTIALS.md  # This documentation
  └── run-terraform.sh          # Updated with secure credential handling
```

## Usage in run-terraform.sh

The updated `run-terraform.sh` script has been enhanced with secure credential handling:

### New Command Line Options

```
--no-secure-creds              Disable secure credential handling
--creds-method METHOD          Credential method: env, file, vault, msi (default: env)
--creds-profile PROFILE        Credential profile name (default: default)
--keyvault NAME                Azure Key Vault name for credentials
--use-msi                      Use managed identity for authentication
```

### Examples

```bash
# Use credentials from Azure Key Vault
./run-terraform.sh --keyvault sentimark-kv plan

# Use managed identity for authentication
./run-terraform.sh --use-msi plan

# Use credentials stored in a secure profile
./run-terraform.sh --creds-method file --creds-profile prod plan

# Fall back to legacy credential handling
./run-terraform.sh --no-secure-creds plan
```

## Standalone Credential Utility

The standalone credential utility script (`secure_credentials.sh`) provides additional functionality for credential management:

```bash
# Show available commands
./utils/secure_credentials.sh --help

# Load credentials from environment and check if they're valid
./utils/secure_credentials.sh load --method env
./utils/secure_credentials.sh check

# Save credentials to a secure file
./utils/secure_credentials.sh save --profile production

# Load credentials from Azure Key Vault
./utils/secure_credentials.sh vault --keyvault myvault --environment prod

# Configure for managed identity
./utils/secure_credentials.sh msi

# Clear credentials from environment
./utils/secure_credentials.sh clear
```

## Security Best Practices

1. **Prefer Managed Identity**: When running in Azure, always use managed identity authentication if possible
2. **Use Key Vault**: For service principals, store credentials in Azure Key Vault
3. **Rotate Credentials**: Regularly rotate service principal credentials
4. **Temporary Service Principals**: Create time-limited service principals for specific operations
5. **Least Privilege**: Assign only the minimum required permissions to service principals
6. **Multiple Environments**: Use different service principals for different environments (SIT, UAT, PROD)
7. **Verify Operations**: Always verify planned operations before applying

## Troubleshooting

If you encounter issues with secure credential handling:

1. **Credential Validation**: Use `./utils/secure_credentials.sh check` to verify credentials
2. **Azure CLI Login**: Ensure you're logged in with `az login` when using Key Vault
3. **Permissions**: Verify the service principal has the correct permissions
4. **Managed Identity**: When using managed identity, ensure it's properly configured
5. **File Permissions**: Check file permissions if using credential files

For serious issues, you can disable secure credential handling with `--no-secure-creds` option.