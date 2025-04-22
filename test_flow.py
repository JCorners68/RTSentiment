#!/usr/bin/env python
"""
Test script to manually push a test article through the entire data flow pipeline
from scraper to sentiment service.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test article to process
TEST_ARTICLE = {
    "title": "AAPL stock surges after earnings beat expectations",
    "content": "Apple (AAPL) reported quarterly earnings that exceeded analyst expectations, causing the stock to rise 5% in after-hours trading. The company announced record iPhone sales and strong growth in its services business.",
    "url": "https://example.com/apple-earnings",
    "source_name": "Test Financial News",
    "tickers": ["AAPL"],
    "timestamp": "2023-04-21T12:00:00+00:00",
    "weight": 0.8,  # High priority item
    "source": "TestScraper",
    "source_type": "news"
}

async def create_producer():
    bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
    logger.info(f"Connecting to Kafka at {bootstrap_servers}")
    
    producer = AIOKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await producer.start()
    return producer

async def create_consumer(topic):
    bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
    group_id = "test-flow-group"
    
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    await consumer.start()
    return consumer

async def monitor_sentiment_events():
    """
    Monitors the sentiment events topic to see if our test article gets processed.
    """
    logger.info("Starting sentiment events monitor...")
    
    # Sentiment results topic
    topic = "sentiment-results"
    
    consumer = await create_consumer(topic)
    
    try:
        async for msg in consumer:
            result = msg.value
            logger.info(f"Received sentiment result: {result}")
            
            # Check if this result matches our test article
            if (result.get("source") == "TestScraper" and 
                "AAPL" in result.get("tickers", [])):
                
                logger.info("========== Found our test article's sentiment result! ==========")
                logger.info(f"Sentiment: {result.get('sentiment')}")
                logger.info(f"Score: {result.get('score')}")
                logger.info(f"Processing time: {result.get('processing_time_ms')} ms")
                logger.info(f"Model used: {result.get('model')}")
                logger.info("=====================================================")
                return result
            
    except Exception as e:
        logger.error(f"Error monitoring sentiment events: {e}")
    finally:
        await consumer.stop()

async def send_test_article():
    """
    Send a test article to the high-priority news topic
    """
    logger.info("Sending test article to high-priority topic...")
    
    producer = await create_producer()
    
    try:
        # Send to high priority topic since weight is 0.8
        topic = "news-events-high"
        
        await producer.send_and_wait(
            topic,
            TEST_ARTICLE
        )
        
        logger.info(f"Test article sent to topic: {topic}")
    except Exception as e:
        logger.error(f"Error sending test article: {e}")
    finally:
        await producer.stop()

async def main():
    logger.info("Starting test article flow...")
    
    # Start monitoring for sentiment results in background
    monitor_task = asyncio.create_task(monitor_sentiment_events())
    
    # Wait a moment for consumer to connect
    await asyncio.sleep(2)
    
    # Send test article
    await send_test_article()
    
    # Wait for monitor to finish or timeout after 60 seconds
    try:
        await asyncio.wait_for(monitor_task, timeout=60)
        logger.info("Test completed successfully")
    except asyncio.TimeoutError:
        logger.error("Timeout waiting for sentiment result - check if sentiment service is processing events")

if __name__ == "__main__":
    asyncio.run(main())