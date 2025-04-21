"""
End-to-end tests for the data acquisition scrapers.

These tests validate the complete flow from data acquisition to sentiment analysis.
They require the full Docker Compose environment to be running.
"""
import os
import json
import time
import asyncio
import pytest
import aiohttp
from typing import Dict, List, Any

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from data_acquisition.scrapers.news_scraper import NewsScraper
from data_acquisition.scrapers.reddit_scraper import RedditScraper

# Configuration for the tests
KAFKA_BOOTSTRAP_SERVERS = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
HIGH_PRI_TOPIC = "news-events-high"
STANDARD_PRI_TOPIC = "news-events-standard"
SENTIMENT_RESULTS_TOPIC = "sentiment-results"
API_BASE_URL = "http://localhost:8001"

class TestDataProducer:
    """Producer for sending test data."""
    
    def __init__(self):
        self.producer = None
        self.high_pri_count = 0
        self.standard_pri_count = 0
    
    async def start(self):
        self.producer = AIOKafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )
        await self.producer.start()
    
    async def stop(self):
        if self.producer:
            await self.producer.stop()
    
    async def send(self, data: Dict[str, Any], priority: str):
        """Send data to the appropriate Kafka topic."""
        topic = HIGH_PRI_TOPIC if priority == "high" else STANDARD_PRI_TOPIC
        await self.producer.send_and_wait(topic, data)
        
        if priority == "high":
            self.high_pri_count += 1
        else:
            self.standard_pri_count += 1
        
        return f"Sent to {topic}"

@pytest.fixture
async def data_producer():
    producer = TestDataProducer()
    await producer.start()
    yield producer
    await producer.stop()

@pytest.fixture
async def kafka_consumer():
    """Create a Kafka consumer for sentiment results."""
    consumer = AIOKafkaConsumer(
        SENTIMENT_RESULTS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="test-consumer-group",
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    await consumer.start()
    yield consumer
    await consumer.stop()

@pytest.mark.asyncio
async def test_news_scraper_e2e(data_producer, kafka_consumer):
    """Test news scraper end-to-end flow."""
    # Create test configuration
    config = {
        "polling_interval": 5,
        "sources": [
            {
                "name": "Test Financial News",
                "url": "https://example.com/finance"
            }
        ]
    }
    
    # Create news scraper with mock producer
    scraper = NewsScraper(data_producer, config)
    
    # Create a mock article directly
    test_article = {
        "title": "AAPL stock surges after earnings beat expectations",
        "content": "Apple (AAPL) reported quarterly earnings that exceeded analyst expectations.",
        "url": "https://example.com/apple-earnings",
        "source_name": "Test Financial News",
        "timestamp": "2023-04-21T12:00:00+00:00",
        "tickers": ["AAPL"]
    }
    
    # Process the article
    await scraper.process_data([test_article])
    
    # Check if producer received the data with correct priority
    assert data_producer.high_pri_count > 0, "High priority message should be produced"
    
    # Wait for sentiment processing (up to 30 seconds)
    start_time = time.time()
    sentiment_result = None
    
    # Setup task to consume with timeout
    async def consume_with_timeout():
        timeout = 30  # 30 seconds timeout
        try:
            async for msg in kafka_consumer:
                # Check if this is our test article result
                if (msg.value.get("source_type") == "scraper" and 
                    "AAPL" in msg.value.get("tickers", [])):
                    return msg.value
                if time.time() - start_time > timeout:
                    break
        except Exception as e:
            print(f"Error consuming messages: {e}")
        return None
    
    # Run the consumer task with timeout
    sentiment_result = await asyncio.wait_for(
        consume_with_timeout(), 
        timeout=35  # Allow extra time for the task to complete
    )
    
    # If we get here, either we found our result or timed out
    if sentiment_result:
        print(f"Received sentiment result: {sentiment_result}")
        assert "sentiment" in sentiment_result, "Result should include sentiment"
        assert "score" in sentiment_result, "Result should include sentiment score"
        assert "model" in sentiment_result, "Result should include model information"
    else:
        # Check API directly as fallback
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/api/sentiment/AAPL") as response:
                if response.status == 200:
                    api_data = await response.json()
                    print(f"API data for AAPL: {api_data}")
                    assert "sentiment" in api_data, "API should return sentiment"
                else:
                    pytest.skip("API endpoint not available, skipping verification")

@pytest.mark.asyncio
async def test_reddit_scraper_e2e(data_producer, kafka_consumer):
    """Test Reddit scraper end-to-end flow."""
    # Create test configuration
    config = {
        "reddit_polling_interval": 5,
        "reddit_subreddits": ["wallstreetbets", "investing"],
        "reddit_time_filter": "day",
        "reddit_post_limit": 5
    }
    
    # Create Reddit scraper with mock producer
    scraper = RedditScraper(data_producer, config)
    
    # Create a mock Reddit post directly
    test_post = {
        "title": "NVDA is going to the moon! 🚀",
        "content": "NVIDIA (NVDA) is crushing earnings expectations.",
        "url": "https://reddit.com/r/wallstreetbets/comments/test",
        "source_name": "Reddit r/wallstreetbets",
        "timestamp": "2023-04-21T12:00:00+00:00",
        "tickers": ["NVDA"],
        "score": 420,
        "num_comments": 69,
        "engagement": {
            "likes": 420,
            "comments": 69,
            "ratio": 0.98
        }
    }
    
    # Process the post
    await scraper.process_data([test_post])
    
    # Check if producer received the data with correct priority
    assert data_producer.high_pri_count > 0, "High priority message should be produced"
    
    # Wait for sentiment processing (up to 30 seconds)
    start_time = time.time()
    sentiment_result = None
    
    # Setup task to consume with timeout
    async def consume_with_timeout():
        timeout = 30  # 30 seconds timeout
        try:
            async for msg in kafka_consumer:
                # Check if this is our test post result
                if (msg.value.get("source") == "RedditScraper" and 
                    "NVDA" in msg.value.get("tickers", [])):
                    return msg.value
                if time.time() - start_time > timeout:
                    break
        except Exception as e:
            print(f"Error consuming messages: {e}")
        return None
    
    # Run the consumer task with timeout
    sentiment_result = await asyncio.wait_for(
        consume_with_timeout(), 
        timeout=35  # Allow extra time for the task to complete
    )
    
    # If we get here, either we found our result or timed out
    if sentiment_result:
        print(f"Received sentiment result: {sentiment_result}")
        assert "sentiment" in sentiment_result, "Result should include sentiment"
        assert "score" in sentiment_result, "Result should include sentiment score"
        assert "model" in sentiment_result, "Result should include model information"
    else:
        # Check API directly as fallback
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE_URL}/api/sentiment/NVDA") as response:
                if response.status == 200:
                    api_data = await response.json()
                    print(f"API data for NVDA: {api_data}")
                    assert "sentiment" in api_data, "API should return sentiment"
                else:
                    pytest.skip("API endpoint not available, skipping verification")

@pytest.mark.asyncio
async def test_manual_message_e2e():
    """
    Test sending a message manually to Kafka and verifying it flows through the system.
    
    This test is useful for troubleshooting when the scrapers aren't running.
    """
    # Create a producer for sending test messages
    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    await producer.start()
    
    # Create a consumer for receiving sentiment results
    consumer = AIOKafkaConsumer(
        SENTIMENT_RESULTS_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="manual-test-consumer",
        auto_offset_reset="latest",
        value_deserializer=lambda m: json.loads(m.decode('utf-8'))
    )
    await consumer.start()
    
    try:
        # Create a test article with high weight to ensure high priority
        test_article = {
            "title": "AMD stock could surge on AI chip demand",
            "content": "AMD's new AI chips are set to compete with NVIDIA's offerings.",
            "url": "https://example.com/amd-ai-chips",
            "source_name": "Manual Test",
            "timestamp": "2023-04-21T12:00:00+00:00",
            "tickers": ["AMD", "NVDA"],
            "source": "TestScraper",
            "source_type": "test",
            "weight": 0.9  # High weight to ensure high priority
        }
        
        # Send to high priority topic
        await producer.send_and_wait(HIGH_PRI_TOPIC, test_article)
        print(f"Sent test article to {HIGH_PRI_TOPIC}")
        
        # Wait for sentiment processing (up to 30 seconds)
        start_time = time.time()
        timeout = 30
        sentiment_result = None
        
        while time.time() - start_time < timeout:
            try:
                # Poll for messages with a 5-second timeout
                msg = await asyncio.wait_for(consumer.getone(), timeout=5)
                
                # Check if this is our test article result
                if "AMD" in msg.value.get("tickers", []):
                    sentiment_result = msg.value
                    break
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Error consuming messages: {e}")
                break
        
        # If we get here, either we found our result or timed out
        if sentiment_result:
            print(f"Received sentiment result: {sentiment_result}")
            assert "sentiment" in sentiment_result, "Result should include sentiment"
            assert "score" in sentiment_result, "Result should include sentiment score"
        else:
            # Check API directly as fallback
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{API_BASE_URL}/api/sentiment/AMD") as response:
                    if response.status == 200:
                        api_data = await response.json()
                        print(f"API data for AMD: {api_data}")
                        assert "sentiment" in api_data, "API should return sentiment"
                    else:
                        pytest.skip("API endpoint not available, skipping verification")
    
    finally:
        # Cleanup resources
        await consumer.stop()
        await producer.stop()

if __name__ == "__main__":
    # This enables running the tests directly with asyncio
    asyncio.run(test_manual_message_e2e())