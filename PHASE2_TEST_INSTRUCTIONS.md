# Phase 2 Testing Instructions

This document provides step-by-step instructions for running the tests in section 2.4 of the Definitive Data Tier Plan, ensuring proper verification with real data.

## Prerequisites

- Docker installed (for Dremio container)
- Python 3.8+
- JDK 8+ installed
- The iceberg_venv virtual environment set up

## Test Execution Steps

### 1. Set Up the JDBC Driver

First, make sure the Dremio JDBC driver is properly set up:

```bash
# Make the script executable if needed
chmod +x scripts/setup_dremio_jdbc.sh

# Run the setup script
./scripts/setup_dremio_jdbc.sh
```

### 2. Start the Dremio Test Container

For real verification, start the Dremio container:

```bash
# Make the script executable if needed
chmod +x start_dremio_test_container.sh

# Start the Dremio container
./start_dremio_test_container.sh
```

Wait for the container to start (it might take a minute or two).

### 3. Run the Tests

Once Dremio is running, run the verification tests:

```bash
# Make the script executable if needed
chmod +x run_phase2_tests.sh

# Run the full battery of tests
./run_phase2_tests.sh
```

This script will:
1. Verify the JDBC driver
2. Run unit tests for the Kafka integration factory
3. Run mock tests for the Dremio Kafka integration
4. Run the Iceberg setup test (if Docker is available)
5. Check if the Dremio container is running
6. If Dremio is running, it will run the real data verification script

### 4. Verify the Results

The verification script will:
1. Connect to Dremio via JDBC
2. Create a test table with the Iceberg schema
3. Write sample test records to the table
4. Query the table to verify the records were written correctly
5. Display the results, including actual data from the table

### 5. Manual Verification (Optional)

You can also manually verify the results by:

1. Opening the Dremio web interface at http://localhost:9047
2. Logging in with the default credentials (dremio/dremio123)
3. Navigating to the "sentiment_test" space
4. Viewing the verification table created during the test

## Troubleshooting

If the tests fail:

1. Check that the Dremio container is running: `docker ps | grep dremio`
2. Verify the JDBC driver is correctly installed: `ls -l drivers/dremio-jdbc-driver.jar`
3. Check the Dremio logs: `docker logs dremio`
4. Try restarting the Dremio container: `docker restart dremio`

## Understanding Test Coverage

These tests verify:

1. **DremioJdbcWriter Component**:
   - Connection management
   - Schema creation
   - Batch writing
   - Error handling
   - Data type mapping

2. **Kafka Integration**:
   - Factory pattern for creating the appropriate integration
   - Event processing
   - Batch processing
   - Automatic flushing

3. **End-to-End Flow**:
   - Real data writing (when Dremio is available)
   - Schema validation
   - Data verification

All these checks ensure that Phase 2 implementation is complete and functional with real data.