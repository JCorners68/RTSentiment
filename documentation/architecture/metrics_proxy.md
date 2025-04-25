# Clean Metrics Proxy

## Overview

The Clean Metrics Proxy is a service that provides a cleaner view of Prometheus metrics by removing HELP and TYPE comment lines. This makes it easier to read and parse the metrics output, especially when monitoring or debugging the system.

## Benefits

- Removes verbose HELP and TYPE comment lines from metrics output
- Makes metrics output more concise and readable
- Easier to grep and filter for specific metrics
- Same metrics data as the original endpoint, just cleaner presentation

## Usage

### Accessing the Clean Metrics

The clean metrics endpoint is available at:

```
http://localhost:8085/metrics
```

The original metrics endpoint with full HELP and TYPE comments is still available at:

```
http://localhost:8081/metrics
```

### Using the Helper Script

We provide a helper script to easily view and filter metrics:

```bash
# View clean metrics (without HELP and TYPE comments)
./scripts/show_metrics.sh

# View raw metrics (with HELP and TYPE comments)
./scripts/show_metrics.sh --raw

# Filter metrics by pattern
./scripts/show_metrics.sh --filter=scraper_items

# Combine options
./scripts/show_metrics.sh --raw --filter=scraper_records
```

## Docker Compose Configuration

The clean metrics proxy is configured in the `docker-compose.override.yml` file:

```yaml
# Add clean metrics proxy
clean-metrics-proxy:
  build:
    context: ./data_acquisition
    dockerfile: Dockerfile.metrics-proxy
  command: python clean_metrics_proxy.py --port 8085 --target http://scraper-metrics:8081/metrics
  ports:
    - "8085:8085"
  restart: unless-stopped
  depends_on:
    - scraper-metrics
  extra_hosts:
    - "host.docker.internal:host-gateway"
```

## Implementation Details

The proxy is implemented using a Flask application that:

1. Receives requests at the `/metrics` endpoint
2. Fetches metrics from the target metrics endpoint
3. Uses a regular expression to remove HELP and TYPE comment lines
4. Returns the cleaned metrics with the appropriate content type

The code is in the `data_acquisition/clean_metrics_proxy.py` file.