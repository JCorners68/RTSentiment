# RT Sentiment Analysis - Azure Infrastructure

This directory contains Terraform configurations for deploying the RT Sentiment Analysis application to Azure with a focus on low-latency performance.

## Architecture Overview

The infrastructure is optimized for low latency with the following components:

- **Azure Kubernetes Service (AKS)** with Proximity Placement Groups for co-located nodes
- **Specialized Node Pools** for data processing and low-latency workloads
- **Azure Front Door** for global distribution with minimal latency
- **Application Insights** for performance monitoring
- **Azure Container Registry** for secure image storage
- **Cost Management Policies** to control resource usage

## Prerequisites

- Azure Subscription with Contributor access
- Service Principal with appropriate permissions
- Docker installed locally (for running Terraform)

## Authentication

This project uses **Service Principal Authentication exclusively**. No Azure CLI fallbacks are used. Authentication is performed using:

1. Service Principal credentials from command line parameters
2. Service Principal credentials stored in `providers.tf`
3. Service Principal credentials from environment variables (for different environments)

For security:
- Azure CLI authentication is explicitly disabled
- Managed Service Identity (MSI) authentication is explicitly disabled

## Directory Structure

- `main.tf` - Core infrastructure components
- `node_pools.tf` - AKS node pools configuration
- `providers.tf` - Provider configurations
- `variables.tf` - Variable definitions
- `terraform.tfvars` - Variable values
- `outputs.tf` - Output values
- `cost_management/` - Cost management policies and controls
- `modules/` - Reusable infrastructure modules:
  - `app-config` - Azure App Configuration service
  - `iceberg` - Apache Iceberg data lake configuration
  - `monitoring` - Monitoring and logging services
- `data_tier_prod.tf` - Production data tier configuration

## Usage

### Using the Helper Script

We provide a convenient script to run Terraform commands with proper authentication:

```bash
# Initialize Terraform
./run-terraform.sh --client-id=YOUR_CLIENT_ID --client-secret=YOUR_CLIENT_SECRET init

# Validate configuration
./run-terraform.sh --client-id=YOUR_CLIENT_ID --client-secret=YOUR_CLIENT_SECRET validate

# Create execution plan
./run-terraform.sh --client-id=YOUR_CLIENT_ID --client-secret=YOUR_CLIENT_SECRET plan

# Apply configuration
./run-terraform.sh --client-id=YOUR_CLIENT_ID --client-secret=YOUR_CLIENT_SECRET apply

# Apply only cost management module
./run-terraform.sh --client-id=YOUR_CLIENT_ID --client-secret=YOUR_CLIENT_SECRET cost-apply
```

The script can also use credentials from providers.tf if no credentials are provided via command line.

### Manual Execution with Docker

Alternatively, you can run Terraform commands directly with Docker:

```bash
# Set environment variables for authentication
export ARM_CLIENT_ID="your-client-id"
export ARM_CLIENT_SECRET="your-client-secret"
export ARM_SUBSCRIPTION_ID="your-subscription-id"
export ARM_TENANT_ID="your-tenant-id"
export ARM_USE_CLI=false
export ARM_USE_MSI=false

# Run Terraform commands
docker run --rm -v $(pwd):/workspace -w /workspace \
  -e ARM_CLIENT_ID -e ARM_CLIENT_SECRET -e ARM_SUBSCRIPTION_ID -e ARM_TENANT_ID \
  -e ARM_USE_CLI=false -e ARM_USE_MSI=false \
  hashicorp/terraform:latest init

docker run --rm -v $(pwd):/workspace -w /workspace \
  -e ARM_CLIENT_ID -e ARM_CLIENT_SECRET -e ARM_SUBSCRIPTION_ID -e ARM_TENANT_ID \
  -e ARM_USE_CLI=false -e ARM_USE_MSI=false \
  hashicorp/terraform:latest plan

docker run --rm -v $(pwd):/workspace -w /workspace \
  -e ARM_CLIENT_ID -e ARM_CLIENT_SECRET -e ARM_SUBSCRIPTION_ID -e ARM_TENANT_ID \
  -e ARM_USE_CLI=false -e ARM_USE_MSI=false \
  hashicorp/terraform:latest apply
```

## Deployment Process

1. **Initialize Terraform**: Set up the working directory with the required provider plugins
2. **Validate Configuration**: Check that the configuration is syntactically valid
3. **Plan Deployment**: Preview the changes that will be made to your infrastructure
4. **Apply Changes**: Create or update the resources in Azure

## Integration with GitHub Actions

This Terraform configuration is designed to work with the GitHub Actions workflow for promotion from SIT to UAT. The workflow:

1. Authenticates to Azure using a Service Principal
2. Runs Terraform to provision or update UAT infrastructure
3. Deploys the application containers to the AKS cluster

## Customization

Edit the `terraform.tfvars` file to customize:

- Resource names
- VM sizes and node counts
- Region selection
- Other environment-specific settings

For different environments:
- SIT: Use `terraform.sit.tfvars`
- UAT/Production: Create specific tfvars files

## Cost Management

The cost management module provides:

1. Budget alerts (thresholds at 70%, 90%, 100%)
2. Resource restrictions via Azure Policy
3. Auto-shutdown for dev/test environments
4. Tag-based cost tracking

Apply only the cost management module with:

```bash
./run-terraform.sh cost-apply
```