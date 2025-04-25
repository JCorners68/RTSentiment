# Extended Scraper System

A comprehensive data acquisition system for collecting financial data from multiple sources for sentiment analysis.

## Overview

The Extended Scraper System expands on the existing data acquisition capabilities by adding support for additional financial data sources:

- Twitter/X API integration for social media sentiment
- SEC filings for official company announcements
- Earnings call transcripts for detailed financial insights
- Historical data collection for backtesting

## Architecture

The system follows a modular architecture where all scrapers inherit from a common `BaseScraper` class:

```
BaseScraper
├── NewsScraper
├── RedditScraper
├── TwitterScraper
├── SECFilingsScraper
├── EarningsCallsScraper
└── HistoricalScraper
```

Data flows through the system as follows:

1. Scrapers collect data from various sources
2. Data is processed and enriched (ticker extraction, deduplication, etc.)
3. Events are sent to Kafka with appropriate priority
4. Processed data is saved to Parquet files for persistence
5. Sentiment analysis is performed on the collected data
6. Results are made available via API and Parquet Query Viewer

## Setup and Installation

### Prerequisites

- Python 3.7+
- Kafka
- Docker and Docker Compose (recommended)
- API credentials for data sources (Twitter, etc.)

### Installation

1. Install required packages:

```bash
pip install -r data_acquisition/requirements.txt
```

2. Configure scraper settings:

```json
# config/scraper_config.json
{
  "scrapers": {
    "twitter_scraper": {
      "enabled": true,
      "polling_interval": 180,
      "api_key": "your-api-key",
      "api_secret": "your-api-secret",
      "bearer_token": "your-bearer-token",
      "search_queries": ["$AAPL", "$TSLA", "stock market"],
      "accounts_to_follow": ["Bloomberg", "WSJ", "CNBC"],
      "tweet_limit": 100
    },
    "sec_filings_scraper": {
      "enabled": true,
      "polling_interval": 3600,
      "sec_url": "https://www.sec.gov/",
      "filing_types": ["10-K", "10-Q", "8-K"],
      "companies": [
        {"ticker": "AAPL", "cik": "0000320193"},
        {"ticker": "MSFT", "cik": "0000789019"},
        {"ticker": "TSLA", "cik": "0001318605"}
      ]
    }
  }
}
```

3. Set up environment variables:

```bash
# API credentials
export TWITTER_API_KEY="your-api-key"
export TWITTER_API_SECRET="your-api-secret"
export TWITTER_BEARER_TOKEN="your-bearer-token"

# Kafka configuration
export KAFKA_BOOTSTRAP_SERVERS="kafka:9092"
export KAFKA_HIGH_PRIORITY_TOPIC="high-priority-events"
export KAFKA_STANDARD_PRIORITY_TOPIC="standard-priority-events"
```

## Usage

### Running Scrapers

To run all scrapers:

```bash
# Using Python directly
python data_acquisition/main.py

# Using Docker
docker-compose up -d data-acquisition
```

To run a specific scraper:

```bash
# Set the scraper type environment variable
export SCRAPER_TYPE=twitter
python data_acquisition/main.py
```

### Docker Deployment

The system can be deployed using Docker:

```bash
# Build and start the services
docker-compose build
docker-compose up -d

# View logs
docker-compose logs -f data-acquisition
```

## Scraper Implementations

### Twitter/X Scraper

The Twitter scraper collects tweets from specified search queries and accounts:

- Searches for cashtags ($AAPL, $TSLA, etc.)
- Follows financial news accounts
- Extracts mentioned tickers
- Calculates engagement metrics
- Handles rate limiting and authentication

```python
from data_acquisition.scrapers.base import BaseScraper

class TwitterScraper(BaseScraper):
    """Scraper for Twitter/X financial content."""
    
    def __init__(self, producer, config):
        super().__init__(producer, config)
        # Initialization
        
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape Twitter/X for financial content."""
        # Implementation
        
    async def process_data(self, data: List[Dict[str, Any]]):
        """Process scraped Twitter/X data."""
        # Implementation
```

### SEC Filings Scraper

The SEC filings scraper collects official company filings:

- Monitors for new 10-K, 10-Q, 8-K, and other filing types
- Extracts key information from filings
- Identifies mentioned companies and tickers
- Prioritizes based on filing importance
- Handles SEC's fair access requirements

```python
from data_acquisition.scrapers.base import BaseScraper

class SECFilingsScraper(BaseScraper):
    """Scraper for SEC filings."""
    
    def __init__(self, producer, config):
        super().__init__(producer, config)
        # Initialization
        
    async def scrape(self) -> List[Dict[str, Any]]:
        """Scrape SEC filings for financial content."""
        # Implementation
        
    async def process_data(self, data: List[Dict[str, Any]]):
        """Process scraped SEC filings data."""
        # Implementation
```

### Earnings Calls Scraper

The earnings calls scraper collects and processes earnings call transcripts:

- Monitors for new transcripts
- Extracts Q&A sections, management commentary
- Identifies key financial metrics
- Detects sentiment indicators
- Prioritizes based on company importance and call content

### Historical Scraper

The historical scraper collects data for specified date ranges:

- Retrieves data from various sources for historical periods
- Enables backtesting of sentiment models
- Supports multiple data source types (news, social media, etc.)
- Maintains proper file organization for historical data

## Configuration

Each scraper can be configured via the `scraper_config.json` file:

```json
{
  "scrapers": {
    "twitter_scraper": {
      "enabled": true,
      "polling_interval": 180,
      "api_key": "your-api-key",
      "api_secret": "your-api-secret",
      "bearer_token": "your-bearer-token",
      "search_queries": ["$AAPL", "$TSLA", "stock market"],
      "accounts_to_follow": ["Bloomberg", "WSJ", "CNBC"],
      "tweet_limit": 100
    },
    "sec_filings_scraper": {
      "enabled": true,
      "polling_interval": 3600,
      "sec_url": "https://www.sec.gov/",
      "filing_types": ["10-K", "10-Q", "8-K"],
      "companies": [
        {"ticker": "AAPL", "cik": "0000320193"},
        {"ticker": "MSFT", "cik": "0000789019"},
        {"ticker": "TSLA", "cik": "0001318605"}
      ]
    },
    "earnings_calls_scraper": {
      "enabled": true,
      "polling_interval": 3600,
      "sources": [
        {"name": "Motley Fool", "url": "https://www.fool.com/earnings-call-transcripts/"},
        {"name": "Seeking Alpha", "url": "https://seekingalpha.com/earnings/earnings-call-transcripts"}
      ],
      "companies": ["AAPL", "MSFT", "TSLA", "GOOGL", "META"]
    },
    "historical_scraper": {
      "enabled": true,
      "source_type": "news",
      "date_format": "%Y-%m-%d",
      "output_dir": "./data/cache/historical/",
      "default_start_date": "2025-01-01",
      "default_end_date": "2025-04-01"
    }
  },
  "kafka": {
    "bootstrap_servers": "kafka:9092",
    "high_priority_topic": "high-priority-events",
    "standard_priority_topic": "standard-priority-events"
  },
  "parquet": {
    "output_dir": "./data/output",
    "compression": "SNAPPY",
    "row_group_size": 100000
  }
}
```

## Monitoring

The system exposes Prometheus metrics for monitoring:

- Success/failure rates for each scraper
- Data volume metrics (items scraped, events produced)
- Processing time and latency
- Rate limiting status
- Error rates by type and source

## Extending the System

To add a new scraper:

1. Create a new class inheriting from `BaseScraper`
2. Implement required methods (`scrape()`, `process_data()`)
3. Add configuration to `scraper_config.json`
4. Register the scraper in `main.py`

Example:

```python
from data_acquisition.scrapers.base import BaseScraper

class MyCustomScraper(BaseScraper):
    """Custom scraper implementation."""
    
    def __init__(self, producer, config):
        super().__init__(producer, config)
        self.custom_config = config.get("my_custom_scraper", {})
        # Additional initialization
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """Implement custom scraping logic."""
        # Custom implementation
        return []
    
    async def process_data(self, data: List[Dict[str, Any]]):
        """Process scraped data."""
        await super().process_data(data)
        # Additional custom processing
```

## Troubleshooting

### Common Issues

1. **API Rate Limiting**
   - Increase polling intervals
   - Implement exponential backoff
   - Use multiple API keys if available

2. **Data Quality Issues**
   - Check ticker extraction logic
   - Verify content parsing
   - Improve deduplication mechanisms

3. **Performance Problems**
   - Monitor Kafka producer throughput
   - Check Parquet file write performance
   - Optimize scraper-specific logic

## License

This project is licensed under the MIT License - see the LICENSE file for details.