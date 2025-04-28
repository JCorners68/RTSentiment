# Real-Time Sentiment Analysis Documentation

This directory contains comprehensive documentation for the Real-Time Sentiment Analysis system. The documentation is organized by category to provide an easy-to-navigate reference for developers, data scientists, and system operators.

## Documentation Structure

- **[architecture/](./architecture/)**: System architecture, component design, and data flows
  - [Architecture Overview](./architecture/architecture_overview.md): Comprehensive system architecture
  - [Updated System Architecture](./architecture/updated_system_architecture.md): Latest architecture with Flutter integration
  - [Scraper Architecture](./architecture/scraper_architecture.md): Data acquisition components
  - [Sentiment Analyzer Architecture](./architecture/sentiment_analyzer_architecture.md): Sentiment analysis components
  - [Parquet Integration](./architecture/parquet_integration.md): Parquet storage implementation
  - [Redis Schema](./architecture/redis_schema.md): Cache design and implementation
  - [Metrics Server](./architecture/metrics_server.md): Performance metrics collection and monitoring
  - [Observability](./architecture/observability_specification.md): System monitoring and alerting

- **[api/](./api/)**: API specifications, endpoints, and integration guides
  - [API Specification](./api/API_spec.md): Comprehensive API documentation
  - [WebSocket Implementation](./api/WebSocket_Implementation.md): Real-time data streaming
  - [Historical Sentiment API](./api/historical_sentiment_api.md): Historical data access
  - [Service Ports](./api/service_ports.md): Service port assignments and configurations

- **[data/](./data/)**: Data structures, schemas, and acquisition processes
  - [Scrapers](./data/scrapers.md): Data acquisition strategies
  - [Parquet FDW](./data/parquet_fdw.md): Foreign Data Wrapper for Parquet files
  - [Parquet Metrics](./data/parquet_metrics.md): Performance metrics for Parquet operations
  - [Financial News Acquisition](./data/get_news_free.md): News acquisition strategies
  - [Wayback Scraper](./data/wayback_scraper_implementation.md): Historical data acquisition

- **[deployment/](./deployment/)**: Deployment guidelines, configurations, and environment setup
  - Docker container configurations
  - Environment setup instructions
  - Production deployment guidelines

- **[testing/](./testing/)**: Testing strategies, methodologies, and procedures
  - [Testing Overview](./testing/TESTING.md): Comprehensive testing documentation
  - Unit, integration, and end-to-end testing methodologies
  - Continuous integration practices

- **[guides/](./guides/)**: User and developer guides, tutorials, and usage examples
  - [Project Overview](./guides/project_overview.md): High-level project description
  - [Usage Guide](./guides/usage_guide.md): System usage instructions
  - [Streamlit to Flutter Migration](./guides/Streamlit_to_Flutter_Migration.md): UI migration guide

- **[future_plans/](./future_plans/)**: Upcoming features and development roadmap
  - [Data Tier Plan](./future_plans/Definitive%20Data%20Tier%20Plan%20for%20Sentiment%20Analysis.md): Future data storage plans

## Key System Components

The Real-Time Sentiment Analysis system consists of these major components:

1. **Data Acquisition** (`/data_acquisition/`): Gathers data from various sources
   - News scrapers for financial news sites
   - Reddit scraper for social media sentiment
   - SEC filings scraper for official company information
   - Subscription-based data sources (Bloomberg, etc.)
   - Metrics collection for scraper performance

2. **Sentiment Analysis** (`/sentiment_service/`, `/sentiment_analyzer/`): Processes and analyzes sentiment
   - Multiple ML models (FinBERT, FinGPT, Llama4)
   - Time-weighted sentiment calculation
   - Impact scoring based on source credibility
   - Event consumers with priority levels (high and standard)

3. **Data Storage**: Efficient data persistence
   - Redis for real-time caching
   - Parquet files for historical data
   - PostgreSQL with Foreign Data Wrapper for structured queries
   - Cache management and deduplication strategies

4. **API Layer** (`/api/`): Provides access to the system
   - RESTful endpoints for data queries
   - WebSocket for real-time sentiment updates
   - Authentication and authorization
   - Statistics and subscription management

5. **Client Applications** (`/senti/`): User interfaces
   - Flutter dashboard with cross-platform support
   - Real-time data visualization components
   - Authentication flow and settings management
   - Charts and data tables for sentiment analysis

6. **Monitoring** (`/monitoring/`): System observability
   - Prometheus metrics collection
   - Grafana dashboards for visualizing performance
   - Alerting rules for system health notifications
   - Parquet metrics for storage performance

## Code Structure Alignment

Our documentation is organized to reflect the actual codebase structure:

- `/data_acquisition/`: Scrapers, subscription services, and data collection utilities
- `/api/`: API endpoints, routes, and WebSocket implementation
- `/sentiment_service/`: Sentiment analysis models and event processing
- `/sentiment_analyzer/`: Core sentiment analysis algorithms and data processing
- `/monitoring/`: Prometheus, Grafana, and metrics collection
- `/senti/`: Flutter-based dashboard UI

## Using This Documentation

Each subdirectory has its own README file that explains the specific documentation contained within. Start with the relevant category based on your needs:

- For system design understanding, begin with the `architecture` section
- For integration details, refer to the `api` section
- For data handling, review the `data` section
- For setup instructions, check the `deployment` section
- For testing procedures, consult the `testing` section
- For general guidance, explore the `guides` section

## Contributing to Documentation

When adding or modifying documentation:

1. Place files in the appropriate category directory
2. Update the relevant README.md file if necessary
3. Use Markdown formatting for consistency
4. Include clear, concise information with examples when possible
5. Use diagrams (Mermaid syntax preferred) for complex relationships
6. Keep documentation in sync with codebase changes

## Further Resources

- [Project README](../README.md): Main project overview
- [Architecture Overview](./architecture/architecture_overview.md): Comprehensive architecture documentation
- [Project Overview](./guides/project_overview.md): Developer-focused system overview