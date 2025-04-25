# Integration Tests

This directory contains integration tests that verify the interactions between multiple components.

## Structure

- `tests/`: Contains all integration test scripts
- `results/`: Contains test results and reports

## Running Tests

To run all integration tests:

```bash
pytest tests/
```

To run a specific test:

```bash
pytest tests/test_filename.py
```

## Writing New Tests

When adding new integration tests, follow these guidelines:

1. Place test scripts in the `tests` directory
2. Test the interaction between multiple components
3. Use mocking sparingly - integration tests should test real interactions
4. Include setup and teardown to ensure a clean test environment
