# Data Tests

This directory contains tests related to data processing, storage, and retrieval.

## Structure

- `tests/`: Contains all test scripts for data components
- `results/`: Contains test results and reports

## Running Tests

To run all data tests:

```bash
pytest tests/
```

To run a specific test:

```bash
pytest tests/test_filename.py
```

## Writing New Tests

When adding new data tests, follow these guidelines:

1. Place test scripts in the `tests` directory
2. Follow the existing naming conventions
3. For data formats or schemas, include validation tests
4. For data processing flows, test both success and error cases
