# Sentimark Helm Charts

This directory contains Helm charts for deploying Sentimark services to Kubernetes environments.

## Charts

- **sentimark-services**: Main services deployment chart
- **sentimark-common**: Common templates and helpers used across charts

## Validation

All Helm charts in this repository must pass validation before deployment. The validation process ensures:

1. Schema compliance: All values comply with defined schemas
2. Security best practices: Proper security context settings and resource definitions
3. AKS compatibility: Charts meet Azure Kubernetes Service requirements
4. Template correctness: Templates render properly with expected values

### Validation Tools

Validation is performed using the following tools:

- `/home/jonat/real_senti/scripts/helm_schema_validator.sh`: Local validation
- `/home/jonat/real_senti/scripts/helm_schema_validator_azure.sh`: Azure DevOps optimized validation

### CI/CD Integration

The Helm charts are automatically validated in CI/CD pipelines using the configuration defined in:
- `/home/jonat/real_senti/infrastructure/helm/sentimark-services/helm-validation-pipeline.yml`

## Documentation

For detailed documentation on Helm chart validation, see:

- [Helm Validation Guidelines](/home/jonat/real_senti/docs/validation/helm_validation.md)
- [Scripts Documentation](/home/jonat/real_senti/scripts/README_HELM_VALIDATION.md)

## Usage

```bash
# Install chart in dev environment
helm install sentimark ./sentimark-services -f ./sentimark-services/values-dev.yaml

# Template chart for validation
helm template sentimark ./sentimark-services -f ./sentimark-services/values-dev.yaml
```