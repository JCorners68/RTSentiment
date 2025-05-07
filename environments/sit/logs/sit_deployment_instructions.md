# SIT Environment Deployment Instructions

This document provides step-by-step instructions for deploying the Sentimark SIT environment on Azure after all fixes have been applied.

## Prerequisites

1. Azure CLI installed and configured
2. Terraform installed (or use the script's Docker-based execution)
3. Python 3.8+ for verification scripts
4. Docker (optional, for running Terraform in a container)

## Step 1: Clone and Setup

Ensure you have the latest code:

```bash
cd /home/jonat/real_senti
git checkout data_tier
git pull
```

## Step 2: Configuration Check

Run the configuration consistency check to ensure all settings are aligned:

```bash
cd /home/jonat/real_senti/environments/sit
./check_config_consistency.sh
```

If any inconsistencies are found, fix them before proceeding with the deployment.

## Step 3: Deployment

The deployment script supports three methods of deployment:
- Python with Azure SDK (primary method)
- Azure CLI (fallback)
- Terraform with Docker (comprehensive option)

To run the deployment:

```bash
cd /home/jonat/real_senti/environments/sit
./deploy_azure_sit.sh
```

The script will:
1. Run configuration consistency checks
2. Set up the necessary environment
3. Choose the appropriate deployment method
4. Create all resources in Azure
5. Save deployment logs

## Step 4: Verification

After deployment, verify the resources:

```bash
cd /home/jonat/real_senti/environments/sit
./verify_deployment.sh
```

This will check for:
- Cluster configuration
- Storage account setup
- Kubernetes connectivity
- Service deployment status

For a more comprehensive verification:

```bash
cd /home/jonat/real_senti/environments/sit
python sentimark_sit_verify.py
```

This will run additional checks and save detailed verification logs.

## Step 5: Deploy Services (Optional)

If you want to deploy services to the Kubernetes cluster:

```bash
cd /home/jonat/real_senti/environments/sit
export KUBECONFIG="${PWD}/config/kubeconfig"
./deploy_services.sh
```

## Troubleshooting

If deployment fails, check the following:

1. **Configuration Issues:**
   - Run `./check_config_consistency.sh` to identify mismatches
   - Check `/logs/verification_*.json` for specific test failures

2. **Resource Errors:**
   - Check `/logs/deployment_*.json` for error messages
   - Run `python tests/run_verification.py` for detailed diagnostics

3. **Permission Issues:**
   - Ensure service principal has required permissions
   - Check RBAC role assignments

4. **Regional Limitations:**
   - Check if any resource is not supported in westus region
   - Consider fallback to eastus if necessary

5. **Manual Recovery:**
   - For Data Lake filesystem issues: use Azure CLI to create filesystems
   - For subnet delegation: manually update subnet properties in Azure Portal

## Cleanup

If needed, you can clean up all resources:

```bash
cd /home/jonat/real_senti/environments/sit
./cleanup_azure_sit.sh
```

For a forced cleanup (if normal cleanup fails):

```bash
cd /home/jonat/real_senti/environments/sit
./force_cleanup.sh
```

## Notes

- The SIT environment uses smaller VM sizes to fit within vCPU quota limits
- Container deployment is disabled by default in SIT due to subnet delegation complexity
- Azure Policy assignments are disabled in SIT due to potential authorization issues
- Resource group naming and locations are validated before deployment

For latest updates and detailed architecture, refer to the docs in `/home/jonat/real_senti/docs/architecture/`.