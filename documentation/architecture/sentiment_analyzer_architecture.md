# Sentiment Analyzer Architecture

## Overview

The Ticker Sentiment Analyzer is a real-time system for tracking and visualizing sentiment for the top S&P 500 tickers. It integrates with the existing Real-Time Sentiment Analysis system by reading Parquet files and maintaining a Redis cache for fast sentiment score calculation and retrieval.

## Components

The system consists of the following core components:

### 1. Sentiment Model

The sentiment model is responsible for calculating weighted sentiment scores based on historical and incoming sentiment events. It applies:

- **Time Decay Functions**: Prioritizes recent sentiment data over older data using configurable decay functions
- **Impact Scoring**: Weights events based on source credibility, engagement metrics, and content factors
- **Aggregation**: Combines multiple events into a single sentiment score ranging from -100 to +100

### 2. Redis Cache

The Redis cache provides:

- Fast storage and retrieval of sentiment events by ticker
- Persistent storage of current sentiment scores
- Efficient data structure for time-based event sorting and filtering
- Expiry management for old events

### 3. Parquet Reader

The Parquet reader interfaces with the existing data pipeline by:

- Reading historical sentiment data from Parquet files
- Filtering by ticker and date range
- Efficiently querying large data volumes using PyArrow
- Supporting both ticker-specific and multi-ticker file formats

### 4. S&P 500 Tracker

The S&P 500 tracker:

- Identifies the top tickers in the S&P 500 by market cap or trading volume
- Periodically updates the tracked ticker list
- Implements caching to reduce API calls
- Falls back to cached data when external sources are unavailable

### 5. Streamlit UI

The user interface provides:

- Real-time dashboard of current sentiment scores
- Heatmap visualization of sentiment across tickers
- Historical time-series charts
- Recent event listings with impact scores
- Configuration options for decay parameters

## Data Flow

1. **Initial Load**:
   - The system reads historical sentiment events from Parquet files
   - Events are loaded into the Redis cache with appropriate timestamps
   - Initial sentiment scores are calculated for each ticker

2. **Continuous Updates**:
   - New sentiment events are processed by the Sentiment Model
   - Scores are recalculated with time decay applied
   - Redis cache is updated with new events and scores
   - Top S&P 500 tickers are refreshed periodically

3. **User Interaction**:
   - Streamlit UI queries Redis for current sentiment scores
   - Historical data is fetched from Parquet files for trend analysis
   - User configuration changes update the model parameters in real-time

## Integration Points

The Sentiment Analyzer integrates with the existing Real-Time Sentiment Analysis system at the following points:

1. **Data Acquisition**: Reads from the same Parquet files produced by the existing scrapers
2. **Schema Compatibility**: Uses the same event schema for sentiment data
3. **Complementary Functionality**: Provides real-time visualization while the existing system focuses on data collection

## Technical Design Decisions

1. **Redis for Caching**: Chosen for its performance with time-series data and sorted sets
2. **PyArrow for Parquet Reading**: Provides efficient filtering and column selection
3. **Streamlit for UI**: Enables rapid dashboard development with interactive components
4. **Weighted Scoring Model**: Balances recency, credibility, and engagement metrics
5. **Asynchronous Updates**: Background thread for maintenance tasks to keep UI responsive

## Scalability Considerations

The architecture supports scaling through:

1. **Redis Sharding**: Data can be partitioned across multiple Redis instances
2. **Configurable Ticker Coverage**: Can track more tickers by adjusting configuration
3. **Time-Based Expiry**: Automatically manages memory usage by expiring old events
4. **Efficient Parquet Reading**: Uses column selection and predicate pushdown