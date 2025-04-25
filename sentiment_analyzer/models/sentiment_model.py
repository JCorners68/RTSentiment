import datetime
import numpy as np
from typing import Dict, List, Tuple, Optional, Union

from sentiment_analyzer.models.decay_functions import apply_decay
from sentiment_analyzer.models.impact_scoring import calculate_impact
from sentiment_analyzer.data.redis_manager import RedisSentimentCache


class SentimentModel:
    """Core sentiment model for calculating ticker sentiment scores."""
    
    def __init__(self, redis_cache: RedisSentimentCache, decay_type: str = "exponential", 
                 decay_half_life: int = 24, max_age_hours: int = 168):
        """
        Initialize the sentiment model.
        
        Args:
            redis_cache: Redis cache instance for storing sentiment data
            decay_type: Type of decay function to use ('linear', 'exponential', 'half_life')
            decay_half_life: Half-life parameter for exponential decay (in hours)
            max_age_hours: Maximum age of sentiment data to consider (in hours)
        """
        self.redis_cache = redis_cache
        self.decay_type = decay_type
        self.decay_half_life = decay_half_life
        self.max_age_hours = max_age_hours
        
    def calculate_sentiment_score(self, ticker: str, 
                                 current_time: Optional[datetime.datetime] = None) -> float:
        """
        Calculate the current sentiment score for a ticker by applying decay and impact factors.
        
        Args:
            ticker: Stock ticker symbol
            current_time: Time to calculate sentiment for (default is now)
            
        Returns:
            Normalized sentiment score between -100 and 100
        """
        if current_time is None:
            current_time = datetime.datetime.now()
            
        # Get sentiment events from Redis cache
        events = self.redis_cache.get_ticker_events(ticker)
        
        if not events:
            return 0.0  # Neutral sentiment if no data
            
        # Calculate weighted sentiment scores with decay and impact
        total_weight = 0
        weighted_sentiment = 0
        
        for event in events:
            # Apply time decay
            age_hours = (current_time - event['timestamp']).total_seconds() / 3600
            
            # Skip events older than max age
            if age_hours > self.max_age_hours:
                continue
                
            # Calculate impact factor
            impact = calculate_impact(event)
            
            # Apply decay factor
            decay_factor = apply_decay(age_hours, self.decay_type, self.decay_half_life)
            
            # Calculate weight (impact * decay)
            weight = impact * decay_factor
            
            # Add to weighted sentiment
            weighted_sentiment += event['sentiment'] * weight
            total_weight += weight
            
        # Normalize the final score
        if total_weight > 0:
            normalized_score = weighted_sentiment / total_weight
            # Scale to -100 to 100 range for easier interpretation
            return np.clip(normalized_score * 100, -100, 100)
        else:
            return 0.0
            
    def update_sentiment(self, event: Dict) -> None:
        """
        Process a new sentiment event and update the ticker's sentiment score in Redis.
        
        Args:
            event: Sentiment event with ticker, timestamp, sentiment, and metadata
        """
        # Add the event to Redis cache
        self.redis_cache.add_ticker_event(event['ticker'], event)
        
        # Recalculate and update the current sentiment score
        new_score = self.calculate_sentiment_score(event['ticker'])
        self.redis_cache.update_ticker_score(event['ticker'], new_score)
        
    def get_top_tickers_sentiment(self, tickers: List[str]) -> Dict[str, float]:
        """
        Get current sentiment scores for a list of tickers.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Dictionary of tickers and their sentiment scores
        """
        return {ticker: self.calculate_sentiment_score(ticker) for ticker in tickers}