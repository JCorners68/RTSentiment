# Detailed Local UAT Instructions for Phase 4 (Azure Migration)

This document provides comprehensive step-by-step instructions for conducting User Acceptance Testing (UAT) of the Phase 4 Azure migration implementation in a local development environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Testing Procedure](#testing-procedure)
4. [Test Scenarios](#test-scenarios)
5. [Verification and Validation](#verification-and-validation)
6. [Troubleshooting](#troubleshooting)
7. [Results Documentation](#results-documentation)
8. [Cleanup](#cleanup)

## Prerequisites

Before beginning UAT, ensure you have the following:

- **Hardware Requirements:**
  - Minimum 8GB RAM
  - 20GB free disk space

- **Software Requirements:**
  - Python 3.8 or higher
  - Docker (version 20.10+) and Docker Compose (version 2.0+)
  - Git client
  - Java Development Kit (JDK) 11+ for JDBC connectivity

- **Access Requirements:**
  - Local administrator privileges (for Docker)
  - Internet connectivity (for downloading dependencies)

## Environment Setup

### Step 1: Verify Repository Status

Since you're already working within the repository, verify you're on the correct branch:

```bash
cd /home/jonat/WSL_RT_Sentiment
git status
```

Ensure you're on the `adv_data_tier` branch. If not, switch to it and pull the latest changes:

```bash
git checkout adv_data_tier
git pull
```

### Step 2: Create UAT Environment

Create and configure a dedicated virtual environment for UAT:

```bash
cd /home/jonat/WSL_RT_Sentiment/P4_UAT
python -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
```

### Step 3: Install Required Packages

Install all dependencies needed for testing:

```bash
cd /home/jonat/WSL_RT_Sentiment
pip install -e .
pip install -r tests/data_tests/azure_migration/requirements.txt
```

### Step 4: Start Local Services

Start the required Docker containers for local testing:

```bash
cd /home/jonat/WSL_RT_Sentiment
docker-compose up -d
```

Verify that the containers are running:

```bash
docker ps | grep -E 'dremio|minio'
```

Expected output:
```
<container_id>  dremio/dremio-oss:latest  "/opt/dremio/bin/dre…"  ...  9047/tcp, 31010/tcp, 45678/tcp  dremio
<container_id>  minio/minio:latest        "/usr/bin/docker-ent…"  ...  9000/tcp, 9001/tcp              minio
```

### Step 5: Set Up JDBC Driver

The Dremio JDBC driver is required for database connectivity:

```bash
cd /home/jonat/WSL_RT_Sentiment
./scripts/setup_dremio_jdbc.sh
```

Verify the JDBC driver installation:

```bash
ls -la drivers/dremio-jdbc-driver.jar
```

### Step 6: Configure Local Test Settings

Create local configuration by copying the template:

```bash
cd /home/jonat/WSL_RT_Sentiment/P4_UAT
cp ../tests/data_tests/azure_migration/config_local.json ./config.json
```

Edit config.json if needed to match your environment:

```bash
nano config.json
# Ensure Dremio host is set to "localhost" and proper credentials are configured
```

## Testing Procedure

### Initial Verification Tests

First, run the basic connectivity tests to ensure your environment is correctly set up:

```bash
cd /home/jonat/WSL_RT_Sentiment/P4_UAT
source venv/bin/activate

# Test Dremio connectivity
python ../tests/data_tests/azure_migration/test_local.py --test-connection --config ./config.json
```

You should see a confirmation message that the Dremio connection is successful.

### Comprehensive Test Suite

Run the full local test suite:

```bash
cd /home/jonat/WSL_RT_Sentiment/P4_UAT
python ../tests/data_tests/azure_migration/run_all_tests.py --local --config ./config.json --verbose
```

This will run through all test cases in sequence and generate a detailed report.

## Test Scenarios

The test suite includes the following key scenarios:

### 1. Azure Connection Setup

Tests the Azure connection configuration classes:

```bash
cd /home/jonat/WSL_RT_Sentiment/P4_UAT
python ../tests/data_tests/azure_migration/test_azure_setup.py --config ./config.json --local-simulation
```

### 2. Dremio-Azure Integration

Tests Dremio connection to simulated Azure storage (using MinIO):

```bash
cd /home/jonat/WSL_RT_Sentiment/P4_UAT
python ../tests/data_tests/azure_migration/test_dremio_azure_connection.py --config ./config.json --local
```

### 3. Parquet Migration

Tests migration of Parquet files to Iceberg format:

```bash
cd /home/jonat/WSL_RT_Sentiment/P4_UAT
python ../tests/data_tests/azure_migration/test_parquet_migration.py --config ./config.json --ticker AAPL --max-records 100 --local
```

### 4. Data Validation

Tests validation of migrated data integrity:

```bash
cd /home/jonat/WSL_RT_Sentiment/P4_UAT
python ../tests/data_tests/azure_migration/test_validation.py --config ./config.json --local
```

## Verification and Validation

### Step 1: Check Test Results

After running the test suite, examine the detailed test report:

```bash
cd /home/jonat/WSL_RT_Sentiment/P4_UAT
cat test_results/summary_report.json
```

### Step 2: Manual Verification in Dremio

1. Open a web browser and navigate to http://localhost:9047
2. Log in with the default credentials (dremio / dremio123)
3. Navigate to Spaces → sentiment
4. Verify that test tables have been created
5. Run a sample query to validate data:

```sql
SELECT COUNT(*) FROM DREMIO.sentiment.sentiment_data_uat_test
```

### Step 3: Validate Data Integrity

Compare source data with migrated data:

```bash
cd /home/jonat/WSL_RT_Sentiment/P4_UAT
python -c "
import pandas as pd
import pyarrow.parquet as pq

# Source data
source_df = pq.read_table('../data_sim/output/aapl_sentiment.parquet').to_pandas()

# Query Dremio for migrated data (using your connection details)
from iceberg_lake.query.dremio_sentiment_query import DremioSentimentQueryService
query_service = DremioSentimentQueryService(
    dremio_host='localhost',
    dremio_port=31010,
    dremio_username='dremio',
    dremio_password='dremio123',
    namespace='sentiment',
    table_name='sentiment_data_uat_test'
)
migrated_df = query_service.run_query('SELECT * FROM DREMIO.sentiment.sentiment_data_uat_test')

# Compare record counts
print(f'Source records: {len(source_df)}')
print(f'Migrated records: {len(migrated_df)}')
"
```

## Troubleshooting

### Common Issues and Solutions

#### Issue: JDBC Connection Failure

```
Error: Could not establish JDBC connection to Dremio
```

**Solutions:**
- Verify Dremio container is running: `docker ps | grep dremio`
- Check container logs: `docker logs dremio`
- Ensure port 31010 is accessible: `nc -zv localhost 31010`
- Verify JDBC driver exists: `ls -la drivers/dremio-jdbc-driver.jar`
- Restart Dremio container: `docker restart dremio`

#### Issue: JVM Not Starting

```
Error: Cannot find JVM or load JVM library
```

**Solutions:**
- Verify Java is installed: `java -version`
- Set JAVA_HOME environment variable: `export JAVA_HOME=/path/to/java`
- Install JDK if missing: `sudo apt install default-jdk`
- Check jpype1 installation: `pip show jpype1`

#### Issue: Missing or Invalid Parquet Files

```
Error: Could not find Parquet file or Parquet file is invalid
```

**Solutions:**
- Check file exists: `ls -la /home/jonat/WSL_RT_Sentiment/data_sim/output/aapl_sentiment.parquet`
- Try a different ticker: `--ticker TSLA`
- Generate sample data if needed: `python /home/jonat/WSL_RT_Sentiment/scripts/generate_sample_data.py`

#### Issue: Schema Validation Errors

```
Error: Schema validation failed: Field X missing or has incorrect type
```

**Solutions:**
- Check schema compatibility
- Run with `--skip-validation` flag to bypass validation
- Use `--truncate-fields` to allow field truncation

### Getting Support

If you encounter persistent issues:

1. Capture full error message and logs
2. Document steps to reproduce
3. Check docker logs: `docker logs dremio > dremio.log`
4. Contact the development team with these details

## Results Documentation

After completing all tests, document your findings:

```bash
cd /home/jonat/WSL_RT_Sentiment/P4_UAT
cat > uat_results.md << EOL
# Phase 4 UAT Results

## Environment
- OS: $(uname -a)
- Docker version: $(docker --version)
- Python version: $(python --version)
- Java version: $(java -version 2>&1 | head -n 1)

## Test Results Summary
- Connection tests: PASS/FAIL
- Azure setup tests: PASS/FAIL
- Migration tests: PASS/FAIL
- Validation tests: PASS/FAIL

## Issues Encountered
1. [Issue description]
2. [Issue description]

## Recommendations
- [Your recommendations]

## Overall Assessment
- [Your assessment of the implementation]
EOL
```

## Cleanup

When UAT is complete, clean up resources:

```bash
# Stop Docker containers
cd /home/jonat/WSL_RT_Sentiment
docker-compose down

# Deactivate virtual environment
deactivate

# Optional: Remove test data
rm -rf /home/jonat/WSL_RT_Sentiment/P4_UAT/test_results
```

## Next Steps

After successful local UAT:

1. Document any issues in the project issue tracker
2. Share UAT results with the development team
3. Proceed with cloud UAT if local testing is successful