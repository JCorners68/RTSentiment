# Real-Time Sentiment Analysis - System Architecture Overview

## System Purpose

The Real-Time Sentiment Analysis system provides:

- Continuous acquisition and analysis of financial sentiment data from multiple sources
- Real-time sentiment scoring for financial instruments (stocks, cryptocurrencies, etc.)
- Time-weighted sentiment calculation with configurable decay functions
- Impact scoring based on source credibility and engagement metrics
- Real-time visualization through a Flutter dashboard
- Historical sentiment trend analysis using Parquet file storage

## High-Level Architecture

The system is composed of these main components:

```
┌───────────────────┐       ┌────────────────────┐       ┌───────────────────┐
│                   │       │                    │       │                   │
│  Data Acquisition │──────►│ Sentiment Analysis │──────►│    Data Storage   │
│                   │       │                    │       │                   │
└───────────────────┘       └────────────────────┘       └──────────┬────────┘
                                                                    │
┌───────────────────┐       ┌────────────────────┐                 │
│                   │       │                    │                 │
│     Monitoring    │◄──────┤       API Layer    │◄────────────────┘
│                   │       │                    │
└───────────────────┘       └────────┬───────────┘
                                     │
                                     ▼
                            ┌────────────────────┐
                            │                    │
                            │ Client Applications │
                            │                    │
                            └────────────────────┘
```

## Component Details

### 1. Data Acquisition (`/data_acquisition`)

Responsible for gathering data from various sources:

- **Scrapers**: Extract data from financial news and social media:
  - `news_scraper.py`: Financial news sources
  - `reddit_scraper.py`: Reddit financial communities
  - Additional specialized scrapers in subdirectories
  
- **Subscription Services**: Process premium data sources:
  - `subscription_service.py`: Coordinates subscription data processing
  - `subscription/bloomberg.py`: Bloomberg data integration
  
- **Data Pre-processing**:
  - `weight_calculator.py`: Assigns initial weight to data points
  - `cache_manager.py`: Manages deduplication and caching
  - `event_producer.py`: Formats and sends events to analysis pipeline

### 2. Sentiment Analysis (`/sentiment_service`, `/sentiment_analyzer`)

Performs sentiment analysis on the acquired data:

- **Analysis Models**:
  - `finbert.py`: BERT-based financial sentiment model
  - `fingpt.py`: GPT-based financial sentiment model
  - `llama4_scout.py`: LLaMA-based model for complex content
  
- **Processing Logic**:
  - `sentiment_analyzer.py`: Core analysis algorithms
  - `decay_functions.py`: Time-based sentiment decay functions
  - `impact_scoring.py`: Source credibility and relevance scoring
  
- **Event Processing**:
  - `hipri_consumer.py`: High priority event processing
  - `stdpri_consumer.py`: Standard priority event processing

### 3. Data Storage

Manages persistence and retrieval of sentiment data:

- **Redis Cache**:
  - `redis_sentiment_cache.py`: Real-time sentiment storage
  - `redis_cache.py`: General caching functionality
  - `redis_manager.py`: Connection and configuration management
  
- **Parquet Storage**:
  - `parquet_reader.py`: Efficient reading of Parquet files
  - `parquet_loader.py`: Writing and updating Parquet files
  - Organized by ticker (`{ticker}_sentiment.parquet`)
  
- **PostgreSQL Database**:
  - `database.py`: Database connection and ORM models

### 4. API Layer (`/api`)

Provides access to the system's functionality:

- **REST API**:
  - `routes/sentiment.py`: Sentiment data endpoints
  - `routes/stats.py`: Statistical data endpoints
  - `routes/subscriptions.py`: Subscription management
  
- **Authentication**:
  - `routes/auth.py`: User authentication and authorization
  - `auth_service/`: Standalone authentication service
  
- **Real-time Updates**:
  - `routes/websocket.py`: WebSocket implementation
  - `ws_test.py`: WebSocket testing utilities

### 5. Client Applications

User interfaces for interacting with the system:

- **Flutter Dashboard** (`/senti`):
  - Modern cross-platform application with WebSocket support
  - State management via Provider architecture
  - Real-time updates and interactive visualizations
  
- **Streamlit Dashboard** (`/streamlit_dashboard`, deprecated):
  - Legacy web-based visualization interface
  
- **Parquet Query Viewer** (`/parquet_query_viewer`):
  - Specialized tool for querying and visualizing Parquet data

### 6. Monitoring

System observability and metrics:

- **Prometheus & Grafana** (`/monitoring`):
  - System metrics collection and visualization
  - Custom alerts for system health
  
- **Metrics Collection**:
  - `metrics.py`: Application-level metrics collection
  - `metrics_server.py`: Metrics HTTP endpoints
  - `parquet_metrics_server.py`: Parquet-specific metrics

## Data Flow

1. **Data Collection**:
   - Scrapers collect data from news and social media
   - Subscription services process premium data
   - Data is validated, weighted, and deduplicated

2. **Sentiment Analysis**:
   - Events are routed to appropriate analysis models
   - Multiple models may analyze the same content for verification
   - Results are scored based on source credibility and content relevance

3. **Storage & Aggregation**:
   - Real-time results stored in Redis for immediate access
   - Aggregated results written to Parquet files for long-term storage
   - PostgreSQL maintains system state and configuration

4. **Access & Visualization**:
   - API provides data access to client applications
   - WebSockets deliver real-time updates
   - Flutter dashboard visualizes current and historical sentiment

5. **Monitoring & Maintenance**:
   - Prometheus collects system metrics
   - Grafana dashboards visualize performance
   - Scheduled jobs optimize and maintain Parquet files

## Integration Points

### External Data Sources
- News APIs and web scrapers
- Reddit and other social media platforms
- Financial data providers through subscription services

### Client Integration
- REST API for data retrieval and system management
- WebSocket API for real-time updates
- Authentication system for secure access

### Observability
- Prometheus metrics endpoints
- Logging infrastructure
- Health check endpoints

## Deployment Architecture

The system is deployed using Docker containers:

- Individual services have dedicated Dockerfiles
- `docker-compose.yml` defines the full stack configuration
- Monitoring stack defined in `docker-compose.monitoring.yml`
- Test environment defined in `docker-compose.test.yml`

## Configuration and Extensibility

The system is designed to be highly configurable:

- Environment variables for deployment configuration
- JSON configuration files for component settings
- Pluggable architecture for sentiment models
- Extensible scraper framework for new data sources

## Performance Considerations

- Redis caching for high-speed data access
- Efficient Parquet file structure for historical data
- Priority-based event processing
- Asynchronous processing with FastAPI