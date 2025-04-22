#!/usr/bin/env python3
"""
Simple Kafka consumer and producer to test message flow.
"""

import json
import asyncio
import logging
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test-service")

# Configure Kafka
BOOTSTRAP_SERVERS = 'localhost:29092'  
INPUT_TOPIC = 'news-events-high'
OUTPUT_TOPIC = 'sentiment-results'

async def consume_and_produce():
    """
    Consume messages from the input topic, simulate sentiment analysis,
    and produce results to the output topic.
    """
    # Create consumer
    consumer = AIOKafkaConsumer(
        INPUT_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id='test-sentiment-group',
        auto_offset_reset='latest',
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    )
    
    # Create producer
    producer = AIOKafkaProducer(
        bootstrap_servers=BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    )
    
    # Start consumer and producer
    await consumer.start()
    await producer.start()
    
    try:
        logger.info(f"Started test service. Listening on {INPUT_TOPIC}...")
        
        # Process messages
        async for msg in consumer:
            try:
                logger.info(f"Received message: {msg.value}")
                
                # Extract data from the message
                event = msg.value
                
                # Add simulated sentiment analysis results
                result = {
                    "source": event.get("source", "unknown"),
                    "source_type": event.get("source_type", "unknown"),
                    "tickers": event.get("tickers", []),
                    "title": event.get("title", ""),
                    "url": event.get("url", ""),
                    "timestamp": event.get("timestamp", ""),
                    "sentiment": "positive",  # Simulated result
                    "score": 0.85,            # Simulated score
                    "model": "test-model",
                    "processing_time_ms": 42,
                }
                
                # Send the result
                await producer.send_and_wait(OUTPUT_TOPIC, result)
                logger.info(f"Sent result to {OUTPUT_TOPIC}: {result}")
                
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                
    finally:
        # Stop consumer and producer
        await consumer.stop()
        await producer.stop()

async def main():
    """Run the test service."""
    try:
        await consume_and_produce()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())