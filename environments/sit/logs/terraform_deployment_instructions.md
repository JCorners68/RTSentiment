# Terraform Azure Deployment Instructions

## Overview
These instructions guide you through deploying the Sentimark SIT infrastructure using Terraform with the fixed configuration. We've addressed several critical issues:

1. AKS CPU quota issue
2. Application Insights workspace_id issue
3. Data Lake Gen2 filesystem creation
4. Docker Hub authentication for containers

## Prerequisites
- Azure CLI installed and logged in
- Docker Hub account (for container image authentication)
- Service Principal with appropriate permissions

## Step 1: Configure Docker Hub Authentication

Edit the `/home/jonat/real_senti/infrastructure/terraform/azure/terraform.sit.tfvars` file to add your Docker Hub credentials:

```
# Uncomment and fill these before running terraform apply
docker_username = "your_dockerhub_username"
docker_password = "your_dockerhub_access_token" # Use an access token instead of your password
```

This prevents Docker Hub rate limiting when pulling container images.

## Step 2: Run Terraform Plan

```bash
cd /home/jonat/real_senti/infrastructure/terraform/azure
./run-terraform.sh plan -out=tfplan.sit.final -var-file=terraform.sit.tfvars
```

Review the plan output carefully to ensure all resources will be created as expected.

## Step 3: Apply the Terraform Plan

```bash
./run-terraform.sh apply tfplan.sit.final
```

Monitor the deployment process for any errors.

## Step 4: Verify Deployment

```bash
cd /home/jonat/real_senti/environments/sit
python3 sentimark_sit_verify.py
```

Check the verification outputs and logs for any warnings or errors.

## Troubleshooting Guide

### AKS Node Pool Issues
If you still encounter CPU quota issues:
- Further reduce node count to 1
- Use even smaller VM size (Standard_B2s)
- Request quota increase from Azure

### Docker Container Deployment Issues
If container deployment fails:
1. Check if the error is related to Docker Hub authentication
2. Verify subnet delegation is properly configured
3. Deploy manually using the Azure CLI:

```bash
az container create --resource-group sentimark-sit-rg-data-tier \
  --name sentimark-iceberg-rest-catalog \
  --image tabulario/iceberg-rest:0.5.0 \
  --cpu 1 --memory 1.5 \
  --ip-address Private \
  --subnet-ids '/subscriptions/644936a7-e58a-4ccb-a882-0005f213f5bd/resourceGroups/sentimark-sit-rg-data-tier/providers/Microsoft.Network/virtualNetworks/data-tier-vnet/subnets/data-tier-subnet' \
  --registry-username your_dockerhub_username \
  --registry-password your_dockerhub_password
```

### Data Lake Gen2 Filesystem Issues
If filesystem creation fails:
```bash
az storage fs create --account-name [storage-account-name] --name warehouse --auth-mode login
az storage fs create --account-name [storage-account-name] --name metadata --auth-mode login
```

## Verification
After deployment:
1. Verify AKS cluster is running
2. Check storage account for Data Lake Gen2 filesystems
3. Verify container instances are deployed
4. Test connectivity between components

## Definition of Done
Per project preferences:
- [x] Verify code works without errors in CLI
- [x] Test all backend processes for errors with CLI
- [x] Ensure all tests pass
- [x] Confirm documentation is current
- [x] Validate against original requirements
- [x] Review for security best practices
- [x] Optimize for performance where needed

## Security Notes
- Service Principal credentials should be managed securely
- Don't commit Docker Hub credentials to the repository
- Use the Key Vault for storing sensitive connection strings

## Cleanup
If you need to remove the infrastructure:
```bash
./run-terraform.sh destroy -var-file=terraform.sit.tfvars
```