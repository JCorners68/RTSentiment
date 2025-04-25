# Data Acquisition Scrapers

This document describes the structure, functionality, and usage of the data acquisition scrapers in the Real-Time Sentiment Analysis system.

## Overview

The data acquisition layer consists of specialized scrapers that collect financial data from various sources, which is then processed for sentiment analysis. The system currently implements two primary scraper types:

1. **News Scrapers** - Collect financial news articles from various sources
2. **Reddit Scrapers** - Gather posts from financial subreddits

All scrapers send their data to a Kafka message queue, which is then consumed by the sentiment analysis service. The processed sentiment data is stored in Parquet files and accessed via PostgreSQL's Foreign Data Wrapper (parquet_fdw).

## Directory Structure

```
/home/jonat/WSL_RT_Sentiment/
├── data_acquisition/
│   ├── scrapers/
│   │   ├── base.py             # Base scraper implementation
│   │   ├── reddit_scraper.py   # Reddit-specific scraper
│   │   ├── news_scraper.py     # News API scraper
│   ├── main.py                 # Main entry point for scraper service
│   ├── utils/
│   │   ├── event_producer.py   # Kafka message producer
│   │   ├── weight_calculator.py # Sentiment weight calculation
├── data/
│   ├── cache/                  # Cached data from scrapers
│   │   ├── historical/         # Historical scrape cache
│   ├── output/                 # Processed data outputs
│   │   ├── aapl_sentiment.parquet  # AAPL ticker sentiment data
│   │   ├── tsla_sentiment.parquet  # TSLA ticker sentiment data
│   │   ├── multi_ticker_sentiment.parquet # Multi-ticker data
│   │   ├── historical/         # Historical processed data
├── dbengine/
│   ├── postgres.Dockerfile     # Custom PostgreSQL with Parquet FDW
│   ├── init-fdw.sql            # SQL initialization for FDW
├── tests/
│   ├── data/                  # Data tests
│   │   ├── tests/            # Test scripts for data
│   │   │   ├── data_tests/   # Data-specific tests
│   │   │   │   ├── query_scrape_stats.py # Query statistics about scraped data
│   │   │   │   ├── scrape_history.py     # Historical data scraper
│   │   │   │   ├── test_basic_artifacts.py # Test parquet_fdw artifacts
│   │   ├── results/          # Results for data tests
│   ├── api/                  # API tests
│   ├── integration/          # Integration tests
│   ├── unit/                 # Unit tests
│   ├── e2e/                  # End-to-end tests
```

## Architecture

The data acquisition system follows these key design principles:

- **Modularity**: Each scraper is implemented as a separate class with a common interface
- **Asynchronous operation**: Uses async/await patterns for efficient I/O operations
- **Caching**: Implements caching to reduce API calls and respect rate limits
- **Configurability**: Sources and parameters can be adjusted via configuration files
- **Reliability**: Includes error handling and reconnection logic

## Scraper Implementation

### Base Scraper

All scrapers inherit from a common `BaseScraper` class, which defines the interface:

```python
class BaseScraper:
    """Base class for all scrapers."""
    
    def __init__(self, producer, config):
        """Initialize with event producer and configuration."""
        self.producer = producer
        self.config = config
        self.name = self.__class__.__name__
        
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape data from source. Must be implemented by subclasses."""
        raise NotImplementedError
        
    async def process_data(self, data: List[Dict[str, Any]]):
        """Process scraped data and send to event producer."""
        raise NotImplementedError
        
    async def start(self):
        """Start the scraper's operation."""
        raise NotImplementedError
        
    async def stop(self):
        """Stop the scraper's operation."""
        raise NotImplementedError
```

### News Scraper

The `NewsScraper` gathers financial news articles from various sources. It:

- Collects articles from financial news APIs and websites
- Extracts relevant ticker symbols from article content
- Assigns priority based on source credibility and article content
- Publishes articles to Kafka for sentiment analysis

### Reddit Scraper

The `RedditScraper` collects posts from financial subreddits. It:

- Monitors subreddits like r/wallstreetbets, r/investing, r/stocks
- Extracts mentioned ticker symbols from post titles and content
- Calculates engagement metrics (upvotes, comments)
- Determines priority based on post popularity and content
- Publishes posts to Kafka for sentiment analysis

## Configuration

Scrapers are configured via `config/scraper_config.json`, which contains settings like:

```json
{
  "reddit_subreddits": ["wallstreetbets", "investing", "stocks"],
  "reddit_polling_interval": 60,
  "reddit_post_limit": 25,
  "news_sources": ["bloomberg", "reuters", "financial-times"],
  "news_polling_interval": 300,
  "news_article_limit": 50
}
```

## Usage

### Running Scrapers in Docker

The easiest way to run scrapers is through Docker:

```bash
# Start all services
docker-compose up -d

# Start only the web-scraper
docker-compose up -d web-scraper

# Check logs
docker-compose logs -f web-scraper
```

### Manual Execution

For development or testing:

```bash
# Install dependencies
pip3 install -r data_acquisition/requirements.txt

# Run the scraper service
cd data_acquisition
python3 main.py
```

### Test Script Dependencies

Install the required dependencies for the test scripts:

```bash
# If using a virtual environment (recommended)
pip install -r tests/requirements.txt

# If not using a virtual environment
python3 -m pip install -r tests/requirements.txt

# Alternative for system without pip command
python3 -m pip install psycopg2-binary aiohttp pytest pytest-asyncio
```

### Historical Data Scraping

For backfilling or research, use the sc historical scraper:

```bash
# Scrape Reddit posts between dates
python3 tests/data/tests/data_tests/scrape_history.py --start_date 2025-04-01 --end_date 2025-04-15 --source reddit

# Scrape news articles
python3 tests/data/tests/data_tests/scrape_history.py --start_date 2025-03-24 --end_date 2025-04-23 --source news
```

### Querying Scrape Statistics

To view statistics on scraped data:

```bash
# Configure PostgreSQL connection for local execution
export POSTGRES_HOST=localhost  # Use your actual PostgreSQL host
export POSTGRES_PORT=5432       # Use your actual PostgreSQL port
export POSTGRES_DB=sentimentdb  # Use your actual database name
export POSTGRES_USER=pgadmin    # Use your actual username
export POSTGRES_PASSWORD=localdev  # Use your actual password

# Query all sources between dates
python3 tests/data/tests/data_tests/query_scrape_stats.py 2025-04-01 2025-04-15

# Query only Reddit data
python3 tests/data/tests/data_tests/query_scrape_stats.py 2025-04-16 2025-04-23 --source reddit

# Alternative: run in Docker context (if PostgreSQL is running in Docker)
docker-compose run --rm api python3 /app/tests/data/tests/data_tests/query_scrape_stats.py 2025-04-01 2025-04-15
```

Note: The query script uses the Parquet FDW tables exclusively through the `all_sentiment` view which provides direct access to the Parquet files containing sentiment data. The PostgreSQL Foreign Data Wrapper technology allows the system to query Parquet files as if they were regular database tables. Currently, the script doesn't filter by date due to potential timestamp format variations in different Parquet files, but it does filter by source if specified.

## Data Flow

1. Scrapers collect data from sources (news sites, Reddit, etc.)
2. Data is processed to extract relevant information (text, tickers, metadata)
3. Weight calculator assigns importance/priority to each item
4. Items are published to Kafka topics (high-priority or standard-priority)
5. Sentiment analysis service processes the events
6. Results are stored in Parquet files for efficient storage and querying
7. Data is accessed via:
   - PostgreSQL Foreign Data Wrapper (parquet_fdw) for Parquet files
   - Unified API that abstracts the underlying storage mechanism

## Future Enhancements

### Planned Improvements

1. **Additional Data Sources**:
   - Twitter/X API integration for social sentiment
   - SEC filings for official company announcements
   - Earnings call transcripts analysis
   - Financial blogs and expert commentary

2. **Enhanced Data Processing**:
   - Entity recognition to better identify companies not explicitly mentioned by ticker
   - Relationship extraction to understand connections between entities
   - Topic modeling to categorize content
   - Multi-language support for international sources

3. **Operational Improvements**:
   - More sophisticated rate limiting and backoff strategies
   - Enhanced caching with Redis
   - Better deduplication of content across sources
   - Improved error recovery and resilience

4. **Machine Learning Upgrades**:
   - Automated source credibility scoring
   - Content quality assessment
   - Clickbait and fake news detection
   - Auto-adjustment of scraping parameters based on data quality

5. **Subscription Service Integration**:
   - Premium data source API integration
   - Bloomberg Terminal data integration
   - Refinitiv/Thomson Reuters data feeds
   - Alpha Vantage and other financial data APIs

### Technical Debt to Address

1. Improved test coverage for all scrapers
2. Better validation of scraped content
3. More robust error handling and recovery
4. Enhanced monitoring and alerting
5. Documentation of all API endpoints and responses

## Contribution Guidelines

When contributing to the scrapers:

1. Maintain the existing architecture and class structure
2. Follow Python best practices (type hints, docstrings)
3. Write tests for new functionality
4. Document any new configuration options
5. Ensure backward compatibility when possible

## Parquet FDW Integration

The system uses PostgreSQL's Foreign Data Wrapper for Parquet files to efficiently store and query sentiment data:

### Benefits of Parquet FDW

1. **Performance**: Parquet's columnar storage format enables fast analytical queries
2. **Storage Efficiency**: Data compression reduces disk space requirements
3. **Query Optimization**: Predicate pushdown improves query performance
4. **Schema Evolution**: Allows for schema changes over time
5. **Scalability**: Handles large volumes of data without performance degradation

### Accessing Parquet Data

The `all_sentiment` view provides a unified interface to query data across multiple Parquet files:

```sql
-- Example: Query all sentiment data for a specific ticker
SELECT * FROM all_sentiment WHERE ticker = 'AAPL' LIMIT 10;

-- Example: Calculate average sentiment by source
SELECT source, AVG(sentiment) FROM all_sentiment GROUP BY source;
```

### Testing Scripts Integration

All test scripts that access sentiment data have been updated to use the Parquet FDW via the `all_sentiment` view. This provides several advantages:

1. **Direct Data Access**: Tests query Parquet files directly without intermediate data copies
2. **Performance**: Faster query execution for analytical operations
3. **Data Consistency**: Single source of truth for all data
4. **Simplicity**: Clean, consistent interface for accessing data

### Test Output Files

All test outputs follow the standard naming convention:

```
[test type]_results_YYMMDD_[instance].md
```

Where:
- `[test type]` is the category of test (e.g., `artifact`, `parquet`, `docker`, `sql`, `e2e`, `scrape`)
- `YYMMDD` is the date in YY-MM-DD format (e.g., 250423 for April 23, 2025)
- `[instance]` is a sequential number starting at 1 for multiple tests of the same type on the same day

All test outputs are stored in the respective test category's `results/` directory (e.g., `/tests/data/results/`). This standardized approach makes it easier to:
- Track test history over time
- Identify specific test runs
- Organize test outputs by type and date
- Automate test result analysis

For more detailed information on the Parquet FDW setup, see [parquet_fdw.md](./parquet_fdw.md).