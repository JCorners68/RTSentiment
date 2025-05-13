# Helm Chart Schema Validation Tools

This directory contains tools for validating Helm charts against schema definitions, ensuring consistency, security, and correctness before deployment. These tools are designed to be integrated into CI/CD pipelines to catch issues early in the development process.

## Tools Overview

### 1. `helm_schema_validator.sh`

A comprehensive Helm chart validation script that checks:
- Schema validation using values.schema.json
- Template rendering verification
- Kubernetes resource validation
- Security context placement checking
- Common misconfigurations detection

### 2. `helm_schema_validator_azure.sh`

An enhanced version of the validation script with Azure DevOps integration that includes:
- Automatic dependency installation in Azure Pipelines
- Azure-friendly path handling and environment detection
- Azure Kubernetes Service (AKS) specific security checks
- Pipeline-aware reporting with task status integration
- Artifact publishing integration

```bash
./helm_schema_validator.sh [options] [chart_dir] [values_file]
```

The Azure-enabled version can be used similarly:

```bash
./helm_schema_validator_azure.sh [options] [chart_dir] [values_file]
```

**Options:**
- `--chart-dir DIR`: Path to the Helm chart directory
- `--values FILE`: Path to the values file to validate
- `--output-dir DIR`: Path to the output directory for results
- `--ci`: Run in CI mode (exit with non-zero code on failure)
- `--quiet`: Reduce output verbosity
- `--skip-security-context`: Skip securityContext placement validation
- `--help`: Display help message

### 3. `ci/validate_helm_charts.sh`

CI/CD integration script to validate multiple Helm charts in one operation. Designed for automation pipelines to validate all charts before deployment.

```bash
./ci/validate_helm_charts.sh [options]
```

**Options:**
- `--charts-dir DIR`: Directory containing Helm charts
- `--results-dir DIR`: Directory to store validation results
- `--env ENV`: Environment to validate for (dev, sit, uat, prod)
- `--notify`: Send email notification on validation failure
- `--email RECIPIENTS`: Comma-separated list of email recipients
- `--no-fail`: Don't fail the pipeline on validation errors
- `--help`: Display help message

### 4. `chart_security_scan.sh`

Security-focused chart validation script that performs:
- Helm lint checks
- Security scanning with kubesec (if available)
- Chart testing with chart-testing (ct)
- Best practices validation
- Resource requirements checks

```bash
./chart_security_scan.sh [options]
```

**Options:**
- `--chart-dir`: Path to the Helm chart directory (required)
- `--output-dir`: Directory to store scan results
- `--verbose`: Enable verbose output
- `--fail-on-error`: Exit with error code on any security issue
- `--help`: Display help message

## Integration with CI/CD

### GitHub Actions Integration

To integrate these validation tools into a GitHub Actions workflow, create a workflow file like:

```yaml
name: Helm Chart Validation

on:
  push:
    paths:
      - 'infrastructure/helm/**'
  pull_request:
    paths:
      - 'infrastructure/helm/**'

jobs:
  validate-charts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Helm
        uses: azure/setup-helm@v3
        with:
          version: 'v3.10.0'
          
      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y jq yamllint
          pip install jsonschema
      
      - name: Validate Helm Charts
        run: |
          chmod +x ./scripts/ci/validate_helm_charts.sh
          ./scripts/ci/validate_helm_charts.sh --env dev
          
      - name: Upload validation results
        uses: actions/upload-artifact@v3
        with:
          name: helm-validation-results
          path: scan-results/
```

### Azure DevOps Pipeline Integration

For Azure DevOps, create a pipeline YAML file using the Azure-enabled script:

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

This pipeline uses the Azure-enabled script which automatically:
- Detects the Azure DevOps environment
- Installs required dependencies
- Uses Azure Pipeline-specific directories
- Reports errors and warnings directly to the pipeline
- Publishes validation results as artifacts

You can also still use the original approach with the validation script:

```yaml
trigger:
  paths:
    include:
    - infrastructure/helm/*

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: Bash@3
  displayName: 'Install dependencies'
  inputs:
    targetType: 'inline'
    script: |
      sudo apt-get update
      sudo apt-get install -y jq yamllint
      pip install jsonschema

- task: Bash@3
  displayName: 'Validate Helm Charts'
  inputs:
    filePath: './scripts/ci/validate_helm_charts.sh'
    arguments: '--env $(Environment) --charts-dir $(System.DefaultWorkingDirectory)/infrastructure/helm'

- task: PublishBuildArtifacts@1
  inputs:
    pathToPublish: 'scan-results'
    artifactName: 'helm-validation-results'
```

## Verification Commands

To validate your Helm charts from the command line:

```bash
# Run comprehensive validation on all charts
./scripts/ci/validate_helm_charts.sh

# Validate a specific chart with detailed output
./scripts/helm_schema_validator.sh --chart-dir /home/jonat/real_senti/infrastructure/helm/sentimark-services

# Validate with Azure DevOps integration
./scripts/helm_schema_validator_azure.sh --chart-dir /home/jonat/real_senti/infrastructure/helm/sentimark-services

# Run security scan only
./scripts/chart_security_scan.sh --chart-dir /home/jonat/real_senti/infrastructure/helm/sentimark-services

# Validate for a specific environment
./scripts/ci/validate_helm_charts.sh --env sit
```

## Dependencies

These tools require the following dependencies:
- `helm` (v3.x)
- `jq` for JSON processing
- `yamllint` for YAML validation (optional but recommended)
- `jsonschema` for schema validation (optional but recommended)
- `kubesec` for security scanning (optional)
- `kubectl` for Kubernetes validation (optional)

Note: The Azure-enabled script (`helm_schema_validator_azure.sh`) will attempt to automatically install missing dependencies when running in an Azure DevOps pipeline environment.

## Output

The validation tools generate detailed reports in the output directory (default: `scan-results/`):
- Markdown validation reports
- JSON summary files
- Rendered templates
- Security scan results
- YAML lint results

## Best Practices

1. **Run validation locally before committing**:
   ```bash
   ./scripts/helm_schema_validator.sh --chart-dir path/to/your/chart
   ```

   Or use the Azure-enabled version:
   ```bash
   ./scripts/helm_schema_validator_azure.sh --chart-dir path/to/your/chart
   ```

2. **Integrate in pre-commit hooks**:
   ```bash
   #!/bin/bash
   # .git/hooks/pre-commit
   changed_charts=$(git diff --cached --name-only | grep -E '^infrastructure/helm/')
   if [ -n "$changed_charts" ]; then
     ./scripts/ci/validate_helm_charts.sh
   fi
   ```

3. **Address all warnings**: Even if validation passes with warnings, it's best practice to address them to prevent potential issues in production.

4. **Keep values.schema.json updated**: When adding new values to your Helm charts, always update the schema to validate them.