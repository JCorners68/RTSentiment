# Using Helm with Private AKS Clusters

This document explains how to use Helm with private AKS clusters through the Azure CLI, allowing full Helm capabilities without requiring direct access to the private Kubernetes API endpoint.

## Overview

Deploying Helm charts to a private AKS cluster presents unique challenges due to DNS resolution issues with the private Kubernetes API endpoint. This document outlines a solution that uses `az aks command invoke` to execute Helm commands directly inside the AKS environment.

## Prerequisites

- Azure CLI (latest version)
- Helm (optional, for local chart packaging)
- Appropriate permissions on the AKS cluster

## Solution Architecture

The solution leverages `az aks command invoke` to execute Helm commands inside the AKS cluster environment. This approach:

1. Packages the Helm chart locally
2. Transfers the chart and values to the AKS environment
3. Executes `helm upgrade --install` within the cluster environment
4. Manages release history and all standard Helm capabilities

## Implementation Options

The implementation provides two methods for executing Helm commands:

### 1. Direct Helm Execution

If Helm is available in the AKS command environment:

```
az aks command invoke \
    --resource-group $RESOURCE_GROUP \
    --name $CLUSTER_NAME \
    --command "helm upgrade --install $RELEASE_NAME /path/to/chart.tgz \
               --namespace $NAMESPACE \
               --values /path/to/values.yaml"
```

### 2. Helm Pod Execution

If Helm is not available in the AKS command environment:

```
# Create a temporary pod with Helm installed
# Transfer the chart and values
# Execute Helm commands inside the pod
# Delete the pod after completion
```

## Idempotence Considerations

The solution maintains idempotence by:

1. Using native Helm commands (`helm upgrade --install`) which are inherently idempotent
2. Creating only temporary resources that are cleaned up after execution
3. Ensuring no persistent state is created as part of the deployment process

## Deployment Script

A comprehensive deployment script (`/home/jonat/real_senti/environments/sit/helm_deploy.sh`) has been created that:

1. Verifies prerequisites (Azure CLI, AKS cluster availability)
2. Packages the Helm chart locally
3. Detects whether Helm is available in the AKS environment
4. Selects the appropriate deployment method (direct or pod-based)
5. Transfers the chart and values to the AKS environment
6. Executes the Helm installation
7. Verifies the deployment status
8. Provides proper error handling and cleanup

### Script Features

- **Auto-detection**: Automatically detects if Helm is available in the AKS command environment
- **Flexibility**: Supports both local charts and chart repositories
- **Cleanup**: Ensures all temporary resources are removed after deployment
- **Logging**: Provides detailed logging of all operations
- **Error Handling**: Includes comprehensive error handling and reporting

## Using the Script

```bash
cd /home/jonat/real_senti/environments/sit
./helm_deploy.sh
```

### Configuration

The script supports the following configuration:

- **Chart Repository**: Can be configured by uncommenting and setting the repository variables
- **Local Chart**: By default, uses the local chart from `/home/jonat/real_senti/infrastructure/helm/sentimark-services`
- **Resource Group and Cluster Name**: Set at the top of the script

## Release Management

The script maintains all Helm release management capabilities:

- **Release History**: Properly tracked by Helm
- **Rollbacks**: Supported through `helm rollback`
- **Upgrades**: Seamless through the same script
- **Uninstallation**: Available through `helm uninstall`

## Troubleshooting

If you encounter issues:

1. **Azure CLI Authentication**: Ensure you're logged in with `az login`
2. **Permissions**: Verify you have appropriate RBAC permissions on the AKS cluster
3. **Chart Validation**: Validate your chart locally with `helm lint` before deployment
4. **Logs**: Check the logs directory for detailed deployment logs

## Limitations

- **Performance**: Initial deployment may be slower than direct Helm access
- **Interactive Features**: Commands requiring interactive input are not supported
- **Large Charts**: Very large charts may encounter size limitations
- **Command Timeout**: Default timeout is 5 minutes, which may need adjustment for complex deployments

## References

- [Azure AKS Documentation](https://docs.microsoft.com/en-us/azure/aks/)
- [az aks command invoke](https://docs.microsoft.com/en-us/cli/azure/aks/command?view=azure-cli-latest#az-aks-command-invoke)
- [Helm Documentation](https://helm.sh/docs/)
- [Private AKS Clusters](https://docs.microsoft.com/en-us/azure/aks/private-clusters)