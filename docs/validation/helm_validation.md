# Helm Chart Validation Documentation

This document provides comprehensive guidance on validating Helm charts in the Sentimark project, with specific emphasis on Azure DevOps integration and AKS-specific requirements.

## Table of Contents

1. [Overview](#overview)
2. [Validation Tools](#validation-tools)
3. [Validation Checks](#validation-checks)
4. [Azure DevOps Integration](#azure-devops-integration)
5. [AKS-Specific Considerations](#aks-specific-considerations)
6. [Usage Examples](#usage-examples)
7. [Troubleshooting](#troubleshooting)
8. [Best Practices](#best-practices)

## Overview

Helm chart validation is a critical component of the Sentimark CI/CD pipeline that ensures all Kubernetes deployments follow best practices, security guidelines, and schema-defined structures. Validation happens at various stages of the development lifecycle:

- Pre-commit (local development)
- Pull request (CI pipeline)
- Build pipeline (CI/CD)
- Release pipeline (CD)

The validation tools are designed to catch issues early in the development process, prevent misconfigurations from reaching production, and ensure consistency across all environments.

## Validation Tools

The Sentimark project includes several tools for Helm chart validation:

### helm_schema_validator.sh

**Location**: `/home/jonat/real_senti/scripts/helm_schema_validator.sh`

A comprehensive validation tool that performs:

- Schema validation using values.schema.json
- Template rendering verification
- Kubernetes resource validation
- Security context placement checking
- Common misconfigurations detection

```bash
/home/jonat/real_senti/scripts/helm_schema_validator.sh --chart-dir /path/to/chart --values /path/to/values.yaml
```

### helm_schema_validator_azure.sh

**Location**: `/home/jonat/real_senti/scripts/helm_schema_validator_azure.sh`

An enhanced version specifically optimized for Azure DevOps with:

- Automatic dependency detection and installation
- Azure Pipeline-specific path handling
- AKS-specific security checks
- Integration with Azure DevOps task status reporting
- Artifact publishing capabilities

```bash
/home/jonat/real_senti/scripts/helm_schema_validator_azure.sh --chart-dir /path/to/chart --ci
```

### chart_security_scan.sh

**Location**: `/home/jonat/real_senti/scripts/chart_security_scan.sh`

A security-focused validation tool that performs:

- Security scanning with kubesec
- Best practices validation
- Resource requirements checking

```bash
/home/jonat/real_senti/scripts/chart_security_scan.sh --chart-dir /path/to/chart
```

### ci/validate_helm_charts.sh

**Location**: `/home/jonat/real_senti/scripts/ci/validate_helm_charts.sh`

A CI/CD integration script that validates multiple charts at once:

```bash
/home/jonat/real_senti/scripts/ci/validate_helm_charts.sh --charts-dir /path/to/charts --env dev
```

## Validation Checks

The validation tools perform the following checks:

### Schema Validation

- Verifies the existence of values.schema.json
- Validates values.yaml against the schema
- Checks schema documentation completeness
- Validates required fields and property types

### Template Rendering

- Renders templates using helm template
- Verifies YAML syntax and structure
- Checks for template function errors
- Validates Kubernetes resource definitions

### Security Context Validation

- Verifies proper placement of securityContext settings
- Validates container-specific vs. pod-level settings
- Checks for required security settings (runAsNonRoot, etc.)
- Validates Azure-specific security requirements

### Resource Validation

- Checks for resource limits and requests
- Validates memory and CPU specifications
- Ensures proper quota utilization

### Misconfiguration Detection

- Identifies deprecated API versions
- Checks for deprecated Kubernetes features
- Validates proper label and selector usage
- Verifies internal consistency of resources

## Azure DevOps Integration

The Azure-optimized validation script is designed to integrate seamlessly with Azure DevOps pipelines.

### Pipeline Configuration

Create a pipeline YAML file at `/home/jonat/real_senti/infrastructure/helm/sentimark-services/helm-validation-pipeline.yml`:

```yaml
trigger:
  branches:
    include:
      - main
      - develop

pool:
  vmImage: 'ubuntu-latest'

steps:
- checkout: self

- task: Bash@3
  displayName: 'Validate Helm Charts'
  inputs:
    targetType: 'filePath'
    filePath: './scripts/helm_schema_validator_azure.sh'
    arguments: '--chart-dir $(Build.SourcesDirectory)/infrastructure/helm/sentimark-services --ci'

- task: PublishBuildArtifacts@1
  displayName: 'Publish Validation Results'
  inputs:
    pathToPublish: '$(Build.ArtifactStagingDirectory)/helm-validation'
    artifactName: 'HelmValidationResults'
  condition: always()
```

### Environment Variables

The Azure-optimized script automatically detects and utilizes Azure Pipeline environment variables:

- `BUILD_SOURCESDIRECTORY` - Source code directory
- `BUILD_ARTIFACTSTAGINGDIRECTORY` - Artifacts directory
- `SYSTEM_TEAMFOUNDATIONCOLLECTIONURI` - Pipeline context indicator
- `HELM_CHART_DIR` - Custom chart directory (optional)
- `HELM_VALUES_FILE` - Custom values file (optional)

### Pipeline Integration

The script integrates with Azure Pipeline capabilities:

- Uses `##vso[task.logissue]` for error and warning reporting
- Uses `##vso[task.complete]` for task status reporting
- Uses `##vso[artifact.upload]` for artifact publication
- Handles pipeline-specific exit codes

## AKS-Specific Considerations

The Azure-optimized validator includes specialized checks for Azure Kubernetes Service (AKS) deployments:

### AKS Security Checks

- Validates AKS-specific security settings:
  - runAsNonRoot configuration
  - seccompProfile configuration
  - hostNetwork, hostIPC, and hostPID restrictions
  - Proper volume mounting with readOnly flags

### Azure Policy Compliance

- Checks for features that might be restricted by Azure Policy:
  - hostPath volumes
  - privileged containers
  - allowPrivilegeEscalation settings

### Azure Resource Management

- Validates resource specifications relevant to AKS:
  - Spot instance compatibility
  - Node pool compatibility
  - Resource constraints

## Usage Examples

### Local Development Validation

```bash
# Basic validation
/home/jonat/real_senti/scripts/helm_schema_validator.sh --chart-dir /home/jonat/real_senti/infrastructure/helm/sentimark-services

# Detailed validation with specific values file
/home/jonat/real_senti/scripts/helm_schema_validator.sh --chart-dir /home/jonat/real_senti/infrastructure/helm/sentimark-services --values /home/jonat/real_senti/infrastructure/helm/sentimark-services/values-dev.yaml --output-dir /tmp/validation-results

# Security-focused validation
/home/jonat/real_senti/scripts/chart_security_scan.sh --chart-dir /home/jonat/real_senti/infrastructure/helm/sentimark-services
```

### Azure DevOps Pipeline Validation

```bash
# Run Azure-optimized validation
/home/jonat/real_senti/scripts/helm_schema_validator_azure.sh --chart-dir /home/jonat/real_senti/infrastructure/helm/sentimark-services --ci

# Validate multiple charts for a specific environment
/home/jonat/real_senti/scripts/ci/validate_helm_charts.sh --charts-dir /home/jonat/real_senti/infrastructure/helm --env sit
```

### Pre-commit Hook Integration

Add this to your `.git/hooks/pre-commit` file:

```bash
#!/bin/bash
changed_charts=$(git diff --cached --name-only | grep -E '^infrastructure/helm/')
if [ -n "$changed_charts" ]; then
  /home/jonat/real_senti/scripts/helm_schema_validator.sh --chart-dir /home/jonat/real_senti/infrastructure/helm/sentimark-services
fi
```

## Troubleshooting

### Common Issues

1. **Missing Dependencies**
   - The Azure-optimized script attempts to install dependencies automatically
   - For local execution, install dependencies: `helm`, `jq`, `yq`, `yamllint`, `jsonschema`, `kubesec`

2. **Chart Rendering Errors**
   - Check for template syntax errors
   - Validate that all required values are provided
   - Check for deprecated APIs or resources

3. **Schema Validation Failures**
   - Ensure values.schema.json is properly formatted
   - Verify that values.yaml conforms to the schema
   - Check for type mismatches or missing required fields

4. **Security Context Issues**
   - Move container-specific settings from pod level to container level
   - Ensure fsGroup remains at pod level
   - Use the fix_securitycontext.sh script to automate corrections

### Azure DevOps Specific Issues

1. **Pipeline Permission Issues**
   - Ensure the pipeline has permissions to install dependencies
   - Use a Microsoft-hosted agent to ensure proper capabilities

2. **Artifact Publication Failures**
   - Check if Build.ArtifactStagingDirectory is properly configured
   - Verify that the artifacts actually exist before publishing

3. **Integration Problems**
   - Check the pipeline logs for vso command issues
   - Ensure the script is executable before running

## Best Practices

1. **Schema-First Development**
   - Define values.schema.json first, with proper documentation
   - Update schema when adding new values
   - Keep schema documentation coverage above 80%

2. **Security Context Configuration**
   - Follow Kubernetes best practices for securityContext
   - Use runAsNonRoot and proper UID/GID settings
   - Implement fsGroup at pod level for volume access
   - Set appropriate capabilities

3. **Resource Management**
   - Always define resource requests and limits
   - Set appropriate CPU and memory constraints
   - Consider AKS-specific constraints and capabilities

4. **Chart Structure**
   - Organize templates logically
   - Use consistent naming conventions
   - Implement proper helpers in _helpers.tpl
   - Keep templates modular and reusable

5. **CI/CD Integration**
   - Run validation on all PRs
   - Block merges on validation failures
   - Include validation reports in PR comments
   - Track validation metrics over time