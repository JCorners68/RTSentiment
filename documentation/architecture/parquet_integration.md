# Parquet Integration for RTSentiment

This document describes the integration of Apache Parquet into the RTSentiment architecture, enabling efficient storage, retrieval, and analysis of historical sentiment data.

## Overview

The RTSentiment system now uses Apache Parquet as a storage format for historical sentiment data. This integration enhances the system with:

1. **Efficient storage** of sentiment data in a columnar format
2. **Fast analytical queries** with predicate pushdown and column pruning
3. **Schema flexibility** with support for evolving data structures
4. **Direct integration** with the sentiment analysis pipeline
5. **Redis caching** for improved query performance

## Architecture

### Data Flow

```
┌───────────┐    ┌───────────┐    ┌───────────┐    ┌────────────┐
│           │    │           │    │           │    │            │
│  Scrapers ├───►│ Sentiment ├───►│ Parquet   ├───►│ Analysis & │
│           │    │ Service   │    │ Storage   │    │ API        │
│           │    │           │    │           │    │            │
└───────────┘    └───────────┘    └───────────┘    └────────────┘
                                        │                 ▲
                                        │                 │
                                        ▼                 │
                                  ┌───────────┐          │
                                  │           │          │
                                  │   Redis   ├──────────┘
                                  │   Cache   │
                                  │           │
                                  └───────────┘
```

The data flow in the RTSentiment system with Parquet integration works as follows:

1. **Data Acquisition**: Scrapers collect sentiment data from various sources (news, social media, etc.)
2. **Sentiment Analysis**: The Sentiment Service analyzes the raw data and computes sentiment scores
3. **Persistence**: Data is stored in Parquet files, organized by ticker
4. **Retrieval & Analysis**: The API and analysis components read data from Parquet files
5. **Caching**: Redis caches frequently accessed data for improved performance

### Component Interaction

#### Scraper → Sentiment Service

Scrapers collect raw text data from various sources and send it to the Sentiment Service. The Sentiment Service analyzes the text and computes sentiment scores, which are then persisted to Parquet files.

#### Sentiment Service → Parquet Storage

The Sentiment Service writes sentiment events to Parquet files, organized by ticker. Each ticker has its own file for ticker-specific queries, and there's also a multi-ticker file for global queries.

#### Parquet Storage → Analysis & API

The Analysis components and API endpoints read data from Parquet files using the ParquetReader utility. The ParquetReader provides efficient query capabilities with filtering by ticker, date range, sentiment score, etc.

#### Redis Cache Integration

The Redis Sentiment Cache stores frequently accessed data from Parquet files, reducing disk I/O and improving query performance. The cache is automatically refreshed when new data is available.

## File Organization

Parquet files are organized in the `data/output` directory as follows:

```
data/output/
├── aapl_sentiment.parquet  # AAPL-specific sentiment data
├── amzn_sentiment.parquet  # AMZN-specific sentiment data
├── googl_sentiment.parquet # GOOGL-specific sentiment data
├── tsla_sentiment.parquet  # TSLA-specific sentiment data
├── ...                     # Other ticker-specific files
└── multi_ticker_sentiment.parquet  # Data for multiple or unknown tickers
```

Each file contains sentiment events with fields according to the schema defined in the next section.

## Schema

The Parquet schema includes the following fields:

### Core Fields

| Field         | Type       | Description                              |
|---------------|------------|------------------------------------------|
| timestamp     | string     | ISO-formatted timestamp of the event     |
| ticker        | string     | Stock symbol or ticker                   |
| sentiment     | float      | Sentiment score between -1.0 and 1.0     |
| confidence    | float      | Confidence score between 0.0 and 1.0     |
| source        | string     | Data source (e.g., "news", "reddit")     |
| model         | string     | Model used for sentiment analysis        |
| article_id    | string     | Unique identifier for the source article |
| article_title | string     | Title or headline of the source article  |

### Extended Fields

| Field             | Type       | Description                              |
|-------------------|------------|------------------------------------------|
| text_snippet      | string     | Short text excerpt from article          |
| source_url        | string     | URL of the source article                |
| source_credibility| float      | Credibility score for the source         |
| event_weight      | float      | Importance weight for the event          |
| priority          | string     | Priority level (e.g., "high", "normal")  |
| subscription_tier | string     | Subscription tier for premium content    |

The schema is flexible, allowing for different field names through column mapping in the ParquetReader.

## Components

### ParquetReader

The `ParquetReader` class (`sentiment_service/utils/parquet_reader.py`) provides utilities for reading and querying Parquet files:

```python
# Create a ParquetReader instance
reader = ParquetReader(data_dir="data/output")

# Query data for a specific ticker
aapl_data = reader.query(tickers=["AAPL"], start_date="2025-01-01", end_date="2025-04-01")

# Get average sentiment
avg_sentiment = reader.get_average_sentiment("AAPL", days=7)

# Get sentiment trend
trend = reader.get_sentiment_trend("AAPL", days=30, interval="D")
```

Key features:

- **Efficient Filtering**: Uses predicate pushdown for performance
- **Caching**: Implements LRU caching for frequent queries
- **Column Mapping**: Handles schema flexibility with column name mapping
- **Analytics**: Provides utilities for sentiment aggregation and trend analysis

### DataVerification

The `DataVerification` class (`sentiment_service/utils/data_verification.py`) validates and sanitizes sentiment data:

```python
# Create a DataVerification instance
verifier = DataVerification()

# Verify a record
is_valid = verifier.verify_required_fields(record)
valid_types, errors = verifier.validate_data_types(record)

# Sanitize a record
sanitized = verifier.sanitize_record(record)
```

Key features:

- **Field Validation**: Checks for required fields
- **Type Validation**: Validates data types
- **Sanitization**: Cleans and normalizes data
- **Error Reporting**: Provides detailed error information

### Redis Sentiment Cache

The `RedisSentimentCache` class (`sentiment_service/utils/redis_sentiment_cache.py`) provides caching for Parquet-derived sentiment data:

```python
# Create a RedisSentimentCache instance
cache = RedisSentimentCache(host="redis", port=6379)
await cache.connect()

# Cache sentiment data
await cache.cache_ticker_sentiment("AAPL", sentiment_data)

# Retrieve sentiment data
aapl_sentiment = await cache.get_ticker_sentiment("AAPL")
```

Key features:

- **Ticker-Based Caching**: Caches sentiment data by ticker
- **Historical Data Caching**: Supports caching of historical time series
- **TTL Management**: Implements time-to-live for cache entries
- **Batch Operations**: Provides efficient batch caching methods

### Model Integration

The sentiment models have been updated to work with Parquet data:

```python
# Create a ModelFactory instance
factory = ModelFactory()

# Analyze sentiment from Parquet data
result = await factory.analyze_ticker_sentiment("AAPL", parquet_reader)
```

The models support:

- **Parquet Data Sources**: Reading directly from Parquet files
- **Time Decay**: Weighting recent sentiment more heavily
- **Source Credibility**: Considering source reliability in sentiment scoring
- **Batch Processing**: Efficiently processing multiple records

## API Endpoints

The system provides API endpoints for accessing Parquet-derived sentiment data:

- **GET /ticker/{ticker}**: Get sentiment for a specific ticker
- **GET /tickers**: Get list of available tickers
- **GET /top**: Get top tickers by sentiment score
- **POST /query**: Query sentiment events with various filters
- **POST /historical**: Get historical sentiment data for a ticker over a time range
- **GET /ticker/{ticker}/timerange**: Get available time range for a ticker
- **GET /ticker/{ticker}/sources**: Get available sources for a ticker

See [Historical Sentiment API Documentation](historical_sentiment_api.md) for detailed API information.

## Usage Examples

### Querying Sentiment Data

```python
import pandas as pd
from sentiment_service.utils.parquet_reader import ParquetReader

# Create a reader
reader = ParquetReader()

# Query for AAPL sentiment in the last 30 days
end_date = pd.Timestamp.now().isoformat()
start_date = (pd.Timestamp.now() - pd.Timedelta(days=30)).isoformat()

aapl_data = reader.query(
    tickers=["AAPL"],
    start_date=start_date,
    end_date=end_date,
    sources=["news", "reddit"]
)

# Analyze the data
avg_sentiment = aapl_data["sentiment"].mean()
sentiment_by_source = aapl_data.groupby("source")["sentiment"].mean()
trend = reader.get_sentiment_trend("AAPL", days=30)
```

### Using the Redis Cache

```python
from sentiment_service.utils.redis_sentiment_cache import RedisSentimentCache
import asyncio

async def get_cached_sentiment():
    # Create cache
    cache = RedisSentimentCache(host="redis", port=6379)
    await cache.connect()
    
    # Get cached sentiment for AAPL
    aapl_sentiment = await cache.get_ticker_sentiment("AAPL")
    
    if aapl_sentiment:
        print(f"AAPL sentiment: {aapl_sentiment['score']}")
    else:
        print("No cached data for AAPL")
    
    await cache.close()

# Run the async function
asyncio.run(get_cached_sentiment())
```

### API Client Example

```python
import requests
import json
from datetime import datetime, timedelta

# API base URL
base_url = "http://localhost:8001"

# Get sentiment for AAPL
response = requests.get(f"{base_url}/sentiment/ticker/AAPL")
aapl_sentiment = response.json()
print(f"AAPL sentiment: {aapl_sentiment['score']}")

# Get historical sentiment
start_date = (datetime.now() - timedelta(days=30)).isoformat()
end_date = datetime.now().isoformat()

historical_data = requests.post(
    f"{base_url}/sentiment/historical",
    json={
        "ticker": "AAPL",
        "start_date": start_date,
        "end_date": end_date,
        "interval": "day"
    }
)

trend_data = historical_data.json()["data"]
print(f"Historical data points: {len(trend_data)}")
```

## Performance Considerations

### Batch Processing

Parquet's columnar format excels at batch processing and analytical queries. For bulk operations on historical data, Parquet offers significant performance advantages over row-based formats.

### Caching Strategy

The Redis caching layer is optimized for:

- **Frequent Queries**: Common ticker queries are cached for fast access
- **TTL-Based Expiration**: Cache entries expire based on data volatility
- **Intelligent Batch Caching**: Related data is cached together for efficiency

### Query Optimization

The ParquetReader implements several optimizations:

- **Predicate Pushdown**: Filters are pushed down to the Parquet reader for efficiency
- **Column Pruning**: Only necessary columns are read from disk
- **LRU Caching**: Frequently accessed data is kept in memory
- **Efficient Time Series Queries**: Optimized for date range filtering

## Testing

Parquet integration includes comprehensive testing:

- **Unit Tests**: Testing individual components (ParquetReader, DataVerification)
- **Integration Tests**: Testing the end-to-end pipeline
- **Performance Benchmarks**: Comparing Kafka-based and Parquet-based approaches
- **Data Quality Tests**: Validating data integrity and consistency
- **Load Tests**: Simulating high-volume query workloads

Run the tests with:

```bash
# Run Parquet integration tests
pytest tests/test_parquet_integration.py

# Run specific test class
pytest tests/test_parquet_integration.py::TestParquetReader

# Run with verbose output
pytest -v tests/test_parquet_integration.py
```

## Future Enhancements

Potential future enhancements to the Parquet integration include:

1. **Partitioning**: Implementing partitioning for larger datasets
2. **Compression**: Optimizing compression strategies for different data types
3. **Delta Lake Integration**: Adding support for Delta Lake for ACID transactions
4. **Distributed Processing**: Integrating with distributed processing frameworks
5. **Advanced Analytics**: Implementing more sophisticated analytical capabilities

## Troubleshooting

Common issues and solutions:

- **Missing Parquet Files**: Ensure the data directory structure is correct
- **Schema Mismatch**: Use the DataVerification class to sanitize data
- **Performance Issues**: Check caching configuration and query patterns
- **Redis Connection Errors**: Verify Redis server availability and connection settings

## Conclusion

The Parquet integration provides RTSentiment with efficient storage and retrieval of historical sentiment data, enabling powerful analytical capabilities and improved performance. By combining Parquet's columnar storage with Redis caching, the system achieves both speed and flexibility for sentiment analysis applications.