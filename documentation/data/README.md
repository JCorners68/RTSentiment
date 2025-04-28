# Data Documentation

This directory contains comprehensive documentation related to data acquisition, storage, and processing within the Real-Time Sentiment Analysis system.

## Data Acquisition

- **[Scrapers](./scrapers.md)**: Details on the implementation of news, Reddit, and other data scrapers
- **[Financial News Acquisition](./get_news_free.md)**: Strategies for acquiring financial news data at scale
- **[Reformatted News Acquisition](./get_news_free_reformatted.md)**: Improved implementation for news acquisition
- **[Wayback Scraper Implementation](./wayback_scraper_implementation.md)**: Strategies for acquiring historical data
- **[Bulk Financial News Acquisition](./Bulk_Financial_News_Acquisition_Prompt.md)**: Guidelines for bulk data collection
- **[Financial Sentiment Data Acquisition Report](./Financial_Sentiment_Data_Acquisition_Report.md)**: Analysis of data acquisition results

## Data Storage

- **[Parquet FDW](./parquet_fdw.md)**: Documentation for the PostgreSQL Foreign Data Wrapper for Parquet files
- **[Parquet Metrics](./parquet_metrics.md)**: Performance metrics and monitoring for Parquet storage

## Data Structures

The system uses several key data structures:

1. **Raw Data Formats**:
   - JSON for scraped news articles and social media posts
   - Plain text for some financial data sources
   - Structured data from APIs

2. **Processing Formats**:
   - Standardized event objects with common fields
   - Sentiment scoring objects with source, text, and scores
   - Time-weighted impact calculations

3. **Storage Formats**:
   - Parquet files (columnar storage) for historical data
   - Redis caches for real-time data access
   - PostgreSQL tables for structured relational data

## Data Flow

The data flows through the system in this sequence:

1. **Acquisition**: Scrapers and subscription services collect raw data
2. **Deduplication**: Cache managers prevent duplicate processing
3. **Transformation**: Raw data is converted to standardized formats
4. **Sentiment Analysis**: Various models perform sentiment scoring
5. **Aggregation**: Scores are aggregated by ticker and time period
6. **Storage**: Data is stored in Redis (short-term) and Parquet (long-term)
7. **Query**: API endpoints provide access to processed data
8. **Visualization**: Dashboard presents data to users

## Directory Structure

The data-related code is organized in these directories:

- `/data_acquisition/scrapers/`: Web scrapers for data collection
- `/data_acquisition/subscription/`: Subscription-based data sources
- `/data_acquisition/utils/`: Utilities for cache management and data processing
- `/sentiment_service/models/`: Sentiment analysis model implementations
- `/sentiment_analyzer/data/`: Data loading and transformation utilities
- `/api/routes/`: API endpoints for data access

## Key Files

Important data-related files include:

- `/data_acquisition/scrapers/base.py`: Base scraper class defining common interfaces
- `/data_acquisition/scrapers/news_scraper.py`: News article scraper implementation
- `/data_acquisition/scrapers/reddit_scraper.py`: Reddit content scraper
- `/sentiment_service/models/model_factory.py`: Factory for sentiment model selection
- `/sentiment_analyzer/data/parquet_reader.py`: Utilities for reading Parquet data

## Contributing to Data Systems

When modifying data-related components:

1. Follow the established schemas and interfaces
2. Maintain backward compatibility or provide migration paths
3. Document changes to data structures or flows
4. Add appropriate tests for data handling
5. Update metrics collection for new data sources
6. Consider performance implications for large datasets
