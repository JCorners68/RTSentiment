# Ticker Sentiment Analyzer Usage Guide

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r sentiment_analyzer/requirements.txt
   ```

3. Ensure Redis is running:
   ```bash
   # Install Redis if needed
   sudo apt-get install redis-server

   # Start Redis server
   sudo service redis-server start

   # Or run with Docker
   docker run -d -p 6379:6379 redis
   ```

## Configuration

Create a `config.json` file with your desired settings:
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
  
  "parquet_dir": "/home/jonat/WSL_RT_Sentiment/data/output"
}
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| redis_host | Redis server hostname | localhost |
| redis_port | Redis server port | 6379 |
| redis_db | Redis database number | 0 |
| event_expiry | Seconds before events expire | 604800 (7 days) |
| decay_type | Type of decay function ("linear", "exponential", "half_life") | exponential |
| decay_half_life | Hours for sentiment to decay by half | 24 |
| max_age_hours | Maximum age of events to consider | 168 (7 days) |
| sp500_update_hours | Hours between S&P 500 ticker updates | 24 |
| top_n_tickers | Number of top tickers to track | 10 |
| ranking_metric | Metric to rank tickers by ("market_cap", "volume") | market_cap |
| update_interval | Seconds between service updates | 60 |
| historical_update_interval | Seconds between historical data refreshes | 3600 (1 hour) |
| parquet_dir | Directory containing Parquet files | /home/jonat/WSL_RT_Sentiment/data/output |

## Running the Service

Start the sentiment analyzer service:
```bash
python sentiment_analyzer/main.py --config config.json
```

The service will:
- Initialize all components
- Load historical data from Parquet files
- Calculate initial sentiment scores
- Start a background thread for updates
- Run until interrupted with Ctrl+C

## Running the Dashboard

Launch the Streamlit dashboard:
```bash
cd sentiment_analyzer
streamlit run ui/app.py
```

Access the dashboard at http://localhost:8501

### Dashboard Features

- **Current Sentiment**: Real-time sentiment scores for top tickers
- **Sentiment Heatmap**: Visual representation of sentiment by ticker
- **Historical Trends**: Line chart of sentiment over time
- **Recent Events**: Table of recent sentiment events
- **Configuration**: Adjust decay parameters in the sidebar

## Running Tests

Run all tests:
```bash
python -m unittest discover tests/sentiment_tests
```

Run specific test file:
```bash
python -m unittest tests/sentiment_tests/test_sentiment_model.py
```

## Integration with Existing System

The sentiment analyzer is designed to work with the existing Real-Time Sentiment Analysis system:

- It reads from the same Parquet files produced by the scrapers
- It provides a real-time visualization layer on top of the collected data
- It uses Redis for caching to avoid constant re-reading of Parquet files

## Troubleshooting

### Redis Connection Issues

If you encounter Redis connection errors:

- Verify Redis is running:
  ```bash
  redis-cli ping
  ```
  Should respond with "PONG"
- Check connection settings in config.json
- Ensure Redis has enough memory:
  ```bash
  redis-cli info memory
  ```

### Missing or Empty Parquet Files

If sentiment data is not appearing:

- Verify the `parquet_dir` setting in config.json
- Check that Parquet files exist and follow the expected naming pattern:
  - `{ticker}_sentiment.parquet`
  - `multi_ticker_sentiment.parquet`
- Examine Parquet file structure:
  ```bash
  pip install parquet-tools
  parquet-tools schema /path/to/file.parquet
  ```

### Dashboard Performance Issues

If the dashboard is slow:

- Reduce the number of tickers tracked (`top_n_tickers` in config)
- Increase the update interval in the dashboard
- Decrease the historical data timeframe in the dashboard