# Real-Time Sentiment Analysis Project Overview

## Project Purpose

The Real-Time Sentiment Analysis system is designed to gather, analyze, and visualize sentiment data from various financial sources in real-time. It provides actionable insights about market sentiment for stocks, cryptocurrencies, and other financial instruments.

## Features

- Real-time sentiment analysis of financial news and social media
- Multiple sentiment analysis models (FinBERT, FinGPT, Llama4)
- API access with tier-based subscription model
- Event-driven architecture
- Redis caching for low-latency responses
- Docker containerization for easy deployment
- Cross-platform Flutter dashboard for rich data visualization
- Real-time data flow monitoring and analysis
- Parquet file storage for efficient historical data analysis

## Code Structure

The codebase is organized into the following key directories, reflecting the system's architecture:

```
/home/jonat/WSL_RT_Sentiment/
├── api/                    # REST API and WebSocket interfaces
├── auth_service/           # Authentication microservice
├── data/                   # Stored data files
│   ├── cache/              # Caching files for deduplication
│   ├── logs/               # System logs
│   └── output/             # Parquet output files by ticker
├── data_acquisition/       # Data collection system 
│   ├── scrapers/           # News and social media scrapers
│   ├── subscription/       # Premium data source integrations
│   └── utils/              # Utilities for data processing
├── data_sim/               # Data simulation environment
├── dbengine/               # Database engine configuration
├── documentation/          # System documentation organized by category
│   ├── api/                # API specifications
│   ├── architecture/       # System architecture docs
│   ├── data/               # Data acquisition and storage docs
│   ├── deployment/         # Deployment guides
│   ├── guides/             # User and developer guides
│   └── testing/            # Testing guidelines
├── monitoring/             # Prometheus and Grafana configuration
├── senti/                  # Flutter dashboard application
├── sentiment_analyzer/     # Sentiment analysis engine
│   ├── data/               # Data readers and loaders
│   ├── models/             # Sentiment analysis models
│   └── utils/              # Analysis utilities
├── sentiment_service/      # Sentiment processing service
│   ├── event_consumers/    # Event queue consumers
│   ├── models/             # Model implementation
│   └── utils/              # Service utilities
└── tests/                  # Test suites
    ├── data_tests/         # Data integrity tests
    ├── integration/        # Integration tests
    ├── sentiment_tests/    # Sentiment analysis tests
    └── ...                 # Other test categories
```

## Architecture

The application is built with a microservices architecture:

1. **Data Acquisition Layer**: Collects data from various sources
2. **Event Ingestion Layer**: Processes events through queues
3. **Processing Layer**: Analyzes sentiment using ML models
4. **API Layer**: Exposes REST endpoints and WebSockets
5. **Data Persistence Layer**: Stores results in Redis and Parquet
6. **UI Layer**: Flutter dashboard for visualization
7. **Monitoring Layer**: Provides metrics and logging via Prometheus/Grafana

Detailed architecture documentation can be found in the [architecture](../architecture) directory:
- [Architecture Overview](../architecture/architecture_overview.md) - Comprehensive overview of the system
- [Updated System Architecture](../architecture/updated_system_architecture.md) - Latest architecture with Flutter integration
- [Scraper Architecture](../architecture/scraper_architecture.md) - Details on data acquisition components
- [Sentiment Analyzer Architecture](../architecture/sentiment_analyzer_architecture.md) - Details on sentiment analysis components

## Key Components and Their Relationships

### 1. Data Acquisition (`/data_acquisition/`)
   - **Purpose**: Collects raw data from various sources
   - **Key Files**:
     - `main.py` - Main entry point for data collection
     - `scrapers/base.py` - Base scraper implementation
     - `scrapers/news_scraper.py` - News-specific scraper
     - `scrapers/reddit_scraper.py` - Reddit-specific scraper
   - **Related Components**: Feeds data to Sentiment Service

### 2. Sentiment Analysis (`/sentiment_service/`, `/sentiment_analyzer/`)
   - **Purpose**: Processes incoming data with various ML models
   - **Key Files**:
     - `sentiment_service/main.py` - Service entry point
     - `sentiment_service/models/model_factory.py` - Model selection
     - `sentiment_analyzer/models/sentiment_analyzer.py` - Core analysis
     - `sentiment_analyzer/models/decay_functions.py` - Time decay
   - **Related Components**: Consumes from Data Acquisition, outputs to Storage

### 3. Data Storage (`/data/`, `/dbengine/`)
   - **Purpose**: Stores sentiment data efficiently
   - **Technologies**: Redis, Parquet files, PostgreSQL
   - **Key Files**:
     - `sentiment_analyzer/data/redis_manager.py` - Redis interface
     - `sentiment_analyzer/data/parquet_reader.py` - Parquet interface
     - `api/database.py` - Database operations
   - **Related Components**: Used by API Layer, populated by Sentiment Analysis

### 4. API Layer (`/api/`, `/auth_service/`)
   - **Purpose**: Exposes data via REST and WebSockets
   - **Key Files**:
     - `api/main.py` - API service entry point
     - `api/routes/sentiment.py` - Sentiment endpoints
     - `api/routes/websocket.py` - WebSocket implementation
     - `auth_service/main.py` - Authentication service
   - **Related Components**: Reads from Data Storage, serves Client Applications

### 5. Client Applications (`/senti/`, `/parquet_query_viewer/`)
   - **Purpose**: User interface for visualization and interaction
   - **Technologies**: Flutter, Provider state management
   - **Key Files**:
     - `senti/lib/main.dart` - Flutter app entry point
     - `senti/lib/providers/dashboard_provider.dart` - State management
     - `senti/lib/screens/home_screen.dart` - Main dashboard UI
     - `parquet_query_viewer/web/app.py` - Parquet data exploration
   - **Related Components**: Consumes data from API Layer

### 6. Monitoring (`/monitoring/`)
   - **Purpose**: System observability and metrics
   - **Technologies**: Prometheus, Grafana
   - **Key Files**:
     - `monitoring/prometheus.yml` - Prometheus configuration
     - `monitoring/grafana/` - Grafana dashboards
     - `monitoring/alertmanager/alertmanager.yml` - Alert configuration
   - **Related Components**: Monitors all other components

## Development Workflow

### Setup Environment

```bash
# Create and setup development environment
./scripts/setup_dev_environment.sh

# Start specific components
cd data_acquisition
python main.py

# In another terminal
cd api
uvicorn main:app --reload --port 8001

# In another terminal
cd sentiment_service
uvicorn main:app --reload --port 8000
```

### Docker-based Development

```bash
# Start all services
docker compose up -d

# Start only specific services
docker compose up -d api sentiment-service redis

# View logs
docker compose logs -f api
```

### Testing

```bash
# Run all tests
./run_tests.sh --all

# Run specific test categories
./run_tests.sh --mock
./run_tests.sh --integration

# Run tests in running containers
docker compose exec api pytest
```

All test outputs follow the standard naming convention:
```
[test type]_results_YYMMDD_[instance].md
```

### Code Quality

Format code and run type checking:
```bash
# Format with Black and isort
black .
isort .

# Type checking with mypy
mypy .
```

## Configuration

Configuration is managed through environment variables, which can be set in the `.env` file or directly in the `docker-compose.yml` file.

### Environment Variables

- `FINBERT_USE_ONNX`: Whether to use ONNX runtime (true/false)
- `FINBERT_USE_GPU`: Whether to use GPU acceleration (true/false)
- `REDIS_HOST`: Redis hostname
- `REDIS_PORT`: Redis port

## Common Development Tasks

### Adding a New Scraper
1. Create a new class in `data_acquisition/scrapers/` extending `base.py`
2. Implement required methods: `scrape()`, `process_data()`
3. Register the scraper in `data_acquisition/main.py`
4. Add configuration in `data_acquisition/config/scraper_config.json`
5. Create tests in `tests/data_tests/`

### Adding a New API Endpoint
1. Create or modify a route file in `api/routes/`
2. Implement the endpoint logic
3. Register the route in `api/main.py`
4. Update API documentation in `documentation/api/`
5. Add tests in `tests/api/`

### Modifying the Sentiment Analysis Logic
1. Update relevant files in `sentiment_analyzer/models/`
2. Adjust the Redis cache structure if needed in `sentiment_analyzer/data/redis_manager.py`
3. Update tests in `tests/sentiment_tests/`
4. Document changes in `documentation/architecture/`

### Updating the Flutter Dashboard
1. Modify the relevant widget or screen in `senti/lib/`
2. Update the provider if state management changes are needed
3. Test changes with `cd senti && flutter test`
4. Run the UI: `cd senti && flutter run`

## Monitoring

- Prometheus metrics: http://localhost:9090
- Grafana dashboards: http://localhost:3000

## API Documentation

When running, the API documentation is available at:
- http://localhost:8001/docs (Swagger UI)
- http://localhost:8001/redoc (ReDoc)

For more detailed information about the API, see the [API documentation](../api/API_spec.md).