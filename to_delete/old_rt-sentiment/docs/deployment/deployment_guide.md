# RT Sentiment Analysis - Deployment Guide

## Deployment Overview

This document provides instructions for deploying the RT Sentiment Analysis system in the SIT (WSL) and UAT (Azure) environments.

## Prerequisites

- Docker and Docker Compose
- WSL2 for local deployment
- Azure CLI for UAT deployment
- Terraform for infrastructure as code
- Git for version control

## SIT Environment Deployment (WSL)

### System Requirements

- WSL2 with Ubuntu 20.04 or later
- Docker Engine 20.10 or later
- Docker Compose 2.0 or later
- 8GB RAM minimum, 16GB recommended
- 50GB disk space

### Setup Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/example/rt-sentiment.git
   cd rt-sentiment
   ```

2. Run the SIT environment setup script:
   ```bash
   cd environments/sit
   ./setup.sh
   ```

3. Start the services:
   ```bash
   cd ../../infrastructure
   docker compose up -d
   ```

4. Verify the deployment:
   ```bash
   cd ../environments/sit/tests
   pytest
   ```

### Configuration

The SIT environment uses configuration files located in `environments/sit/config`.

### Accessing Services

- API Service: http://localhost:8001
- Admin Web App: http://localhost:8080
- Monitoring Dashboard: http://localhost:3000

## UAT Environment Deployment (Azure)

### Prerequisites

- Azure subscription
- Azure CLI installed and configured
- Terraform 1.0 or later
- Service Principal with necessary permissions

### Infrastructure Provisioning

1. Initialize Terraform:
   ```bash
   cd infrastructure/terraform/azure
   terraform init
   ```

2. Apply the Terraform configuration:
   ```bash
   terraform apply
   ```

3. Run the UAT environment setup script:
   ```bash
   cd ../../../environments/uat
   ./setup.sh
   ```

4. Verify the deployment:
   ```bash
   cd tests
   pytest
   ```

### Configuration

The UAT environment uses configuration files located in `environments/uat/config`.

### Accessing Services

- API Service: https://uat-sentiment-api.azure.example.com
- Admin Web App: https://uat-sentiment-admin.azure.example.com
- Monitoring Dashboard: https://uat-sentiment-monitoring.azure.example.com

## CI/CD Pipeline

The CI/CD pipeline is configured to automatically:

1. Build and test services on each commit
2. Deploy to SIT environment on successful builds
3. Deploy to UAT environment after manual approval

### Pipeline Configuration

Pipeline configuration files are located in `.github/workflows/`.

## Monitoring and Logging

### Monitoring

The system includes a monitoring stack based on Prometheus and Grafana:

- Prometheus for metrics collection
- Grafana for visualization
- AlertManager for alerting

### Logging

Logs are collected using:

- Fluentd for log collection
- Elasticsearch for log storage
- Kibana for log visualization

## Troubleshooting

### Common Issues

1. **Service not starting:**
   - Check Docker logs: `docker compose logs <service-name>`
   - Verify environment configuration

2. **API connection issues:**
   - Check network connectivity
   - Verify API service is running

3. **Database errors:**
   - Check database connection settings
   - Verify database service is running

### Support

For additional support, contact the development team at support@example.com.