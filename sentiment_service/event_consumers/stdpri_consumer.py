import json
import logging
from typing import Dict, Any

from utils.cache import RedisClient
from models.model_factory import ModelType
from models.finbert import FinBertModel
from event_consumers.base_consumer import BaseConsumer

logger = logging.getLogger(__name__)

class StandardPriorityConsumer(BaseConsumer):
    """Consumer for standard priority events."""
    
    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        sentiment_model: FinBertModel,
        redis_client: RedisClient,
    ):
        """
        Initialize the standard priority consumer.
        
        Args:
            bootstrap_servers (str): Kafka bootstrap servers
            topic (str): Kafka topic to consume from
            group_id (str): Consumer group 
            sentiment_model (FinBertModel): Sentiment model instance
            redis_client (RedisClient): Redis client instance
        """
        super().__init__(
            bootstrap_servers=bootstrap_servers,
            topic=topic,
            group_id=group_id,
            redis_client=redis_client,
            default_model_type=ModelType.FINBERT,
        )
        self.sentiment_model = sentiment_model
        
        # Batch processing configuration
        self.batch_size = 100
        self.batch_interval = 10  # seconds
    
    async def process_message(self, message):
        """
        Process a standard priority message.
        
        Args:
            message: Kafka message
        
        Returns:
            Dict[str, Any]: Processing result
        """
        try:
            event = message.value
            
            # Log basic event info
            logger.debug(f"Processing standard priority event: {event.get('id', 'unknown')}")
            
            # Extract text and metadata
            text = event.get("text", "")
            ticker = event.get("ticker")
            weight = event.get("weight", 1.0)
            
            if not text or not ticker:
                logger.warning(f"Missing required fields in event: {event.get('id', 'unknown')}")
                return {"status": "error", "reason": "missing_required_fields"}
            
            # Determine which model to use
            model_type = await self.select_model_for_event(event)
            
            # Analyze sentiment
            analysis_result = await self.analyze_sentiment([text], model_type)
            if not analysis_result:
                return {"status": "error", "reason": "analysis_failed"}
            
            # Get the first result
            sentiment_data = analysis_result[0]
            sentiment_score = sentiment_data.get("score", 0.0)
            
            # Update cache with the sentiment score
            await self.update_redis_cache(ticker, sentiment_score, weight, model_type)
            
            # Return result
            return {
                "status": "success",
                "event_id": event.get("id"),
                "ticker": ticker,
                "sentiment_score": sentiment_score,
                "model_used": model_type.name,
            }
            
        except Exception as e:
            logger.error(f"Error processing standard priority event: {str(e)}")
            return {"status": "error", "reason": str(e)}