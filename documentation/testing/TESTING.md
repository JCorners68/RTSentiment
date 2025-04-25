# Testing Guide for Real-Time Sentiment Analysis

This document provides an overview of the testing strategy for the Real-Time Sentiment Analysis application.

## Testing Approach

The application uses a multi-layered testing approach:

1. **Unit Tests**: Test individual components in isolation
2. **Mock-Based Integration Tests**: Test component integration using mocks
3. **Full Integration Tests**: Test actual integration between services
4. **End-to-End Tests**: Test the complete data flow from scrapers to sentiment analysis

## Test Types

### Unit Tests

- `test_minimal.py`: Basic functionality tests that don't require external dependencies
- `test_finbert_model.py`: Tests for the FinBERT sentiment model

### Mock-Based Integration Tests

- `test_mock_sentiment_service.py`: Tests the sentiment service API using mocks
- `test_integration.py`: Tests the message processing flow with mocked components

### Full Integration Tests

- `test_sentiment_api.py`: Tests the full API with actual FastAPI client

### End-to-End Tests

- `test_e2e_scrapers.py`: Tests the complete flow from data acquisition to sentiment analysis
  - `test_news_scraper_e2e`: Tests the news scraper end-to-end flow
  - `test_reddit_scraper_e2e`: Tests the Reddit scraper end-to-end flow
  - `test_manual_message_e2e`: Tests the system with a manually injected message

## Running Tests

### Standard Tests

The `run_tests.sh` script provides a unified testing interface with several options:

#### Quick Test Run (Mock-Based Tests Only)

```bash
./run_tests.sh --mock
```

This runs the mock-based tests using a Python container with a virtual environment, without requiring the full environment. This is the default if no options are specified.

#### API Unit Tests

```bash
./run_tests.sh --unit
```

This runs unit tests for the API in an isolated environment. It automatically:
1. Starts only the required services (PostgreSQL and Redis)
2. Creates a temporary Python container with a virtual environment
3. Runs the API unit tests
4. Cleans up the services when done

#### Full Integration Tests

```bash
./run_tests.sh --integration
```

This runs the full integration tests using Docker Compose:
1. Builds and starts the test containers defined in `docker-compose.test.yml`
2. Runs tests that validate interactions between services
3. Terminates all containers when tests complete

### End-to-End Tests

The `run_e2e_tests.sh` script provides a dedicated interface for end-to-end testing:

```bash
./run_e2e_tests.sh
```

This script:
1. Checks if the Docker Compose environment is running, starts it if needed
2. Creates a Python container with the required dependencies
3. Runs the end-to-end tests that validate the complete data flow
4. Optionally shuts down the environment when finished

Options:
- `--skip-env-check`: Skip environment check (use when environment is already running)
- `--file <path>`: Run a specific test file
- `--help`: Display help message

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

## Testing the Scrapers

### Unit Testing

The scrapers have individual unit tests that verify their core functionality:
- `test_news_scraper.py`: Tests for the news website scraper
- `test_reddit_scraper.py`: Tests for the Reddit scraper

### End-to-End Testing

The end-to-end tests validate the complete data flow:

1. **Scraper initialization** - Set up the scraper with test configuration
2. **Data acquisition** - Simulate or mock data gathering
3. **Data preprocessing** - Process and enrich the data
4. **Event production** - Send events to Kafka topics
5. **Sentiment analysis** - Process events through the sentiment service
6. **Result verification** - Verify sentiment results in Kafka or via API

To test the scrapers end-to-end:

```bash
./run_e2e_tests.sh
```

For troubleshooting individual scraper issues, you can use the manual message test:

```bash
python -m pytest data_acquisition/tests/test_e2e_scrapers.py::test_manual_message_e2e -v
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

## Test Results Directory Structure

All test results are stored in the standard `/tests/test_results/` directory using a consistent naming convention:

```
[test type]_results_YYMMDD_[instance].md
```

Where:
- `[test type]` is the category of test, such as:
  - `artifact` - Tests for required artifacts
  - `docker` - Docker configuration tests
  - `sql` - SQL initialization tests
  - `parquet` - Parquet file verification tests
  - `doc` - Documentation review tests
  - `scrape` - Scraper test results
  - `e2e` - End-to-end test results
- `YYMMDD` is the date in YY-MM-DD format (e.g., 250423 for April 23, 2025)
- `[instance]` is a sequential number starting at 1 for multiple tests of the same type on the same day

This standardized approach makes it easier to:
- Track test history over time
- Identify specific test runs
- Organize test outputs by type and date
- Automate test result analysis
- Compare results across different test runs

### Output Types

Test outputs are stored in different formats depending on the test type:

- **Markdown (.md)** - Used for human-readable reports with formatted tables and pass/fail indicators
- **JSON (.json)** - Used for structured data that can be programmatically processed, typically from API tests
- **HTML (.html)** - Used for coverage reports and interactive test visualizations

## Best Practices

1. Keep tests independent of each other
2. Clean up resources after tests
3. Use descriptive test names
4. Add docstrings to test functions
5. Use parametrized tests for similar test cases
6. Aim for high test coverage, especially for critical paths
7. For end-to-end tests, use timeout handling to prevent hanging tests
8. Include fallback verification methods (e.g., API checks if Kafka consumer times out)
9. Always save test results to the standard test_results directory with the proper naming convention
10. Include timestamp and context information in test outputs