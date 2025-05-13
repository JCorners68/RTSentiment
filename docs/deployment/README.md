# Deployment Architecture

This directory contains documentation for deploying the Sentimark system across different environments.

## Contents

- **deployment_dev.md** - Development environment deployment guide
- **deployment_sit.md** - System Integration Testing environment deployment
- **deployment_uat.md** - User Acceptance Testing environment deployment
- **deployment_prod.md** - Production environment deployment
- **deployment_infrastructure_guide.md** - Comprehensive infrastructure deployment guide

## Purpose

These documents provide environment-specific deployment instructions, including configuration details, resource requirements, and deployment processes. They ensure consistent deployment across all environments while accounting for their specific characteristics.

## Environments

- **Development**: Local environment using Docker Compose
- **SIT**: Azure Container Apps with PostgreSQL
- **UAT**: Azure Kubernetes Service with Iceberg on Data Lake Storage
- **Production**: Full-scale production deployment

## Key Concepts

- Infrastructure as Code (Terraform)
- Containerization (Docker)
- Orchestration (Kubernetes, Container Apps)
- Environment-specific configurations
- Deployment verification

## Related Sections

- See **infrastructure/** for detailed cloud resource specifications
- See **cost-management/** for environment cost optimization
- See **data-tier/** for database configuration by environment