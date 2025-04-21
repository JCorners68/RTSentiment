import logging
from typing import Dict, Any

from models.model_factory import ModelType
try:
    from .base_consumer import BaseConsumer
except ImportError:
    from event_consumers.base_consumer import BaseConsumer
from utils.cache import RedisClient

logger = logging.getLogger(__name__)

class HighPriorityConsumer(BaseConsumer):
    """Consumer for high-priority events."""
    
    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        sentiment_model,
        redis_client: RedisClient,
    ):
        super().__init__(
            bootstrap_servers=bootstrap_servers,
            topic=topic,
            group_id=group_id,
            redis_client=redis_client,
            default_model_type=ModelType.FINBERT,  # Use FinBERT as default
        )
        logger.info("High Priority Consumer initialized")
    
    async def process_message(self, message):
        """
        Process a high-priority event message.
        
        Args:
            message: Kafka message
        """
        try:
            event = message.value
            event_id = event.get("id", "unknown")
            logger.debug(f"Processing high-priority event: {event_id}")
            
            # Extract relevant data
            event_type = event.get("type", "unknown")
            source = event.get("source", "unknown")
            weight = event.get("weight", 1.0)
            tickers = event.get("tickers", [])
            text = event.get("text", "")
            
            if not text or not tickers:
                logger.warning("Event missing text or tickers, skipping")
                return
            
            # Select appropriate model based on event characteristics
            model_type = await self.select_model_for_event(event)
            logger.info(f"Selected model {model_type.name} for event {event_id}")
            
            # Analyze sentiment
            sentiment_results = await self.analyze_sentiment([text], model_type=model_type)
            if not sentiment_results:
                logger.warning("Failed to analyze sentiment, skipping")
                return
            
            sentiment_result = sentiment_results[0]
            sentiment_score = sentiment_result["sentiment_score"]
            
            # Apply source-based weight adjustment
            adjusted_weight = self._adjust_weight(weight, source, event_type)
            
            # Update sentiment for each ticker
            for ticker in tickers:
                await self.update_redis_cache(ticker, sentiment_score, adjusted_weight, model_type)
            
            # Store the processed event for auditing
            await self._store_processed_event(event, sentiment_result, adjusted_weight, model_type)
            
            logger.debug(
                f"Processed high-priority event: id={event_id}, model={model_type.name}, " 
                f"score={sentiment_score:.4f}, weight={adjusted_weight:.2f}, tickers={tickers}"
            )
        except Exception as e:
            logger.error(f"Error processing high-priority event: {str(e)}")
            raise
    
    def _adjust_weight(self, base_weight: float, source: str, event_type: str) -> float:
        """
        Adjust weight based on source and event type.
        
        Args:
            base_weight (float): Base weight from event
            source (str): Source of the event
            event_type (str): Type of event
            
        Returns:
            float: Adjusted weight
        """
        # Apply source-based multipliers
        source_multipliers = {
            "bloomberg": 1.5,
            "reuters": 1.4,
            "wsj": 1.3,
            "ft": 1.3,
            "cnbc": 1.2,
            "twitter": 0.8,
            "reddit": 0.6,
        }
        
        # Apply event type multipliers
        type_multipliers = {
            "earnings_report": 1.5,
            "breaking_news": 1.4,
            "press_release": 1.2,
            "analyst_rating": 1.3,
            "social_media": 0.7,
            "financial_filing": 1.4,
            "executive_change": 1.3,
            "merger_acquisition": 1.5,
        }
        
        # Calculate final weight
        source_mult = source_multipliers.get(source.lower(), 1.0)
        type_mult = type_multipliers.get(event_type.lower(), 1.0)
        
        return base_weight * source_mult * type_mult
    
    async def _store_processed_event(
        self, 
        event: Dict[str, Any], 
        sentiment_result: Dict[str, Any],
        adjusted_weight: float,
        model_type: ModelType
    ):
        """
        Store processed event for auditing.
        
        Args:
            event (Dict[str, Any]): Original event
            sentiment_result (Dict[str, Any]): Sentiment analysis result
            adjusted_weight (float): Adjusted weight
            model_type (ModelType): Model type used for analysis
        """
        # Create a record of the processed event
        processed_event = {
            "event_id": event.get("id"),
            "event_type": event.get("type"),
            "source": event.get("source"),
            "tickers": event.get("tickers"),
            "original_weight": event.get("weight"),
            "adjusted_weight": adjusted_weight,
            "sentiment_score": sentiment_result.get("sentiment_score"),
            "sentiment_label": sentiment_result.get("sentiment_label"),
            "model_used": model_type.name,
            "premium_tier": event.get("premium_tier", "standard"),
            "timestamp": event.get("timestamp"),
            "processed_at": round(self.redis_client.get_current_time()),
        }
        
        # Store in Redis with TTL (e.g., keep for 24 hours)
        event_id = event.get("id", f"unknown-{processed_event['processed_at']}")
        await self.redis_client.set(
            f"processed:hipri:{event_id}", 
            processed_event,
            expire=86400  # 24 hours
        )