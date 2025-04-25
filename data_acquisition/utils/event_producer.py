"""
Kafka producer for sending events to the message queue.
"""
import logging
import json
import uuid
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from aiokafka import AIOKafkaProducer

logger = logging.getLogger(__name__)

class EventProducer:
    """
    Producer for sending events to Kafka.
    
    This class handles serializing and routing events to the appropriate
    Kafka topics based on their priority.
    """
    
    def __init__(
            self, 
            bootstrap_servers: str = "localhost:29092",  # Use the external port exposed by docker-compose
            high_priority_topic: str = "sentiment-events-high",
            standard_priority_topic: str = "sentiment-events-standard"
        ):
        """
        Initialize the event producer.
        
        Args:
            bootstrap_servers: Kafka bootstrap servers
            high_priority_topic: Topic for high priority events
            standard_priority_topic: Topic for standard priority events
        """
        self.bootstrap_servers = bootstrap_servers
        self.high_priority_topic = high_priority_topic
        self.standard_priority_topic = standard_priority_topic
        self.producer = None
        self.connected = False
        self._connect_task = None
        
        # Start connection attempt
        self._connect_task = asyncio.create_task(self._connect())
        
        logger.info(f"EventProducer initialized. High priority topic: {high_priority_topic}, Standard priority topic: {standard_priority_topic}")
    
    async def _connect(self):
        """Connect to Kafka and create the producer."""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8')
            )
            await self.producer.start()
            self.connected = True
            logger.info("Connected to Kafka")
        except Exception as e:
            logger.error(f"Failed to connect to Kafka: {e}", exc_info=True)
            self.connected = False
            # Schedule reconnection attempt
            asyncio.create_task(self._reconnect())
    
    async def _reconnect(self, delay: int = 5):
        """Attempt to reconnect to Kafka after a delay."""
        await asyncio.sleep(delay)
        logger.info(f"Attempting to reconnect to Kafka")
        await self._connect()
    
    async def send(self, event: Dict[str, Any], priority: str = "standard") -> bool:
        """
        Send an event to the appropriate topic.
        
        Args:
            event: Event data to send
            priority: Priority level ("high" or "standard")
            
        Returns:
            bool: True if sent successfully, False otherwise
        """
        # Wait for connection if needed
        if not self.connected:
            if self._connect_task and not self._connect_task.done():
                try:
                    await asyncio.wait_for(self._connect_task, timeout=5.0)
                except asyncio.TimeoutError:
                    logger.warning("Timed out waiting for Kafka connection")
                    return False
                except Exception as e:
                    logger.error(f"Error while waiting for Kafka connection: {e}")
                    return False
            
            # If still not connected, return False
            if not self.connected:
                logger.warning("Not connected to Kafka, cannot send event")
                return False
        
        # Prepare the message data
        if not isinstance(event, dict):
            logger.error(f"Event must be a dictionary, got {type(event)}")
            return False
        
        # Add unique event ID if not present
        if "event_id" not in event:
            event["event_id"] = str(uuid.uuid4())
        
        # Add timestamp if not present
        if "timestamp" not in event:
            event["timestamp"] = datetime.utcnow().isoformat()
        
        # Determine topic based on priority
        topic = self.high_priority_topic if priority.lower() == "high" else self.standard_priority_topic
        
        # Send to Kafka
        try:
            await self.producer.send_and_wait(
                topic=topic,
                value=event,
                key=event.get("event_id", str(uuid.uuid4()))
            )
            logger.debug(f"Sent event to {topic}: {event.get('title', '')}")
            return True
        except Exception as e:
            logger.error(f"Failed to send event to Kafka: {e}", exc_info=True)
            # If there was a connection error, attempt to reconnect
            if "connection" in str(e).lower():
                self.connected = False
                asyncio.create_task(self._reconnect())
            return False
    
    async def close(self):
        """Close the producer connection."""
        if self.producer:
            await self.producer.stop()
        self.connected = False
        logger.info("EventProducer closed")