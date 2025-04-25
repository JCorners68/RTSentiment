# End-to-End Tests

This directory contains end-to-end tests that verify the complete system workflow.

## Structure

- `tests/`: Contains all end-to-end test scripts
- `results/`: Contains test results and reports

## Running Tests

To run all end-to-end tests:

```bash
../run_e2e_tests.sh
```

To run a specific test:

```bash
pytest tests/test_filename.py
```

## Writing New Tests

When adding new end-to-end tests, follow these guidelines:

1. Place test scripts in the `tests` directory
2. Test complete user workflows
3. Include cleanup to prevent test data from affecting other tests
4. Be mindful of test duration - E2E tests are typically slower
