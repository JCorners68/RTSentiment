# Phase 5 Kickoff Guide: Production Deployment and Migration

This guide outlines the step-by-step process for initiating Phase 5 of the data tier implementation, which focuses on production deployment and migration between PostgreSQL and Iceberg.

## Prerequisites

- Completion of Phases 1-4
- Azure subscription with appropriate permissions
- Terraform CLI installed
- Azure CLI installed and configured
- Docker and Kubernetes CLI tools installed

## Step 1: Deploy Production Infrastructure

First, we'll deploy the Azure infrastructure required for Iceberg in production:

```bash
# Navigate to the Azure Terraform directory
cd /home/jonat/real_senti/infrastructure/terraform/azure

# Initialize Terraform
terraform init

# Review the planned changes
terraform plan -out tfplan

# Apply the changes
terraform apply tfplan
```

This will create:
- Azure Data Lake Storage Gen2 for Iceberg tables
- Azure App Configuration for feature flags
- Azure Monitoring resources for observability
- Key Vault for storing secrets
- Network security components

## Step 2: Configure the Data Tier Service for Production

Update the data tier service to connect to both PostgreSQL and Iceberg:

```bash
# Navigate to the data tier service directory
cd /home/jonat/real_senti/services/data-tier

# Build the service with production configuration
./mvnw clean package -DskipTests -Pprod

# Build the migration service Docker image
docker build -t data-migration-service:latest -f Dockerfile.migration .
```

## Step 3: Deploy Services to Kubernetes

Deploy the updated services to the AKS cluster:

```bash
# Set environment variables
export AKS_RESOURCE_GROUP="rt-sentiment-uat"
export AKS_CLUSTER_NAME="rt-sentiment-aks"

# Get AKS credentials
az aks get-credentials --resource-group $AKS_RESOURCE_GROUP --name $AKS_CLUSTER_NAME

# Apply Kubernetes configurations
kubectl apply -f /home/jonat/real_senti/infrastructure/kubernetes/base/data-tier.yaml
kubectl apply -f /home/jonat/real_senti/infrastructure/kubernetes/base/data-migration.yaml
```

## Step 4: Create Kubernetes Secrets

Create the secrets required for the services:

```bash
# Get required values from Terraform outputs
export POSTGRES_URL=$(terraform output -raw postgres_connection_string)
export POSTGRES_USERNAME=$(terraform output -raw postgres_username)
export POSTGRES_PASSWORD=$(terraform output -raw postgres_password)
export APP_CONFIG_ENDPOINT=$(terraform output -raw app_config_endpoint)
export APP_INSIGHTS_CONNECTION_STRING=$(terraform output -raw app_insights_connection_string)
export ICEBERG_REST_CATALOG_URL=$(terraform output -raw iceberg_rest_catalog_url)
export ICEBERG_STORAGE_ACCOUNT=$(terraform output -raw iceberg_storage_account_name)
export ICEBERG_STORAGE_ACCESS_KEY=$(terraform output -raw iceberg_storage_account_primary_key)

# Create the Kubernetes secret
kubectl create secret generic data-tier-secrets \
  --from-literal=postgres-url="$POSTGRES_URL" \
  --from-literal=postgres-username="$POSTGRES_USERNAME" \
  --from-literal=postgres-password="$POSTGRES_PASSWORD" \
  --from-literal=app-config-endpoint="$APP_CONFIG_ENDPOINT" \
  --from-literal=app-insights-connection-string="$APP_INSIGHTS_CONNECTION_STRING" \
  --from-literal=iceberg-rest-catalog-url="$ICEBERG_REST_CATALOG_URL" \
  --from-literal=iceberg-storage-account="$ICEBERG_STORAGE_ACCOUNT" \
  --from-literal=iceberg-storage-access-key="$ICEBERG_STORAGE_ACCESS_KEY"
```

## Step 5: Initialize Iceberg Schema

Create the Iceberg tables in the catalog:

```bash
# Deploy the schema initialization job
kubectl apply -f /home/jonat/real_senti/infrastructure/kubernetes/base/schema-init.yaml

# Verify job completion
kubectl get jobs schema-init-job
```

## Step 6: Start Data Migration

Initiate the data migration from PostgreSQL to Iceberg:

```bash
# Get the data migration service endpoint
export MIGRATION_SERVICE=$(kubectl get svc data-migration-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Start SentimentRecord migration
curl -X POST "http://$MIGRATION_SERVICE:8080/api/v1/migration/sentiment-records/postgres-to-iceberg"

# Start MarketEvent migration
curl -X POST "http://$MIGRATION_SERVICE:8080/api/v1/migration/market-events/postgres-to-iceberg"
```

## Step 7: Monitor Migration Progress

Monitor the migration status through these methods:

1. **Kubernetes Logs**:
   ```bash
   kubectl logs -f deployment/data-migration-service
   ```

2. **Migration API**:
   ```bash
   # Check status using the job IDs returned from previous step
   curl "http://$MIGRATION_SERVICE:8080/api/v1/migration/status/$JOB_ID"
   ```

3. **Azure Portal**:
   - Go to the Application Insights resource
   - Navigate to Logs
   - Run queries to check migration metrics

## Step 8: Validate Migration Results

Validate that the data was migrated correctly:

```bash
# Validate SentimentRecord migration
curl "http://$MIGRATION_SERVICE:8080/api/v1/migration/validate/sentiment-records"

# Validate MarketEvent migration
curl "http://$MIGRATION_SERVICE:8080/api/v1/migration/validate/market-events"
```

## Step 9: Configure Feature Flags for Gradual Rollout

Configure feature flags in Azure App Configuration:

1. Go to the Azure Portal
2. Navigate to the App Configuration resource
3. Under "Feature Manager", set the following flags:
   - `use-iceberg-backend`: Set to false initially
   - `use-iceberg-optimizations`: Set to false
   - `use-iceberg-partitioning`: Set to false
   - `use-iceberg-time-travel`: Set to false
   - `iceberg-roll-percentage`: Set to 0

## Step 10: Begin Gradual Rollout

Start a controlled rollout to Iceberg:

1. Increase `iceberg-roll-percentage` to 5%
2. Monitor performance and error rates
3. If stable, gradually increase to 10%, 25%, 50%, 75%, and finally 100%
4. Once at 100%, enable `use-iceberg-backend` feature flag

## Step 11: Monitor Production Performance

Monitor the production environment continuously:

1. Check the Azure Monitor dashboard
2. Set up alerts for:
   - Query performance degradation
   - Error rate spikes
   - Storage capacity issues

## Rollback Procedure

If issues are encountered, use the rollback mechanism:

```bash
# Rollback to PostgreSQL
curl -X POST "http://$MIGRATION_SERVICE:8080/api/v1/migration/rollback" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Performance degradation observed"}'
```

## Completion Criteria

Phase 5 is considered complete when:

1. All data is successfully migrated to Iceberg
2. Validation shows 100% data consistency
3. The production system is running on Iceberg with feature flags enabled
4. Monitoring shows stable performance
5. Rollback mechanism has been tested

## Next Steps

After completing Phase 5:
1. Document the production architecture
2. Develop a long-term maintenance plan
3. Plan for future optimizations of the Iceberg implementation