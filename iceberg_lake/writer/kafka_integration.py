"""
Kafka integration for Iceberg writer.

This module provides integration between Kafka consumers and the Iceberg writer,
enabling real-time streaming of sentiment analysis results to the Iceberg data lake.
It includes support for both direct PyIceberg writing and writing via Dremio JDBC.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable

from iceberg_lake.writer.iceberg_writer import IcebergSentimentWriter

logger = logging.getLogger(__name__)


class IcebergKafkaIntegration:
    """
    Integration between Kafka consumers and Iceberg writer.
    
    This class provides a bridge between Kafka consumers and the Iceberg writer,
    enabling real-time streaming of sentiment analysis results to the Iceberg data lake.
    It includes support for all advanced sentiment fields and schema validation.
    """
    
    def __init__(
        self,
        iceberg_writer: IcebergSentimentWriter,
        batch_size: int = 100,
        flush_interval: int = 30,  # seconds
        event_transformer: Optional[Callable] = None
    ):
        """
        Initialize Iceberg Kafka integration.
        
        Args:
            iceberg_writer: Configured Iceberg writer instance
            batch_size: Number of events to batch before writing
            flush_interval: Maximum time (seconds) between writes
            event_transformer: Optional function to transform events before writing
        """
        self.writer = iceberg_writer
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.event_transformer = event_transformer
        self.event_buffer = []
        self.last_flush_time = datetime.utcnow()
        self.flush_task = None
        self.running = False
        
    async def start(self):
        """Start the integration service."""
        if self.running:
            logger.warning("Iceberg Kafka integration already running")
            return
            
        self.running = True
        self.last_flush_time = datetime.utcnow()
        self.flush_task = asyncio.create_task(self._schedule_flush())
        logger.info("Iceberg Kafka integration started")
        
    async def stop(self):
        """Stop the integration service."""
        if not self.running:
            logger.warning("Iceberg Kafka integration not running")
            return
            
        self.running = False
        if self.flush_task:
            self.flush_task.cancel()
            self.flush_task = None
            
        # Flush any remaining events
        await self.flush()
        logger.info("Iceberg Kafka integration stopped")
    
    async def process_event(self, event: Dict[str, Any]) -> bool:
        """
        Process a Kafka event and add it to the batch for writing to Iceberg.
        
        Args:
            event: Kafka event data
            
        Returns:
            bool: True if event was processed and added to batch
        """
        if not self.running:
            logger.warning("Iceberg Kafka integration not running, event ignored")
            return False
        
        try:
            # Transform event if transformer provided
            if self.event_transformer:
                transformed_event = self.event_transformer(event)
            else:
                transformed_event = self._default_transform(event)
            
            # Add to buffer
            self.event_buffer.append(transformed_event)
            
            # Flush if batch size reached
            if len(self.event_buffer) >= self.batch_size:
                asyncio.create_task(self.flush())
                
            return True
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")
            return False
    
    async def flush(self) -> int:
        """
        Flush buffered events to Iceberg.
        
        Returns:
            int: Number of events written
        """
        if not self.event_buffer:
            return 0
            
        # Get events to write
        events_to_write = self.event_buffer.copy()
        self.event_buffer = []
        self.last_flush_time = datetime.utcnow()
        
        try:
            # Write to Iceberg
            num_written = self.writer.write_data(events_to_write)
            logger.info(f"Wrote {num_written} events to Iceberg")
            return num_written
        except Exception as e:
            logger.error(f"Error writing events to Iceberg: {str(e)}")
            # Add back to buffer for retry
            self.event_buffer = events_to_write + self.event_buffer
            return 0
    
    async def _schedule_flush(self):
        """Task to periodically flush events."""
        while self.running:
            try:
                # Sleep until next flush
                await asyncio.sleep(1)  # Check every second
                
                # Check if flush interval exceeded
                if self.event_buffer and (datetime.utcnow() - self.last_flush_time).total_seconds() >= self.flush_interval:
                    await self.flush()
            except asyncio.CancelledError:
                logger.info("Flush task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in scheduled flush: {str(e)}")
    
    def _default_transform(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Default event transformation function.
        
        Args:
            event: Kafka event data
            
        Returns:
            Dict[str, Any]: Transformed event for Iceberg
        """
        # Extract common fields
        event_id = event.get("id", "")
        text = event.get("text", "")
        source = event.get("source", "unknown")
        tickers = event.get("tickers", [])
        timestamp = event.get("timestamp", datetime.utcnow().isoformat())
        
        # Convert timestamp string to datetime if needed
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        # Extract sentiment analysis results if available
        sentiment_result = event.get("sentiment_result", {})
        
        # For different event structures
        if not sentiment_result and "sentiment_score" in event:
            sentiment_result = {
                "sentiment_score": event.get("sentiment_score"),
                "sentiment_label": event.get("sentiment_label", "neutral"),
                "sentiment_magnitude": event.get("sentiment_magnitude", 0.5),
            }
        
        # Handle multiple tickers by creating one record per ticker
        if not tickers:
            # Default record with no ticker
            return self._create_iceberg_record(
                message_id=event_id, 
                event_timestamp=timestamp,
                source_system=source,
                text_content=text,
                sentiment_result=sentiment_result,
                article_title=event.get("title", ""),
                source_url=event.get("url", ""),
                model_name=event.get("model", "")
            )
        else:
            # First ticker is primary
            return self._create_iceberg_record(
                message_id=event_id, 
                event_timestamp=timestamp,
                source_system=source,
                text_content=text,
                sentiment_result=sentiment_result,
                ticker=tickers[0] if tickers else None,
                article_title=event.get("title", ""),
                source_url=event.get("url", ""),
                model_name=event.get("model", "")
            )
    
    def _create_iceberg_record(
        self,
        message_id: str,
        event_timestamp: datetime,
        source_system: str,
        text_content: str,
        sentiment_result: Dict[str, Any],
        ticker: Optional[str] = None,
        article_title: Optional[str] = None,
        source_url: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a record for the Iceberg table.
        
        Args:
            message_id: Unique identifier for the message
            event_timestamp: Timestamp of the event
            source_system: Source system identifier
            text_content: Raw text content
            sentiment_result: Sentiment analysis results
            ticker: Optional stock ticker symbol
            article_title: Optional article title
            source_url: Optional source URL
            model_name: Optional model name/version
            
        Returns:
            Dict[str, Any]: Record for Iceberg table
        """
        # Core sentiment fields with defaults
        sentiment_score = sentiment_result.get("sentiment_score", 0.0)
        sentiment_magnitude = sentiment_result.get("sentiment_magnitude", 0.5)
        primary_emotion = sentiment_result.get("primary_emotion", "neutral")
        
        # Advanced sentiment fields
        emotion_intensity = sentiment_result.get("emotion_intensity_vector", {})
        if isinstance(emotion_intensity, list) and all(isinstance(item, dict) for item in emotion_intensity):
            # Convert list of dicts to a single dict
            emotion_intensity = {item["emotion"]: item["intensity"] for item in emotion_intensity if "emotion" in item and "intensity" in item}
        
        # Create record with all required fields
        return {
            "message_id": message_id,
            "event_timestamp": event_timestamp,
            "ingestion_timestamp": datetime.utcnow(),
            "source_system": source_system,
            "text_content": text_content,
            
            # Core sentiment fields
            "sentiment_score": sentiment_score,
            "sentiment_magnitude": sentiment_magnitude,
            "primary_emotion": primary_emotion,
            
            # Advanced sentiment fields
            "emotion_intensity_vector": emotion_intensity,
            "aspect_target_identification": sentiment_result.get("aspect_target_identification", []),
            "aspect_based_sentiment": sentiment_result.get("aspect_based_sentiment", {}),
            "sarcasm_detection": sentiment_result.get("sarcasm_detection", False),
            "subjectivity_score": sentiment_result.get("subjectivity_score", 0.5),
            "toxicity_score": sentiment_result.get("toxicity_score", 0.0),
            
            # Entity recognition
            "entity_recognition": sentiment_result.get("entity_recognition", []),
            
            # Intent and influence
            "user_intent": sentiment_result.get("user_intent", "information_seeking"),
            "influence_score": sentiment_result.get("influence_score", None),
            
            # Metadata
            "processing_version": sentiment_result.get("processing_version", "1.0.0"),
            
            # Financial context
            "ticker": ticker,
            "article_title": article_title,
            "source_url": source_url,
            "model_name": model_name
        }

def create_kafka_integration(writer_type="auto", config=None, **kwargs):
    """
    Factory function to create the appropriate Kafka integration.
    
    This function creates either a direct IcebergKafkaIntegration or a 
    DremioKafkaIntegration based on configuration and the specified writer type.
    
    Args:
        writer_type: Type of writer to use ("auto", "pyiceberg", or "dremio")
        config: Optional configuration (uses default if not provided)
        **kwargs: Additional arguments to pass to the integration constructor
        
    Returns:
        An integration instance (IcebergKafkaIntegration or DremioKafkaIntegration)
    """
    from iceberg_lake.utils.config import IcebergConfig
    from iceberg_lake.writer.writer_factory import WriterFactory
    
    # Load configuration
    config = config or IcebergConfig()
    
    # Create writer using factory
    factory = WriterFactory(config)
    writer = factory.create_writer(writer_type)
    
    # Determine integration type based on writer type
    if hasattr(writer, 'jdbc_url'):  # Check if it's a DremioJdbcWriter
        from iceberg_lake.writer.dremio_kafka_integration import DremioKafkaIntegration
        return DremioKafkaIntegration(writer, **kwargs)
    else:
        return IcebergKafkaIntegration(writer, **kwargs)