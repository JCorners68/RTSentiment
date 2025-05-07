# Data Acquisition Service

This service is responsible for gathering data from various sources for sentiment analysis, with a focus on financial news and market events.

## Features

- **Finnhub Integration**: Collect financial news, earnings reports, and sentiment data from Finnhub API
- **Apache Iceberg Support**: Direct writing to Iceberg tables for production data storage
- **Redis Caching**: Optional caching for improved performance and reduced API quota usage
- **Rate Limiting**: Built-in rate limit handling for all external APIs
- **CLI Tool**: Command-line interface for testing and data collection
- **FastAPI Service**: REST API for service integration in the broader system

## Getting Started

### Prerequisites

- Python 3.10+
- Apache Iceberg setup (for production)
- Redis (optional, for caching)
- Finnhub API key

### Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

1. Set your API keys as environment variables or update the `config.py` file:
   ```bash
   export FINNHUB_API_KEY="your_finnhub_api_key"
   ```

2. Configure Iceberg warehouse location if needed:
   ```bash
   export ICEBERG_WAREHOUSE="/path/to/iceberg/warehouse"
   ```

### Usage

#### CLI Tool

Initialize Iceberg tables:
```bash
python src/cli.py init-iceberg
```

Set your Finnhub API key:
```bash
python src/cli.py set-api-key YOUR_API_KEY
```

Collect data for specific tickers:
```bash
python src/cli.py collect-data --tickers AAPL MSFT GOOGL
```

Collect data for S&P 500 companies:
```bash
python src/cli.py collect-data --sp500 --limit 10
```

Verify data in Iceberg tables:
```bash
python src/cli.py verify-data
```

#### API Service

Start the service:
```bash
uvicorn src.main:app --reload --port 8002
```

The API will be available at http://localhost:8002

## Testing

Run the tests:
```bash
pytest tests/
```

Run specific tests:
```bash
pytest tests/unit/test_finnhub_source.py
```

## Architecture

The service uses a modular architecture:

- `src/main.py`: FastAPI application
- `src/iceberg_setup.py`: Iceberg table setup and management
- `src/finnhub_source.py`: Finnhub API integration with Iceberg
- `src/cli.py`: Command-line interface for testing and data collection
- `config.py`: Configuration settings and API keys