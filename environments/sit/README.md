# Sentimark SIT Environment

This directory contains scripts and configuration for deploying the System Integration Testing (SIT) environment for the Sentimark project to Azure.

## Deployment Status

The SIT environment has been successfully deployed to Azure. All necessary resources have been created and configured in the `eastus` region.

## Prerequisites

To deploy this environment, you need:
- Access to Azure subscription: `644936a7-e58a-4ccb-a882-0005f213f5bd`
- Access to Azure tenant: `1ced8c49-a03c-439c-9ff1-0c23f5128720`
- Service Principal credentials (already configured in the scripts)
- Azure CLI or Docker with WSL integration

## Deployment Instructions

Detailed deployment instructions are available in the [DEPLOYMENT_INSTRUCTIONS.md](./DEPLOYMENT_INSTRUCTIONS.md) file.

### Quickstart

1. **Using the setup script (Recommended)**:
   ```bash
   # Run the setup script which guides you through deployment options
   ./setup.sh
   ```

2. **Direct deployment with Python SDK**:
   ```bash
   # Deploy to Azure directly using Python SDK
   ./deploy_azure_sit.sh
   ```

3. **Verification and service deployment**:
   ```bash
   # Verify the deployment
   ./verify_deployment.sh
   
   # Deploy services (requires kubectl)
   export KUBECONFIG=./config/kubeconfig
   ./deploy_services.sh
   ```

## Environment Configuration

The SIT environment will be deployed with the following configuration:

- **Resource Group**: `sentimark-sit-rg`
- **Location**: `westus`
- **AKS Cluster**: `sentimark-sit-aks`
- **Node Pools**:
  - **default**: 1 node (Standard_D2s_v3) - System pool for core Kubernetes components
  - **dataspots**: 1 node (Standard_D2s_v3) - Spot instance pool for data processing workloads
  - **lowspots**: 1 node (Standard_F2s_v2) - Spot instance pool for low-latency workloads
- **Storage Account**: `sentimarksitstorage`

### Spot Instance Configuration

The SIT environment uses Azure Spot Virtual Machines to reduce costs:

- **60-80% cost savings** compared to regular on-demand VMs
- **Taints** are applied to spot instance nodes to control workload scheduling:
  - `kubernetes.azure.com/scalesetpriority=spot:NoSchedule`
  - `workload=dataprocessing:NoSchedule` or `workload=lowlatency:NoSchedule`
- **Pod tolerations** must be configured in deployment manifests to use spot instances
- See `/infrastructure/kubernetes/base/*-spot.yaml` for deployment examples

## Verification

After deployment, verify the environment using:

```bash
# Option 1: Using the verification script (doesn't require kubectl)
./verify_deployment.sh

# Option 2: Using Python test script
python tests/run_verification.py

# Option 3: Using pytest (requires kubectl)
cd tests
pytest -xvs test_azure_sit.py
```

## Available Scripts

- [setup.sh](./setup.sh): Main setup script that handles all deployment options
- [deploy_azure_sit.sh](./deploy_azure_sit.sh): Deploys the SIT environment to Azure
- [continue_deploy.sh](./continue_deploy.sh): Continues deployment if the initial script times out
- [deploy_services.sh](./deploy_services.sh): Deploys services to the SIT environment
- [verify_deployment.sh](./verify_deployment.sh): Verifies the deployment status without requiring kubectl
- [cleanup_azure_sit.sh](./cleanup_azure_sit.sh): Removes the SIT environment from Azure

## Services Deployed

- **Data Acquisition Service**: Responsible for ingesting data
- **Data Tier**: Database layer for storing sentiment data
- **Data Migration Service**: (If available) Handles data migration between storage types

## Troubleshooting

### Common Issues

1. **Docker detection issues**:
   - The script may detect Docker but it might not be running correctly in WSL.
   - Solution: Use the Python SDK method instead.

2. **Azure CLI not installed**:
   - The script automatically falls back to the Python SDK method.

3. **Resource group location mismatch**:
   - The script now automatically detects and uses the existing resource group's location.

4. **VM quota limitations**:
   - The deployment now uses spot instances to maximize resource efficiency within quota limits.
   - Current quota allows for: 3 Standard_D2s_v3 VMs and 2 Standard_F2s_v2 VMs.

5. **kubectl not available or fails to connect**:
   - Use the `verify_deployment.sh` script which doesn't require kubectl.
   - Use Azure Cloud Shell which has direct private network access to the AKS cluster.
   - See `/logs/azure_aks_verification.md` for Cloud Shell verification commands.

6. **DNS resolution errors with private AKS endpoint**:
   - Error: `lookup rt-sentiment-pu1l2xsk.e0a6a092-8322-4fa7-84a5-8b90d32afcb2.privatelink.westus.azmk8s.io: no such host`
   - Solution: Use Azure Cloud Shell which has direct access to private AKS endpoints.

## Implementation Notes

This environment is optimized for low latency and high performance. The infrastructure is designed to support real-time sentiment analysis with fast data processing capabilities.

## Next Steps

After successful deployment:

1. Verify all services are running correctly
2. Configure any necessary environment-specific settings
3. Run integration tests to ensure end-to-end functionality
4. Document any environment-specific configurations or issues