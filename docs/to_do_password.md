# Password and Secret Rotation To-Do

## Affected Resources

Based on the repository security scan, the following Azure resources need credential rotation:

### 1. Azure Storage Account
- **Files containing credentials**: 
  - `/environments/sit/config/storage_connection.txt`
  - `/infrastructure/terraform/azure/terraform.tfstate`
  - `/infrastructure/terraform/azure/terraform.tfstate.backup`
- **Command to generate new key**:
  ```bash
  # Replace RESOURCE_GROUP_NAME and STORAGE_ACCOUNT_NAME with your actual values
  az storage account keys renew --resource-group RESOURCE_GROUP_NAME --account-name STORAGE_ACCOUNT_NAME --key key1 --query "[0].value" -o tsv
  ```

### 2. Azure Container Registry
- **Files containing credentials**:
  - `/infrastructure/terraform/azure/terraform.tfstate`
  - `/infrastructure/terraform/azure/terraform.tfstate.backup`
- **Command to regenerate credentials**:
  ```bash
  # Replace RESOURCE_GROUP_NAME and REGISTRY_NAME with your actual values
  az acr credential renew --name REGISTRY_NAME --resource-group RESOURCE_GROUP_NAME --password-name password1 --query "passwords[0].value" -o tsv
  ```

### 3. Azure Active Directory Application (Service Principal)
- **Files containing credentials**:
  - `/infrastructure/terraform/azure/providers.tf`
  - `/environments/sit/DEPLOYMENT_INSTRUCTIONS.md`
  - `/environments/sit/continue_deploy.sh`
  - `/infrastructure/terraform/azure/backends/sit.tfbackend`
- **Command to create new client secret**:
  ```bash
  # Replace APPLICATION_ID with your actual app ID (client ID)
  # Replace SECRET_DISPLAY_NAME with a name for the new secret
  az ad app credential reset --id APPLICATION_ID --display-name SECRET_DISPLAY_NAME --query "password" -o tsv
  ```

## Steps to Update Credentials

1. Run the above commands to generate new credentials
2. Update the credentials in your local environment files
3. Update any deployed resources that depend on these credentials
4. Do not commit the actual credentials to the repository
5. Consider using Azure Key Vault or environment variables for credential management

## Best Practices Moving Forward

1. **Never commit credentials to Git repositories**
2. Use environment variables for local development
3. For CI/CD pipelines, use secure secret storage:
   - GitHub Secrets
   - Azure Key Vault
   - Azure Managed Identities where possible
4. Add sensitive file patterns to `.gitignore`
5. Add a pre-commit hook to detect secrets before they're committed
6. Run `git-secrets` or similar tool as part of CI/CD
7. Use service principals with least privilege access
8. Rotate credentials regularly (every 90 days recommended)

## Files to Clean Up

Add these patterns to `.gitignore`:
```
*.tfstate
*.tfstate.backup
terraform.tfvars
*.tfbackend
storage_connection.txt
kubeconfig
*.key
*.pem
config/storage_connection.txt
```