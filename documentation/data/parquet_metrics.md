# Parquet Metrics Server

This documentation describes the Parquet metrics server implementation that exports sentiment data from Parquet files as Prometheus metrics.

## Overview

The Parquet metrics server reads sentiment data stored in Parquet files and exposes this data as Prometheus metrics. This allows the real-time dashboard to visualize actual sentiment data rather than simulated metrics.

## Key Features

- Automatically reads all Parquet files in the specified directory
- Calculates aggregate metrics (average sentiment, count, etc.) by ticker, source, and model
- Updates metrics at configurable intervals
- Exposes metrics via an HTTP endpoint for Prometheus to scrape
- Handles multi-ticker sentiment data

## Metrics Exposed

The server exposes the following metrics:

- `sentiment_value`: Average sentiment value by ticker, source, and model
- `sentiment_count`: Number of sentiment records by ticker and source
- `sentiment_confidence`: Average confidence level by ticker, source, and model
- `parquet_file_count`: Number of Parquet files by type
- `sentiment_data_last_update_timestamp`: Timestamp of the last data update by ticker

## Running the Server

### Standalone Mode

Run the server directly with Python:

```bash
python data_acquisition/parquet_metrics_server.py --port 8082 --parquet-dir ./data/output --update-interval 30
```

Or use the provided script:

```bash
./scripts/start_parquet_metrics.sh
```

### Docker Mode

The server is included in the Docker Compose setup as `parquet-metrics` service:

```bash
docker-compose up -d parquet-metrics
```

## Configuration

The server accepts the following command-line arguments:

- `--port`: Port to expose Prometheus metrics on (default: 8082)
- `--parquet-dir`: Directory containing Parquet files (default: ./data/output)
- `--update-interval`: Update interval in seconds (default: 60)

## Integration with Prometheus

The Prometheus configuration includes a job specifically for the Parquet metrics server:

```yaml
- job_name: 'parquet-metrics'
  metrics_path: /metrics
  static_configs:
    - targets: ['host.docker.internal:8082']
  scrape_interval: 30s
```

## Dashboard Integration

The "Real Sentiment Analysis Dashboard" uses these metrics to display actual sentiment data. It includes:

- Major Tech Stocks Sentiment panel
- Current Sentiment panel 
- Articles by Source panel
- Top 10 Tickers by Volume panel
- Top 10 Positive Sentiment panel

## Troubleshooting

If metrics are not appearing in Prometheus:

1. Check that the Parquet metrics server is running (`docker ps` or `ps aux | grep parquet_metrics`)
2. Verify that the metrics endpoint is accessible (`curl http://localhost:8082/metrics`)
3. Check Prometheus targets status in the Prometheus UI (`http://localhost:9090/targets`)
4. Verify that Parquet files exist in the configured directory
5. Check the logs for any errors (`docker logs parquet-metrics`)