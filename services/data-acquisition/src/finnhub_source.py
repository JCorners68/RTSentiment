"""
Finnhub Data Source Module

This module provides the FinnhubDataSource class which connects to the Finnhub API and 
Iceberg tables to fetch and store company news, sentiment data, and earnings data.
"""

import os
import sys
import time
import json
import asyncio
import logging
import datetime
from typing import Dict, List, Optional, Any, Union, Set, Tuple
import uuid
from functools import wraps

import httpx
import finnhub
import pandas as pd
import redis
from pyiceberg.catalog import Catalog
from pyiceberg.expressions import And, Equal
from pyiceberg.table import Table

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config
from src.iceberg_setup import get_iceberg_catalog, get_table, generate_uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Type aliases
SentimentRecord = Dict[str, Any]
MarketEvent = Dict[str, Any]


class RateLimiter:
    """
    Rate limiter for API calls.
    
    Ensures API rate limits are respected by tracking the number of requests made
    within a time period and delaying requests when necessary.
    """
    
    def __init__(self, requests_per_minute: int):
        """
        Initialize the rate limiter.
        
        Args:
            requests_per_minute: Maximum number of requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.interval = 60.0 / requests_per_minute  # Time between requests
        self.last_request_time = 0.0
        self.request_count = 0
        self.window_start_time = time.time()
    
    async def wait(self) -> None:
        """
        Wait if necessary to respect the rate limit.
        """
        current_time = time.time()
        
        # Reset counter if window has passed
        if current_time - self.window_start_time >= 60.0:
            self.request_count = 0
            self.window_start_time = current_time
        
        # If we've made too many requests, wait until the next window
        if self.request_count >= self.requests_per_minute:
            wait_time = 60.0 - (current_time - self.window_start_time)
            if wait_time > 0:
                logger.debug(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                current_time = time.time()
                self.window_start_time = current_time
                self.request_count = 0
        
        # Calculate time to wait between requests to distribute them evenly
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.interval and self.last_request_time > 0:
            wait_time = self.interval - time_since_last
            if wait_time > 0:
                logger.debug(f"Throttling request, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
        self.request_count += 1


def cache_result(ttl: int = 3600):
    """
    Decorator to cache function results in Redis if enabled.
    
    Args:
        ttl: Time-to-live for cache entries in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        async def wrapped(self, *args, **kwargs):
            # Skip caching if redis is not enabled
            if not self.use_redis_cache or not self.redis_client:
                return await func(self, *args, **kwargs)
            
            # Create cache key based on function name and arguments
            key_parts = [func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
            cache_key = f"finnhub:{':'.join(key_parts)}"
            
            # Try to get from cache
            cached_result = self.redis_client.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for {cache_key}")
                return json.loads(cached_result)
            
            # Call the original function
            result = await func(self, *args, **kwargs)
            
            # Store in cache
            try:
                self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(result)
                )
                logger.debug(f"Stored in cache: {cache_key}")
            except Exception as e:
                logger.warning(f"Failed to cache result: {e}")
            
            return result
        
        return wrapped
    
    return decorator


class FinnhubDataSource:
    """
    FinnhubDataSource class for fetching data from Finnhub API and storing in Iceberg tables.
    
    This class provides methods to fetch company news, sentiment data, and earnings data
    from Finnhub, and write them to Iceberg tables. It includes rate limiting, error handling,
    and optional Redis caching.
    """
    
    def __init__(self):
        """
        Initialize the FinnhubDataSource with configuration settings.
        """
        # Load configuration
        self.config = get_config()
        
        # API key and client
        self.api_key = self.config["api_keys"]["finnhub"]
        self.client = finnhub.Client(api_key=self.api_key)
        self.async_client = httpx.AsyncClient(
            base_url="https://finnhub.io/api/v1",
            params={"token": self.api_key},
            timeout=30.0
        )
        
        # Rate limiting
        self.rate_limiter = RateLimiter(self.config["rate_limits"]["finnhub"])
        
        # Redis caching
        self.use_redis_cache = self.config["features"]["use_redis_cache"]
        self.redis_client = None
        if self.use_redis_cache:
            try:
                self.redis_client = redis.Redis(
                    host=self.config["redis"]["host"],
                    port=self.config["redis"]["port"],
                    db=self.config["redis"]["db"],
                    decode_responses=True
                )
                logger.info("Redis caching enabled")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self.redis_client = None
                self.use_redis_cache = False
        
        # Iceberg tables
        self.use_iceberg = self.config["features"]["use_iceberg_backend"]
        self.sentiment_table = None
        self.market_events_table = None
        if self.use_iceberg:
            try:
                self._initialize_iceberg_tables()
                logger.info("Iceberg backend enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Iceberg tables: {e}")
                self.use_iceberg = False
        
        # Stock tickers from config
        self.tickers = self.config["data_sources"]["sp500_tickers"]
        
        logger.info("FinnhubDataSource initialized")
    
    def _initialize_iceberg_tables(self) -> None:
        """
        Initialize Iceberg tables for storing data.
        """
        try:
            self.sentiment_table = get_table("sentiment_records")
            self.market_events_table = get_table("market_events")
            
            if not self.sentiment_table or not self.market_events_table:
                logger.warning("Iceberg tables not found, initializing...")
                catalog = get_iceberg_catalog()
                
                # Check and create tables if needed
                if not self.sentiment_table:
                    from src.iceberg_setup import create_sentiment_records_table
                    create_sentiment_records_table(catalog)
                    self.sentiment_table = get_table("sentiment_records")
                
                if not self.market_events_table:
                    from src.iceberg_setup import create_market_events_table
                    create_market_events_table(catalog)
                    self.market_events_table = get_table("market_events")
            
            logger.info("Iceberg tables initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Iceberg tables: {e}")
            raise
    
    async def close(self) -> None:
        """
        Close connections and resources.
        """
        if self.async_client:
            await self.async_client.aclose()
        
        if self.redis_client:
            self.redis_client.close()
        
        logger.info("FinnhubDataSource closed")
    
    async def _handle_api_error(
        self, 
        response: httpx.Response, 
        ticker: str, 
        endpoint: str
    ) -> None:
        """
        Handle API error responses.
        
        Args:
            response: The HTTP response
            ticker: The ticker symbol for the request
            endpoint: The API endpoint that was called
        """
        error_msg = f"Finnhub API error for {ticker} on {endpoint}: "
        
        try:
            error_data = response.json()
            error_msg += f"{error_data.get('error', str(response.status_code))}"
        except Exception:
            error_msg += f"Status {response.status_code}"
        
        if response.status_code == 429:
            error_msg += " (Rate limit exceeded)"
            # Exponential backoff for rate limiting
            logger.warning(error_msg)
            await asyncio.sleep(5)
        elif response.status_code in (500, 502, 503, 504):
            error_msg += " (Server error)"
            logger.warning(error_msg)
            await asyncio.sleep(2)
        else:
            logger.error(error_msg)
    
    @cache_result(ttl=3600)  # Cache for 1 hour
    async def get_company_news(
        self, 
        ticker: str, 
        from_date: Optional[str] = None, 
        to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch company news from Finnhub.
        
        Args:
            ticker: Stock ticker symbol
            from_date: Start date in YYYY-MM-DD format
            to_date: End date in YYYY-MM-DD format
            
        Returns:
            List of news items
        """
        # Set default date range if not provided
        if not from_date:
            from_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        
        if not to_date:
            to_date = datetime.datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Fetching news for {ticker} from {from_date} to {to_date}")
        
        # Wait for rate limiter
        await self.rate_limiter.wait()
        
        try:
            # Make API request
            response = await self.async_client.get(
                "/company-news",
                params={
                    "symbol": ticker,
                    "from": from_date,
                    "to": to_date
                }
            )
            
            if response.status_code != 200:
                await self._handle_api_error(response, ticker, "company-news")
                return []
            
            news_data = response.json()
            logger.info(f"Retrieved {len(news_data)} news items for {ticker}")
            
            # Ensure all news items have required fields
            validated_news = []
            for item in news_data:
                if all(k in item for k in ["datetime", "headline", "summary", "url", "source"]):
                    # Convert timestamp to ISO format
                    if "datetime" in item and isinstance(item["datetime"], int):
                        item["datetime"] = datetime.datetime.fromtimestamp(
                            item["datetime"]
                        ).isoformat()
                    
                    # Add ticker to each news item
                    item["ticker"] = ticker
                    validated_news.append(item)
            
            return validated_news
        
        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {e}")
            return []
    
    @cache_result(ttl=3600 * 24)  # Cache for 24 hours
    async def get_company_earnings(
        self, 
        ticker: str, 
        limit: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Fetch company earnings data from Finnhub.
        
        Args:
            ticker: Stock ticker symbol
            limit: Number of past quarters to fetch
            
        Returns:
            List of earnings reports
        """
        logger.info(f"Fetching earnings for {ticker}, limit: {limit}")
        
        # Wait for rate limiter
        await self.rate_limiter.wait()
        
        try:
            # Make API request
            response = await self.async_client.get(
                "/stock/earnings",
                params={
                    "symbol": ticker,
                    "limit": limit
                }
            )
            
            if response.status_code != 200:
                await self._handle_api_error(response, ticker, "stock/earnings")
                return []
            
            earnings_data = response.json()
            
            # Flatten the response structure
            flattened_data = []
            if earnings_data and "earningsCalendar" in earnings_data:
                for item in earnings_data["earningsCalendar"]:
                    # Add ticker to each earnings item
                    item["ticker"] = ticker
                    
                    # Convert dates to ISO format if necessary
                    if "date" in item and item["date"]:
                        try:
                            date_obj = datetime.datetime.strptime(item["date"], "%Y-%m-%d")
                            item["timestamp"] = date_obj.isoformat()
                        except ValueError:
                            item["timestamp"] = item["date"]
                    
                    flattened_data.append(item)
            
            logger.info(f"Retrieved {len(flattened_data)} earnings reports for {ticker}")
            return flattened_data
        
        except Exception as e:
            logger.error(f"Error fetching earnings for {ticker}: {e}")
            return []
    
    @cache_result(ttl=3600 * 12)  # Cache for 12 hours
    async def get_sentiment_data(
        self, 
        ticker: str
    ) -> Dict[str, Any]:
        """
        Fetch sentiment data from Finnhub.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Sentiment data for the ticker
        """
        logger.info(f"Fetching sentiment data for {ticker}")
        
        # Wait for rate limiter
        await self.rate_limiter.wait()
        
        try:
            # Make API request
            response = await self.async_client.get(
                "/news-sentiment",
                params={
                    "symbol": ticker
                }
            )
            
            if response.status_code != 200:
                await self._handle_api_error(response, ticker, "news-sentiment")
                return {}
            
            sentiment_data = response.json()
            
            # Add timestamp and ticker to sentiment data
            sentiment_data["timestamp"] = datetime.datetime.now().isoformat()
            sentiment_data["ticker"] = ticker
            
            logger.info(f"Retrieved sentiment data for {ticker}")
            return sentiment_data
        
        except Exception as e:
            logger.error(f"Error fetching sentiment for {ticker}: {e}")
            return {}
    
    async def write_to_sentiment_records(
        self, 
        records: List[SentimentRecord]
    ) -> bool:
        """
        Write sentiment records to the Iceberg table.
        
        Args:
            records: List of sentiment records to write
            
        Returns:
            Success status
        """
        if not self.use_iceberg or not self.sentiment_table:
            logger.warning("Iceberg backend not enabled or table not available")
            return False
        
        if not records:
            logger.info("No sentiment records to write")
            return True
        
        try:
            logger.info(f"Writing {len(records)} sentiment records to Iceberg")
            
            # Convert records to DataFrames for efficient writing
            df_records = []
            
            for record in records:
                # Ensure required fields
                if not all(k in record for k in ["ticker", "text"]):
                    logger.warning(f"Skipping record missing required fields: {record}")
                    continue
                
                # Generate UUID if not present
                if "id" not in record:
                    record["id"] = str(generate_uuid())
                
                # Ensure timestamp is present
                if "timestamp" not in record:
                    record["timestamp"] = datetime.datetime.now().isoformat()
                
                # Convert string timestamp to datetime if needed
                if isinstance(record["timestamp"], str):
                    record["timestamp"] = datetime.datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))
                
                # Ensure metadata is a dict
                if "metadata" not in record or not record["metadata"]:
                    record["metadata"] = {}
                
                # Prepare record for DataFrame
                df_record = {
                    "id": uuid.UUID(record["id"]) if isinstance(record["id"], str) else record["id"],
                    "ticker": record["ticker"],
                    "timestamp": record["timestamp"],
                    "source": record.get("source", "finnhub"),
                    "text": record["text"],
                    "sentiment_score": record.get("sentiment_score"),
                    "sentiment_label": record.get("sentiment_label"),
                    "metadata": record["metadata"]
                }
                
                df_records.append(df_record)
            
            if not df_records:
                logger.warning("No valid records to write after filtering")
                return False
            
            # Create DataFrame from records
            df = pd.DataFrame(df_records)
            
            # Write to table
            with self.sentiment_table.newAppend() as append:
                append.writeDF(df)
                append.commit()
            
            logger.info(f"Successfully wrote {len(df_records)} sentiment records to Iceberg")
            return True
        
        except Exception as e:
            logger.error(f"Error writing sentiment records to Iceberg: {e}")
            return False
    
    async def write_to_market_events(
        self, 
        events: List[MarketEvent]
    ) -> bool:
        """
        Write market events to the Iceberg table.
        
        Args:
            events: List of market events to write
            
        Returns:
            Success status
        """
        if not self.use_iceberg or not self.market_events_table:
            logger.warning("Iceberg backend not enabled or table not available")
            return False
        
        if not events:
            logger.info("No market events to write")
            return True
        
        try:
            logger.info(f"Writing {len(events)} market events to Iceberg")
            
            # Convert events to DataFrames for efficient writing
            df_events = []
            
            for event in events:
                # Ensure required fields
                required_fields = ["ticker", "title", "event_type"]
                if not all(k in event for k in required_fields):
                    logger.warning(f"Skipping event missing required fields: {event}")
                    continue
                
                # Generate UUID if not present
                if "id" not in event:
                    event["id"] = str(generate_uuid())
                
                # Ensure timestamp is present
                if "timestamp" not in event:
                    event["timestamp"] = datetime.datetime.now().isoformat()
                
                # Convert string timestamp to datetime if needed
                if isinstance(event["timestamp"], str):
                    event["timestamp"] = datetime.datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                
                # Ensure metadata is a dict
                if "metadata" not in event or not event["metadata"]:
                    event["metadata"] = {}
                
                # Prepare event for DataFrame
                df_event = {
                    "id": uuid.UUID(event["id"]) if isinstance(event["id"], str) else event["id"],
                    "ticker": event["ticker"],
                    "timestamp": event["timestamp"],
                    "event_type": event["event_type"],
                    "title": event["title"],
                    "summary": event.get("summary", ""),
                    "url": event.get("url", ""),
                    "source": event.get("source", "finnhub"),
                    "metadata": event["metadata"]
                }
                
                df_events.append(df_event)
            
            if not df_events:
                logger.warning("No valid events to write after filtering")
                return False
            
            # Create DataFrame from events
            df = pd.DataFrame(df_events)
            
            # Write to table
            with self.market_events_table.newAppend() as append:
                append.writeDF(df)
                append.commit()
            
            logger.info(f"Successfully wrote {len(df_events)} market events to Iceberg")
            return True
        
        except Exception as e:
            logger.error(f"Error writing market events to Iceberg: {e}")
            return False
    
    async def process_news_to_events(
        self, 
        news_items: List[Dict[str, Any]]
    ) -> List[MarketEvent]:
        """
        Process news items into market events.
        
        Args:
            news_items: List of news items from Finnhub
            
        Returns:
            List of market events ready for storage
        """
        events = []
        
        for item in news_items:
            # Skip items without required fields
            if not all(k in item for k in ["headline", "datetime", "ticker"]):
                continue
            
            # Create event record
            event = {
                "id": str(generate_uuid()),
                "ticker": item["ticker"],
                "timestamp": item["datetime"] if isinstance(item["datetime"], datetime.datetime) else 
                             datetime.datetime.fromtimestamp(item["datetime"]) if isinstance(item["datetime"], int) else
                             datetime.datetime.fromisoformat(item["datetime"]) if isinstance(item["datetime"], str) else
                             datetime.datetime.now(),
                "event_type": "news",
                "title": item["headline"],
                "summary": item.get("summary", ""),
                "url": item.get("url", ""),
                "source": item.get("source", "finnhub"),
                "metadata": {
                    "category": item.get("category", ""),
                    "related": item.get("related", ""),
                    "image": item.get("image", ""),
                }
            }
            
            events.append(event)
        
        logger.info(f"Processed {len(events)} news items into market events")
        return events
    
    async def process_earnings_to_events(
        self, 
        earnings_items: List[Dict[str, Any]]
    ) -> List[MarketEvent]:
        """
        Process earnings items into market events.
        
        Args:
            earnings_items: List of earnings items from Finnhub
            
        Returns:
            List of market events ready for storage
        """
        events = []
        
        for item in earnings_items:
            # Skip items without required fields
            if not all(k in item for k in ["date", "ticker"]):
                continue
            
            # Construct title and summary
            actual = item.get("actual", "N/A")
            estimate = item.get("estimate", "N/A")
            
            title = f"{item['ticker']} Earnings Report"
            summary = f"EPS Actual: {actual}, Estimate: {estimate}"
            if "surprise" in item and item["surprise"] is not None:
                summary += f", Surprise: {item['surprise']}"
            
            # Create event record
            event = {
                "id": str(generate_uuid()),
                "ticker": item["ticker"],
                "timestamp": datetime.datetime.strptime(item["date"], "%Y-%m-%d") if isinstance(item["date"], str) else item.get("timestamp", datetime.datetime.now()),
                "event_type": "earnings",
                "title": title,
                "summary": summary,
                "url": "",  # Finnhub doesn't provide URLs for earnings
                "source": "finnhub",
                "metadata": {
                    "quarter": item.get("quarter", ""),
                    "year": item.get("year", ""),
                    "actual": str(actual),
                    "estimate": str(estimate),
                    "surprise": str(item.get("surprise", "")),
                    "surprise_percent": str(item.get("surprisePercent", "")),
                }
            }
            
            events.append(event)
        
        logger.info(f"Processed {len(events)} earnings items into market events")
        return events
    
    async def process_sentiment_to_records(
        self, 
        sentiment_data: Dict[str, Any]
    ) -> List[SentimentRecord]:
        """
        Process sentiment data into sentiment records.
        
        Args:
            sentiment_data: Sentiment data from Finnhub
            
        Returns:
            List of sentiment records ready for storage
        """
        records = []
        
        # Skip if data is missing required fields
        if not sentiment_data or "ticker" not in sentiment_data:
            return records
        
        ticker = sentiment_data["ticker"]
        timestamp = sentiment_data.get("timestamp", datetime.datetime.now().isoformat())
        
        # Process buzz sentiment
        if "buzz" in sentiment_data:
            buzz_record = {
                "id": str(generate_uuid()),
                "ticker": ticker,
                "timestamp": timestamp,
                "source": "finnhub_buzz",
                "text": f"Buzz score for {ticker}",
                "sentiment_score": sentiment_data["buzz"].get("buzz", 0),
                "sentiment_label": "neutral",
                "metadata": {
                    "buzz_articles_in_last_week": str(sentiment_data["buzz"].get("articlesInLastWeek", 0)),
                    "buzz_weekly_average": str(sentiment_data["buzz"].get("weeklyAverage", 0)),
                    "data_type": "buzz"
                }
            }
            records.append(buzz_record)
        
        # Process company news sentiment
        if "companyNewsScore" in sentiment_data:
            news_record = {
                "id": str(generate_uuid()),
                "ticker": ticker,
                "timestamp": timestamp,
                "source": "finnhub_news",
                "text": f"News sentiment for {ticker}",
                "sentiment_score": sentiment_data.get("companyNewsScore", 0),
                "sentiment_label": self._get_sentiment_label(sentiment_data.get("companyNewsScore", 0)),
                "metadata": {
                    "data_type": "news_sentiment"
                }
            }
            records.append(news_record)
        
        # Process sector sentiment
        if "sectorAverageNewsScore" in sentiment_data:
            sector_record = {
                "id": str(generate_uuid()),
                "ticker": ticker,
                "timestamp": timestamp,
                "source": "finnhub_sector",
                "text": f"Sector sentiment for {ticker}",
                "sentiment_score": sentiment_data.get("sectorAverageNewsScore", 0),
                "sentiment_label": self._get_sentiment_label(sentiment_data.get("sectorAverageNewsScore", 0)),
                "metadata": {
                    "sector": sentiment_data.get("sector", "unknown"),
                    "data_type": "sector_sentiment"
                }
            }
            records.append(sector_record)
        
        logger.info(f"Processed sentiment data into {len(records)} sentiment records for {ticker}")
        return records
    
    def _get_sentiment_label(self, score: float) -> str:
        """
        Convert a sentiment score to a label.
        
        Args:
            score: Sentiment score from 0 to 1
            
        Returns:
            Sentiment label (very_negative, negative, neutral, positive, very_positive)
        """
        if score <= 0.2:
            return "very_negative"
        elif score <= 0.4:
            return "negative"
        elif score <= 0.6:
            return "neutral"
        elif score <= 0.8:
            return "positive"
        else:
            return "very_positive"
    
    async def collect_data_for_ticker(
        self, 
        ticker: str, 
        historical_days: int = 7
    ) -> Tuple[bool, Dict[str, int]]:
        """
        Collect and store all data for a single ticker.
        
        Args:
            ticker: Stock ticker symbol
            historical_days: Number of historical days to collect
            
        Returns:
            Tuple of (success status, counts dictionary)
        """
        logger.info(f"Collecting data for ticker: {ticker}, historical days: {historical_days}")
        
        # Calculate date range
        to_date = datetime.datetime.now()
        from_date = to_date - datetime.timedelta(days=historical_days)
        
        from_date_str = from_date.strftime("%Y-%m-%d")
        to_date_str = to_date.strftime("%Y-%m-%d")
        
        # Track counts
        counts = {
            "news_items": 0,
            "sentiment_records": 0,
            "earnings_items": 0,
            "market_events": 0
        }
        
        try:
            # Fetch company news
            news_items = await self.get_company_news(
                ticker=ticker,
                from_date=from_date_str,
                to_date=to_date_str
            )
            counts["news_items"] = len(news_items)
            
            # Process news to market events
            news_events = await self.process_news_to_events(news_items)
            
            # Fetch earnings data
            earnings_items = await self.get_company_earnings(ticker=ticker)
            counts["earnings_items"] = len(earnings_items)
            
            # Process earnings to market events
            earnings_events = await self.process_earnings_to_events(earnings_items)
            
            # Combine all market events
            market_events = news_events + earnings_events
            counts["market_events"] = len(market_events)
            
            # Write market events to Iceberg
            if market_events:
                await self.write_to_market_events(market_events)
            
            # Fetch sentiment data
            sentiment_data = await self.get_sentiment_data(ticker=ticker)
            
            # Process sentiment to records
            sentiment_records = await self.process_sentiment_to_records(sentiment_data)
            counts["sentiment_records"] = len(sentiment_records)
            
            # Write sentiment records to Iceberg
            if sentiment_records:
                await self.write_to_sentiment_records(sentiment_records)
            
            logger.info(f"Successfully collected data for {ticker}: {counts}")
            return True, counts
        
        except Exception as e:
            logger.error(f"Error collecting data for {ticker}: {e}")
            return False, counts
    
    async def batch_collect_historical_data(
        self, 
        tickers: Optional[List[str]] = None,
        days: int = 30,
        batch_size: int = 5
    ) -> Dict[str, Any]:
        """
        Collect historical data for multiple tickers in batches.
        
        Args:
            tickers: List of ticker symbols (defaults to config tickers)
            days: Number of historical days to collect
            batch_size: Size of ticker batches to process concurrently
            
        Returns:
            Dictionary with collection stats
        """
        if not tickers:
            tickers = self.tickers
        
        logger.info(f"Starting batch collection for {len(tickers)} tickers, {days} days of history")
        
        results = {
            "success_count": 0,
            "failure_count": 0,
            "total_tickers": len(tickers),
            "total_news": 0,
            "total_sentiment_records": 0,
            "total_earnings": 0,
            "total_market_events": 0
        }
        
        # Process in batches to control concurrency
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}/{(len(tickers) + batch_size - 1)//batch_size}: {batch}")
            
            # Process batch concurrently
            tasks = [self.collect_data_for_ticker(ticker, days) for ticker in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Analyze batch results
            for j, (ticker, result) in enumerate(zip(batch, batch_results)):
                if isinstance(result, Exception):
                    logger.error(f"Failed to process {ticker}: {result}")
                    results["failure_count"] += 1
                else:
                    success, counts = result
                    if success:
                        results["success_count"] += 1
                        results["total_news"] += counts["news_items"]
                        results["total_sentiment_records"] += counts["sentiment_records"]
                        results["total_earnings"] += counts["earnings_items"]
                        results["total_market_events"] += counts["market_events"]
                    else:
                        results["failure_count"] += 1
            
            # Pause between batches to avoid overwhelming rate limits
            if i + batch_size < len(tickers):
                await asyncio.sleep(1)
        
        logger.info(f"Batch collection completed: {results}")
        return results
    
    async def real_time_update(
        self, 
        tickers: Optional[List[str]] = None,
        lookback_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Perform a real-time update for the specified tickers.
        
        Args:
            tickers: List of ticker symbols (defaults to config tickers)
            lookback_hours: Hours to look back for news and events
            
        Returns:
            Dictionary with update stats
        """
        if not tickers:
            tickers = self.tickers
        
        logger.info(f"Starting real-time update for {len(tickers)} tickers")
        
        # Convert lookback hours to days (at least 1)
        days = max(1, lookback_hours // 24)
        
        # Use the batch collect method with a shorter timeframe
        results = await self.batch_collect_historical_data(
            tickers=tickers,
            days=days,
            batch_size=10  # Larger batch size for real-time updates
        )
        
        logger.info(f"Real-time update completed: {results}")
        return results
    
    async def search_company(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for companies using Finnhub symbol lookup.
        
        Args:
            query: Search query
            
        Returns:
            List of company results
        """
        logger.info(f"Searching for companies with query: {query}")
        
        # Wait for rate limiter
        await self.rate_limiter.wait()
        
        try:
            # Make API request
            response = await self.async_client.get(
                "/search",
                params={
                    "q": query
                }
            )
            
            if response.status_code != 200:
                await self._handle_api_error(response, query, "search")
                return []
            
            search_data = response.json()
            
            # Extract and format results
            results = []
            if search_data and "result" in search_data:
                for item in search_data["result"]:
                    results.append({
                        "symbol": item.get("symbol", ""),
                        "description": item.get("description", ""),
                        "type": item.get("type", ""),
                        "primary_exchange": item.get("primaryExchange", "")
                    })
            
            logger.info(f"Search returned {len(results)} results for '{query}'")
            return results
        
        except Exception as e:
            logger.error(f"Error searching for '{query}': {e}")
            return []


async def main():
    """
    Main function to demonstrate the FinnhubDataSource.
    """
    # Initialize data source
    finnhub_source = FinnhubDataSource()
    
    try:
        # Get configuration
        config = get_config()
        tickers = config["data_sources"]["sp500_tickers"][:3]  # Use first 3 tickers for demo
        
        print(f"Demonstrating FinnhubDataSource with tickers: {tickers}")
        
        # Fetch and process recent news for tickers
        for ticker in tickers:
            print(f"\nCollecting data for {ticker}...")
            success, counts = await finnhub_source.collect_data_for_ticker(ticker, historical_days=1)
            
            if success:
                print(f"  Successfully collected {counts} for {ticker}")
            else:
                print(f"  Failed to collect data for {ticker}")
        
        print("\nDemonstration complete!")
    
    finally:
        # Clean up resources
        await finnhub_source.close()


if __name__ == "__main__":
    asyncio.run(main())