# Ticker Sentiment Analyzer Setup Guide

This guide provides instructions for setting up and running the Ticker Sentiment Analyzer system.

## Prerequisites

- Python 3.8+
- Redis server
- Access to Parquet files from the Real-Time Sentiment Analysis system

## Installation

1. Clone the repository (if applicable)

2. Install required dependencies:
```bash
pip install -r sentiment_analyzer/requirements.txt
```

3. Ensure Redis is running:
```bash
# Check Redis status
redis-cli ping

# If Redis is not running, start it:
sudo service redis-server start

# Or run Redis in Docker:
docker run -d -p 6379:6379 redis
```

## Configuration

Create a `config.json` file with your settings:

```json
{
  "redis_host": "localhost",
  "redis_port": 6379,
  "redis_db": 0,
  "event_expiry": 604800,
  
  "decay_type": "exponential",
  "decay_half_life": 24,
  "max_age_hours": 168,
  
  "sp500_update_hours": 24,
  "top_n_tickers": 10,
  "ranking_metric": "market_cap",
  
  "update_interval": 60,
  "historical_update_interval": 3600,
  
  "parquet_dir": "/path/to/parquet/files"
}
```

## Running the System

### 1. Start the Main Service

The main service loads historical data and updates sentiment scores:

```bash
python sentiment_analyzer/main.py --config config.json
```

### 2. Launch the Dashboard

The Streamlit dashboard provides visualization and interaction:

```bash
cd sentiment_analyzer
streamlit run ui/app.py
```

Access the dashboard at http://localhost:8501

## Running Tests

Run the test suite to verify functionality:

```bash
# Run all tests
python -m unittest discover tests/sentiment_tests

# Run specific test file
python -m unittest tests/sentiment_tests/test_sentiment_model.py
```

## Troubleshooting

### Redis Connection Issues

If you encounter Redis connection errors:

1. Verify Redis is running:
```bash
redis-cli ping  # Should return "PONG"
```

2. Check Redis configuration in your config.json
3. Make sure you have the correct permissions to access Redis

### Missing or Empty Data

If sentiment data is not appearing:

1. Verify the `parquet_dir` setting points to valid Parquet files
2. Ensure Parquet files follow naming conventions (ticker_sentiment.parquet)
3. Check logs for any error messages

### Dashboard Performance Issues

If the dashboard is slow:

1. Reduce the number of tracked tickers (top_n_tickers setting)
2. Increase update interval values
3. Consider using a more powerful Redis server

## System Architecture

The system consists of the following components:

- **Sentiment Model**: Calculates weighted sentiment scores
- **Redis Cache**: Stores events and current scores
- **Parquet Reader**: Reads historical data
- **S&P 500 Tracker**: Tracks top tickers
- **Streamlit Dashboard**: Visualizes sentiment data

For more details, see the architecture documentation.