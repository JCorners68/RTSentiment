# API Tests

This directory contains tests for the API endpoints of the system.

## Structure

- `tests/`: Contains all test scripts for API endpoints
- `results/`: Contains test results and reports

## Running Tests

To run all API tests:

```bash
../run_api_tests.sh
```

To run a specific test:

```bash
pytest tests/test_filename.py
```

## Writing New Tests

When adding new API tests, follow these guidelines:

1. Place test scripts in the `tests` directory
2. Use pytest fixtures for common setup
3. Follow the existing naming conventions
4. Include both positive and negative test cases
