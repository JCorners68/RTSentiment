# Real-Time Sentiment Analysis System

This repository contains a comprehensive system for real-time sentiment analysis of financial market data.

## System Components

The system is composed of several interconnected components:

1. **Data Acquisition Service**: Collects financial data from various sources
2. **Sentiment Analysis Service**: Processes text data to extract sentiment
3. **API Server**: Provides access to sentiment data and statistics
4. **Storage Engine**: Parquet files and Redis for data persistence (with Iceberg enhancement in development)
5. **Dashboard UI**: Visualization of sentiment trends

## New Features

### Data Deduplication and Cleaning

We've implemented a comprehensive data deduplication process to ensure data quality:

- **Duplicate Detection**: Identifies records with matching timestamps and titles
- **Clean Dataset**: Removes redundant records to ensure data accuracy
- **Consolidated Files**: Combined cleaned data in central parquet files
- **Analysis Reports**: Visualizations of ticker distribution and sentiment
- **Quality Improvements**: Better sentiment analysis through data cleaning

See the [Data Cleaning Report](DATA_CLEANING.md) and [Deduplication Report](deduplication_report.md) for details.

### Parquet Integration

We've added robust Apache Parquet integration for efficient storage and analysis of historical sentiment data:

- **Columnar Storage**: Efficient storage format optimized for analytical queries
- **Fast Querying**: Predicate pushdown and column pruning for performance
- **Historical Analysis**: Access to historical sentiment trends and patterns
- **Redis Caching**: In-memory caching for frequently accessed data
- **API Integration**: New endpoints for historical sentiment analysis

Learn more in our [Parquet Integration Documentation](documentation/architecture/parquet_integration.md) and [Historical Sentiment API](documentation/api/historical_sentiment_api.md) guides.

### Iceberg Lakehouse (In Development)

We're enhancing our data tier with Apache Iceberg for even better performance and data management:

- **ACID Transactions**: Ensure data consistency with full ACID compliance
- **Schema Evolution**: Flexible schema updates without data rewriting
- **Time Travel**: Access historical versions of data
- **Advanced Partitioning**: Optimized for financial time-series data
- **Dremio Integration**: SQL-based querying with powerful analytics

This enhancement is currently in development. See our [Data Tier Plan](documentation/future_plans/Definitive%20Data%20Tier%20Plan%20for%20Sentiment%20Analysis.md) for details.

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

Our system is extensively documented in the `/documentation` directory:

- [Documentation Overview](/documentation/README.md): Main documentation index
- [Architecture Documentation](/documentation/architecture/README.md): System design and component architecture
- [API Documentation](/documentation/api/README.md): API specifications and usage guides
- [Data Documentation](/documentation/data/README.md): Data structures and processing
- [Code to Documentation Mapping](/documentation/CODE_TO_DOCS_MAPPING.md): Quick reference for finding documentation

### Key Documents

- [System Architecture](/documentation/architecture/architecture_overview.md): Complete system design
- [API Specification](/documentation/api/API_spec.md): API endpoints and integration
- [Parquet Integration](/documentation/architecture/parquet_integration.md): Efficient data storage
- [Sentiment Analyzer Architecture](/documentation/architecture/sentiment_analyzer_architecture.md): Analysis pipeline
- [WebSocket Implementation](/documentation/api/WebSocket_Implementation.md): Real-time data streaming
- [Usage Guide](/documentation/guides/usage_guide.md): How to use the system

## Getting Started

### Prerequisites

- Python 3.8+
- Redis server
- Access to Parquet sentiment data files

### Data Processing Tools

Our repository includes several tools for data processing and maintenance:

- **deduplicate_parquet.py**: Removes duplicate records from parquet files
- **combine_parquet.py**: Combines multiple parquet files into a unified dataset
- **analyze_clean_sentiment.py**: Generates visualizations and statistics on cleaned data
- **recalculate_sentiment_finbert.py**: Recalculates sentiment scores using FinBERT model

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