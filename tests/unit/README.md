# Unit Tests

This directory contains unit tests for individual components of the system.

## Structure

- `tests/`: Contains all unit test scripts
- `results/`: Contains test results and reports

## Running Tests

To run all unit tests:

```bash
pytest tests/
```

To run a specific test:

```bash
pytest tests/test_filename.py
```

## Writing New Tests

When adding new unit tests, follow these guidelines:

1. Place test scripts in the `tests` directory
2. Each test should test a single function or method
3. Use mocking for external dependencies
4. Follow the pytest style of using assertions
