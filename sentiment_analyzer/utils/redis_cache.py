"""
Redis cache utility for storing sentiment data
"""
import logging
import json
import redis
from datetime import datetime

logger = logging.getLogger(__name__)

class RedisCache:
    """
    Redis cache for storing sentiment data and analysis results
    """
    def __init__(self, config):
        """
        Initialize Redis connection
        
        Args:
            config: Configuration dictionary with Redis settings
        """
        self.host = config.get('redis_host', 'localhost')
        self.port = config.get('redis_port', 6379)
        self.db = config.get('redis_db', 0)
        self.event_expiry = config.get('event_expiry', 604800)  # 7 days in seconds
        
        self.redis = None
        self._connect()
        
    def _connect(self):
        """
        Establish connection to Redis
        """
        try:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True  # Automatically decode responses to strings
            )
            logger.info(f"Connected to Redis at {self.host}:{self.port}/{self.db}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis = None
            
    def _ensure_connection(self):
        """
        Ensure Redis connection is active, reconnect if needed
        
        Returns:
            True if connected, False otherwise
        """
        if self.redis is None:
            self._connect()
            
        try:
            self.redis.ping()
            return True
        except:
            logger.warning("Redis connection lost, attempting to reconnect")
            self._connect()
            return self.redis is not None
            
    def store_event(self, event_id, event_data):
        """
        Store a sentiment event in Redis
        
        Args:
            event_id: Unique event identifier
            event_data: Dictionary with event data
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not self._ensure_connection():
            return False
            
        try:
            # Convert event data to JSON string
            event_json = json.dumps(event_data)
            
            # Store in Redis with expiration
            key = f"event:{event_id}"
            self.redis.set(key, event_json, ex=self.event_expiry)
            
            # Add to events sorted set by timestamp
            timestamp = event_data.get('timestamp')
            if timestamp:
                # Convert timestamp to Unix timestamp if string
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.timestamp()
                    
                self.redis.zadd('events:timeline', {event_id: timestamp})
                
            # Add to ticker-specific sets if applicable
            ticker = event_data.get('ticker')
            if ticker:
                self.redis.sadd(f"events:ticker:{ticker}", event_id)
                
            logger.debug(f"Stored event {event_id} in Redis")
            return True
        except Exception as e:
            logger.error(f"Failed to store event {event_id}: {e}")
            return False
            
    def get_event(self, event_id):
        """
        Retrieve a sentiment event from Redis
        
        Args:
            event_id: Event identifier
            
        Returns:
            Event data dictionary or None if not found
        """
        if not self._ensure_connection():
            return None
            
        try:
            key = f"event:{event_id}"
            event_json = self.redis.get(key)
            
            if event_json:
                return json.loads(event_json)
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve event {event_id}: {e}")
            return None
            
    def store_ticker_sentiment(self, ticker, sentiment_data):
        """
        Store ticker sentiment data in Redis
        
        Args:
            ticker: Ticker symbol
            sentiment_data: Dictionary with sentiment metrics
            
        Returns:
            True if stored successfully, False otherwise
        """
        if not self._ensure_connection():
            return False
            
        try:
            # Convert sentiment data to JSON string
            sentiment_json = json.dumps(sentiment_data)
            
            # Store in Redis
            key = f"sentiment:ticker:{ticker}"
            self.redis.set(key, sentiment_json)
            
            # Add to tickers set
            self.redis.sadd("tickers", ticker)
            
            # Store score in sorted set for quick ranking
            score = sentiment_data.get('avg_sentiment', 0)
            self.redis.zadd('sentiment:scores', {ticker: score})
            
            # Store update timestamp
            now = datetime.now().isoformat()
            self.redis.hset('sentiment:last_updated', ticker, now)
            
            logger.debug(f"Stored sentiment for ticker {ticker} in Redis")
            return True
        except Exception as e:
            logger.error(f"Failed to store sentiment for ticker {ticker}: {e}")
            return False
            
    def get_ticker_sentiment(self, ticker):
        """
        Retrieve ticker sentiment data from Redis
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Sentiment data dictionary or None if not found
        """
        if not self._ensure_connection():
            return None
            
        try:
            key = f"sentiment:ticker:{ticker}"
            sentiment_json = self.redis.get(key)
            
            if sentiment_json:
                return json.loads(sentiment_json)
            else:
                return None
        except Exception as e:
            logger.error(f"Failed to retrieve sentiment for ticker {ticker}: {e}")
            return None
            
    def get_top_tickers(self, n=10, by_sentiment=True):
        """
        Get top N tickers by sentiment or volatility
        
        Args:
            n: Number of tickers to return
            by_sentiment: If True, sort by sentiment score, else by volatility
            
        Returns:
            List of (ticker, score) tuples
        """
        if not self._ensure_connection():
            return []
            
        try:
            # Get from sorted set
            key = 'sentiment:scores' if by_sentiment else 'sentiment:volatility'
            # Get highest scores (with scores, in descending order)
            results = self.redis.zrevrange(key, 0, n-1, withscores=True)
            return [(ticker, score) for ticker, score in results]
        except Exception as e:
            logger.error(f"Failed to retrieve top tickers: {e}")
            return []