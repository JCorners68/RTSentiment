# Helm Chart Deployment for Private AKS Clusters

This document explains how to use the `helm_deploy.sh` script to deploy Helm charts to a private AKS cluster.

## Overview

The `helm_deploy.sh` script provides a robust way to deploy Helm charts to a private AKS cluster using the `az aks command invoke` approach. This eliminates the need for direct connectivity to the private AKS API endpoint.

## Prerequisites

- Azure CLI installed and configured (`az login` completed)
- jq installed (the script will attempt to install it automatically if missing)
- Proper permissions on the AKS cluster (Contributor or Owner role)

## Usage

Basic usage:

```bash
./helm_deploy.sh
```

Advanced usage with options:

```bash
./helm_deploy.sh --test-chart --namespace my-namespace --release-name my-release
```

### Parameters

- `--test-chart`: Deploy a test chart (simplified nginx deployment) instead of the actual chart
- `--chart-dir PATH`: Specify an alternative chart directory (default: `/home/jonat/real_senti/infrastructure/helm/sentimark-services`)
- `--release-name NAME`: Specify the Helm release name (default: `sentimark`)
- `--namespace NAMESPACE`: Specify the Kubernetes namespace (default: `sit`)

## How It Works

1. **Prerequisite Verification**: Checks for Azure CLI and jq, attempts to install jq if missing
2. **Chart Packaging**: Packages the Helm chart (either the actual chart or a test chart)
3. **Deployment Strategy Selection**: Determines whether to use a temporary pod with Helm or direct Helm execution
4. **Chart Transfer**: Transfers the chart and values to the AKS environment
5. **Helm Deployment**: Executes `helm upgrade --install` to deploy the chart
6. **Verification**: Verifies the deployment by checking Helm releases and deployed pods
7. **Cleanup**: Ensures all temporary resources are removed

## Deployment Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Package Chart  │────▶│ Transfer Chart  │────▶│ Deploy with Helm│
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        │                                               ▼
┌─────────────────┐                         ┌─────────────────┐
│  Create Log     │◀────────────────────────│ Verify & Cleanup│
└─────────────────┘                         └─────────────────┘
```

## Key Features

- **Automatic jq Installation**: Attempts to install jq if missing
- **Robust Error Handling**: Proper handling of errors with detailed logging
- **Comprehensive Cleanup**: Ensures all temporary resources are cleaned up
- **Test Chart Option**: Allows deploying a simple test chart for verification
- **Size Validation**: Validates chart size to ensure it can be transferred
- **Deployment Logging**: Creates detailed logs of the deployment process
- **Helm Release Management**: Provides commands for managing Helm releases

## Examples

Deploy the default chart:

```bash
./helm_deploy.sh
```

Deploy a test chart to a different namespace:

```bash
./helm_deploy.sh --test-chart --namespace test
```

Deploy a specific chart with a custom release name:

```bash
./helm_deploy.sh --chart-dir /path/to/my-chart --release-name my-app
```

## Troubleshooting

### jq Installation Issues

If jq installation fails automatically:

```bash
# Debian/Ubuntu
sudo apt update && sudo apt install -y jq

# RHEL/CentOS
sudo yum install -y jq

# macOS
brew install jq
```

### Chart Size Limitations

If your chart is too large for transfer (>20MB by default):

1. Reduce your chart size by removing unnecessary files
2. Increase the `MAX_TRANSFER_SIZE_MB` value in the script
3. Consider uploading your chart to a Helm repository

### Deployment Failures

Check the logs in `/home/jonat/real_senti/environments/sit/logs/` for detailed error information.

## Best Practices

1. **Use the Test Chart First**: Start with `--test-chart` to verify connectivity
2. **Validate Charts Locally**: Use `helm lint` and `helm template` for validation
3. **Keep Charts Small**: Minimize chart size for faster transfers
4. **Use a Helm Repository**: For production, consider setting up a Helm repository

## References

- [Azure AKS Documentation](https://docs.microsoft.com/en-us/azure/aks/)
- [Helm Documentation](https://helm.sh/docs/)
- [Private AKS Cluster Guide](/docs/deployment/private_aks_access.md)