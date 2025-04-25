# Real-Time Sentiment Analysis System

This repository contains a comprehensive system for real-time sentiment analysis of financial market data.

## System Components

The system is composed of several interconnected components:

1. **Data Acquisition Service**: Collects financial data from various sources
2. **Sentiment Analysis Service**: Processes text data to extract sentiment
3. **API Server**: Provides access to sentiment data and statistics
4. **Storage Engine**: Parquet files and Redis for data persistence
5. **Dashboard UI**: Visualization of sentiment trends

## New Features

### Parquet Integration

We've added robust Apache Parquet integration for efficient storage and analysis of historical sentiment data:

- **Columnar Storage**: Efficient storage format optimized for analytical queries
- **Fast Querying**: Predicate pushdown and column pruning for performance
- **Historical Analysis**: Access to historical sentiment trends and patterns
- **Redis Caching**: In-memory caching for frequently accessed data
- **API Integration**: New endpoints for historical sentiment analysis

Learn more in our [Parquet Integration Documentation](Documentation/parquet_integration.md) and [Historical Sentiment API](Documentation/historical_sentiment_api.md) guides.

## New Component: Ticker Sentiment Analyzer

A new component has been added:

### Ticker Sentiment Analyzer

The Ticker Sentiment Analyzer provides time-weighted sentiment analysis for top S&P 500 tickers with the following features:

- **Time-Weighted Scoring**: Prioritizes recent sentiment data
- **Source Credibility**: Weights data based on source reliability
- **Real-Time Dashboard**: Interactive visualization of sentiment trends
- **Historical Analysis**: Tracks sentiment changes over time

#### Key Components:

- **Sentiment Model**: Calculates weighted sentiment scores
- **Redis Cache**: Real-time caching of events and scores
- **Parquet Reader**: Access to historical sentiment data
- **S&P 500 Tracker**: Top ticker identification
- **Streamlit Dashboard**: User interface for visualization

## Documentation

- [System Architecture](/documentation/architecture/sentiment_analyzer_architecture.md)
- [Redis Schema Design](/documentation/architecture/redis_schema.md)
- [Usage Guide](/documentation/usage_guide.md)
- [Architecture Overview](/documentation/architecture_overview.md)
- [Parquet Integration](/Documentation/parquet_integration.md)
- [Historical Sentiment API](/Documentation/historical_sentiment_api.md)

## Getting Started

### Prerequisites

- Python 3.8+
- Redis server
- Access to Parquet sentiment data files

### Installation

1. Install dependencies:
   ```bash
   pip install -r sentiment_analyzer/requirements.txt
   ```

2. Ensure Redis is running:
   ```bash
   redis-cli ping  # Should return "PONG"
   ```

3. Configure the system:
   Create a `config.json` file with connection settings and parameters.

### Running the System

1. Start the main service:
   ```bash
   python sentiment_analyzer/main.py --config config.json
   ```

2. Launch the dashboard:
   ```bash
   cd sentiment_analyzer
   streamlit run ui/app.py
   ```

## Testing

Run the tests to verify functionality:

```bash
# Run all tests
python -m unittest discover tests/sentiment_tests

# Run Parquet integration tests
pytest tests/test_parquet_integration.py
```

## License

[Insert license information here]

## Contributors

[Insert contributor information here]