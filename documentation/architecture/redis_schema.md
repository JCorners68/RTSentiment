# Redis Schema Design for Sentiment Analyzer

## Overview

The sentiment analyzer uses Redis as a real-time cache for sentiment events and scores. This document describes the Redis schema design, key patterns, and data structures used.

## Key Patterns

The system uses the following key patterns:

1. **Sentiment Scores**: `sentiment:score:{TICKER}`
   - Example: `sentiment:score:AAPL`
   - Type: String
   - Value: Float (sentiment score between -100 and 100)
   - Purpose: Stores the current sentiment score for quick access

2. **Sentiment Events**: `sentiment:events:{TICKER}`
   - Example: `sentiment:events:TSLA`
   - Type: Sorted Set
   - Score: Unix timestamp of the event
   - Value: JSON-serialized event data
   - Purpose: Stores all recent sentiment events for a ticker

## Data Structure Details

### Sentiment Score String

The sentiment score is stored as a simple string value containing a float. This enables:
- Atomic updates to the current score
- Efficient retrieval of scores for display
- Minimal memory usage

Example:
```
SET sentiment:score:AAPL 42.5
GET sentiment:score:AAPL

"42.5"
```

### Sentiment Events Sorted Set

Sentiment events are stored in a sorted set, which provides:
- Automatic ordering by timestamp (score)
- Efficient range queries by time (e.g., "all events in the last 24 hours")
- O(log N) insertion time
- O(log N + M) retrieval time for M elements

Each member of the sorted set is a JSON-serialized event with the following structure:

```json
{
  "ticker": "AAPL",
  "timestamp": "2025-04-23T14:30:00.000Z",
  "sentiment": 0.75,
  "source_type": "news",
  "source_name": "bloomberg",
  "url": "https://example.com/article",
  "title": "Apple Reports Strong Quarterly Results",
  "text": "Apple Inc. reported quarterly results that...",
  "additional_metadata": {
    "author": "John Doe",
    "keywords": ["earnings", "technology", "quarterly results"]
  }
}
```

Special considerations:
- The timestamp is stored as an ISO-8601 string in the JSON
- The actual sorted set score uses the Unix timestamp for proper ordering
- Datetime objects are converted to/from strings during serialization/deserialization

## Time-to-Live (TTL) Management

To prevent unlimited growth of the Redis database, TTL values are set on keys:

- Sentiment Events: 7 days (604800 seconds) by default
  ```
  EXPIRE sentiment:events:AAPL 604800
  ```

- Sentiment Scores: No explicit TTL, as these represent current values

The TTL values are configurable through the application settings.

## Query Patterns

### Common Query Operations

- Get Current Sentiment:
  ```
  GET sentiment:score:AAPL
  ```

- Get All Sentiment Events (newest to oldest):
  ```
  ZRANGE sentiment:events:AAPL 0 -1 REV
  ```

- Get Recent Sentiment Events (last 24 hours):
  ```
  ZRANGEBYSCORE sentiment:events:AAPL {now-86400} +inf
  ```

- Update Sentiment Score:
  ```
  SET sentiment:score:AAPL 45.2
  ```

- Add New Sentiment Event:
  ```
  ZADD sentiment:events:AAPL {timestamp} "{json_event}"
  ```

- Get All Tracked Tickers:
  ```
  KEYS sentiment:score:*
  ```

## Memory Considerations

The Redis schema is designed to be memory-efficient:

- Only essential event data is stored
- TTL prevents unlimited historical data accumulation
- JSON serialization provides a good balance of readability and size
- Sorted sets offer efficient storage for time-series data

For 10 tickers with an average of 1000 events each, the expected memory usage is approximately:
- Events: ~10 MB (assuming 1KB per event)
- Scores: ~1 KB
- Total: ~10-15 MB including Redis overhead

## Integration with Parquet Files

The Redis cache complements the Parquet storage by:
- Providing faster access to recent data
- Enabling real-time updates and score calculation
- Storing only the most recent events (7 days by default)

For historical data beyond the Redis TTL, the system falls back to reading from Parquet files.