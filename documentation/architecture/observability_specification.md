# Real-Time Sentiment Analysis Observability Specification

This document outlines the comprehensive observability strategy for the Real-Time Sentiment Analysis system using Prometheus and Grafana.

## 1. Overview

The observability implementation provides real-time visibility into:

- API Service health and performance
- Docker container status
- Data acquisition and scraping metrics
- Kafka message queue performance
- Sentiment analysis model performance
- Database metrics
- System-wide resource utilization

## 2. Architecture

```mermaid
graph TD
    subgraph Services
        A[API Service] --> M[Metrics Endpoints]
        S[Sentiment Service] --> M
        W[Web Scraper] --> M
        K[Kafka] --> KE[Kafka Exporter]
        P[PostgreSQL] --> PE[Postgres Exporter]
        R[Redis] --> RE[Redis Exporter]
    end
    
    subgraph Monitoring
        M --> PR[Prometheus]
        KE --> PR
        PE --> PR
        RE --> PR
        NE[Node Exporter] --> PR
        PR --> G[Grafana]
        G --> D[Dashboards]
    end
    
    D --> API[API Dashboard]
    D --> DOCKER[Docker Status Dashboard]
    D --> DATA[Data Acquisition Dashboard]
    D --> MODEL[Model Performance Dashboard]
    D --> SYSTEM[System Health Dashboard]
```

## 3. Metrics Collection

### 3.1 API Service Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `api_http_requests_total` | Counter | Total HTTP requests by endpoint, method, and status code |
| `api_http_request_duration_seconds` | Histogram | HTTP request duration |
| `api_http_request_size_bytes` | Histogram | HTTP request size |
| `api_http_response_size_bytes` | Histogram | HTTP response size |
| `api_active_requests` | Gauge | Currently active HTTP requests |
| `api_health_status` | Gauge | Health status (1 = healthy, 0 = unhealthy) |
| `api_database_connection_errors` | Counter | Database connection errors |
| `api_redis_connection_errors` | Counter | Redis connection errors |
| `api_uptime_seconds` | Counter | API service uptime |

### 3.2 Docker Container Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `container_cpu_usage_seconds_total` | Counter | CPU usage in seconds |
| `container_memory_usage_bytes` | Gauge | Memory usage in bytes |
| `container_network_receive_bytes_total` | Counter | Network bytes received |
| `container_network_transmit_bytes_total` | Counter | Network bytes transmitted |
| `container_fs_usage_bytes` | Gauge | File system usage in bytes |
| `container_last_seen` | Gauge | Unix timestamp when container was last seen |
| `container_start_time_seconds` | Gauge | Start time in seconds since epoch |
| `container_restarts_total` | Counter | Container restarts |

### 3.3 Data Acquisition Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `scraper_items_scraped_total` | Counter | Total items scraped by source |
| `scraper_processing_duration_seconds` | Histogram | Scraper processing time |
| `scraper_errors_total` | Counter | Total scraper errors by source and type |
| `scraper_cache_hits_total` | Counter | Cache hits when retrieving data |
| `scraper_cache_misses_total` | Counter | Cache misses when retrieving data |
| `scraper_api_calls_total` | Counter | External API calls by endpoint |
| `scraper_api_errors_total` | Counter | External API errors by endpoint |
| `scraper_items_by_ticker` | Counter | Scraped items by ticker symbol |
| `scraper_run_duration_seconds` | Histogram | Full scraper run duration |
| `scraper_scheduled_runs_total` | Counter | Total scheduled scraper runs |
| `scraper_manual_runs_total` | Counter | Total manual scraper runs |

### 3.4 Kafka Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `kafka_topic_partitions` | Gauge | Number of partitions for each topic |
| `kafka_consumergroup_lag` | Gauge | Lag by consumergroup and topic |
| `kafka_topic_partition_current_offset` | Gauge | Current offset by topic and partition |
| `kafka_topic_partition_oldest_offset` | Gauge | Oldest offset by topic and partition |
| `kafka_messages_in_total` | Counter | Total messages in Kafka topics |
| `kafka_high_priority_messages_total` | Counter | High priority messages by source |
| `kafka_standard_priority_messages_total` | Counter | Standard priority messages by source |

### 3.5 Sentiment Analysis Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `model_inference_duration_seconds` | Histogram | Model inference duration |
| `model_processed_messages_total` | Counter | Total processed messages by model and source |
| `model_processing_errors_total` | Counter | Total processing errors by model |
| `model_average_sentiment_score` | Gauge | Average sentiment score by ticker |
| `model_memory_usage_bytes` | Gauge | Model memory usage |
| `model_gpu_memory_usage_bytes` | Gauge | GPU memory usage by model |
| `model_queue_size` | Gauge | Current processing queue size |
| `model_average_processing_time` | Gauge | Average processing time in last minute |

## 4. Dashboard Specifications

### 4.1 System Health Dashboard

Primary dashboard showing overall system health with panels for:

- Service status (up/down)
- CPU, memory, disk, and network usage by service
- Number of errors by service
- Error rate trends
- Service uptime

### 4.2 API Performance Dashboard

Detailed API performance monitoring with panels for:

- Request rate by endpoint
- Response time by endpoint
- Error rate by endpoint
- Active connections
- Database query performance
- Cache hit/miss ratio
- HTTP status code distribution

### 4.3 Data Acquisition Dashboard

Monitors the scraping and data collection processes:

- Items scraped by source and time period
- Scraping success rate
- API call volume and errors
- Cache performance
- Processing time
- Data volume by ticker
- Latest scrape status
- Scrape frequency

### 4.4 Message Processing Dashboard

Tracks Kafka message processing:

- Message ingestion rate by topic
- Consumer lag by consumer group
- Processing time
- Error rate
- Message distribution by priority
- Throughput by source
- Backlog size

### 4.5 Model Performance Dashboard

Monitors sentiment analysis model performance:

- Inference time by model
- Throughput (messages processed per second)
- Error rate
- GPU utilization
- Memory usage
- Sentiment distribution
- Model performance comparison

## 5. Alerting Rules

### 5.1 Critical Alerts

| Alert | Condition | Description |
|-------|-----------|-------------|
| `ServiceDown` | `up == 0` | Any service is down |
| `HighErrorRate` | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05` | Error rate exceeds 5% |
| `APIHighLatency` | `api_http_request_duration_seconds{quantile="0.9"} > 2` | 90th percentile latency exceeds 2 seconds |
| `DiskSpaceCritical` | `disk_free_percent < 10` | Less than 10% disk space remaining |
| `KafkaLagCritical` | `kafka_consumergroup_lag > 1000` | Consumer lag exceeds 1000 messages |
| `ModelProcessingError` | `rate(model_processing_errors_total[5m]) > 0.1` | Model processing error rate exceeds 10% |

### 5.2 Warning Alerts

| Alert | Condition | Description |
|-------|-----------|-------------|
| `ServiceHighLoad` | `cpu_usage_percent > 80` | CPU usage exceeds 80% |
| `MemoryHighUsage` | `memory_usage_percent > 85` | Memory usage exceeds 85% |
| `APIIncreasingLatency` | `api_http_request_duration_seconds{quantile="0.5"} > 0.5` | Median latency exceeds 0.5 seconds |
| `DiskSpaceWarning` | `disk_free_percent < 20` | Less than 20% disk space remaining |
| `ScraperError` | `increase(scraper_errors_total[15m]) > 5` | More than 5 scraper errors in 15 minutes |
| `KafkaLagWarning` | `kafka_consumergroup_lag > 500` | Consumer lag exceeds 500 messages |

## 6. Implementation

### 6.1 Prometheus Configuration

Update the `/home/jonat/WSL_RT_Sentiment/monitoring/prometheus.yml` file:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s

rule_files:
  - "rules/alerts.yml"
  - "rules/recording_rules.yml"

alerting:
  alertmanagers:
  - static_configs:
    - targets:
      - 'alertmanager:9093'

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'api'
    metrics_path: /metrics
    static_configs:
      - targets: ['api:8001']

  - job_name: 'sentiment-service'
    metrics_path: /metrics
    static_configs:
      - targets: ['sentiment-analysis:8000']
      
  - job_name: 'web-scraper'
    metrics_path: /metrics
    static_configs:
      - targets: ['web-scraper:8080']
      
  - job_name: 'subscription-receiver'
    metrics_path: /metrics
    static_configs:
      - targets: ['subscription-receiver:8080']

  - job_name: 'kafka'
    static_configs:
      - targets: ['kafka-exporter:9308']

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

### 6.2 Docker Compose Updates

Add the following services to `docker-compose.yml`:

```yaml
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter
    environment:
      DATA_SOURCE_NAME: "postgresql://pgadmin:localdev@postgres:5432/sentimentdb?sslmode=disable"
    ports:
      - "9187:9187"
    depends_on:
      - postgres

  redis-exporter:
    image: oliver006/redis_exporter
    ports:
      - "9121:9121"
    command:
      - '--redis.addr=redis://redis:6379'
    depends_on:
      - redis

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    ports:
      - "8090:8080"
    depends_on:
      - redis

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager:/etc/alertmanager
      - alertmanager-data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
```

### 6.3 Service Instrumentation

#### API Service

Add Prometheus instrumentation to the FastAPI application in `api/main.py`:

```python
from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Sentiment Analysis API")

# Initialize Prometheus instrumentator
Instrumentator().instrument(app).expose(app)
```

#### Sentiment Service

Add Prometheus instrumentation to the sentiment service in `sentiment_service/main.py`:

```python
from fastapi import FastAPI, Request
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Sentiment Analysis Service")

# Initialize Prometheus instrumentator
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

# Add custom metrics
from prometheus_client import Counter, Histogram, Gauge
model_inference_duration = Histogram(
    "model_inference_duration_seconds", 
    "Model inference duration in seconds",
    ["model_name"]
)
model_processed_messages = Counter(
    "model_processed_messages_total",
    "Total processed messages by model and source",
    ["model_name", "source"]
)
model_average_sentiment = Gauge(
    "model_average_sentiment_score",
    "Average sentiment score by ticker",
    ["ticker"]
)
```

#### Web Scraper

Add Prometheus instrumentation to the web scraper in `data_acquisition/main.py`:

```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import threading

# Initialize metrics
scraper_items_scraped = Counter(
    "scraper_items_scraped_total", 
    "Total items scraped by source",
    ["source"]
)
scraper_processing_duration = Histogram(
    "scraper_processing_duration_seconds",
    "Scraper processing time",
    ["source"]
)
scraper_errors = Counter(
    "scraper_errors_total",
    "Total scraper errors by source and type",
    ["source", "error_type"]
)
scraper_items_by_ticker = Counter(
    "scraper_items_by_ticker",
    "Scraped items by ticker symbol",
    ["source", "ticker"]
)

# Start metrics server
def start_metrics_server():
    start_http_server(8080)

threading.Thread(target=start_metrics_server, daemon=True).start()
```

## 7. Grafana Dashboards

Create JSON dashboard definitions in `/home/jonat/WSL_RT_Sentiment/monitoring/grafana/dashboards/`:

1. `system_health_dashboard.json`
2. `api_performance_dashboard.json`
3. `data_acquisition_dashboard.json`
4. `message_processing_dashboard.json`
5. `model_performance_dashboard.json`

Example dashboard structure for the Data Acquisition Dashboard:

```json
{
  "title": "Data Acquisition Dashboard",
  "uid": "data-acquisition",
  "panels": [
    {
      "title": "Items Scraped by Source",
      "type": "timeseries",
      "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
      "targets": [
        {
          "expr": "sum(increase(scraper_items_scraped_total[1h])) by (source)",
          "legendFormat": "{{source}}"
        }
      ]
    },
    {
      "title": "Scraper Processing Time",
      "type": "timeseries",
      "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8},
      "targets": [
        {
          "expr": "rate(scraper_processing_duration_seconds_sum[5m]) / rate(scraper_processing_duration_seconds_count[5m])",
          "legendFormat": "{{source}}"
        }
      ]
    },
    {
      "title": "Scraper Errors",
      "type": "timeseries",
      "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8},
      "targets": [
        {
          "expr": "sum(increase(scraper_errors_total[1h])) by (source)",
          "legendFormat": "{{source}}"
        }
      ]
    },
    {
      "title": "Top Tickers by Volume",
      "type": "bar",
      "gridPos": {"x": 12, "y": 8, "w": 12, "h": 8},
      "targets": [
        {
          "expr": "topk(10, sum(scraper_items_by_ticker) by (ticker))",
          "legendFormat": "{{ticker}}"
        }
      ]
    }
  ]
}
```

## 8. Metrics Retention

Configure Prometheus data retention based on system capacity:

- High-resolution metrics (15s interval): 7 days
- Aggregated hourly metrics: 30 days
- Aggregated daily metrics: 1 year

This is configured in the Prometheus command line arguments in the docker-compose.yml file:

```yaml
command:
  - '--config.file=/etc/prometheus/prometheus.yml'
  - '--storage.tsdb.path=/prometheus'
  - '--storage.tsdb.retention.time=7d'
  - '--web.console.libraries=/usr/share/prometheus/console_libraries'
  - '--web.console.templates=/usr/share/prometheus/consoles'
```

## 9. Access Control

- Prometheus: Basic authentication using a reverse proxy
- Grafana: User authentication with roles
  - Admin: Full access
  - Editor: Can edit dashboards but not modify data sources
  - Viewer: Read-only access

## 10. Implementation Roadmap

1. **Phase 1: Basic Monitoring**
   - Setup Prometheus and Grafana
   - Implement service health monitoring
   - Create system health dashboard

2. **Phase 2: Service Instrumentation**
   - Add instrumentation to API service
   - Add instrumentation to sentiment service
   - Add instrumentation to web scraper
   - Create service-specific dashboards

3. **Phase 3: Advanced Monitoring**
   - Implement alerting
   - Add advanced metrics for model performance
   - Set up distributed tracing
   - Integrate with incident management system

4. **Phase 4: Optimization**
   - Review and optimize metric collection
   - Implement metric aggregation for historical data
   - Set up automated reporting
   - Create custom visualizations for business metrics