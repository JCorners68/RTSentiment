import redis
import json
import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)

class RedisSentimentCache:
    """Manages Redis caching for sentiment data."""
    
    def __init__(self, host='localhost', port=6379, db=0, 
                 event_expiry_seconds=604800):  # 7 days default
        """
        Initialize Redis connection and configure settings.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            event_expiry_seconds: Time in seconds before events expire
        """
        self.redis_client = redis.Redis(host=host, port=port, db=db)
        self.event_expiry = event_expiry_seconds
        
        # Key prefixes
        self.score_prefix = "sentiment:score:"
        self.events_prefix = "sentiment:events:"
        
    def _serialize_event(self, event: Dict[str, Any]) -> str:
        """
        Serialize an event for storage in Redis.
        
        Args:
            event: Event data dictionary
            
        Returns:
            JSON string representation
        """
        # Make a copy to avoid modifying the original
        event_copy = event.copy()
        
        # Convert datetime objects to ISO format strings
        if 'timestamp' in event_copy and isinstance(event_copy['timestamp'], datetime.datetime):
            event_copy['timestamp'] = event_copy['timestamp'].isoformat()
            
        return json.dumps(event_copy)
        
    def _deserialize_event(self, event_json: str) -> Dict[str, Any]:
        """
        Deserialize an event from Redis storage.
        
        Args:
            event_json: JSON string
            
        Returns:
            Event data dictionary
        """
        event = json.loads(event_json)
        
        # Convert ISO format strings back to datetime objects
        if 'timestamp' in event and isinstance(event['timestamp'], str):
            try:
                event['timestamp'] = datetime.datetime.fromisoformat(event['timestamp'])
            except ValueError:
                logger.warning(f"Could not parse timestamp: {event['timestamp']}")
                
        return event
        
    def add_ticker_event(self, ticker: str, event: Dict[str, Any]) -> None:
        """
        Add a sentiment event for a ticker to Redis.
        
        Args:
            ticker: Ticker symbol
            event: Sentiment event data
        """
        # Create a Redis sorted set key for this ticker's events
        events_key = f"{self.events_prefix}{ticker.upper()}"
        
        # Use the timestamp as score for the sorted set
        if isinstance(event.get('timestamp'), datetime.datetime):
            timestamp = event['timestamp'].timestamp()
        else:
            timestamp = datetime.datetime.now().timestamp()
            
        # Add to sorted set
        event_json = self._serialize_event(event)
        self.redis_client.zadd(events_key, {event_json: timestamp})
        
        # Set expiry on the key if it's new
        self.redis_client.expire(events_key, self.event_expiry)
        
    def get_ticker_events(self, ticker: str, 
                          max_age: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all sentiment events for a ticker.
        
        Args:
            ticker: Ticker symbol
            max_age: Maximum age in seconds to include
            
        Returns:
            List of sentiment events sorted by timestamp
        """
        events_key = f"{self.events_prefix}{ticker.upper()}"
        
        # If max_age specified, only get events newer than that
        if max_age is not None:
            min_timestamp = datetime.datetime.now().timestamp() - max_age
            event_jsons = self.redis_client.zrangebyscore(events_key, min_timestamp, float('inf'))
        else:
            event_jsons = self.redis_client.zrange(events_key, 0, -1)
            
        # Deserialize events
        events = [self._deserialize_event(event_json.decode('utf-8')) 
                 for event_json in event_jsons]
                 
        return events
        
    def update_ticker_score(self, ticker: str, score: float) -> None:
        """
        Update the current sentiment score for a ticker.
        
        Args:
            ticker: Ticker symbol
            score: Current sentiment score
        """
        score_key = f"{self.score_prefix}{ticker.upper()}"
        self.redis_client.set(score_key, str(score))
        
    def get_ticker_score(self, ticker: str) -> Optional[float]:
        """
        Get the current sentiment score for a ticker.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            Current sentiment score or None if not available
        """
        score_key = f"{self.score_prefix}{ticker.upper()}"
        score_str = self.redis_client.get(score_key)
        
        if score_str is not None:
            try:
                return float(score_str)
            except ValueError:
                logger.error(f"Invalid score value in Redis: {score_str}")
                
        return None
        
    def get_all_ticker_scores(self) -> Dict[str, float]:
        """
        Get sentiment scores for all tracked tickers.
        
        Returns:
            Dictionary mapping ticker symbols to sentiment scores
        """
        # Get all score keys
        keys = self.redis_client.keys(f"{self.score_prefix}*")
        
        scores = {}
        for key in keys:
            ticker = key.decode('utf-8').replace(self.score_prefix, '')
            score_str = self.redis_client.get(key)
            
            if score_str is not None:
                try:
                    scores[ticker] = float(score_str)
                except ValueError:
                    logger.error(f"Invalid score for {ticker}: {score_str}")
                    
        return scores