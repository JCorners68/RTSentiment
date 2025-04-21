import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Set, Union

import redis.asyncio as redis

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client for caching sentiment data."""
    
    def __init__(self, host: str = "localhost", port: int = 6379, password: str = None):
        """
        Initialize Redis client.
        
        Args:
            host (str): Redis host
            port (int): Redis port
            password (str): Redis password
        """
        self.host = host
        self.port = port
        self.password = password
        self.client = None
        self.is_connected = False
    
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
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis.
        
        Args:
            key (str): Redis key
            
        Returns:
            Optional[str]: Value or None if not found
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return None
        
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {str(e)}")
            return None
    
    async def set(self, key: str, value: Union[str, Dict], expire: int = None):
        """
        Set value in Redis.
        
        Args:
            key (str): Redis key
            value (Union[str, Dict]): Value to set
            expire (int): Expiration time in seconds
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return
        
        try:
            # Convert dict to JSON string if needed
            if isinstance(value, dict):
                value = json.dumps(value)
            
            if expire:
                await self.client.setex(key, expire, value)
            else:
                await self.client.set(key, value)
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {str(e)}")
    
    async def delete(self, key: str):
        """
        Delete key from Redis.
        
        Args:
            key (str): Redis key
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return
        
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {str(e)}")
    
    async def sadd(self, key: str, *values):
        """
        Add values to a set.
        
        Args:
            key (str): Redis key
            *values: Values to add
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return
        
        try:
            await self.client.sadd(key, *values)
        except Exception as e:
            logger.error(f"Error adding to set {key} in Redis: {str(e)}")
    
    async def smembers(self, key: str) -> Set[str]:
        """
        Get all members of a set.
        
        Args:
            key (str): Redis key
            
        Returns:
            Set[str]: Set members
        """
        if not self.is_connected:
            logger.warning("Redis not connected")
            return set()
        
        try:
            return await self.client.smembers(key)
        except Exception as e:
            logger.error(f"Error getting members of set {key} from Redis: {str(e)}")
            return set()
    
    async def get_all_tickers(self) -> Set[str]:
        """
        Get all ticker symbols.
        
        Returns:
            Set[str]: Set of ticker symbols
        """
        return await self.smembers("tickers")
    
    async def get_ticker_sentiment(self, ticker: str) -> Dict[str, Any]:
        """
        Get sentiment data for a ticker.
        
        Args:
            ticker (str): Ticker symbol
            
        Returns:
            Dict[str, Any]: Sentiment data
        """
        data = await self.get(f"sentiment:{ticker}")
        if data:
            return json.loads(data)
        return None
    
    async def get_all_sentiments(self) -> Dict[str, Dict[str, Any]]:
        """
        Get sentiment data for all tickers.
        
        Returns:
            Dict[str, Dict[str, Any]]: Sentiment data keyed by ticker
        """
        tickers = await self.get_all_tickers()
        result = {}
        
        for ticker in tickers:
            sentiment = await self.get_ticker_sentiment(ticker)
            if sentiment:
                result[ticker] = sentiment
        
        return result
    
    def get_current_time(self) -> float:
        """
        Get current time in seconds.
        
        Returns:
            float: Current time
        """
        return time.time()