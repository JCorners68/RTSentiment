# User Acceptance Testing (UAT) Procedure for Data Tier Plan Phase 3

This document outlines the step-by-step procedure for testing and verifying the Phase 3 implementation of the Data Tier Plan. The UAT process is designed to be straightforward and verify all key components of the Phase 3 implementation.

## Prerequisites

Before beginning UAT, ensure you have:

1. Access to the project repository
2. Python 3.8+ installed
3. Docker and Docker Compose installed (for Dremio)
4. At least 8GB of RAM available
5. Basic familiarity with command-line operations

## Test Environment Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/JCorners68/RTSentiment.git
   cd RTSentiment
   git checkout adv_data_tier
   ```

2. Navigate to the project root directory
3. Create and activate a Python virtual environment:

```bash
python3 -m venv dremio_venv
source dremio_venv/bin/activate  # On Windows: dremio_venv\Scripts\activate
```

4. Install required packages:

```bash
pip install jpype1 jaydebeapi pandas fastapi uvicorn tabulate
```

## UAT Procedure

### Test 1: Environment and JDBC Connection Verification

**Purpose**: Verify that the JVM environment is properly configured and that the JDBC connection to Dremio works.

**Steps**:

1. Run the Dremio connection test script:

```bash
./scripts/test_dremio_connection.sh
```

2. Verify the output shows successful connection, including:
   - Driver initialization
   - Connection establishment
   - Query execution

**Expected Result**: Script completes with a success message and displays test results showing all connection tests passed.

**Pass Criteria**: The script runs without errors and displays "Test complete!" message.

### Test 2: Query Service Verification

**Purpose**: Verify that all query service functionality works correctly.

**Steps**:

1. Run the comprehensive query service verification script:

```bash
source ./drivers/config/setenv.sh
python ./iceberg_lake/query/verify_query_service.py --ticker AAPL
```

2. Observe the output, which will test:
   - Basic sentiment queries
   - Time series analysis
   - Emotion analysis
   - Entity-based sentiment
   - Aspect-based sentiment

**Expected Result**: The verification script should show "PASS" for all test categories in the summary table.

**Pass Criteria**: All tests in the summary show "PASS" status, and sample data is displayed for each query type.

### Test 3: API Service Verification

**Purpose**: Verify that the FastAPI service is running and accessible.

**Steps**:

1. Start the API service:

```bash
source ./drivers/config/setenv.sh
python ./iceberg_lake/api/run_api.py
```

2. Open a new terminal window (keep the API running)

3. Run the API client demo script:

```bash
source dremio_venv/bin/activate  # Activate the virtual environment in the new terminal
python ./iceberg_lake/examples/api_client_demo.py
```

**Expected Result**: The demo script runs successfully and displays sample data from each API endpoint.

**Pass Criteria**: 
- API client connects successfully
- Top tickers are displayed
- Sentiment data for a ticker is shown
- Time series data is displayed
- Source breakdown information is returned

### Test 4: Performance Evaluation

**Purpose**: Evaluate the performance of the query service and API.

**Steps**:

1. With the API service still running, test its response time using curl or a browser:

```bash
time curl -s "http://localhost:8000/sentiment/tickers?days=30&limit=5" | head -20
```

2. Run the query service with a larger date range:

```bash
source ./drivers/config/setenv.sh
python ./iceberg_lake/query/minimal_example.py --days 90 --ticker AAPL
```

**Expected Result**: Queries should complete in a reasonable time frame (usually under 5 seconds for simple queries).

**Pass Criteria**: All queries complete without timing out and return results within 10 seconds.

### Test 5: Error Handling Verification

**Purpose**: Verify that the system properly handles error conditions.

**Steps**:

1. Test with an invalid ticker:

```bash
curl -s "http://localhost:8000/sentiment/timeseries?ticker=INVALID&interval=day&days=30"
```

2. Test with missing parameters:

```bash
curl -s "http://localhost:8000/sentiment/timeseries"
```

3. Test with an invalid date range:

```bash
curl -s "http://localhost:8000/sentiment/timeseries?ticker=AAPL&interval=day&days=-1"
```

**Expected Result**: Each request should return an appropriate error message with a non-200 status code.

**Pass Criteria**: System returns proper error messages rather than crashing or returning invalid data.

## Verification Checklist

Use this checklist to record the results of your UAT:

- [ ] Test 1: Environment and JDBC Connection Verification
  - [ ] Script runs without errors
  - [ ] Connection to Dremio is established
  - [ ] Driver information is displayed

- [ ] Test 2: Query Service Verification
  - [ ] Connection test passes
  - [ ] Basic sentiment query passes
  - [ ] Time series query passes
  - [ ] Emotion analysis query passes
  - [ ] Entity query passes
  - [ ] Aspect-based sentiment query passes
  - [ ] Overall verification status is PASS

- [ ] Test 3: API Service Verification
  - [ ] API service starts correctly
  - [ ] Client demo connects to API
  - [ ] Top tickers endpoint works
  - [ ] Sentiment data endpoint works
  - [ ] Time series endpoint works
  - [ ] Sources endpoint works

- [ ] Test 4: Performance Evaluation
  - [ ] API responses return within 5 seconds
  - [ ] Larger queries complete within 10 seconds

- [ ] Test 5: Error Handling Verification
  - [ ] Invalid ticker handled correctly
  - [ ] Missing parameters handled correctly
  - [ ] Invalid date range handled correctly

## Troubleshooting Common Issues

### JVM Configuration Issues

If you encounter JVM-related errors:

1. Ensure you've run the JVM configuration script:
```bash
source ./drivers/config/setenv.sh
```

2. Check that the JDBC driver is properly installed:
```bash
ls -la ./drivers/dremio-jdbc-driver.jar
```

3. If needed, reinstall the JDBC driver:
```bash
./scripts/setup_dremio_jdbc.sh
```

### Connection Issues

If you can't connect to Dremio:

1. Verify Dremio is running:
```bash
docker ps | grep dremio
```

2. Check the Dremio logs for errors:
```bash
docker logs dremio
```

3. Ensure port 31010 is accessible:
```bash
nc -zv localhost 31010
```

### API Service Issues

If the API service doesn't start:

1. Check for port conflicts:
```bash
lsof -i :8000
```

2. Verify uvicorn is installed:
```bash
pip list | grep uvicorn
```

## Reporting Issues

If you encounter issues during UAT that can't be resolved with the troubleshooting steps, please report them with:

1. The exact command that failed
2. The complete error message
3. The environment information (OS, Python version)
4. Screenshots if applicable

## Environment Setup with AI Assistants

If you prefer to use an AI code assistant (like Claude Code, GitHub Copilot, or similar) to help set up your environment, you can provide the following prompt:

```
I need to set up an environment for UAT testing of the Real-Time Sentiment Analysis system's data tier plan Phase 3 implementation. 

My working directory is: ~/sentiment_test

Please help me:
1. Clone the repository: https://github.com/JCorners68/RTSentiment.git with branch adv_data_tier
2. Set up a Python virtual environment called dremio_venv and install all required packages
3. Set up the Dremio JDBC driver and configuration
4. Configure the JVM environment for compatibility with the Dremio driver
5. Run the connection test to verify the setup

The repository contains a Phase 3 implementation of a sentiment analysis data tier using Dremio, JDBC, and Iceberg. I need to validate that the system is working correctly on my environment.
```

## Conclusion

Upon successful completion of all UAT tests, the Phase 3 implementation should be considered verified and ready for migration to production. The next phase will involve data migration from existing Parquet files to the Iceberg tables.