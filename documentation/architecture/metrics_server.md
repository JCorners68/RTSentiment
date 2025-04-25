# Metrics Server

This document describes the metrics server for the real-time sentiment analysis system, particularly for the data acquisition module.

## Overview

The metrics server is a standalone service that exposes Prometheus-compatible metrics for the data acquisition system. It provides a consistent metrics endpoint for Prometheus to scrape, allowing for monitoring of the scraper's performance and health.

## Key Features

- Long-running service that maintains metrics even after scraper runs complete
- Exposes metrics on a configurable port (default: 8081)
- Provides metrics for items scraped, processing time, duplicates removed, and more
- Loads historical metrics from cached data files
- Integrated with Docker Compose for easy deployment

## Available Metrics

| Metric Name | Type | Description | Labels |
|-------------|------|-------------|--------|
| `scraper_items_scraped_total` | Counter | Total items scraped | `source` |
| `scraper_processing_duration_seconds` | Histogram | Scraper processing time | `source` |
| `scraper_duplicates_removed_total` | Counter | Total duplicate items removed | `source` |
| `scraper_unique_items_total` | Gauge | Total unique items scraped | `source` |
| `scraper_errors_total` | Counter | Total scraper errors | `source`, `error_type` |
| `scraper_cache_hits_total` | Counter | Cache hits when retrieving data | `source` |
| `scraper_cache_misses_total` | Counter | Cache misses when retrieving data | `source` |
| `scraper_last_run_timestamp` | Gauge | Timestamp of last scraper run | `source` |
| `scraper_uptime_seconds` | Gauge | Scraper service uptime in seconds | |

## Deployment

The metrics server is deployed as a Docker container alongside the other services of the real-time sentiment analysis system.

### Docker Compose Configuration

```yaml
services:
  scraper-metrics:
    build:
      context: ./data_acquisition
      dockerfile: Dockerfile.metrics
    volumes:
      - ./data:/app/data
    ports:
      - "8081:8081"
    restart: unless-stopped
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

## Usage

### Running Locally

To run the metrics server locally:

```bash
cd /path/to/WSL_RT_Sentiment
python data_acquisition/metrics_server.py --port 8081
```

### Running with Docker Compose

```bash
docker-compose up -d scraper-metrics
```

### Testing the Metrics Server

To test if the metrics server is running correctly:

```bash
./tests/test_metrics_server.sh
```

### Running the Historical Scraper with Metrics

To run the historical scraper with metrics enabled:

```bash
./tests/run_historical_scraper.sh --source news --start-date 2025-03-01 --end-date 2025-04-01
```

## Integration with Prometheus and Grafana

The metrics server is automatically discovered by Prometheus using the configuration in `monitoring/prometheus/prometheus.yml`:

```yaml
- job_name: 'historical-scraper'
  metrics_path: /metrics
  static_configs:
    - targets: ['host.docker.internal:8081']
```

Grafana dashboards for visualizing the metrics are available in `monitoring/grafana/dashboards/scraper_dashboard.json`.

## Troubleshooting

1. If metrics are not showing up in Grafana:
   - Verify that the metrics server is running: `curl http://localhost:8081/metrics`
   - Check Prometheus logs for scrape errors
   - Ensure that the network configuration in `docker-compose.override.yml` is correct

2. If the metrics server fails to start:
   - Check if the port is already in use
   - Verify that the prometheus-client library is installed
   - Ensure that the data directories exist and are writable