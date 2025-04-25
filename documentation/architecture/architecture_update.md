# Sentiment Analyzer Architecture Update

## Architecture Overview

The Ticker Sentiment Analyzer extends the existing Real-Time Sentiment Analysis system by adding a layer of time-weighted sentiment analysis and real-time visualization. This document outlines the key architecture decisions and implementation details.

## System Components

The system is built around the following core components:

### 1. Sentiment Model

The **Sentiment Model** is the heart of the system, responsible for calculating weighted sentiment scores. It:

- Applies time decay to prioritize recent events
- Weights events based on source credibility and engagement
- Aggregates multiple events into a single sentiment score
- Scales scores to a -100 to +100 range for intuitive understanding

Implementation: `sentiment_analyzer/models/sentiment_model.py`

### 2. Time Decay Functions

The **Decay Functions** provide temporal weighting algorithms:

- **Linear**: Linear decrease to zero at half-life
- **Exponential**: Standard exponential decay (e^(-λt))
- **Half-life**: Power-based decay (0.5^(t/half-life))

Implementation: `sentiment_analyzer/models/decay_functions.py`

### 3. Impact Scoring

The **Impact Scoring** system weights sentiment events based on:

- Source credibility (news > reddit > twitter)
- Engagement metrics (comments, likes, shares)
- Content length and quality indicators
- Author reputation where available

Implementation: `sentiment_analyzer/models/impact_scoring.py`

### 4. Redis Cache

The **Redis Cache** provides:

- Fast access to recent sentiment events
- Persistence of current sentiment scores
- Time-ordered storage using sorted sets
- Automatic expiry of old events

Implementation: `sentiment_analyzer/data/redis_manager.py`

### 5. Parquet Reader

The **Parquet Reader** interfaces with historical data:

- Reads ticker-specific and multi-ticker Parquet files
- Filters by date range and ticker
- Uses PyArrow for efficient columnar access
- Supports querying the latest events across all files

Implementation: `sentiment_analyzer/data/parquet_reader.py`

### 6. S&P 500 Tracker

The **S&P 500 Tracker** identifies important tickers:

- Fetches current S&P 500 constituents
- Ranks by market cap or trading volume
- Periodically refreshes the tracked list
- Falls back to cached data when external sources are unavailable

Implementation: `sentiment_analyzer/data/sp500_tracker.py`

### 7. Streamlit Dashboard

The **Streamlit Dashboard** provides:

- Real-time sentiment visualization
- Heatmap and metric displays
- Historical trend charts
- Configurable decay parameters
- List of recent sentiment events

Implementation: `sentiment_analyzer/ui/app.py`

### 8. Main Service

The **Main Service** coordinates all components:

- Initializes system components based on configuration
- Loads historical data from Parquet to Redis
- Periodically updates sentiment scores with time decay
- Manages proper startup and shutdown sequence

Implementation: `sentiment_analyzer/main.py`

## Data Flow

The system's data flow follows this sequence:

1. **Data Acquisition**: 
   - Load historical events from Parquet files
   - Store in Redis cache with appropriate timestamps

2. **Score Calculation**:
   - Apply time decay based on event age
   - Weight by source credibility and engagement
   - Aggregate to produce a single score per ticker

3. **Visualization**:
   - Present current scores and historical trends
   - Update in real-time as new data arrives
   - Allow configuration of decay parameters

## Integration with Existing System

The Sentiment Analyzer integrates with the existing Real-Time Sentiment Analysis system at these points:

1. **Data Sources**: Reads from Parquet files produced by existing scrapers
2. **Event Schema**: Uses compatible event schema for sentiment data
3. **Visualization**: Complements existing analysis with real-time dashboard

## Key Design Decisions

1. **Separate Model from Storage**: Clear separation between the sentiment model and data storage
2. **Configurable Decay**: Multiple decay functions with adjustable parameters
3. **Redis for Real-time**: Using Redis sorted sets for efficient time-based event storage
4. **PyArrow for Parquet**: Efficiently reading historical data using column selection
5. **Background Processing**: Asynchronous updates to keep the UI responsive

## Performance Considerations

The architecture addresses performance through:

1. **Caching Strategy**: Redis caching for recent events and current scores
2. **Selective Loading**: Only load data for tracked tickers and within time window
3. **Efficient Parquet Reading**: Using PyArrow for optimized reading
4. **Configurable Update Intervals**: Tunable parameters for update frequency
5. **Time-Based Expiry**: Automatic management of cache size

## Future Enhancements

Potential future enhancements include:

1. **ML-based Impact Scoring**: Using machine learning for more sophisticated impact scoring
2. **Direct API Integration**: Direct connection to data sources rather than Parquet files
3. **Advanced Visualizations**: Price correlation and anomaly detection
4. **Alerting System**: Notification system for significant sentiment changes
5. **Distributed Processing**: Scaling to handle larger volumes of ticker data