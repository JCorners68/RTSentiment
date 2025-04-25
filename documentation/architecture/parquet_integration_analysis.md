# Parquet Integration Analysis for RTSentiment

## Current Data Flow Architecture

The RTSentiment platform implements a sophisticated data pipeline for processing financial sentiment data:

1. **Data Acquisition & Scraping**
   - Various scrapers collect data from news sources, Reddit, and other platforms
   - The `BaseScraper` class in `data_acquisition/scrapers/base.py` provides the foundation
   - Each scraper enriches data with metadata and assigns priority
   - Data is both saved to Parquet files and sent to Kafka for real-time processing

2. **Event Production & Streaming**
   - `EventProducer` in `data_acquisition/utils/event_producer.py` routes data to Kafka topics
   - Events are segregated by priority ("sentiment-events-high" and "sentiment-events-standard" topics)
   - Each event has a unique ID and timestamp

3. **Sentiment Analysis Processing**
   - Event consumers in `sentiment_service/event_consumers/` process incoming events from Kafka
   - Circuit breaker pattern implemented for system resilience
   - Sentiment analysis models are selected based on content type and priority

4. **Sentiment Analysis Models**
   - FinBERT (`sentiment_service/models/finbert.py`) is the primary implementation
   - Alternative models include FinGPT and Llama4 Scout for premium content
   - Models classify text as positive, negative, or neutral with confidence scores

5. **Results Storage & Caching**
   - Results are stored in Redis cache and ultimately in Parquet files
   - Real-time updates published via WebSockets to clients

## Current Data Persistence Methods

The RTSentiment platform currently employs multiple data persistence methods:

### 1. Parquet Files

Parquet serves as the primary long-term storage mechanism for sentiment data:

- **Organization**: Files are organized by ticker symbol in `/home/jonat/WSL_RT_Sentiment/data/output/`
  - Individual ticker files (e.g., `aapl_sentiment.parquet`)
  - Multi-ticker data (`multi_ticker_sentiment.parquet`)

- **Schema**:
  ```
  timestamp (string): ISO format timestamp
  ticker (string): Stock symbol/ticker
  sentiment (float64): Sentiment score
  confidence (float64): Confidence level of analysis
  source (string): Data source identifier
  model (string): Model used for sentiment analysis
  article_id (string): Unique identifier
  article_title (string): Title or headline
  ```

- **Write Operations**:
  - `BaseScraper._save_to_parquet()`: Groups data by ticker
  - `BaseScraper._append_to_parquet_file()`: Writes to specific files using PyArrow

- **Read Operations**:
  - `ParquetReader.read_ticker_data()`: Retrieves data for specific tickers
  - `ParquetReader.get_all_tickers()`: Lists available tickers
  - `ParquetReader.get_latest_events()`: Gets most recent sentiment events

### 2. Redis Cache

Redis provides a high-performance cache layer:

- **Key Patterns**:
  - `sentiment:score:{TICKER}`: Current sentiment score
  - `sentiment:events:{TICKER}`: Recent events (sorted set)
  - `tickers`: Set of all ticker symbols
  - `event:{EVENT_ID}`: Individual event data
  - `events:timeline`: Time-ordered events

- **TTL Policies**:
  - Event data: 7 days default
  - Sentiment scores: No explicit TTL (current values)

- **Redis Operations**:
  - Updates: Weighted averaging for new sentiment scores
  - Queries: Fast retrieval of recent and current sentiment

### 3. PostgreSQL Database (Secondary)

While not the primary storage, PostgreSQL is used for:
  - Fallback queries when Parquet is unavailable
  - System metadata and configuration
  - User authentication and subscription data

## FinBERT Integration Points

FinBERT is integrated at the following points:

1. **Model Loading**:
   - `FinBertModel` in `sentiment_service/models/finbert.py`
   - Supports PyTorch and ONNX runtime
   - Loaded at service startup

2. **Sentiment Analysis Processing**:
   - Called from event consumers after receiving Kafka messages
   - Processes text to generate sentiment scores (-1 to +1)

3. **Model Selection Logic**:
   - `ModelFactory` in `sentiment_service/models/model_factory.py`
   - Selects appropriate model based on content type and priority
   - Falls back to simpler models if errors occur

4. **Results Processing**:
   - Sentiment scores are normalized and scaled
   - Confidence values are derived from model outputs
   - Results are cached in Redis and stored in Parquet

## Redis Caching Patterns

Redis implements sophisticated caching patterns:

1. **Time-Series Data Storage**:
   - Recent events stored in sorted sets by timestamp
   - Enables efficient time-range queries

2. **Weighted Averaging**:
   - New sentiment scores combined with existing ones
   - Higher weights for more reliable or important sources
   - Atomic operations for concurrent updates

3. **Memory Efficiency**:
   - TTL prevents unlimited growth (7-day default)
   - Only essential data kept in memory

4. **Fault Tolerance**:
   - Graceful degradation when Redis unavailable
   - Connection retry mechanisms

5. **Cross-Service Communication**:
   - Redis facilitates data sharing between services
   - Avoids unnecessary database queries

## API and Data Access Patterns

The API provides multiple ways to access sentiment data:

1. **REST Endpoints**:
   - `/event`: Creates sentiment events
   - `/query`: Queries sentiment with filters
   - `/ticker/{ticker}`: Gets sentiment for specific ticker
   - `/tickers`: Lists all available tickers
   - `/top`: Gets top tickers by sentiment
   - `/analyze`: Analyzes custom text

2. **WebSocket Real-time Updates**:
   - Provides real-time sentiment updates
   - Subscription model for specific tickers
   - Authentication and connection management

3. **Query Strategies**:
   - First attempts Parquet via Foreign Data Wrapper
   - Falls back to PostgreSQL if needed
   - Redis cache for frequent or recent queries

## Recommended Integration Points for Parquet-based Sentiment Analyzer

Based on the analysis of the RTSentiment architecture, here are the recommended integration points for a Parquet-based sentiment analyzer:

### 1. Data Access Layer

**Location**: Create a new module in `sentiment_analyzer/data/parquet_analyzer.py`

**Features**:
- Implement efficient Parquet reading optimized for analysis
- Add caching mechanisms for frequently analyzed data
- Support for different aggregation levels (ticker, source, time period)

**Integration**: This component would extend the existing `ParquetReader` with analysis-specific functionality.

### 2. Analysis Engine

**Location**: Create a new module in `sentiment_analyzer/models/time_series_analyzer.py`

**Features**:
- Advanced trend analysis for sentiment data
- Anomaly detection for sudden sentiment shifts
- Correlation analysis between tickers
- Volume-weighted sentiment scoring

**Integration**: This would integrate with the existing model architecture but focus on historical and aggregate analysis rather than real-time classification.

### 3. Redis Cache Integration

**Location**: Enhance `sentiment_analyzer/data/redis_manager.py`

**Features**:
- Cache analysis results with appropriate TTL
- Store computed metrics for quick retrieval
- Implement pub/sub for analysis updates

**Integration**: This would extend the existing Redis caching to include analysis results, not just raw sentiment scores.

### 4. API Extensions

**Location**: Create a new route file in `api/routes/analysis.py`

**Features**:
- Endpoints for trend analysis
- Comparative ticker analysis
- Sector-wide sentiment analysis
- Advanced filtering and aggregation

**Integration**: These endpoints would leverage the Parquet-based analyzer to provide insights beyond raw sentiment scores.

### 5. Scheduled Analysis Jobs

**Location**: Create a new module in `sentiment_analyzer/tasks/scheduled_analysis.py`

**Features**:
- Periodic computation of complex metrics
- Daily/weekly summary generation
- Trending topic identification
- Historical performance evaluation

**Integration**: These jobs would run on a schedule to pre-compute expensive analyses for faster API responses.

### 6. Data Optimization

**Location**: Enhance `parquet_utils.py` and `cron_jobs/optimize_parquet.sh`

**Features**:
- Column pruning for analysis-specific queries
- Predicate pushdown optimization
- Partitioning strategy for time-based queries
- Metadata and statistics generation

**Integration**: These optimizations would make the Parquet files more efficient for the specific analysis patterns required.

## Conclusion

The RTSentiment architecture provides a solid foundation for integrating a Parquet-based sentiment analyzer. The existing data flow from scrapers to sentiment analysis and storage is well-designed, with clear separation of concerns.

By focusing on the recommended integration points, the new Parquet-based analyzer can leverage the strengths of the current architecture while adding powerful analytical capabilities. The combination of Redis for caching, Parquet for efficient storage, and a dedicated analysis engine will enable sophisticated financial sentiment analysis with both real-time and historical perspectives.