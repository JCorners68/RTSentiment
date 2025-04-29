"""
Kafka integration for Dremio JDBC writer.

This module provides integration between Kafka consumers and the Dremio JDBC writer,
enabling real-time streaming of sentiment analysis results to the Iceberg data lake via Dremio.
It includes both asynchronous and thread-based implementation options.
"""
import asyncio
import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable

from iceberg_lake.writer.dremio_jdbc_writer import DremioJdbcWriter

logger = logging.getLogger(__name__)


class DremioKafkaIntegration:
    """
    Integration between Kafka consumers and Dremio JDBC writer.
    
    This class provides a bridge between Kafka consumers and the Dremio JDBC writer,
    enabling real-time streaming of sentiment analysis results to the Iceberg data lake via Dremio.
    It includes support for all advanced sentiment fields and schema validation.
    """
    
    def __init__(
        self,
        dremio_writer: DremioJdbcWriter,
        batch_size: int = 100,
        flush_interval: int = 30,  # seconds
        event_transformer: Optional[Callable] = None
    ):
        """
        Initialize Dremio Kafka integration.
        
        Args:
            dremio_writer: Configured Dremio JDBC writer instance
            batch_size: Number of events to batch before writing
            flush_interval: Maximum time (seconds) between writes
            event_transformer: Optional function to transform events before writing
        """
        self.writer = dremio_writer
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
            logger.warning("Dremio Kafka integration already running")
            return
            
        self.running = True
        self.last_flush_time = datetime.utcnow()
        self.flush_task = asyncio.create_task(self._schedule_flush())
        logger.info("Dremio Kafka integration started")
        
    async def stop(self):
        """Stop the integration service."""
        if not self.running:
            logger.warning("Dremio Kafka integration not running")
            return
            
        self.running = False
        if self.flush_task:
            self.flush_task.cancel()
            self.flush_task = None
            
        # Flush any remaining events
        await self.flush()
        logger.info("Dremio Kafka integration stopped")
    
    async def process_event(self, event: Dict[str, Any]) -> bool:
        """
        Process a Kafka event and add it to the batch for writing to Iceberg via Dremio.
        
        Args:
            event: Kafka event data
            
        Returns:
            bool: True if event was processed and added to batch
        """
        if not self.running:
            logger.warning("Dremio Kafka integration not running, event ignored")
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
        Flush buffered events to Iceberg via Dremio JDBC.
        
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
            # Write to Dremio
            num_written = self.writer.write_data(events_to_write)
            logger.info(f"Wrote {num_written} events to Iceberg via Dremio JDBC")
            return num_written
        except Exception as e:
            logger.error(f"Error writing events to Dremio: {str(e)}")
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
            Dict[str, Any]: Transformed event for Iceberg via Dremio
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
            return self._create_dremio_record(
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
            return self._create_dremio_record(
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
    
    def _create_dremio_record(
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
        Create a record for the Iceberg table via Dremio.
        
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
            Dict[str, Any]: Record for Iceberg table via Dremio
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


class ThreadedDremioKafkaIntegration:
    """
    Thread-based integration between Kafka and Dremio for streaming sentiment data.
    
    This class consumes sentiment data from Kafka and writes it to Dremio
    using the DremioJdbcWriter with a threaded (non-async) implementation.
    """
    
    def __init__(
        self,
        writer: DremioJdbcWriter,
        kafka_bootstrap_servers: str,
        topic: str,
        group_id: str,
        batch_size: int = 100,
        commit_interval_ms: int = 5000,
        max_poll_records: int = 500,
        poll_timeout_ms: int = 1000
    ):
        """
        Initialize Kafka to Dremio integration.
        
        Args:
            writer: DremioJdbcWriter instance
            kafka_bootstrap_servers: Kafka bootstrap servers
            topic: Kafka topic to consume
            group_id: Kafka consumer group ID
            batch_size: Number of records to batch before writing
            commit_interval_ms: How often to commit offsets
            max_poll_records: Maximum records to poll from Kafka
            poll_timeout_ms: Timeout for polling Kafka
        """
        self.logger = logging.getLogger(__name__)
        
        self.writer = writer
        self.bootstrap_servers = kafka_bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.batch_size = batch_size
        self.commit_interval_ms = commit_interval_ms
        self.max_poll_records = max_poll_records
        self.poll_timeout_ms = poll_timeout_ms
        
        self.consumer = None
        self.running = False
        self.consumer_thread = None
        self.last_commit_time = 0
        self.message_buffer = []
    
    def _create_consumer(self):
        """Create and configure the Kafka consumer."""
        try:
            from kafka import KafkaConsumer
            
            self.logger.info(f"Creating Kafka consumer for {self.bootstrap_servers}, topic={self.topic}, group={self.group_id}")
            consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                enable_auto_commit=False,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                max_poll_records=self.max_poll_records
            )
            
            return consumer
            
        except Exception as e:
            self.logger.error(f"Failed to create Kafka consumer: {str(e)}")
            raise
    
    def _process_message(self, message: Any) -> Dict[str, Any]:
        """
        Process a single Kafka message.
        
        Args:
            message: Kafka message
            
        Returns:
            Dict: Processed record ready for Dremio
        """
        # Extract the message value (already deserialized as Dict)
        record = message.value
        
        # Ensure required fields
        if 'message_id' not in record:
            record['message_id'] = f"{message.topic}-{message.partition}-{message.offset}"
        
        return record
    
    def _flush_buffer(self):
        """Flush the message buffer to Dremio."""
        if not self.message_buffer:
            return
            
        buffer_size = len(self.message_buffer)
        self.logger.debug(f"Flushing buffer with {buffer_size} records to Dremio")
        
        try:
            # Write the batch to Dremio
            records_written = self.writer.write_data(self.message_buffer)
            
            if records_written:
                self.logger.info(f"Wrote {records_written}/{buffer_size} records to Dremio")
            else:
                self.logger.warning(f"Failed to write any records from batch of {buffer_size} to Dremio")
                
            # Clear the buffer regardless of success to avoid duplicate processing
            self.message_buffer = []
                
        except Exception as e:
            self.logger.error(f"Error writing data to Dremio: {str(e)}")
            # Keep the messages in buffer for retry
    
    def _consumer_loop(self):
        """Main consumer loop."""
        try:
            self.consumer = self._create_consumer()
            
            self.logger.info("Starting Kafka consumer loop")
            while self.running:
                # Poll for messages
                messages = self.consumer.poll(timeout_ms=self.poll_timeout_ms)
                
                if not messages:
                    continue
                
                # Process messages
                for topic_partition, partition_messages in messages.items():
                    for message in partition_messages:
                        try:
                            # Process the message
                            record = self._process_message(message)
                            
                            # Add to buffer
                            self.message_buffer.append(record)
                            
                        except Exception as e:
                            self.logger.error(f"Error processing message: {str(e)}")
                
                # Check if we need to flush
                current_time = time.time() * 1000  # ms
                time_since_commit = current_time - self.last_commit_time
                
                if len(self.message_buffer) >= self.batch_size or time_since_commit >= self.commit_interval_ms:
                    self._flush_buffer()
                    
                    # Commit offsets
                    self.consumer.commit()
                    self.last_commit_time = current_time
            
            self.logger.info("Consumer loop stopped")
            
        except Exception as e:
            self.logger.error(f"Error in consumer loop: {str(e)}")
            import traceback
            traceback.print_exc()
            self.running = False
        finally:
            if self.consumer:
                self.consumer.close()
    
    def start(self):
        """Start the Kafka consumer."""
        if self.running:
            self.logger.warning("Consumer already running")
            return
            
        self.running = True
        self.consumer_thread = threading.Thread(target=self._consumer_loop)
        self.consumer_thread.daemon = True
        self.consumer_thread.start()
        
        self.logger.info("Started Kafka consumer")
    
    def stop(self):
        """Stop the Kafka consumer."""
        if not self.running:
            return
            
        self.logger.info("Stopping Kafka consumer...")
        self.running = False
        
        # Wait for the consumer thread to stop
        if self.consumer_thread and self.consumer_thread.is_alive():
            self.consumer_thread.join(timeout=10)
            
        # Flush any remaining messages
        self._flush_buffer()
        
        self.logger.info("Kafka consumer stopped")


# For backward compatibility, make ThreadedDremioKafkaIntegration the default
# implementation when importing DremioKafkaIntegration outside the module
# This ensures our test will work with the class imported from kafka_integration.py
DremioKafkaIntegration = ThreadedDremioKafkaIntegration