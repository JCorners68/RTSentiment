# Ticker Sentiment Analyzer - Architecture Overview

## System Purpose

The Ticker Sentiment Analyzer extends the existing Real-Time Sentiment Analysis system by providing:

- Continuous tracking of sentiment for top S&P 500 tickers
- Time-weighted sentiment calculation with configurable decay functions
- Impact scoring based on source credibility and engagement metrics
- Real-time visualization dashboard for sentiment monitoring
- Historical sentiment trend analysis

## High-Level Architecture

The system is composed of five main components:

```
┌───────────────────┐       ┌───────────────────┐       ┌───────────────────┐
│                   │       │                   │       │                   │
│  Parquet Reader   │◄─────►│  Sentiment Model  │◄─────►│    Redis Cache    │
│                   │       │                   │       │                   │
└───────────────────┘       └────────┬──────────┘       └───────────────────┘
                                     │
                                     ▼
┌───────────────────┐       ┌───────────────────┐
│                   │       │                   │
│   S&P500 Tracker  │◄─────►│    Streamlit UI   │
│                   │       │                   │
└───────────────────┘       └───────────────────┘
```

## Data Flow

1. **Data Acquisition**:
   - Parquet Reader loads sentiment events from existing Parquet files
   - Events are stored in Redis cache with appropriate time-based sorted sets

2. **Sentiment Calculation**:
   - Sentiment Model applies time decay to historical events
   - Impact scoring weights events by credibility and engagement
   - Aggregated scores are calculated and stored in Redis

3. **Ticker Selection**:
   - S&P500 Tracker identifies top tickers by market cap or volume
   - Periodically refreshes the tracked ticker list

4. **Visualization**:
   - Streamlit UI presents real-time sentiment scores and trends
   - Allows customization of decay parameters and timeframes

5. **Continuous Updates**:
   - Main service periodically refreshes data from Parquet files
   - Updates sentiment scores with appropriate time decay

## Integration Points

The system integrates with the existing RTSentiment architecture at these points:

1. **Data Sources**:
   - Reads from the same Parquet files produced by existing scrapers
   - Uses the same schema for sentiment events

2. **Storage**:
   - Adds Redis as a real-time cache layer
   - Maintains compatibility with existing Parquet storage

3. **Processing**:
   - Complements existing sentiment analysis with time-weighted scoring
   - Provides additional impact metrics based on research

## Implementation Details

### Python Libraries:
- pandas/pyarrow for Parquet processing
- redis-py for Redis integration
- streamlit for dashboard UI
- plotly for interactive visualizations

### Key Algorithms:
- Time decay functions (exponential, linear, half-life)
- Impact scoring based on source credibility matrix
- Weighted sentiment aggregation

### Data Structures:
- Redis sorted sets for time-ordered events
- Redis strings for current sentiment scores
- DataFrame-based processing for historical trends

## Configuration and Extensibility

The system is designed to be configurable through:

### JSON Configuration:
- Redis connection parameters
- Decay function selection and parameters
- Ticker tracking parameters
- Update intervals

### Extensibility Points:
- Additional decay functions can be added to decay_functions.py
- Source credibility matrix can be extended in impact_scoring.py
- UI components can be added to the Streamlit dashboard

## Performance Considerations

### Redis Caching:
- Provides sub-millisecond access to current sentiment scores
- Efficient time-based filtering with sorted sets

### Selective Parquet Reading:
- Uses PyArrow for efficient column and predicate filtering
- Loads only necessary data for the requested time periods

### Asynchronous Updates:
- Background thread handles periodic updates
- Prevents UI blocking during data refreshes

### Time-Based Expiry:
- Prevents unbounded growth of the Redis database
- Configurable retention period (default 7 days)

## Future Enhancements

Potential enhancements for future versions:

### Machine Learning Integration:
- ML-based impact scoring
- Automated credibility assessment
- Predictive sentiment modeling

### Additional Data Sources:
- Direct integration with social media APIs
- Real-time news feed processing

### Advanced Visualizations:
- Sentiment correlation with price movements
- Network graphs of influencer impact
- Anomaly detection and alerting