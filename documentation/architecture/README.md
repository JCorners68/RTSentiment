# Real-Time Sentiment Analysis Architecture Documentation

This directory contains the architectural documentation for the Real-Time Sentiment Analysis system. The documentation includes diagrams, component descriptions, and architectural decisions.

## Architecture Documents

### Core System Architecture

- **[Architecture Overview](./architecture_overview.md)**: Comprehensive system architecture overview
- **[Updated System Architecture](./updated_system_architecture.md)**: Latest architecture with Flutter integration
- **[System Architecture HTML](./system_architecture.html)**: Interactive system architecture diagram
- **[Local Development](./local_development.html)**: Local development environment setup

### Component-Specific Architecture

- **[API Architecture](./API_architecture.md)**: API service design and endpoints
- **[Scraper Architecture](./scraper_architecture.md)**: Data acquisition components
- **[Sentiment Analyzer Architecture](./sentiment_analyzer_architecture.md)**: Sentiment analysis components
- **[Senti Architecture](./senti_architecture.md)**: Flutter dashboard architecture

### Data Management

- **[Parquet Integration](./parquet_integration.md)**: Parquet storage implementation
- **[Parquet Integration Analysis](./parquet_integration_analysis.md)**: Performance analysis of Parquet storage
- **[Parquet Schema](./parquet_schema.md)**: Schema definition for Parquet files
- **[Redis Schema](./redis_schema.md)**: Cache design and implementation

### Observability

- **[Metrics Server](./metrics_server.md)**: Metrics collection architecture
- **[Metrics Proxy](./metrics_proxy.md)**: Proxy for metrics collection
- **[Observability Specification](./observability_specification.md)**: Monitoring and alerting architecture

### Testing

- **[Testing Architecture](./testing_architecture.html)**: Comprehensive testing strategy

## System Components

The system architecture consists of six primary components, each with its own documentation:

### 1. Data Acquisition (`/data_acquisition/`)

Data collection from various sources:
- News scrapers for financial news sites (`news_scraper.py`)
- Reddit scraper for social media sentiment (`reddit_scraper.py`)
- SEC filings scraper for official company information (`sec_filings_scraper.py`)
- Subscription-based data sources (Bloomberg integration)
- Scraper base classes and abstractions (`base.py`)
- Metrics collection and monitoring

### 2. Sentiment Analysis (`/sentiment_service/`, `/sentiment_analyzer/`)

Sentiment processing pipeline:
- Model implementations (FinBERT, FinGPT, Llama4)
- Event consumers with priority levels
- Time-weighted sentiment calculation
- Impact scoring based on source credibility
- Redis cache integration for performance

### 3. Data Storage

Multiple storage strategies:
- Redis for real-time caching
- Parquet files for efficient historical data storage
- PostgreSQL with Foreign Data Wrapper for SQL access to Parquet
- Deduplication and cache management

### 4. API Layer (`/api/`)

System interfaces:
- RESTful endpoints for data queries
- WebSocket implementation for real-time updates
- Authentication and authorization
- Statistics and subscription management

### 5. Client Applications (`/senti/`)

User interfaces:
- Flutter dashboard with cross-platform support
- Real-time data visualization components
- Provider-based state management
- REST API and WebSocket integration

### 6. Monitoring (`/monitoring/`)

System observability:
- Prometheus metrics collection
- Grafana dashboards for visualization
- Alerting rules for system health
- Parquet metrics for storage performance

## Data Flow Architecture

The system implements an event-driven architecture with:

1. **Data Collection**: Scrapers and subscription services gather data
2. **Event Production**: Raw data is transformed into standardized events
3. **Sentiment Analysis**: Events are processed for sentiment scoring
4. **Storage**: Results are stored in Redis (recent) and Parquet (historical)
5. **API Access**: Data is exposed via REST and WebSocket interfaces
6. **Visualization**: Flutter dashboard presents data to users
7. **Monitoring**: System health and performance is continuously tracked

## Architectural Decisions

### Separation of Concerns

The system follows a clear separation of concerns with distinct services:
- Data acquisition services
- Event processing pipeline
- Sentiment analysis processing
- API layer
- Client applications

### Storage Strategy

A hybrid storage approach:
- Redis for high-speed caching and recent data
- Parquet files for efficient columnar storage of historical data
- PostgreSQL Foreign Data Wrapper for SQL access to Parquet data

### Event-Driven Architecture

The core system uses an event-driven architecture with:
- Asynchronous event processing
- Priority-based event consumers (high and standard priority)
- Decoupled components for better scaling

### Frontend Implementation

Flutter-based dashboard providing:
- Better performance over previous Streamlit implementation
- Enhanced UI/UX with responsive design
- Cross-platform support (mobile, web, desktop)
- Provider-based state management

### API Design

The API follows modern design principles:
- RESTful endpoints for data access
- WebSocket for real-time updates
- Standardized response formats
- Authentication and authorization

## Getting Started

To visualize the architecture diagrams:
1. Open the HTML files in a web browser to view the interactive diagrams
2. For the Mermaid diagrams in markdown files, use a Mermaid-compatible viewer or editor

## Contributing

When making architectural changes:
1. Update the relevant diagrams
2. Document the rationale behind changes
3. Ensure backward compatibility or provide migration paths
4. Update testing strategies to match architectural changes
5. Keep documentation aligned with the actual code structure