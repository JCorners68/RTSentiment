import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Union, Tuple

import pyarrow.parquet as pq
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class RedisSentimentCache:
    """Redis cache for sentiment data derived from Parquet files."""
    
    def __init__(
        self, 
        host: str = "localhost", 
        port: int = 6379, 
        password: str = None,
        default_ttl: int = 3600,  # 1 hour default TTL
        ticker_prefix: str = "parquet:sentiment:",
        metadata_prefix: str = "parquet:metadata:",
        batch_size: int = 100
    ):
        """
        Initialize Redis sentiment cache.
        
        Args:
            host (str): Redis host
            port (int): Redis port
            password (str): Redis password
            default_ttl (int): Default TTL for cached items in seconds
            ticker_prefix (str): Prefix for ticker sentiment keys
            metadata_prefix (str): Prefix for metadata keys
            batch_size (int): Default batch size for batch operations
        """
        self.host = host
        self.port = port
        self.password = password
        self.client = None
        self.is_connected = False
        self.default_ttl = default_ttl
        self.ticker_prefix = ticker_prefix
        self.metadata_prefix = metadata_prefix
        self.batch_size = batch_size
        self.parquet_tickers_key = "parquet:tickers"
        self.last_updated_key = "parquet:last_updated"
    
    async def connect(self):
        """Connect to Redis."""
        try:
            logger.info(f"Connecting to Redis at {self.host}:{self.port}...")
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            # Test connection
            await self.client.ping()
            self.is_connected = True
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.is_connected = False
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            logger.info("Closing Redis connection...")
            await self.client.close()
            self.is_connected = False
            logger.info("Redis connection closed")
    
    def _get_ticker_key(self, ticker: str, timestamp: Optional[str] = None) -> str:
        """
        Generate Redis key for ticker sentiment.
        
        Args:
            ticker (str): Ticker symbol
            timestamp (Optional[str]): Optional timestamp for historical data
            
        Returns:
            str: Redis key
        """
        if timestamp:
            return f"{self.ticker_prefix}{ticker}:{timestamp}"
        return f"{self.ticker_prefix}{ticker}"
    
    def _get_metadata_key(self, ticker: str) -> str:
        """
        Generate Redis key for ticker metadata.
        
        Args:
            ticker (str): Ticker symbol
            
        Returns:
            str: Redis key
        """
        return f"{self.metadata_prefix}{ticker}"
    
    async def cache_ticker_sentiment(
        self, 
        ticker: str, 
        sentiment_data: Dict[str, Any], 
        ttl: Optional[int] = None
    ):
        """
        Cache sentiment data for a ticker.
        
        Args:
            ticker (str): Ticker symbol
            sentiment_data (Dict[str, Any]): Sentiment data to cache
            ttl (Optional[int]): TTL in seconds, uses default if None
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return
        
        key = self._get_ticker_key(ticker)
        expire_time = ttl if ttl is not None else self.default_ttl
        
        try:
            # Serialize and store the sentiment data
            await self.client.setex(key, expire_time, json.dumps(sentiment_data))
            
            # Add ticker to the set of available parquet tickers
            await self.client.sadd(self.parquet_tickers_key, ticker)
            
            # Update the last updated timestamp
            await self.client.set(self.last_updated_key, str(time.time()))
            
            logger.debug(f"Cached sentiment data for ticker {ticker}")
        except Exception as e:
            logger.error(f"Error caching sentiment data for ticker {ticker}: {str(e)}")
    
    async def cache_historical_ticker_sentiment(
        self, 
        ticker: str, 
        timestamp: str,
        sentiment_data: Dict[str, Any], 
        ttl: Optional[int] = None
    ):
        """
        Cache historical sentiment data for a ticker at a specific timestamp.
        
        Args:
            ticker (str): Ticker symbol
            timestamp (str): Timestamp for the data point (ISO format)
            sentiment_data (Dict[str, Any]): Sentiment data to cache
            ttl (Optional[int]): TTL in seconds, uses default if None
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return
        
        key = self._get_ticker_key(ticker, timestamp)
        expire_time = ttl if ttl is not None else self.default_ttl
        
        try:
            # Serialize and store the sentiment data
            await self.client.setex(key, expire_time, json.dumps(sentiment_data))
            logger.debug(f"Cached historical sentiment data for ticker {ticker} at {timestamp}")
        except Exception as e:
            logger.error(f"Error caching historical sentiment data for ticker {ticker} at {timestamp}: {str(e)}")
    
    async def cache_ticker_metadata(
        self, 
        ticker: str, 
        metadata: Dict[str, Any], 
        ttl: Optional[int] = None
    ):
        """
        Cache metadata for a ticker.
        
        Args:
            ticker (str): Ticker symbol
            metadata (Dict[str, Any]): Metadata to cache
            ttl (Optional[int]): TTL in seconds, uses default if None
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return
        
        key = self._get_metadata_key(ticker)
        expire_time = ttl if ttl is not None else self.default_ttl
        
        try:
            # Serialize and store the metadata
            await self.client.setex(key, expire_time, json.dumps(metadata))
            logger.debug(f"Cached metadata for ticker {ticker}")
        except Exception as e:
            logger.error(f"Error caching metadata for ticker {ticker}: {str(e)}")
    
    async def get_ticker_sentiment(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get cached sentiment data for a ticker.
        
        Args:
            ticker (str): Ticker symbol
            
        Returns:
            Optional[Dict[str, Any]]: Sentiment data or None if not found
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return None
        
        key = self._get_ticker_key(ticker)
        
        try:
            data = await self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting sentiment data for ticker {ticker}: {str(e)}")
            return None
    
    async def get_historical_ticker_sentiment(
        self, 
        ticker: str, 
        timestamp: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached historical sentiment data for a ticker at a specific timestamp.
        
        Args:
            ticker (str): Ticker symbol
            timestamp (str): Timestamp for the data point (ISO format)
            
        Returns:
            Optional[Dict[str, Any]]: Sentiment data or None if not found
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return None
        
        key = self._get_ticker_key(ticker, timestamp)
        
        try:
            data = await self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting historical sentiment data for ticker {ticker} at {timestamp}: {str(e)}")
            return None
    
    async def get_ticker_metadata(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get cached metadata for a ticker.
        
        Args:
            ticker (str): Ticker symbol
            
        Returns:
            Optional[Dict[str, Any]]: Metadata or None if not found
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return None
        
        key = self._get_metadata_key(ticker)
        
        try:
            data = await self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting metadata for ticker {ticker}: {str(e)}")
            return None
    
    async def get_available_tickers(self) -> Set[str]:
        """
        Get all available tickers from Parquet data.
        
        Returns:
            Set[str]: Set of ticker symbols
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return set()
        
        try:
            return await self.client.smembers(self.parquet_tickers_key)
        except Exception as e:
            logger.error(f"Error getting available tickers: {str(e)}")
            return set()
    
    async def get_last_updated(self) -> Optional[float]:
        """
        Get the timestamp of the last cache update.
        
        Returns:
            Optional[float]: Timestamp or None if not found
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return None
        
        try:
            data = await self.client.get(self.last_updated_key)
            if data:
                return float(data)
            return None
        except Exception as e:
            logger.error(f"Error getting last updated timestamp: {str(e)}")
            return None
    
    async def batch_cache_ticker_sentiments(
        self, 
        ticker_sentiments: Dict[str, Dict[str, Any]], 
        ttl: Optional[int] = None
    ):
        """
        Cache sentiment data for multiple tickers in batch.
        
        Args:
            ticker_sentiments (Dict[str, Dict[str, Any]]): Sentiment data keyed by ticker
            ttl (Optional[int]): TTL in seconds, uses default if None
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return
        
        expire_time = ttl if ttl is not None else self.default_ttl
        pipeline = self.client.pipeline()
        
        try:
            batch_count = 0
            for ticker, sentiment_data in ticker_sentiments.items():
                key = self._get_ticker_key(ticker)
                pipeline.setex(key, expire_time, json.dumps(sentiment_data))
                pipeline.sadd(self.parquet_tickers_key, ticker)
                
                batch_count += 1
                if batch_count >= self.batch_size:
                    await pipeline.execute()
                    pipeline = self.client.pipeline()
                    batch_count = 0
            
            if batch_count > 0:
                await pipeline.execute()
            
            # Update the last updated timestamp
            await self.client.set(self.last_updated_key, str(time.time()))
            
            logger.info(f"Batch cached sentiment data for {len(ticker_sentiments)} tickers")
        except Exception as e:
            logger.error(f"Error batch caching sentiment data: {str(e)}")
    
    async def batch_cache_historical_sentiments(
        self, 
        ticker: str, 
        timestamp_data: Dict[str, Dict[str, Any]], 
        ttl: Optional[int] = None
    ):
        """
        Cache historical sentiment data for a ticker across multiple timestamps.
        
        Args:
            ticker (str): Ticker symbol
            timestamp_data (Dict[str, Dict[str, Any]]): Sentiment data keyed by timestamp
            ttl (Optional[int]): TTL in seconds, uses default if None
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return
        
        expire_time = ttl if ttl is not None else self.default_ttl
        pipeline = self.client.pipeline()
        
        try:
            batch_count = 0
            for timestamp, sentiment_data in timestamp_data.items():
                key = self._get_ticker_key(ticker, timestamp)
                pipeline.setex(key, expire_time, json.dumps(sentiment_data))
                
                batch_count += 1
                if batch_count >= self.batch_size:
                    await pipeline.execute()
                    pipeline = self.client.pipeline()
                    batch_count = 0
            
            if batch_count > 0:
                await pipeline.execute()
            
            logger.info(f"Batch cached historical sentiment data for ticker {ticker} across {len(timestamp_data)} timestamps")
        except Exception as e:
            logger.error(f"Error batch caching historical sentiment data for ticker {ticker}: {str(e)}")
    
    async def delete_ticker_sentiment(self, ticker: str):
        """
        Delete cached sentiment data for a ticker.
        
        Args:
            ticker (str): Ticker symbol
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return
        
        key = self._get_ticker_key(ticker)
        
        try:
            await self.client.delete(key)
            logger.debug(f"Deleted sentiment data for ticker {ticker}")
        except Exception as e:
            logger.error(f"Error deleting sentiment data for ticker {ticker}: {str(e)}")
    
    async def delete_all_ticker_sentiments(self):
        """Delete all cached ticker sentiment data."""
        if not self.is_connected:
            logger.warning("Redis not connected")
            return
        
        try:
            tickers = await self.get_available_tickers()
            pipeline = self.client.pipeline()
            
            for ticker in tickers:
                key = self._get_ticker_key(ticker)
                pipeline.delete(key)
            
            # Delete the set of available tickers
            pipeline.delete(self.parquet_tickers_key)
            
            # Delete the last updated timestamp
            pipeline.delete(self.last_updated_key)
            
            await pipeline.execute()
            logger.info("Deleted all cached ticker sentiment data")
        except Exception as e:
            logger.error(f"Error deleting all ticker sentiment data: {str(e)}")
    
    async def cache_parquet_timerange(
        self, 
        ticker: str, 
        start_date: str, 
        end_date: str, 
        available: bool = True,
        ttl: Optional[int] = None
    ):
        """
        Cache information about available data timerange for a ticker.
        
        Args:
            ticker (str): Ticker symbol
            start_date (str): Start date of available data (ISO format)
            end_date (str): End date of available data (ISO format)
            available (bool): Whether data is available for this timerange
            ttl (Optional[int]): TTL in seconds, uses default if None
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return
        
        key = f"{self.metadata_prefix}{ticker}:timerange:{start_date}:{end_date}"
        expire_time = ttl if ttl is not None else self.default_ttl
        
        try:
            await self.client.setex(key, expire_time, json.dumps({
                "available": available,
                "start_date": start_date,
                "end_date": end_date
            }))
            logger.debug(f"Cached timerange information for ticker {ticker}")
        except Exception as e:
            logger.error(f"Error caching timerange information for ticker {ticker}: {str(e)}")
    
    async def get_parquet_timerange(
        self, 
        ticker: str, 
        start_date: str, 
        end_date: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get cached timerange information for a ticker.
        
        Args:
            ticker (str): Ticker symbol
            start_date (str): Start date (ISO format)
            end_date (str): End date (ISO format)
            
        Returns:
            Optional[Dict[str, Any]]: Timerange information or None if not found
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return None
        
        key = f"{self.metadata_prefix}{ticker}:timerange:{start_date}:{end_date}"
        
        try:
            data = await self.client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Error getting timerange information for ticker {ticker}: {str(e)}")
            return None