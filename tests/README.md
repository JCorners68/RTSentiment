# Real-Time Sentiment Analysis Tests

This directory contains comprehensive tests for the Real-Time Sentiment Analysis system. Tests are organized by category to provide clear isolation and maintainability.

## Test Structure

- **[api/](./api/)**: Tests for API endpoints and interfaces
  - `tests/`: Test scripts
  - `results/`: Test results and reports

- **[data/](./data/)**: Tests for data processing, storage, and retrieval
  - `tests/`: Test scripts
  - `results/`: Test results and reports

- **[integration/](./integration/)**: Tests verifying interactions between components
  - `tests/`: Test scripts
  - `results/`: Test results and reports

- **[unit/](./unit/)**: Tests for individual functions and components
  - `tests/`: Test scripts
  - `results/`: Test results and reports

- **[e2e/](./e2e/)**: End-to-end tests for complete system workflows
  - `tests/`: Test scripts
  - `results/`: Test results and reports

## Running Tests

Each test category includes specific instructions for running tests in its README file. For convenience, you can also use the following scripts:

- `run_api_tests.sh`: Run API tests
- `run_e2e_tests.sh`: Run end-to-end tests
- `run_tests.sh`: Run all tests

## Test Dependencies

Test dependencies are listed in `requirements.txt`. Install them using:

```bash
pip install -r requirements.txt
```

## Writing New Tests

When adding new tests:

1. Place the test in the appropriate category directory
2. Follow the existing naming conventions
3. Update the relevant README.md file if necessary
4. Ensure tests can run in isolation and as part of a batch
5. Document any specific setup requirements or dependencies