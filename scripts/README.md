# Sentimark Scripts

This directory contains utility scripts for the Sentimark project.

## Helm Chart Validation

### helm_schema_validator.sh

A comprehensive Helm chart validation script that checks:
- Schema validation using values.schema.json
- Template rendering verification
- Kubernetes resource validation
- Security context placement checking
- Common misconfigurations detection

### helm_schema_validator_azure.sh

An enhanced version of the validation script with Azure DevOps integration that includes:
- Automatic dependency installation in Azure Pipelines
- Azure-friendly path handling and environment detection
- Azure Kubernetes Service (AKS) specific security checks
- Pipeline-aware reporting with task status integration
- Artifact publishing integration

### chart_security_scan.sh

Security-focused chart validation script that performs:
- Helm lint checks
- Security scanning with kubesec (if available)
- Chart testing with chart-testing (ct)
- Best practices validation
- Resource requirements checks

See [README_HELM_VALIDATION.md](/home/jonat/real_senti/scripts/README_HELM_VALIDATION.md) for detailed usage information.
Comprehensive documentation is also available at [/home/jonat/real_senti/docs/validation/helm_validation.md](/home/jonat/real_senti/docs/validation/helm_validation.md).

## fix_securitycontext.sh

A script to fix securityContext fields in Kubernetes Helm charts, moving from pod-level to container-level securityContext configuration, which is the recommended best practice.

### Purpose

This script fixes security context settings in Kubernetes Helm charts by:

1. Moving securityContext settings from pod level to container level
2. Commenting out pod-level securityContext settings (but preserving fsGroup information)
3. Maintaining proper YAML indentation for both regular Deployment and CronJob resources
4. Validating the changes to ensure proper YAML syntax

### Usage

```bash
# Fix all *-deployment.yaml files in the templates directory
./fix_securitycontext.sh

# Fix specific files
./fix_securitycontext.sh /path/to/file1.yaml /path/to/file2.yaml

# Display help
./fix_securitycontext.sh --help
```

### Features

- Automatically detects different types of resources (Deployment, CronJob) and applies appropriate indentation
- Creates timestamped backups of all files before modifications
- Provides clear logging of all operations
- Handles YAML indentation correctly for nested structures
- Preserves template directives and conditional sections

### Validation

After running the script, you should validate your Helm charts with:

```bash
helm lint /path/to/chart
```

### Best Practices

For Kubernetes security context settings:

1. Pod-level securityContext should only contain fsGroup settings
2. Container-level securityContext should contain:
   - runAsNonRoot
   - runAsUser
   - runAsGroup
   - allowPrivilegeEscalation
   - capabilities (drop)
   - readOnlyRootFilesystem

Following these practices helps ensure proper security scanning and compliance.