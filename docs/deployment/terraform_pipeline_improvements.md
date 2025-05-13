# Terraform Pipeline Improvements

## Overview

This document details the improvements made to the Terraform CI/CD pipeline for the Sentimark project. These changes address stability issues, state locking problems, and enhance the overall CI/CD workflow for infrastructure deployment.

## Issues Addressed

1. **State Locking Issues**: Previously, Terraform state locking was not properly implemented, leading to concurrent modification risks
2. **Manual Pipeline Execution**: The CI/CD workflow lacked proper automation for Terraform operations
3. **Error Handling**: Pipeline jobs didn't handle common Terraform errors properly
4. **Environment Separation**: Lack of clear separation between environments (SIT, UAT, PROD)
5. **Monitoring and Validation**: Insufficient validation of deployed infrastructure

## Implemented Solutions

### 1. Terraform State Locking

We've implemented Azure Blob Storage-based state locking:

- Created environment-specific backend configurations (`sit.tfbackend`, `uat.tfbackend`, `prod.tfbackend`)
- Enabled Azure lease-based state locking with extended timeout (600 seconds, up from 300 seconds)
- Added proper error handling for state lock contentions with retry mechanisms
- Created setup script (`setup_terraform_backend.sh`) to provision backend resources
- Added a reusable state locking module in `modules/state-locking/` for consistent configuration

### 2. Enhanced CI/CD Workflow

A new GitHub Actions workflow (`terraform-cicd.yml`) has been created with:

- Separate jobs for validation, planning, applying, and destroying
- Environment-specific handling (SIT, UAT, PROD)
- Manual approval gates for sensitive operations
- Artifact management for Terraform plans
- Clear logging and error reporting
- Concurrency control to prevent multiple workflows running for the same environment
- Cancel-in-progress capability for non-production environments
- Automatic stale lock detection and resolution (for non-production environments)
- Intelligent retry mechanisms for common errors

### 3. Enhanced Terraform Runners

The main `run-terraform.sh` script has been updated with:

- Configurable timeout parameters via command-line flags
- Debug mode option for troubleshooting
- Enhanced error detection and improved recovery suggestions
- Comprehensive logging for better visibility
- Support for lock retries and configurable lock parameters

Additionally, the CI-optimized runner script (`run_terraform_ci.sh`) has been improved with:

- Better error handling and reporting
- Support for different environments and workspaces
- Automatic backend selection
- Support for cost management module isolation
- Artifact generation for CI systems
- Integration with the new state locking module

### 4. Security Improvements

- Azure AD-based authentication for state access
- Service principal permissions management
- Secure handling of credentials using GitHub Secrets
- Protection against destructive operations with confirmation steps

## Usage Instructions

### Running the Terraform Pipeline Manually

To manually trigger the Terraform pipeline:

1. Go to the GitHub Actions tab in the repository
2. Select the "Terraform CI/CD Pipeline" workflow
3. Click "Run workflow"
4. Select the desired environment (sit, uat, prod)
5. Choose the action (plan, apply, destroy)
6. Click "Run workflow"

### Setting Up CI/CD Secrets

The following secrets are required in GitHub repository settings:

```
AZURE_CLIENT_ID
AZURE_CLIENT_SECRET
AZURE_TENANT_ID
AZURE_SUBSCRIPTION_ID
```

### Local Testing of CI Pipeline

To test the CI pipeline locally:

```bash
cd infrastructure/terraform/azure

# Set required environment variables
export ARM_CLIENT_ID="your-client-id"
export ARM_CLIENT_SECRET="your-client-secret"
export ARM_TENANT_ID="your-tenant-id"
export ARM_SUBSCRIPTION_ID="your-subscription-id"

# Run with desired environment and action
./run_terraform_ci.sh --environment=sit --action=plan
```

## Workflow Design

### Pipeline Stages

1. **Validate**: Format check and validation without backend initialization
2. **Plan**: Initialize backend, create execution plan, save as artifact
3. **Apply**: Apply the plan from artifact with proper state locking
4. **Destroy**: Requires manual approval and confirmation

### Environment Handling

- Main branch deployments target production by default
- Develop branch deployments target UAT by default
- Pull requests target SIT environment for testing
- Manual workflow triggers can specify any environment

### Branch Protection Rules

For complete pipeline security, we recommend adding these branch protection rules:

- Require status checks to pass before merging (terraform-cicd)
- Require conversations to be resolved before merging
- Require signed commits
- Include administrators in these restrictions

## Monitoring and Troubleshooting

### Common State Locking Issues

If you encounter state locking issues:

1. Check the error message for the lock ID (now easier to find with enhanced diagnostics)
2. Verify if the locking process is still running
3. Look for lock holder information and lock age in the error message
4. For non-production environments, consider using the auto-unlock feature:
   - In CI/CD: The pipeline will attempt to auto-unlock stale locks (>30 minutes old)
   - Locally: Use `./run-terraform.sh force-unlock <LOCK_ID>`
5. Examine Azure storage logs for unauthorized access attempts
6. If problems persist, adjust the lock timeout with `--lock-timeout=<SECONDS>`

### Pipeline Workflow Issues

If the pipeline fails:

1. Check the GitHub Actions logs for error messages
2. Verify that the service principal has required permissions
3. Check the Terraform logs for detailed error information
4. Validate that the backend storage accounts are accessible

## Best Practices

1. **Never commit secrets** to the repository
2. **Always plan before applying** changes
3. **Use workspaces** for feature development
4. **Review plans carefully** before applying
5. **Test changes in SIT** before promoting to UAT/PROD
6. **Use meaningful commit messages** for infrastructure changes
7. **Document all manual operations** performed outside the pipeline