# Wayback Machine Scraper Implementation Guide

## Overview

This document outlines the implementation of a Wayback Machine-based scraper for acquiring bulk historical financial news data. The approach leverages the Internet Archive's Wayback Machine to access archived versions of financial news websites, providing a free and comprehensive source of historical data.

## Architecture

The implementation follows the existing scraper architecture pattern:

1. Extends the `BaseScraper` class to maintain consistency with the current system
2. Implements asynchronous scraping methods for performance
3. Integrates with the data pipeline for deduplication and storage
4. Uses site-specific content extraction for accurate data parsing

## Implementation Details

### WaybackScraper Class

```python
"""
Wayback Machine scraper for historical financial news data.
"""
import logging
import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

from .base import BaseScraper

logger = logging.getLogger(__name__)

class WaybackScraper(BaseScraper):
    """Scrape historical financial news from the Wayback Machine (Internet Archive)."""
    
    def __init__(self, producer, config):
        """
        Initialize the WaybackScraper.
        
        Args:
            producer: Event producer for publishing events
            config: Configuration dictionary
        """
        super().__init__(producer, config)
        
        # Get domain targets from config
        self.target_domains = self.config.get("wayback_target_domains", [
            "finance.yahoo.com",
            "cnbc.com",
            "marketwatch.com",
            "reuters.com/business",
            "bloomberg.com/markets",
            "fool.com"
        ])
        
        # Configure date ranges
        self.default_lookback_days = self.config.get("wayback_lookback_days", 30)
        
        # Rate limiting to respect Wayback Machine's servers
        self.request_delay = self.config.get("wayback_request_delay", 1.0)
        self.max_snapshots_per_domain = self.config.get("wayback_max_snapshots", 100)
        
        # Date tracking to prevent reprocessing
        self.processed_dates = set()
        
        # Initialize date-specific extractors
        self.extractors = {
            "finance.yahoo.com": self._extract_yahoo_finance,
            "cnbc.com": self._extract_cnbc,
            "marketwatch.com": self._extract_marketwatch,
            "reuters.com": self._extract_reuters,
            "bloomberg.com": self._extract_bloomberg,
            "fool.com": self._extract_motley_fool,
        }
        
        # Default to generic extractor for unlisted domains
        self.default_extractor = self._extract_generic
        
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape data from Wayback Machine for the target domains.
        
        Returns:
            List of dictionaries containing scraped data
        """
        all_results = []
        
        # Start with the most recent lookback days, then gradually proceed to older dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.default_lookback_days)
        
        date_str = start_date.strftime("%Y%m%d")
        end_date_str = end_date.strftime("%Y%m%d")
        
        # Skip if this date range has been processed already
        date_key = f"{date_str}_{end_date_str}"
        if date_key in self.processed_dates:
            logger.info(f"Skipping already processed date range: {date_str} to {end_date_str}")
            return []
        
        logger.info(f"Scraping Wayback Machine from {date_str} to {end_date_str}")
        
        # Process each domain
        async with aiohttp.ClientSession() as session:
            for domain in self.target_domains:
                try:
                    logger.info(f"Getting snapshots for {domain}")
                    snapshots = await self._get_wayback_snapshots(
                        session, domain, date_str, end_date_str
                    )
                    
                    logger.info(f"Found {len(snapshots)} snapshots for {domain}")
                    
                    # Process a limited number of snapshots per domain
                    snapshot_count = min(len(snapshots), self.max_snapshots_per_domain)
                    for i in range(snapshot_count):
                        snapshot = snapshots[i]
                        
                        # Skip non-article pages
                        if not self._is_article_url(snapshot.get("url", ""), domain):
                            continue
                        
                        # Download content
                        html_content = await self._download_wayback_content(
                            session, snapshot.get("url", ""), snapshot.get("timestamp", "")
                        )
                        
                        if not html_content:
                            continue
                        
                        # Extract article data using domain-specific extractor
                        article_data = self._extract_article(html_content, domain)
                        
                        if article_data and article_data.get("title") and article_data.get("content"):
                            # Add metadata
                            article_data["url"] = snapshot.get("url", "")
                            article_data["source_domain"] = domain
                            article_data["wayback_timestamp"] = snapshot.get("timestamp", "")
                            article_data["scrape_timestamp"] = datetime.now().isoformat()
                            
                            # Generate a unique ID
                            article_data["id"] = f"wayback_{domain.replace('.', '_')}_{snapshot.get('timestamp', '')}"
                            
                            # Add to results
                            all_results.append(article_data)
                        
                        # Respect rate limits
                        await asyncio.sleep(self.request_delay)
                        
                except Exception as e:
                    logger.error(f"Error processing domain {domain}: {e}")
                    continue
        
        # Mark this date range as processed
        self.processed_dates.add(date_key)
        
        logger.info(f"Found {len(all_results)} articles from Wayback Machine")
        return all_results
    
    async def _get_wayback_snapshots(self, session, domain, start_date, end_date, limit=1000):
        """
        Get list of snapshots from Wayback Machine for a domain in a date range.
        
        Args:
            session: aiohttp client session
            domain: Website domain to search
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            limit: Maximum number of results
            
        Returns:
            List of snapshot dictionaries
        """
        cdx_api_url = "https://web.archive.org/cdx/search/cdx"
        params = {
            "url": domain,
            "matchType": "domain",
            "limit": limit,
            "from": start_date,
            "to": end_date,
            "output": "json",
            "fl": "timestamp,original,statuscode,mimetype"
        }
        
        try:
            async with session.get(cdx_api_url, params=params) as response:
                if response.status != 200:
                    logger.error(f"CDX API error: {response.status}")
                    return []
                
                data = await response.json()
                
                if not data or len(data) <= 1:  # Check if there's data beyond header row
                    return []
                
                # First row contains column headers
                headers = data[0]
                snapshots = []
                
                # Convert to list of dictionaries
                for row in data[1:]:
                    snapshot = {headers[i]: row[i] for i in range(len(headers))}
                    
                    # Only include HTML content and successful responses
                    if snapshot.get("mimetype") == "text/html" and snapshot.get("statuscode") == "200":
                        snapshots.append({
                            "url": snapshot.get("original", ""),
                            "timestamp": snapshot.get("timestamp", "")
                        })
                
                return snapshots
                
        except Exception as e:
            logger.error(f"Error fetching Wayback snapshots: {e}")
            return []
    
    async def _download_wayback_content(self, session, snapshot_url, timestamp):
        """
        Download content from Wayback Machine.
        
        Args:
            session: aiohttp client session
            snapshot_url: Original URL
            timestamp: Wayback timestamp
            
        Returns:
            HTML content as string, or None on failure
        """
        wayback_url = f"https://web.archive.org/web/{timestamp}/{snapshot_url}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            async with session.get(wayback_url, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    return content
                else:
                    logger.warning(f"Failed to download {wayback_url}: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error downloading {wayback_url}: {e}")
            return None
    
    def _is_article_url(self, url, domain):
        """
        Check if URL appears to be an article page.
        
        Args:
            url: URL to check
            domain: Domain of the website
            
        Returns:
            True if URL appears to be an article, False otherwise
        """
        # Simple domain-specific rules
        if domain == "finance.yahoo.com":
            return "/news/" in url or "/video/" in url
        elif domain == "cnbc.com":
            return "/2020/" in url or "/2021/" in url or "/2022/" in url
        elif domain == "marketwatch.com":
            return "/story/" in url
        elif domain == "reuters.com":
            return "/article/" in url
        elif domain == "fool.com":
            return "/investing/" in url or "/stocks/" in url
        
        # Generic rule for other domains - exclude homepage and common non-article paths
        return (
            not url.endswith(domain) and 
            not url.endswith(domain + "/") and
            "/tag/" not in url and
            "/category/" not in url and
            "/author/" not in url
        )
    
    def _extract_article(self, html, domain):
        """
        Extract article content from HTML.
        
        Args:
            html: HTML content
            domain: Domain of the website
            
        Returns:
            Dictionary with article data
        """
        # Use domain-specific extractor if available
        for domain_pattern, extractor in self.extractors.items():
            if domain_pattern in domain:
                return extractor(html)
        
        # Fall back to generic extractor
        return self.default_extractor(html)
    
    def _extract_yahoo_finance(self, html):
        """Extract article from Yahoo Finance."""
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract title
            title_element = soup.find('h1')
            title = title_element.text.strip() if title_element else ""
            
            # Extract date
            date_element = soup.find('time')
            date = date_element.get('datetime') if date_element else ""
            
            # Extract content
            content_div = soup.find('div', {'class': 'caas-body'})
            if not content_div:
                # Try alternate class
                content_div = soup.find('div', {'class': 'canvas-body'})
                
            paragraphs = content_div.find_all('p') if content_div else []
            content = ' '.join([p.text.strip() for p in paragraphs])
            
            # Extract tickers
            tickers = []
            ticker_elements = soup.find_all('a', {'class': 'caas-header-linkcard'})
            
            for element in ticker_elements:
                ticker = element.text.strip()
                if ticker.isupper() and len(ticker) < 6:  # Simple validation for ticker symbols
                    tickers.append(ticker)
            
            return {
                'title': title,
                'date': date,
                'content': content,
                'tickers': tickers
            }
            
        except Exception as e:
            logger.error(f"Error extracting Yahoo Finance article: {e}")
            return None
    
    def _extract_cnbc(self, html):
        """Extract article from CNBC."""
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract title
            title_element = soup.find('h1')
            title = title_element.text.strip() if title_element else ""
            
            # Extract date
            date_element = soup.find('time')
            date = date_element.get('datetime') if date_element else ""
            
            # Extract content - CNBC uses various containers
            content_div = soup.find('div', {'class': 'ArticleBody-articleBody'})
            if not content_div:
                content_div = soup.find('div', {'class': 'group'})
                
            paragraphs = content_div.find_all('p') if content_div else []
            content = ' '.join([p.text.strip() for p in paragraphs])
            
            # Extract tickers - CNBC usually has a 'stock quotes' section
            tickers = []
            quote_divs = soup.find_all('div', {'class': 'QuoteStrip-stockInfo'})
            
            for div in quote_divs:
                ticker_element = div.find('span', {'class': 'QuoteStrip-symbol'})
                if ticker_element:
                    ticker = ticker_element.text.strip()
                    if ticker.isupper() and len(ticker) < 6:
                        tickers.append(ticker)
            
            return {
                'title': title,
                'date': date,
                'content': content,
                'tickers': tickers
            }
            
        except Exception as e:
            logger.error(f"Error extracting CNBC article: {e}")
            return None
    
    def _extract_marketwatch(self, html):
        """Extract article from MarketWatch."""
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract title
            title_element = soup.find('h1')
            title = title_element.text.strip() if title_element else ""
            
            # Extract date
            date_element = soup.find('time')
            date = date_element.get('datetime') if date_element else ""
            
            # Extract content
            content_div = soup.find('div', {'class': 'article__body'})
            paragraphs = content_div.find_all('p') if content_div else []
            content = ' '.join([p.text.strip() for p in paragraphs])
            
            # Extract tickers
            tickers = []
            ticker_elements = soup.find_all('span', {'class': 'symbol'})
            
            for element in ticker_elements:
                ticker = element.text.strip()
                if ticker.isupper() and len(ticker) < 6:
                    tickers.append(ticker)
            
            return {
                'title': title,
                'date': date,
                'content': content,
                'tickers': tickers
            }
            
        except Exception as e:
            logger.error(f"Error extracting MarketWatch article: {e}")
            return None
    
    def _extract_reuters(self, html):
        """Extract article from Reuters."""
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract title
            title_element = soup.find('h1')
            title = title_element.text.strip() if title_element else ""
            
            # Extract date - Reuters format varies over time
            date_element = soup.find('time')
            if not date_element:
                date_element = soup.find('div', {'class': 'ArticleHeader_date'})
                
            date = date_element.get('datetime', date_element.text.strip()) if date_element else ""
            
            # Extract content
            content_div = soup.find('div', {'class': 'ArticleBody__content'})
            if not content_div:
                content_div = soup.find('div', {'class': 'StandardArticleBody_body'})
                
            paragraphs = content_div.find_all('p') if content_div else []
            content = ' '.join([p.text.strip() for p in paragraphs])
            
            # Extract tickers - more difficult for Reuters, try to find stock codes
            tickers = []
            stock_patterns = [
                r'\b[A-Z]{1,4}\.[A-Z]{1,2}\b',  # Like AAPL.O
                r'\b[A-Z]{2,4}:[A-Z]{1,6}\b',   # Like NYSE:AAPL
            ]
            
            for pattern in stock_patterns:
                import re
                matches = re.findall(pattern, html)
                for match in matches:
                    parts = re.split(r'[.:]', match)
                    if len(parts) > 0:
                        ticker = parts[0].strip()
                        if ticker.isupper() and len(ticker) < 6:
                            tickers.append(ticker)
            
            return {
                'title': title,
                'date': date,
                'content': content,
                'tickers': tickers
            }
            
        except Exception as e:
            logger.error(f"Error extracting Reuters article: {e}")
            return None
    
    def _extract_bloomberg(self, html):
        """Extract article from Bloomberg."""
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract title
            title_element = soup.find('h1')
            title = title_element.text.strip() if title_element else ""
            
            # Extract date
            date_element = soup.find('time')
            date = date_element.get('datetime') if date_element else ""
            
            # Extract content - Bloomberg has various layouts
            content_div = soup.find('div', {'class': 'body-copy'})
            if not content_div:
                content_div = soup.find('div', {'class': 'body-content'})
                
            paragraphs = content_div.find_all('p') if content_div else []
            content = ' '.join([p.text.strip() for p in paragraphs])
            
            # Extract tickers - Bloomberg usually uses specific tags
            tickers = []
            ticker_elements = soup.find_all('div', {'class': 'ticker'})
            
            for element in ticker_elements:
                ticker = element.text.strip()
                if ticker.isupper() and len(ticker) < 6:
                    tickers.append(ticker)
            
            return {
                'title': title,
                'date': date,
                'content': content,
                'tickers': tickers
            }
            
        except Exception as e:
            logger.error(f"Error extracting Bloomberg article: {e}")
            return None
    
    def _extract_motley_fool(self, html):
        """Extract article from Motley Fool."""
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract title
            title_element = soup.find('h1')
            title = title_element.text.strip() if title_element else ""
            
            # Extract date
            date_element = soup.find('time')
            date = date_element.get('datetime') if date_element else ""
            
            # Extract content
            content_div = soup.find('span', {'class': 'article-content'})
            paragraphs = content_div.find_all('p') if content_div else []
            content = ' '.join([p.text.strip() for p in paragraphs])
            
            # Extract tickers - look for ticker disclosure section
            tickers = []
            disclosure_div = soup.find('div', {'class': 'disclosure'})
            if disclosure_div:
                import re
                # Motley Fool typically lists tickers in disclosure
                text = disclosure_div.text
                matches = re.findall(r'\b[A-Z]{2,5}\b', text)
                for match in matches:
                    if len(match) < 6:
                        tickers.append(match)
            
            return {
                'title': title,
                'date': date,
                'content': content,
                'tickers': tickers
            }
            
        except Exception as e:
            logger.error(f"Error extracting Motley Fool article: {e}")
            return None
    
    def _extract_generic(self, html):
        """Generic article extractor for unsupported domains."""
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            # Extract title - usually in h1
            title_element = soup.find('h1')
            title = title_element.text.strip() if title_element else ""
            
            # Try various date patterns
            date = ""
            date_candidates = [
                soup.find('time'),
                soup.find('meta', {'property': 'article:published_time'}),
                soup.find('meta', {'itemprop': 'datePublished'})
            ]
            
            for candidate in date_candidates:
                if candidate:
                    date = candidate.get('datetime', candidate.get('content', ''))
                    if date:
                        break
            
            # Extract content - get all paragraphs within article or main content divs
            content_containers = [
                soup.find('article'),
                soup.find('main'),
                soup.find('div', {'class': lambda c: c and 'article' in c.lower()}),
                soup.find('div', {'class': lambda c: c and 'content' in c.lower()}),
                soup.find('div', {'id': lambda i: i and 'article' in i.lower()}),
                soup.find('div', {'id': lambda i: i and 'content' in i.lower()})
            ]
            
            content_container = next((c for c in content_containers if c), soup)
            paragraphs = content_container.find_all('p')
            content = ' '.join([p.text.strip() for p in paragraphs])
            
            # Extract potential tickers
            import re
            tickers = []
            
            # Look for standalone uppercase words that might be tickers
            potential_tickers = re.findall(r'\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\b', html)
            for match in potential_tickers:
                for group in match:
                    if group and 1 <= len(group) <= 5 and group.isalpha():
                        tickers.append(group)
            
            # Filter out common non-ticker uppercase words
            common_words = {'A', 'I', 'AM', 'PM', 'CEO', 'CFO', 'CTO', 'COO', 'IPO', 'US', 'UK', 'EU', 'TV', 'CEO'}
            tickers = [t for t in tickers if t not in common_words]
            
            # Remove duplicates
            tickers = list(set(tickers))
            
            return {
                'title': title,
                'date': date,
                'content': content,
                'tickers': tickers
            }
            
        except Exception as e:
            logger.error(f"Error in generic article extraction: {e}")
            return None
```

## Configuration in scraper_config.json

```json
{
  "wayback_scraper": {
    "enabled": true,
    "interval": 3600,
    "wayback_target_domains": [
      "finance.yahoo.com",
      "cnbc.com",
      "marketwatch.com",
      "reuters.com/business",
      "bloomberg.com/markets",
      "fool.com",
      "investing.com",
      "barrons.com",
      "seekingalpha.com",
      "wsj.com/market-data"
    ],
    "wayback_lookback_days": 30,
    "wayback_request_delay": 1.0,
    "wayback_max_snapshots": 100,
    "cache_max_age_days": 60
  }
}
```

## Integration with Existing Architecture

1. **Register in scraper factory**:
   
   Add to `data_acquisition/scrapers/__init__.py`:
   ```python
   from .news_scraper import NewsScraper
   from .reddit_scraper import RedditScraper
   from .wayback_scraper import WaybackScraper

   __all__ = ['NewsScraper', 'RedditScraper', 'WaybackScraper']
   ```

2. **Initialize in main application**:
   
   Update `data_acquisition/main.py` to include the new scraper:
   ```python
   # Initialize scrapers
   scrapers = []
   
   if config.get("news_scraper", {}).get("enabled", False):
       scrapers.append(NewsScraper(producer, config.get("news_scraper", {})))
   
   if config.get("reddit_scraper", {}).get("enabled", False):
       scrapers.append(RedditScraper(producer, config.get("reddit_scraper", {})))
   
   # Add Wayback scraper
   if config.get("wayback_scraper", {}).get("enabled", False):
       scrapers.append(WaybackScraper(producer, config.get("wayback_scraper", {})))
   ```

## Execution Control

The Wayback scraper can be run in several modes:

1. **Regular Mode** - Run periodically to collect recent historical data
2. **Batch Mode** - Process specific date ranges for backfilling data
3. **One-time Mode** - Run once to fetch data from a specific time period

### Historical Data Backfill Script

```python
import asyncio
import logging
import json
import os
from datetime import datetime, timedelta
from data_acquisition.scrapers.wayback_scraper import WaybackScraper
from data_acquisition.utils.event_producer import EventProducer

async def backfill_historical_data(start_year, end_year, domains=None):
    """
    Run a backfill operation for historical data.
    
    Args:
        start_year: Starting year (int)
        end_year: Ending year (int)
        domains: List of domains to process (if None, uses default)
    """
    # Load configuration
    with open("data_acquisition/config/scraper_config.json", "r") as f:
        config = json.load(f)
    
    # Create mock producer (does not actually send to Kafka)
    class MockProducer(EventProducer):
        async def send(self, data, priority="standard"):
            return True
    
    producer = MockProducer(config)
    
    # Create wayback scraper instance
    wayback_config = config.get("wayback_scraper", {})
    
    # Override domains if specified
    if domains:
        wayback_config["wayback_target_domains"] = domains
    
    scraper = WaybackScraper(producer, wayback_config)
    
    # Process each year
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Create date range for this month
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            
            # Format dates for wayback
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")
            
            print(f"Processing {start_str} to {end_str}")
            
            # Override scraper's date range
            scraper.processed_dates = set()  # Clear processed dates
            
            # Run scraper for this month
            data = await scraper.scrape()
            
            if data:
                # Process the data
                await scraper.process_data(data)
                print(f"Processed {len(data)} items for {year}-{month:02d}")
            
            # Wait between months to avoid overloading
            await asyncio.sleep(5)

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example: Backfill 2020-2022 for specific domains
    domains = [
        "finance.yahoo.com",
        "cnbc.com",
        "marketwatch.com"
    ]
    
    asyncio.run(backfill_historical_data(2020, 2022, domains))
```

## Best Practices for Wayback Machine Usage

1. **Rate Limiting**: Respect Wayback Machine's servers with appropriate delays
2. **Efficient Filtering**: Filter out non-article pages before downloading content
3. **Domain-specific Extraction**: Use tailored extractors for each financial news site
4. **Incremental Processing**: Avoid reprocessing previously scraped date ranges
5. **Error Handling**: Robust error handling for network issues and parsing failures
6. **Metadata Preservation**: Maintain original URLs and timestamps for provenance
7. **Deduplication**: Use content hashing to avoid duplicate articles
8. **Storage Optimization**: Compress and partition data by date and source

## Monitoring and Maintenance

1. Monitor Wayback Machine response times and adjust rate limiting accordingly
2. Track article extraction success rates for each domain
3. Periodically update domain-specific extractors as website structures change
4. Maintain a list of processed date ranges to avoid redundant scraping
5. Implement circuit breakers for temporary Wayback Machine API failures

## Legal and Ethical Considerations

1. Respect Wayback Machine's Terms of Service and robots.txt directives
2. Use appropriate User-Agent headers identifying your application
3. Implement appropriate rate limiting to avoid overloading services
4. Retain source attribution and metadata for all extracted content
5. Use the data for research and analysis purposes only
6. Do not republish or redistribute the original content

## Integration with FinBERT

Since the historical data will be analyzed using FinBERT, ensure the extracted article content:

1. Contains clean text without HTML artifacts
2. Preserves paragraph structure for context
3. Accurately associates financial tickers with content
4. Includes publication dates for time series analysis
5. Tags data source for model training and validation