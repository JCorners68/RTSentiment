# Secure Azure Credential System Implementation

This document outlines the secure credential system implemented for Terraform deployments in the Sentimark project.

## System Components

1. **Secure Credential Storage**
   - Pass password manager with GPG encryption
   - Hierarchical structure under `sentimark/azure/` namespace
   - Integration with Azure Key Vault for centralized credential management

2. **Credential Synchronization**
   - Script: `~/.sentimark/bin/sync-azure-credentials.sh`
   - Synchronizes credentials between Azure Key Vault and local pass store
   - Handles initial setup of Key Vault and pass/GPG if needed

3. **Environment Variable Loading**
   - Script: `~/.sentimark/bin/load-terraform-env.sh` 
   - Loads credentials into environment variables for Terraform
   - Supports both TF_VAR_* and ARM_* variable formats

4. **Terraform Configuration Templates**
   - Templates for providers.tf and backend configurations
   - Separate backend configurations for different environments (SIT, UAT)
   - Located in `/home/jonat/real_senti/infrastructure/terraform/azure/templates/`

5. **Terraform Initialization**
   - Script: `/home/jonat/real_senti/infrastructure/terraform/azure/init-terraform.sh`
   - Creates Terraform configuration files from templates
   - Loads credentials from secure storage

## Usage Instructions

### Initial Setup

1. **Install Required Tools**
   ```bash
   sudo apt-get update
   sudo apt-get install -y pass gnupg2
   ```

2. **Set Up GPG Key** (if not already done)
   ```bash
   gpg --full-generate-key
   # Follow the prompts to create a key
   ```

3. **Initialize Pass** (if not already done)
   ```bash
   pass init "Your GPG Key ID or Email"
   ```

4. **Sync Credentials from Azure Key Vault**
   ```bash
   ~/.sentimark/bin/sync-azure-credentials.sh
   ```

### Using the Secure Credentials

1. **Initialize Terraform Configuration**
   ```bash
   cd /home/jonat/real_senti/infrastructure/terraform/azure
   ./init-terraform.sh
   ```

2. **Run Terraform Commands**
   ```bash
   source ~/.sentimark/bin/load-terraform-env.sh
   terraform init -backend-config=backends/sit.tfbackend
   terraform plan -out=tfplan.sit
   terraform apply tfplan.sit
   ```

## Security Considerations

- Credentials are never stored in plaintext files
- GPG encryption provides strong security for stored credentials
- Azure Key Vault provides centralized credential management
- Environment variables are only loaded in the current shell session
- Template files never contain actual credentials
- Timestamp tracking for generated configuration files

## Maintenance

To update credentials:

1. Update in Azure Key Vault
2. Run `~/.sentimark/bin/sync-azure-credentials.sh` to sync locally
3. No changes to Terraform configuration files are needed

## Verification

Verify the setup is working correctly:

```bash
# Ensure credentials are properly stored in pass
pass ls sentimark/azure

# Verify credentials can be loaded into environment
source ~/.sentimark/bin/load-terraform-env.sh
env | grep -E "(TF_VAR_|ARM_)" | wc -l  # Should show 8 variables
```