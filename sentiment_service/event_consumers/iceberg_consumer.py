"""
Iceberg integration consumer for sentiment events.

This module extends the base consumer to integrate with the Iceberg lakehouse,
providing ACID-compliant storage of sentiment events in the data lake.
"""
import logging
import asyncio
from typing import Dict, Any, Optional, List

try:
    from .base_consumer import BaseConsumer
except ImportError:
    from event_consumers.base_consumer import BaseConsumer

from utils.cache import RedisClient
from models.model_factory import ModelType

# Import Iceberg writer
import sys
import os
from pathlib import Path

# Ensure iceberg_lake module is in path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from iceberg_lake.writer.iceberg_writer import IcebergSentimentWriter
from iceberg_lake.writer.kafka_integration import IcebergKafkaIntegration
from iceberg_lake.utils.config import IcebergConfig

logger = logging.getLogger(__name__)


class IcebergConsumer(BaseConsumer):
    """
    Consumer for sentiment events with Iceberg integration.
    
    This consumer processes events from Kafka and stores them in the Iceberg
    data lake, providing ACID-compliant storage and advanced schema capabilities.
    """
    
    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        redis_client: RedisClient,
        default_model_type: ModelType = ModelType.FINBERT,
        iceberg_config_path: Optional[str] = None,
        batch_size: int = 100,
        flush_interval: int = 30,  # seconds
    ):
        """
        Initialize Iceberg consumer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            topic: Kafka topic to consume from
            group_id: Consumer group
            redis_client: Redis client instance
            default_model_type: Default model type to use
            iceberg_config_path: Path to Iceberg configuration file
            batch_size: Number of events to batch before writing to Iceberg
            flush_interval: Maximum time (seconds) between writes to Iceberg
        """
        super().__init__(
            bootstrap_servers=bootstrap_servers,
            topic=topic,
            group_id=group_id,
            redis_client=redis_client,
            default_model_type=default_model_type
        )
        
        # Initialize Iceberg integration
        self.iceberg_config = IcebergConfig(iceberg_config_path)
        self.iceberg_writer = None
        self.iceberg_integration = None
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        logger.info(f"Iceberg Consumer initialized for topic {topic}")
    
    async def connect(self):
        """Connect to Kafka and initialize Iceberg integration."""
        # Connect to Kafka first
        connected = await super().connect()
        if not connected:
            return False
        
        # Initialize Iceberg writer
        try:
            self._init_iceberg_writer()
            logger.info("Iceberg writer initialized")
            
            # Initialize integration service
            self.iceberg_integration = IcebergKafkaIntegration(
                iceberg_writer=self.iceberg_writer,
                batch_size=self.batch_size,
                flush_interval=self.flush_interval
            )
            await self.iceberg_integration.start()
            logger.info("Iceberg integration started")
            
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Iceberg integration: {str(e)}")
            return False
    
    def _init_iceberg_writer(self):
        """Initialize the Iceberg writer."""
        catalog_config = self.iceberg_config.get_catalog_config()
        writer_config = self.iceberg_config.get_writer_config()
        
        self.iceberg_writer = IcebergSentimentWriter(
            catalog_uri=catalog_config["uri"],
            warehouse_location=catalog_config["warehouse_location"],
            namespace=catalog_config["namespace"],
            table_name=catalog_config["table_name"],
            max_retries=writer_config.get("max_retries", 3),
            retry_delay=writer_config.get("retry_delay", 1000)
        )
    
    async def stop_consuming(self):
        """Stop consuming events and clean up resources."""
        # Stop Iceberg integration first
        if self.iceberg_integration:
            await self.iceberg_integration.stop()
            logger.info("Iceberg integration stopped")
        
        # Stop Kafka consumer
        await super().stop_consuming()
    
    async def process_message(self, message):
        """
        Process a message from Kafka and store it in Iceberg.
        
        Args:
            message: Kafka message
        """
        try:
            event = message.value
            event_id = event.get("id", "unknown")
            logger.debug(f"Processing event for Iceberg: {event_id}")
            
            # Extract relevant data
            event_type = event.get("type", "unknown")
            source = event.get("source", "unknown")
            weight = event.get("weight", 1.0)
            tickers = event.get("tickers", [])
            text = event.get("text", "")
            
            if not text:
                logger.warning("Event missing text, skipping")
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
            
            # Update Redis cache for real-time access
            for ticker in tickers:
                await self.update_redis_cache(ticker, sentiment_score, adjusted_weight, model_type)
            
            # Prepare event for Iceberg with advanced fields
            enriched_event = self._enrich_event(event, sentiment_result, adjusted_weight, model_type)
            
            # Process with Iceberg integration
            if self.iceberg_integration:
                await self.iceberg_integration.process_event(enriched_event)
            else:
                logger.error("Iceberg integration not initialized")
            
            logger.debug(
                f"Processed event for Iceberg: id={event_id}, model={model_type.name}, "
                f"score={sentiment_score:.4f}, weight={adjusted_weight:.2f}, tickers={tickers}"
            )
        except Exception as e:
            logger.error(f"Error processing event for Iceberg: {str(e)}")
            raise
    
    def _adjust_weight(self, base_weight: float, source: str, event_type: str) -> float:
        """
        Adjust weight based on source and event type.
        
        Args:
            base_weight: Base weight from event
            source: Source of the event
            event_type: Type of event
            
        Returns:
            float: Adjusted weight
        """
        # Source-based multipliers
        source_multipliers = {
            "bloomberg": 1.5,
            "reuters": 1.4,
            "wsj": 1.3,
            "ft": 1.3,
            "cnbc": 1.2,
            "twitter": 0.8,
            "reddit": 0.6,
        }
        
        # Event type multipliers
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
    
    def _enrich_event(
        self, 
        event: Dict[str, Any], 
        sentiment_result: Dict[str, Any],
        adjusted_weight: float,
        model_type: ModelType
    ) -> Dict[str, Any]:
        """
        Enrich event with advanced sentiment fields for Iceberg.
        
        Args:
            event: Original event
            sentiment_result: Sentiment analysis result
            adjusted_weight: Adjusted weight
            model_type: Model type used for analysis
            
        Returns:
            Dict[str, Any]: Enriched event for Iceberg
        """
        # Combine results into enriched event
        enriched_event = {
            # Original event data
            "id": event.get("id"),
            "type": event.get("type"),
            "source": event.get("source"),
            "tickers": event.get("tickers", []),
            "text": event.get("text", ""),
            "title": event.get("title", ""),
            "url": event.get("url", ""),
            "timestamp": event.get("timestamp"),
            
            # Sentiment results
            "sentiment_result": {
                # Basic sentiment fields
                "sentiment_score": sentiment_result.get("sentiment_score"),
                "sentiment_label": sentiment_result.get("sentiment_label"),
                "sentiment_magnitude": adjusted_weight,  # Use adjusted weight as magnitude
                
                # Extract probabilities if available
                "probabilities": sentiment_result.get("probabilities", {}),
                
                # Advanced sentiment fields
                "primary_emotion": self._detect_primary_emotion(sentiment_result),
                "emotion_intensity_vector": self._extract_emotions(sentiment_result),
                "aspect_based_sentiment": self._extract_aspects(event, sentiment_result),
                "sarcasm_detection": self._detect_sarcasm(sentiment_result),
                "subjectivity_score": self._calculate_subjectivity(sentiment_result),
                "toxicity_score": self._calculate_toxicity(sentiment_result),
                
                # Entity extraction
                "entity_recognition": self._extract_entities(event),
                
                # Intent analysis
                "user_intent": self._detect_intent(event, sentiment_result),
                "influence_score": self._calculate_influence(event, adjusted_weight),
                
                # Processing metadata
                "processing_version": "1.0.0",
                "model_name": model_type.name
            }
        }
        
        return enriched_event
    
    def _detect_primary_emotion(self, sentiment_result: Dict[str, Any]) -> str:
        """Detect primary emotion from sentiment result."""
        # Simple mapping based on sentiment score
        score = sentiment_result.get("sentiment_score", 0.0)
        
        if score >= 0.6:
            return "joy"
        elif score >= 0.2:
            return "optimism"
        elif score <= -0.6:
            return "anger"
        elif score <= -0.2:
            return "sadness"
        else:
            return "neutral"
    
    def _extract_emotions(self, sentiment_result: Dict[str, Any]) -> Dict[str, float]:
        """Extract emotion intensity vector from sentiment result."""
        # Default implementation uses sentiment score to infer emotions
        score = sentiment_result.get("sentiment_score", 0.0)
        
        # Create simple emotion vector based on sentiment score
        emotions = {
            "joy": max(0, score * 0.8) if score > 0 else 0,
            "optimism": max(0, score * 0.9) if score > 0 else 0,
            "sadness": max(0, -score * 0.7) if score < 0 else 0,
            "anger": max(0, -score * 0.5) if score < 0 else 0,
            "fear": max(0, -score * 0.3) if score < 0 else 0,
            "neutral": 1.0 - abs(score * 0.7)
        }
        
        return emotions
    
    def _extract_aspects(self, event: Dict[str, Any], sentiment_result: Dict[str, Any]) -> Dict[str, float]:
        """Extract aspect-based sentiment from event and sentiment result."""
        # Default implementation uses tickers as aspects
        aspects = {}
        score = sentiment_result.get("sentiment_score", 0.0)
        
        # Simple approach: use same sentiment for all tickers
        for ticker in event.get("tickers", []):
            aspects[ticker] = score
        
        # Add event type as aspect if available
        if "type" in event:
            aspects[event["type"]] = score
        
        return aspects
    
    def _detect_sarcasm(self, sentiment_result: Dict[str, Any]) -> bool:
        """Detect sarcasm in sentiment result."""
        # Simple heuristic: mixed signals might indicate sarcasm
        # E.g., positive words with negative sentiment or vice versa
        probabilities = sentiment_result.get("probabilities", {})
        
        if not probabilities:
            return False
        
        # Get probabilities of different sentiments
        pos_prob = probabilities.get("positive", 0.0)
        neg_prob = probabilities.get("negative", 0.0)
        neu_prob = probabilities.get("neutral", 0.0)
        
        # Look for conflicting signals
        if (pos_prob > 0.3 and neg_prob > 0.3) or (abs(pos_prob - neg_prob) < 0.1 and pos_prob > 0.25):
            return True
        
        return False
    
    def _calculate_subjectivity(self, sentiment_result: Dict[str, Any]) -> float:
        """Calculate subjectivity score from sentiment result."""
        # Simple heuristic: strength of sentiment indicates subjectivity
        # Neutral sentiment is objective, strong sentiment is subjective
        score = sentiment_result.get("sentiment_score", 0.0)
        
        # Absolute value of sentiment maps to subjectivity (0.0-1.0)
        return min(1.0, abs(score) * 1.5)
    
    def _calculate_toxicity(self, sentiment_result: Dict[str, Any]) -> float:
        """Calculate toxicity score from sentiment result."""
        # Simple heuristic: very negative sentiment might indicate toxicity
        score = sentiment_result.get("sentiment_score", 0.0)
        
        # Only negative sentiment can be toxic
        if score >= 0:
            return 0.0
        
        # Map very negative sentiment to toxicity
        return min(1.0, max(0.0, abs(score) - 0.5) * 2)
    
    def _extract_entities(self, event: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract entities from event."""
        entities = []
        
        # Add tickers as TICKER entities
        for ticker in event.get("tickers", []):
            entities.append({
                "text": ticker,
                "type": "TICKER"
            })
        
        # Add source as SOURCE entity
        if "source" in event:
            entities.append({
                "text": event["source"],
                "type": "SOURCE"
            })
        
        # Add event type as EVENT_TYPE entity
        if "type" in event:
            entities.append({
                "text": event["type"],
                "type": "EVENT_TYPE"
            })
        
        return entities
    
    def _detect_intent(self, event: Dict[str, Any], sentiment_result: Dict[str, Any]) -> str:
        """Detect user intent from event and sentiment result."""
        event_type = event.get("type", "").lower()
        score = sentiment_result.get("sentiment_score", 0.0)
        
        # Map event types to intents
        if event_type in ["earnings_report", "financial_filing"]:
            return "information_sharing"
        elif event_type in ["analyst_rating", "price_target"]:
            return "recommendation"
        elif event_type == "breaking_news":
            return "alerting"
        elif event_type in ["social_media", "tweet", "reddit_post"]:
            if score > 0.5:
                return "promoting"
            elif score < -0.5:
                return "criticizing"
            else:
                return "discussing"
        
        # Default based on sentiment
        if score > 0.5:
            return "positive_sharing"
        elif score < -0.5:
            return "negative_sharing"
        else:
            return "information_seeking"
    
    def _calculate_influence(self, event: Dict[str, Any], weight: float) -> float:
        """Calculate influence score from event and weight."""
        # Influence is based on source credibility and adjusted weight
        source = event.get("source", "unknown").lower()
        
        # Source credibility factors
        source_credibility = {
            "bloomberg": 0.9,
            "reuters": 0.9,
            "wsj": 0.85,
            "ft": 0.85,
            "cnbc": 0.8,
            "seeking_alpha": 0.7,
            "twitter": 0.5,
            "reddit": 0.4
        }
        
        # Base influence on source credibility and weight
        base_influence = source_credibility.get(source, 0.5) * min(1.0, weight / 2)
        
        # Boost for premium sources
        if event.get("premium_tier", False):
            premium_boost = {
                "professional": 0.3,
                "premium": 0.2,
                "standard": 0.1
            }
            base_influence += premium_boost.get(event.get("premium_tier"), 0.0)
        
        return min(1.0, base_influence)


# Factory function to create Iceberg consumer
def create_iceberg_consumer(
    bootstrap_servers: str,
    topic: str,
    group_id: str,
    redis_client: RedisClient,
    iceberg_config_path: Optional[str] = None,
    batch_size: int = 100,
    flush_interval: int = 30
) -> IcebergConsumer:
    """
    Create an Iceberg consumer instance.
    
    Args:
        bootstrap_servers: Kafka bootstrap servers
        topic: Kafka topic to consume from
        group_id: Consumer group
        redis_client: Redis client instance
        iceberg_config_path: Path to Iceberg configuration file
        batch_size: Number of events to batch before writing to Iceberg
        flush_interval: Maximum time (seconds) between writes to Iceberg
        
    Returns:
        IcebergConsumer: Configured Iceberg consumer
    """
    return IcebergConsumer(
        bootstrap_servers=bootstrap_servers,
        topic=topic,
        group_id=group_id,
        redis_client=redis_client,
        default_model_type=ModelType.FINBERT,
        iceberg_config_path=iceberg_config_path,
        batch_size=batch_size,
        flush_interval=flush_interval
    )