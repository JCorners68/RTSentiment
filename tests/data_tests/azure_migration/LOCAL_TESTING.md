# Local Testing Guide for Phase 4 Implementation

This guide explains how to test the Phase 4 implementation locally without Azure.

## Prerequisites

- Python 3.8+
- Local Dremio instance running (via Docker)
- Local MinIO instance running (via Docker)
- Required Python packages:
  - jaydebeapi
  - jpype1
  - pandas
  - pyarrow
  - pyiceberg

## Step 1: Start Local Services

Ensure your local Dremio and MinIO services are running:

```bash
# Start the containers using docker-compose
cd /home/jonat/WSL_RT_Sentiment
docker compose up -d
```

## Step 2: Verify Configuration

Check the local configuration file:

```bash
cat /home/jonat/WSL_RT_Sentiment/tests/data_tests/azure_migration/config_local.json
```

Make sure the Dremio host, port, username, and password match your local setup.

## Step 3: Run the Local Test Script

Run the local test script with a specific ticker:

```bash
cd /home/jonat/WSL_RT_Sentiment/tests/data_tests/azure_migration
./test_local.py --ticker AAPL --verbose
```

This will:
1. Test Dremio JDBC connectivity
2. Test Iceberg table creation
3. Test writing a sample record
4. Test migrating a Parquet file to Iceberg

The test results will be saved in the output directory specified in your config file.

## Step 4: Verify Results

1. Log in to Dremio UI (typically at http://localhost:9047)
2. Navigate to your catalog and namespace
3. Check that the table was created and contains data
4. Run a sample query to verify the data:

   ```sql
   SELECT COUNT(*) FROM DREMIO.sentiment.sentiment_data_local
   ```

## Troubleshooting

Common issues:

1. **JDBC Connection Issues**:
   - Verify Dremio is running: `docker ps | grep dremio`
   - Check Docker networking: `docker network inspect bridge`
   - Ensure port 31010 is accessible

2. **Missing Parquet Files**:
   - Check that the Parquet files exist: `ls -l /home/jonat/WSL_RT_Sentiment/data_sim/output/`
   - Try a different ticker if needed

3. **JVM/JDBC Driver Issues**:
   - Run the setup script: `./scripts/setup_dremio_jdbc.sh`
   - Verify the driver exists: `ls -l /home/jonat/WSL_RT_Sentiment/drivers/dremio-jdbc-driver.jar`

4. **Table Creation Failures**:
   - Check Dremio logs: `docker logs dremio`
   - Verify that you have permissions to create tables in Dremio

## Next Steps

After successfully testing locally, you'll be ready for Azure migration:

1. Set up Azure Blob Storage
2. Update the Azure configuration file with your credentials
3. Run the full Azure migration test suite