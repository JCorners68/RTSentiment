# Azure Migration Test Framework for Phase 4

This directory contains test scripts for the Phase 4 Azure migration of the RT Sentiment Iceberg data tier.

## Overview

The test framework validates the complete workflow of migrating Parquet files to Iceberg tables hosted in Azure Blob Storage via Dremio. It includes tests for:

1. Azure Blob Storage setup and configuration
2. Dremio JDBC connection with Azure integration
3. Parquet to Iceberg migration
4. Data integrity validation

## Prerequisites

- Python 3.8+
- Azure Blob Storage account
- Dremio instance (local or remote)
- Required Python packages (install with `pip install -r requirements.txt`):
  - azure-storage-blob
  - azure-identity
  - jaydebeapi
  - jpype1
  - pandas
  - pyarrow
  - numpy

## Configuration

The tests use a configuration file (`config.json`) with the following structure:

```json
{
  "azure": {
    "connection_string": "YOUR_AZURE_STORAGE_CONNECTION_STRING",
    "account_name": "YOUR_STORAGE_ACCOUNT_NAME",
    "account_key": "YOUR_STORAGE_ACCOUNT_KEY",
    "container_name": "iceberg-warehouse",
    "folder_path": "sentiment-data",
    "service_principal_id": "YOUR_SERVICE_PRINCIPAL_ID",
    "service_principal_secret": "YOUR_SERVICE_PRINCIPAL_SECRET",
    "tenant_id": "YOUR_TENANT_ID"
  },
  "dremio": {
    "host": "localhost",
    "port": 31010,
    "username": "dremio",
    "password": "dremio123",
    "catalog": "DREMIO",
    "namespace": "sentiment",
    "table_name": "sentiment_data_azure"
  },
  "test": {
    "parquet_dir": "/home/jonat/WSL_RT_Sentiment/data_sim/output",
    "batch_size": 100,
    "max_workers": 4,
    "validation_sample_size": 50,
    "output_dir": "/home/jonat/WSL_RT_Sentiment/tests/data_tests/azure_migration/results"
  }
}
```

**Important**: You must provide either:
- `connection_string` OR
- `account_name` AND `account_key` OR
- `account_name`, `service_principal_id`, `service_principal_secret`, and `tenant_id`

## Running Tests

### Option 1: Run All Tests

The simplest way to run all tests is to use the master test script:

```bash
./run_all_tests.py --ticker AAPL
```

This will run all test steps in sequence. If any step fails, subsequent steps will not be executed.

Options:
- `--config PATH`: Path to the configuration file (default: `config.json`)
- `--ticker SYMBOL`: Ticker to migrate (migrates all tickers if not specified)
- `--verbose, -v`: Enable verbose logging
- `--skip-steps LIST`: Comma-separated list of steps to skip (1-4)

### Option 2: Run Individual Tests

You can also run individual test scripts:

1. **Azure Blob Storage Setup**:
   ```bash
   ./test_azure_setup.py
   ```

2. **Dremio JDBC Connection**:
   ```bash
   ./test_dremio_azure_connection.py
   ```

3. **Parquet Migration**:
   ```bash
   ./test_parquet_migration.py --ticker AAPL
   ```

4. **Migration Validation**:
   ```bash
   ./test_validation.py --parquet-file /path/to/AAPL_sentiment.parquet
   ```

## Test Reports

All test results are saved in the output directory specified in the configuration file. Each test run creates a timestamped directory containing:

- `config.json`: The configuration used for the test run
- `test_report.json`: Overall test report
- `migration_report_*.json`: Detailed migration report
- `validation_report_*.json`: Detailed validation report

## Verification Procedure

After running the tests, you should verify the results by:

1. Checking the test reports in the output directory
2. Logging in to Dremio UI and verifying the migrated data
3. Running sample queries in Dremio to verify the data is correct
4. Checking the Azure portal to verify the Blob Storage container and files

## Troubleshooting

Common issues:

1. **Authentication Errors**:
   - Verify your Azure credentials are correct
   - Check for expired service principal secrets or credentials
   - Ensure proper permissions are granted for the storage account

2. **JDBC Connection Issues**:
   - Verify Dremio is running
   - Check that the JDBC driver is available
   - Ensure firewall or network settings allow connectivity

3. **Migration Failures**:
   - Check that the Parquet files exist in the specified directory
   - Verify the schema compatibility between Parquet and Iceberg
   - Check for sufficient permissions to read/write data

4. **Validation Errors**:
   - Check for data type mismatches between source and target
   - Verify that all required fields are present in both source and target
   - Check that complex data types are properly handled

## Support

For assistance with these tests, contact the RT Sentiment team.