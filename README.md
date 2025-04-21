# Real-Time Sentiment Analysis for Trading

A real-time financial sentiment analysis system for trading applications, processing news and social media data to provide actionable sentiment insights.

## Features

- Real-time sentiment analysis of financial news and social media
- Multiple sentiment analysis models (FinBERT, FinGPT, Llama4)
- API access with tier-based subscription model
- Event-driven architecture with Kafka/Event Hub
- Redis caching for low-latency responses
- Docker containerization for easy deployment

## Architecture

The application is built with a microservices architecture:

1. **Data Acquisition Layer**: Collects data from various sources
2. **Event Ingestion Layer**: Processes events via Kafka/Event Hub
3. **Processing Layer**: Analyzes sentiment using ML models
4. **API Layer**: Exposes REST endpoints
5. **Data Persistence Layer**: Stores results
6. **Monitoring Layer**: Provides metrics and logging

## Setup

### Prerequisites

- Docker and Docker Compose
- NVIDIA Docker runtime (for GPU support)

### Quick Start

1. Clone the repository
2. Run the setup script to download models:
   ```
   ./scripts/download_models.sh
   ```
3. Start the services:
   ```
   docker-compose up -d
   ```
4. Access the API at http://localhost:8001

## Configuration

Configuration is managed through environment variables, which can be set in the `.env` file or directly in the `docker-compose.yml` file.

### Environment Variables

- `FINBERT_USE_ONNX`: Whether to use ONNX runtime (true/false)
- `FINBERT_USE_GPU`: Whether to use GPU acceleration (true/false)
- `REDIS_HOST`: Redis hostname
- `REDIS_PORT`: Redis port
- `KAFKA_BOOTSTRAP_SERVERS`: Kafka broker addresses

## Development

### Running Tests

The project includes unit tests, mock-based integration tests, and full integration tests.

To run the mock-based tests (recommended for development):

```bash
./run_tests.sh --mock
```

To run unit tests for the API:

```bash
./run_tests.sh --unit
```

To run full integration tests with Docker Compose:

```bash
./run_tests.sh --integration
```

You can also run tests directly inside a running container:

```bash
docker compose up -d
docker compose exec api pytest
```

For more details about testing, see [TESTING.md](TESTING.md).

### Code Formatting

Format code using Black and isort:

```bash
black .
isort .
```

### Type Checking

Check types with MyPy:

```bash
mypy .
```

## API Documentation

When running, the API documentation is available at:
- http://localhost:8001/docs (Swagger UI)
- http://localhost:8001/redoc (ReDoc)

## Monitoring

- Prometheus metrics: http://localhost:9090
- Grafana dashboards: http://localhost:3000
- Kafka monitoring: http://localhost:8080

## License

[MIT License](LICENSE)