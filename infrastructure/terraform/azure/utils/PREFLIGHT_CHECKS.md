# Terraform Pre-Flight Environment Checks

This document describes the pre-flight environment check system implemented for Terraform operations in the Sentimark project.

## Overview

The Terraform pre-flight check system performs comprehensive validation of the Azure environment before executing Terraform operations. This helps prevent common deployment failures by catching issues early, such as:

1. Authentication and permission problems
2. Missing resource provider registrations
3. Quota limitations that would block deployments
4. Network connectivity issues
5. State storage configuration problems
6. Security and compliance concerns

## Components

The pre-flight check system consists of two main components:

### 1. `tf_preflight.sh` - Core Pre-Flight Check Utility

This script performs all the actual validation checks against the Azure environment. It can:

- Validate Azure authentication
- Check service principal permissions
- Verify state storage access
- Ensure resource providers are registered
- Validate subscription quotas
- Test network connectivity
- Verify Terraform configuration syntax
- Check for security best practices

### 2. `tf_preflight_wrapper.sh` - Integration Wrapper

This script integrates pre-flight checks with the existing `run-terraform.sh` script:

- Determines environment context from Terraform arguments
- Runs pre-flight checks before Terraform operations
- Supports skipping checks or continuing despite failures
- Passes through all Terraform arguments to `run-terraform.sh`

## Usage

### Running Pre-Flight Checks Before Terraform Operations

Instead of directly running `run-terraform.sh`, use the wrapper:

```bash
# Run pre-flight checks before planning
./utils/tf_preflight_wrapper.sh plan

# With specific environment
./utils/tf_preflight_wrapper.sh --preflight-env prod plan

# With regular Terraform options
./utils/tf_preflight_wrapper.sh -var 'foo=bar' plan
```

### Running Only Pre-Flight Checks

```bash
# Run only pre-flight checks without Terraform
./utils/tf_preflight_wrapper.sh --preflight-only --preflight-env prod

# Run focused checks
./utils/tf_preflight_wrapper.sh --preflight-only --preflight-option "--no-quota-check"
```

### Skipping Pre-Flight Checks

```bash
# Skip pre-flight checks
./utils/tf_preflight_wrapper.sh --no-preflight plan

# Continue despite pre-flight failures
./utils/tf_preflight_wrapper.sh --skip-on-failure plan
```

### Running Pre-Flight Checks Directly

You can also run the pre-flight utility directly:

```bash
# Basic usage
./utils/tf_preflight.sh --environment sit

# With all options
./utils/tf_preflight.sh --environment prod --backend backends/prod.tfbackend --verbose --output json
```

## Checks Performed

### 1. Azure Authentication and Permissions

- Verifies Azure CLI installation and login
- Checks service principal validity and permissions
- Validates role assignments at subscription and resource levels
- Specialized checks for AKS if Kubernetes is used

### 2. State Storage Validation

- Verifies access to storage account and container
- Tests blob read and write operations
- Validates lease operations (needed for state locking)
- Checks for existing state file and locked state

### 3. Resource Provider Registration

- Detects provider usage in Terraform code
- Checks registration status of required providers
- Provides instructions for registering missing providers

### 4. Quota and Limits

- Checks core quotas for VM families
- Validates public IP address limits
- Detects high usage percentages that could block deployment

### 5. Network Connectivity

- Tests connectivity to critical Azure endpoints
- Validates DNS resolution for required services
- Checks for proxy or firewall issues

### 6. Terraform Syntax

- Validates Terraform configuration
- Checks for deprecated syntax patterns
- Verifies provider version constraints

### 7. Security and Compliance

- Enforces security best practices
- Checks for public resource exposure
- Validates encryption settings
- Environment-specific security rules (stricter for prod)

## Customization

Pre-flight checks can be customized for different environments:

### 1. Environment-Specific Checks

The script applies different validation rules based on the environment:

- **SIT**: Basic validation with relaxed quota checks
- **UAT**: Medium strictness, validates integrations
- **PROD**: Strict validation with additional security checks

### 2. Selective Checks

You can skip specific checks that may be slow or unnecessary:

```bash
# Skip quota checks (faster)
./utils/tf_preflight.sh --no-quota-check

# Skip network checks
./utils/tf_preflight.sh --no-network-check

# Run minimal checks
./utils/tf_preflight.sh --no-quota-check --no-network-check --no-security-check
```

### 3. Output Formats

Pre-flight checks can generate reports in multiple formats:

```bash
# Default text output
./utils/tf_preflight.sh

# JSON output for integration with other tools
./utils/tf_preflight.sh --output json > report.json

# Markdown report
./utils/tf_preflight.sh --output markdown
```

## Integration with CI/CD

For CI/CD pipelines, pre-flight checks can be integrated as a separate verification step:

```yaml
- name: Run Terraform Pre-Flight Checks
  run: |
    cd infrastructure/terraform/azure
    ./utils/tf_preflight.sh --environment ${{ env.ENVIRONMENT }} --output json > preflight.json
    
- name: Check Pre-Flight Results
  run: |
    PREFLIGHT_STATUS=$(jq -r '.status' preflight.json)
    if [ "$PREFLIGHT_STATUS" != "Passed" ]; then
      echo "::warning::Pre-flight checks did not pass: $PREFLIGHT_STATUS"
      jq -r '.results[] | select(.level == "ERROR" or .level == "WARNING") | .message' preflight.json
      exit 1
    fi
```

## Error Handling

Pre-flight checks classify issues into:

- **Errors**: Critical issues that will definitely cause deployment failure
- **Warnings**: Potential issues that may cause problems

By default, the utility fails on errors but continues with warnings. This behavior can be customized with the `--skip-warnings` flag.

## Best Practices

1. **Always Run Pre-Flight Checks**: Run pre-flight checks before all production deployments
2. **Address Warnings**: Don't ignore warnings, as they often indicate real issues
3. **Customize for Environment**: Use stricter checks for production
4. **Automate**: Integrate pre-flight checks into your CI/CD pipelines
5. **Update Tests**: When you encounter new failure modes, add them to the pre-flight checks

## Troubleshooting

If pre-flight checks fail:

1. **Review Reports**: Check the detailed report for specific issues
2. **Fix Permissions**: Most common issues are related to insufficient permissions
3. **Register Providers**: Ensure all required resource providers are registered
4. **Check Quotas**: Request quota increases well in advance of deployments
5. **Validate Access**: Ensure service principals can access all required resources