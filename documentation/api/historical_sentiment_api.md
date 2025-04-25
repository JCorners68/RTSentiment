# Historical Sentiment API Documentation

This document describes the API endpoints for accessing historical sentiment data from Parquet files through Redis caching.

## Overview

The historical sentiment API provides access to pre-computed sentiment data stored in Parquet files. To improve performance and reduce system load, the API implements Redis caching for frequently accessed data.

## Redis Sentiment Cache

The Redis caching implementation provides the following features:

1. Efficient storage and retrieval of Parquet-derived sentiment data
2. TTL-based cache expiration to ensure data freshness
3. Batch operations for improved performance
4. Fallback mechanisms when Redis is unavailable
5. Metadata caching for ticker information

## API Endpoints

### Query Sentiment Events

```
POST /sentiment/query
```

Query sentiment events with various filters, with optional Redis caching.

**Request Body:**
```json
{
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-04-01T00:00:00Z",
  "sources": ["reddit", "news"],
  "priority": ["high"],
  "models": ["finbert"],
  "min_score": -0.5,
  "max_score": 0.5,
  "tickers": ["AAPL", "TSLA"],
  "limit": 100,
  "offset": 0,
  "use_cache": true
}
```

**Response:**
```json
[
  {
    "id": 1,
    "event_id": "12345-abcde",
    "timestamp": "2025-03-15T14:30:00Z",
    "source": "reddit",
    "priority": "high",
    "model": "finbert",
    "sentiment_score": 0.75,
    "sentiment_label": "positive"
  },
  ...
]
```

### Get Ticker Sentiment

```
GET /sentiment/ticker/{ticker}?use_cache=true
```

Get sentiment for a specific ticker with optional Redis caching.

**Parameters:**
- `ticker`: Ticker symbol (e.g., "AAPL")
- `use_cache`: Whether to use Redis cache (default: true)

**Response:**
```json
{
  "ticker": "AAPL",
  "sentiment": "positive",
  "score": 0.75,
  "weight": 1.2,
  "count": 250,
  "model": "aggregate"
}
```

### Get Available Tickers

```
GET /sentiment/tickers?use_cache=true
```

Get list of available tickers with optional Redis caching.

**Parameters:**
- `use_cache`: Whether to use Redis cache (default: true)

**Response:**
```json
["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
```

### Get Top Sentiment Tickers

```
GET /sentiment/top?limit=10&min_score=0.2&max_score=1.0&sort_by=score&order=desc&use_cache=true
```

Get top tickers by sentiment score with optional Redis caching.

**Parameters:**
- `limit`: Number of results to return (default: 10, max: 50)
- `min_score`: Minimum sentiment score (-1.0 to 1.0)
- `max_score`: Maximum sentiment score (-1.0 to 1.0)
- `sort_by`: Field to sort by ("score" or "count")
- `order`: Sort order ("asc" or "desc")
- `use_cache`: Whether to use Redis cache (default: true)

**Response:**
```json
[
  {
    "ticker": "AAPL",
    "sentiment": "positive",
    "score": 0.85,
    "weight": 1.5,
    "count": 350,
    "model": "aggregate"
  },
  ...
]
```

### Analyze Text Sentiment

```
POST /sentiment/analyze?use_cache=true
```

Analyze sentiment of custom text with optional Redis caching.

**Parameters:**
- `text`: Text to analyze
- `use_cache`: Whether to use Redis cache (default: true)

**Response:**
```json
{
  "sentiment": "positive",
  "score": 0.78,
  "tickers": ["AAPL", "MSFT"],
  "model": "finbert"
}
```

### Get Metadata

```
GET /sentiment/metadata?use_cache=true
```

Get metadata for UI filtering with optional Redis caching.

**Parameters:**
- `use_cache`: Whether to use Redis cache (default: true)

**Response:**
```json
{
  "sources": ["reddit", "news", "twitter"],
  "models": ["finbert", "fingpt", "aggregate"],
  "priorities": ["high", "standard", "low"]
}
```

### Get Historical Sentiment

```
POST /sentiment/historical
```

Get historical sentiment data for a ticker over a time range.

**Request Body:**
```json
{
  "ticker": "AAPL",
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-04-01T00:00:00Z",
  "source": "reddit",
  "interval": "day",
  "use_cache": true
}
```

**Response:**
```json
{
  "ticker": "AAPL",
  "data": [
    {
      "ticker": "AAPL",
      "timestamp": "2025-01-01T00:00:00Z",
      "sentiment": "positive",
      "score": 0.65,
      "source": "reddit",
      "count": 25,
      "model": "parquet"
    },
    ...
  ],
  "start_date": "2025-01-01T00:00:00Z",
  "end_date": "2025-04-01T00:00:00Z",
  "interval": "day"
}
```

### Get Ticker Time Range

```
GET /sentiment/ticker/{ticker}/timerange
```

Get the available time range for historical data for a ticker.

**Parameters:**
- `ticker`: Ticker symbol (e.g., "AAPL")

**Response:**
```json
{
  "ticker": "AAPL",
  "min_date": "2025-01-01T00:00:00Z",
  "max_date": "2025-04-23T00:00:00Z"
}
```

### Get Ticker Sources

```
GET /sentiment/ticker/{ticker}/sources
```

Get the available sources for historical data for a ticker.

**Parameters:**
- `ticker`: Ticker symbol (e.g., "AAPL")

**Response:**
```json
["reddit", "news", "twitter"]
```

## Error Handling

The API uses status codes to indicate success or failure:

- **200 OK**: Request succeeded
- **400 Bad Request**: Invalid parameters
- **404 Not Found**: Resource not found
- **500 Internal Server Error**: Server error

## Caching Behavior

1. **Cache Keys**: Generated based on query parameters to ensure uniqueness
2. **TTL (Time to Live)**:
   - General queries: 1 hour
   - Ticker sentiment: 1 hour
   - Historical data: 24 hours
   - Metadata: 6 hours
3. **Cache Invalidation**: Automatic expiration based on TTL
4. **Cache Bypass**: Use `use_cache=false` to bypass caching

## Fallback Mechanisms

If Redis is unavailable or a cache miss occurs, the API falls back to:

1. Direct Parquet FDW queries
2. Traditional database queries

## Implementation Details

The Redis sentiment cache is implemented in `sentiment_service/utils/redis_sentiment_cache.py` and provides:

1. **RedisSentimentCache class**: Manages Redis connection and operations
2. **Ticker-based caching**: Stores sentiment data by ticker symbol
3. **Historical data caching**: Stores time series data efficiently
4. **Batch operations**: For improved performance when handling multiple items
5. **Connection management**: Lazy connection establishment and graceful error handling