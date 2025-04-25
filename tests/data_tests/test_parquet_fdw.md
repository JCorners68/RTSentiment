# parquet_fdw Testing Framework

This document describes the testing framework for the PostgreSQL Foreign Data Wrapper for Parquet files (parquet_fdw) implementation in the Senti Hub application.

## Overview

The testing framework is designed to validate all aspects of the parquet_fdw implementation, from the Docker setup to the API integration. It consists of two main test scripts:

1. **test_parquet_fdw.py**: A comprehensive test script that requires external dependencies and tests the full functionality.
2. **test_basic_artifacts.py**: A simplified test script that checks if all required files and artifacts are in place, without requiring external dependencies.

## Prerequisites

For the comprehensive test script, you'll need the following Python packages:

```bash
pip install psycopg2-binary pandas pyarrow requests
```

No additional packages are required for the basic test script.

## Running the Tests

### Basic Artifact Tests

The basic tests are designed to run without any external dependencies and validate that all the required files and artifacts are in place.

```bash
# Run all basic tests
./test_basic_artifacts.py --test all

# Run specific test categories
./test_basic_artifacts.py --test artifacts    # Check all required files
./test_basic_artifacts.py --test docs         # Check documentation completeness
./test_basic_artifacts.py --test docker       # Check Docker configuration
./test_basic_artifacts.py --test sql          # Check SQL initialization
./test_basic_artifacts.py --test parquet      # Check Parquet files
```

### Comprehensive Tests

The comprehensive tests validate the full functionality of the parquet_fdw implementation, including Docker operations, database connections, and API integration. These tests require running Docker containers and external dependencies.

```bash
# Run all comprehensive tests
./test_parquet_fdw.py --test all

# Run specific test categories
./test_parquet_fdw.py --test setup           # Test Docker image build
./test_parquet_fdw.py --test docker          # Test Docker Compose stack
./test_parquet_fdw.py --test fdw-init        # Test FDW initialization
./test_parquet_fdw.py --test fdw-core        # Test FDW core functionality
./test_parquet_fdw.py --test file-mod        # Test Parquet file modifications
./test_parquet_fdw.py --test pipeline        # Test data pipeline integration
./test_parquet_fdw.py --test api             # Test API integration
./test_parquet_fdw.py --test performance     # Test query performance
./test_parquet_fdw.py --test integrity       # Test data integrity
./test_parquet_fdw.py --test artifacts       # Verify all required artifacts
./test_parquet_fdw.py --test docs            # Review documentation
```

## Test Reports

The testing framework generates Markdown reports for each test category in the `tests/data_tests/` directory. A summary report is also generated. Reports follow the naming convention `test_results_YYMMDD_X.md`, where:

- `YYMMDD` is the date in year-month-day format (e.g., `250423` for April 23, 2025)
- `X` is a sequential number starting from 1 for each day's tests

This format allows multiple test runs on the same day without overwriting previous results.

### Test Report Content

Each test report includes:
- A title indicating the type of test
- Generation timestamp
- Test type identifier
- Detailed test results with pass/fail indicators
- Recommendations for improvements when applicable

The summary report links to all individual test reports from the same test run and provides an overall assessment of the implementation status.

## Final Report

After running all tests, a comprehensive final report is available at:

`/home/jonat/WSL_RT_Sentiment/tests/data_tests/parquet_fdw_final_report.md`

This report summarizes the implementation status, test results, and recommendations for future improvements.

## Troubleshooting

If you encounter issues running the tests:

1. **Dependencies**: Make sure all required Python packages are installed.
2. **Docker**: Ensure Docker is running and the PostgreSQL container is accessible.
3. **Permissions**: Make sure the test scripts have execute permissions (`chmod +x test_*.py`).
4. **API Service**: For API tests, ensure the API service is running on port 8001.
5. **Test Paths**: If running the tests from a different directory, update the `PROJECT_ROOT` variable in the scripts.