# Code to Documentation Mapping

This document provides a quick reference to help developers find documentation for specific codebase components. It maps directories and key files to their corresponding documentation.

## Core System Components

| Code Directory/File | Documentation |
|---|---|
| `/data_acquisition/` | [Scraper Architecture](./architecture/scraper_architecture.md), [Data Acquisition](./data/scrapers.md) |
| `/data_acquisition/scrapers/base.py` | [Scraper Architecture](./architecture/scraper_architecture.md) |
| `/data_acquisition/scrapers/news_scraper.py` | [News Scraper](./data/get_news_free.md) |
| `/data_acquisition/scrapers/reddit_scraper.py` | [Scrapers](./data/scrapers.md) |
| `/data_acquisition/metrics.py` | [Metrics Server](./architecture/metrics_server.md) |
| `/sentiment_service/` | [Sentiment Analyzer Architecture](./architecture/sentiment_analyzer_architecture.md) |
| `/sentiment_service/models/` | [Model Implementation](./architecture/sentiment_analyzer_architecture.md) |
| `/sentiment_service/event_consumers/` | [Event Processing](./architecture/updated_system_architecture.md) |
| `/sentiment_analyzer/` | [Sentiment Analysis](./architecture/sentiment_analyzer_architecture.md) |
| `/sentiment_analyzer/models/decay_functions.py` | [Time Weighting](./architecture/sentiment_analyzer_architecture.md) |
| `/api/` | [API Specification](./api/API_spec.md), [API Architecture](./architecture/API_architecture.md) |
| `/api/routes/` | [API Endpoints](./api/API_spec.md) |
| `/api/routes/websocket.py` | [WebSocket Implementation](./api/WebSocket_Implementation.md) |
| `/monitoring/` | [Observability Specification](./architecture/observability_specification.md) |
| `/monitoring/prometheus/` | [Metrics Collection](./architecture/metrics_server.md) |
| `/senti/` | [Flutter Architecture](./architecture/senti_architecture.md) |
| `/senti/lib/providers/` | [State Management](./architecture/senti_architecture.md) |

## Data Storage

| Component | Documentation |
|---|---|
| Parquet Files | [Parquet Integration](./architecture/parquet_integration.md), [Parquet Schema](./architecture/parquet_schema.md) |
| Redis Cache | [Redis Schema](./architecture/redis_schema.md) |
| PostgreSQL | [Parquet FDW](./data/parquet_fdw.md) |

## Key Processes

| Process | Documentation |
|---|---|
| Data Acquisition | [Data Acquisition Report](./data/Financial_Sentiment_Data_Acquisition_Report.md) |
| Sentiment Analysis | [Sentiment Analyzer Architecture](./architecture/sentiment_analyzer_architecture.md) |
| API Access | [API Specification](./api/API_spec.md) |
| Monitoring | [Observability Specification](./architecture/observability_specification.md) |
| Testing | [Testing Architecture](./architecture/testing_architecture.html), [Testing Documentation](./testing/TESTING.md) |
| Deployment | [Deployment Documentation](./deployment/README.md) |

## Docker Infrastructure

| Component | Documentation |
|---|---|
| `docker-compose.yml` | [Local Development](./architecture/local_development.html) |
| `Dockerfile.*` | [Deployment Documentation](./deployment/README.md) |

## Flutter Dashboard

| Feature | Documentation |
|---|---|
| API Client | [API Integration](./architecture/senti_architecture.md) |
| State Management | [Flutter Architecture](./architecture/senti_architecture.md) |
| Real-time Updates | [WebSocket Implementation](./api/WebSocket_Implementation.md) |

## Testing

| Test Type | Documentation |
|---|---|
| Unit Tests | [Testing Documentation](./testing/TESTING.md) |
| Integration Tests | [Testing Documentation](./testing/TESTING.md) |
| End-to-End Tests | [Testing Documentation](./testing/TESTING.md) |

## Development Guides

| Topic | Documentation |
|---|---|
| Project Overview | [Project Overview](./guides/project_overview.md) |
| Usage | [Usage Guide](./guides/usage_guide.md) |
| UI Framework | [Streamlit to Flutter Migration](./guides/Streamlit_to_Flutter_Migration.md) |

## Future Plans

| Area | Documentation |
|---|---|
| Data Storage | [Data Tier Plan](./future_plans/Definitive%20Data%20Tier%20Plan%20for%20Sentiment%20Analysis.md) |