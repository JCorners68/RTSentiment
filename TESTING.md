# Testing Guide for Real-Time Sentiment Analysis

This document provides an overview of the testing strategy for the Real-Time Sentiment Analysis application.

## Testing Approach

The application uses a multi-layered testing approach:

1. **Unit Tests**: Test individual components in isolation
2. **Mock-Based Integration Tests**: Test component integration using mocks
3. **Full Integration Tests**: Test actual integration between services

## Test Types

### Unit Tests

- `test_minimal.py`: Basic functionality tests that don't require external dependencies
- `test_finbert_model.py`: Tests for the FinBERT sentiment model

### Mock-Based Integration Tests

- `test_mock_sentiment_service.py`: Tests the sentiment service API using mocks
- `test_integration.py`: Tests the message processing flow with mocked components

### Full Integration Tests

- `test_sentiment_api.py`: Tests the full API with actual FastAPI client

## Running Tests

The `run_tests.sh` script provides a unified testing interface with several options:

### Quick Test Run (Mock-Based Tests Only)

```bash
./run_tests.sh --mock
```

This runs the mock-based tests using a Python container with a virtual environment, without requiring the full environment. This is the default if no options are specified.

### API Unit Tests

```bash
./run_tests.sh --unit
```

This runs unit tests for the API in an isolated environment. It automatically:
1. Starts only the required services (PostgreSQL and Redis)
2. Creates a temporary Python container with a virtual environment
3. Runs the API unit tests
4. Cleans up the services when done

### Full Integration Tests

```bash
./run_tests.sh --integration
```

This runs the full integration tests using Docker Compose:
1. Builds and starts the test containers defined in `docker-compose.test.yml`
2. Runs tests that validate interactions between services
3. Terminates all containers when tests complete

### Running Tests Directly

If you already have the environment running:

```bash
docker compose up -d
docker compose exec api pytest
```

### Run Specific Tests

To run a specific test file:
```bash
pytest tests/test_minimal.py -v
```

To run a specific test function:
```bash
pytest tests/test_minimal.py::test_sentiment_score_calculation -v
```

### Run with Coverage

```bash
pytest tests/ --cov=api --cov=sentiment_service
```

## Adding New Tests

1. Create a new test file in the `tests/` directory with the `test_` prefix
2. Use pytest fixtures for setup/teardown
3. Use `@pytest.mark.asyncio` for testing async functions
4. Group related tests in classes
5. Follow the naming convention: `test_<what_is_being_tested>.py`

## Mock Strategy

For mock-based tests:
1. Create mock classes that mimic the behavior of real components
2. Use the `unittest.mock` module for patching dependencies
3. Ensure mocks return realistic data that matches the real components
4. Consider using `AsyncMock` for async functions

## Best Practices

1. Keep tests independent of each other
2. Clean up resources after tests
3. Use descriptive test names
4. Add docstrings to test functions
5. Use parametrized tests for similar test cases
6. Aim for high test coverage, especially for critical paths