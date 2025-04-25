# Parquet Schema Definition for RTSentiment

This document defines the schema specifications for Parquet files used in the RTSentiment architecture. These schema definitions are designed to support efficient storage and retrieval of sentiment data across multiple tiers of analysis.

## 1. Ticker-Specific Sentiment Schema (`{ticker}_sentiment.parquet`)

Files following this schema are organized by individual ticker symbols (e.g., `aapl_sentiment.parquet`, `tsla_sentiment.parquet`) and contain sentiment data specific to a single ticker.

### Core Fields (Required)

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `timestamp` | string | ISO 8601 format timestamp | "2025-04-25T06:27:53" |
| `ticker` | string | Stock symbol/ticker | "AAPL" |
| `sentiment` | float64 | Sentiment score (-1.0 to 1.0) | 0.75 |
| `confidence` | float64 | Confidence level (0.0 to 1.0) | 0.95 |
| `source` | string | Data source identifier | "RedditScraper" |
| `model` | string | Model used for analysis | "finbert" |
| `article_id` | string | Unique identifier | "82ff4499-da59-47b3-811c-2fe57f8f51f4" |
| `article_title` | string | Title or headline | "Apple's new product exceeds expectations" |

### Extended Fields (Optional)

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `text_snippet` | string | Relevant text extract | "Apple's latest product launch has exceeded..." |
| `source_url` | string | Original content URL | "https://example.com/news/12345" |
| `source_credibility` | float32 | Source reliability score (0.0-1.0) | 0.85 |
| `event_weight` | float32 | Importance weight factor | 1.5 |
| `engagement_metrics` | map[string, int32] | Engagement data | {"comments": 324, "likes": 2100} |
| `priority` | string | Processing priority | "high" |
| `subscription_tier` | string | User tier for this analysis | "premium" |
| `sector` | string | Industry sector | "Technology" |
| `topic_tags` | list[string] | Related topics/categories | ["earnings", "product_launch"] |
| `sentiment_breakdown` | map[string, float32] | Detailed sentiment categories | {"positive": 0.8, "negative": 0.1, "neutral": 0.1} |
| `language` | string | Content language | "en" |
| `geo_relevance` | string | Geographic scope | "global" |
| `processed_date` | string | Processing timestamp | "2025-04-25T06:28:01" |

## 2. Multi-Ticker Sentiment Schema (`multi_ticker_sentiment.parquet`)

This schema is used for the special `multi_ticker_sentiment.parquet` file which contains sentiment data relevant to multiple ticker symbols.

### Core Fields (Required)

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `timestamp` | string | ISO 8601 format timestamp | "2025-04-25T06:27:53" |
| `tickers` | list[string] | List of related tickers | ["AAPL", "MSFT", "GOOGL"] |
| `primary_ticker` | string | Primary relevant ticker | "AAPL" |
| `sentiment` | float64 | Overall sentiment score (-1.0 to 1.0) | 0.65 |
| `confidence` | float64 | Confidence level (0.0 to 1.0) | 0.92 |
| `source` | string | Data source identifier | "NewsScraper" |
| `model` | string | Model used for analysis | "finbert" |
| `article_id` | string | Unique identifier | "82ff4499-da59-47b3-811c-2fe57f8f51f4" |
| `article_title` | string | Title or headline | "Tech sector rallies on strong earnings" |

### Extended Fields (Optional)

| Field Name | Data Type | Description | Example |
|------------|-----------|-------------|---------|
| `text_snippet` | string | Relevant text extract | "The tech sector rallied today as..." |
| `source_url` | string | Original content URL | "https://example.com/news/67890" |
| `source_credibility` | float32 | Source reliability score (0.0-1.0) | 0.9 |
| `event_weight` | float32 | Importance weight factor | 2.0 |
| `engagement_metrics` | map[string, int32] | Engagement data | {"comments": 512, "shares": 1024} |
| `priority` | string | Processing priority | "high" |
| `subscription_tier` | string | User tier for this analysis | "professional" |
| `sector` | string | Industry sector | "Technology" |
| `topic_tags` | list[string] | Related topics/categories | ["market_news", "earnings_season"] |
| `ticker_sentiments` | map[string, float32] | Per-ticker sentiment | {"AAPL": 0.7, "MSFT": 0.6, "GOOGL": 0.65} |
| `ticker_mentions` | map[string, int32] | Mention count by ticker | {"AAPL": 5, "MSFT": 3, "GOOGL": 2} |
| `language` | string | Content language | "en" |
| `geo_relevance` | string | Geographic scope | "us_market" |
| `processed_date` | string | Processing timestamp | "2025-04-25T06:28:12" |
| `relation_type` | string | How tickers are related | "sector_news" |

## 3. Schema Design Considerations

### Model Support

Both schemas are designed to support our three-model approach:

1. **FinBERT (Core Model)**
   - Standard sentiment analysis for all tiers
   - `model` field will contain "finbert"
   - Appropriate for high volume, general sentiment analysis

2. **FinGPT (Premium Tier)**
   - Enhanced sentiment analysis with more nuance
   - `model` field will contain "fingpt"
   - `subscription_tier` field will be "premium"
   - `sentiment_breakdown` will contain more detailed categories

3. **Llama 4 Scout (Professional Tier)**
   - Most sophisticated sentiment analysis
   - `model` field will contain "llama4_scout"
   - `subscription_tier` field will be "professional"
   - Additional fields like `topic_tags` and detailed breakdowns will be populated

### Source Credibility and Event Weighting

To handle source credibility and event weights as described in the architecture:

1. **Source Credibility**
   - `source_credibility` field measures reliability (0.0-1.0)
   - Higher values indicate more trusted sources
   - This allows filtering or weighting based on source quality

2. **Event Weights**
   - `event_weight` indicates importance (default: 1.0)
   - Higher values (>1.0) for more significant events
   - Lower values (<1.0) for less impactful mentions
   - Used for weighted averaging in sentiment analysis

3. **Engagement Metrics**
   - `engagement_metrics` captures audience response
   - Used to compute event weights dynamically
   - Includes metrics like comments, shares, likes, etc.

### Partitioning Recommendations

For optimal performance with large datasets:

1. **Time-based Partitioning**
   - Partition by year/month for efficient time-range queries
   - Example: `/data/output/2025/04/aapl_sentiment.parquet`

2. **Tier-based Partitioning (Optional)**
   - For organizations with clear subscription tiers
   - Example: `/data/output/professional/multi_ticker_sentiment.parquet`

## 4. PyArrow Schema Definition

Below is the PyArrow schema definition for implementing these schemas:

```python
# For ticker_sentiment.parquet
import pyarrow as pa

ticker_schema = pa.schema([
    # Core Fields
    ('timestamp', pa.string()),
    ('ticker', pa.string()),
    ('sentiment', pa.float64()),
    ('confidence', pa.float64()),
    ('source', pa.string()),
    ('model', pa.string()),
    ('article_id', pa.string()),
    ('article_title', pa.string()),
    
    # Extended Fields (Optional)
    ('text_snippet', pa.string()),
    ('source_url', pa.string()),
    ('source_credibility', pa.float32()),
    ('event_weight', pa.float32()),
    ('engagement_metrics', pa.map_(pa.string(), pa.int32())),
    ('priority', pa.string()),
    ('subscription_tier', pa.string()),
    ('sector', pa.string()),
    ('topic_tags', pa.list_(pa.string())),
    ('sentiment_breakdown', pa.map_(pa.string(), pa.float32())),
    ('language', pa.string()),
    ('geo_relevance', pa.string()),
    ('processed_date', pa.string())
])

# For multi_ticker_sentiment.parquet
multi_ticker_schema = pa.schema([
    # Core Fields
    ('timestamp', pa.string()),
    ('tickers', pa.list_(pa.string())),
    ('primary_ticker', pa.string()),
    ('sentiment', pa.float64()),
    ('confidence', pa.float64()),
    ('source', pa.string()),
    ('model', pa.string()),
    ('article_id', pa.string()),
    ('article_title', pa.string()),
    
    # Extended Fields (Optional)
    ('text_snippet', pa.string()),
    ('source_url', pa.string()),
    ('source_credibility', pa.float32()),
    ('event_weight', pa.float32()),
    ('engagement_metrics', pa.map_(pa.string(), pa.int32())),
    ('priority', pa.string()),
    ('subscription_tier', pa.string()),
    ('sector', pa.string()),
    ('topic_tags', pa.list_(pa.string())),
    ('ticker_sentiments', pa.map_(pa.string(), pa.float32())),
    ('ticker_mentions', pa.map_(pa.string(), pa.int32())),
    ('language', pa.string()),
    ('geo_relevance', pa.string()),
    ('processed_date', pa.string()),
    ('relation_type', pa.string())
])
```

## 5. Schema Migration Strategy

To migrate from the current schema to this enhanced schema:

1. **Backward Compatibility**
   - All core fields from existing schema retained
   - New fields are optional to allow gradual adoption

2. **Data Migration Steps**
   - Add new optional fields to existing files when rewriting
   - Calculate source credibility based on historical reliability
   - Derive event weights from engagement metrics
   - Populate subscription_tier based on current user status

3. **Minimal Viable Schema**
   - For initial implementation, core fields are sufficient
   - Extended fields can be added progressively

This schema design provides flexibility for future enhancements while maintaining compatibility with the existing RTSentiment architecture.