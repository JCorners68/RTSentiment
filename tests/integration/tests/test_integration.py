import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import patch, AsyncMock, MagicMock

# Import mock classes from the mock_sentiment_service test
from tests.test_mock_sentiment_service import MockFinBertModel, MockRedisClient, MockSentimentService

# This test simulates the integration between components
# Note: This is still a mock-based integration test; for true integration testing,
# you would need to run the actual services in a test environment

class MockEventConsumer:
    """Mock event consumer for testing."""
    
    def __init__(self, topic, group_id, sentiment_model, redis_client):
        self.topic = topic
        self.group_id = group_id
        self.sentiment_model = sentiment_model
        self.redis_client = redis_client
        self.is_running = False
        self.processed_messages = []
        
    async def start_consuming(self):
        """Start consuming messages (simulated)."""
        self.is_running = True
        
    async def stop_consuming(self):
        """Stop consuming messages."""
        self.is_running = False
        
    async def process_message(self, message):
        """Process a message (simulated)."""
        # Parse message
        data = json.loads(message)
        
        # Analyze sentiment
        analysis = await self.sentiment_model.analyze(data["text"])
        
        # Cache results if needed
        if "ticker" in data:
            key = f"sentiment:{data['ticker']}"
            
            # Update or create ticker sentiment
            existing = await self.redis_client.get(key)
            if existing:
                existing = json.loads(existing)
                # Update with new data
                existing["sentiment"] = analysis["sentiment"]
                existing["score"] = analysis["score"]
                existing["source_count"] = existing.get("source_count", 0) + 1
                existing["timestamp"] = datetime.now().isoformat()
                await self.redis_client.set(key, json.dumps(existing))
            else:
                # Create new entry
                new_entry = {
                    "ticker": data["ticker"],
                    "sentiment": analysis["sentiment"],
                    "score": analysis["score"],
                    "confidence": analysis["confidence"],
                    "source_count": 1,
                    "timestamp": datetime.now().isoformat()
                }
                await self.redis_client.set(key, json.dumps(new_entry))
        
        # Record processed message for testing
        self.processed_messages.append({
            "message": data,
            "analysis": analysis
        })
        
        return analysis

@pytest.mark.asyncio
async def test_message_processing_flow():
    """Test the flow of message processing from consumption to sentiment analysis."""
    # Initialize mocks
    model = MockFinBertModel()
    redis = MockRedisClient()
    
    # Create consumer
    consumer = MockEventConsumer(
        topic="test-topic",
        group_id="test-group",
        sentiment_model=model,
        redis_client=redis
    )
    
    # Start consumer
    await consumer.start_consuming()
    assert consumer.is_running
    
    # Test processing a positive message about Apple
    positive_message = json.dumps({
        "id": "msg-001",
        "ticker": "AAPL",
        "text": "Apple's quarterly results exceeded expectations with strong iPhone sales.",
        "source": "news",
        "timestamp": datetime.now().isoformat()
    })
    
    positive_result = await consumer.process_message(positive_message)
    assert positive_result["sentiment"] == "positive"
    assert positive_result["score"] > 0
    
    # Verify data was cached in Redis
    cached_data = await redis.get("sentiment:AAPL")
    assert cached_data is not None
    cached_json = json.loads(cached_data)
    assert cached_json["ticker"] == "AAPL"
    assert cached_json["sentiment"] == "positive"
    
    # Test processing a negative message about Tesla
    negative_message = json.dumps({
        "id": "msg-002",
        "ticker": "TSLA",
        "text": "Tesla reported significant losses in the European market this quarter.",
        "source": "social",
        "timestamp": datetime.now().isoformat()
    })
    
    negative_result = await consumer.process_message(negative_message)
    assert negative_result["sentiment"] == "negative"
    assert negative_result["score"] < 0
    
    # Verify both messages were processed
    assert len(consumer.processed_messages) == 2
    
    # Stop consumer
    await consumer.stop_consuming()
    assert not consumer.is_running

@pytest.mark.asyncio
async def test_sentiment_aggregation():
    """Test aggregation of sentiment data from multiple sources."""
    # Initialize mocks
    model = MockFinBertModel()
    redis = MockRedisClient()
    
    # Create consumer and service
    consumer = MockEventConsumer(
        topic="test-topic",
        group_id="test-group",
        sentiment_model=model,
        redis_client=redis
    )
    service = MockSentimentService()
    
    # Process multiple messages for the same ticker
    messages = [
        {"id": "msg-1", "ticker": "GOOGL", "text": "Google's ad revenue was positive this quarter", "source": "news"},
        {"id": "msg-2", "ticker": "GOOGL", "text": "Google announced layoffs in its hardware division", "source": "news"},
        {"id": "msg-3", "ticker": "GOOGL", "text": "Google Cloud continues to grow steadily", "source": "analyst"},
    ]
    
    for i, msg_data in enumerate(messages):
        await consumer.process_message(json.dumps(msg_data))
        
        # Verify the message was processed
        assert len(consumer.processed_messages) == i + 1
        
        # Check that the sentiment data is cached
        cached_data = await redis.get(f"sentiment:{msg_data['ticker']}")
        assert cached_data is not None
        
        cached_json = json.loads(cached_data)
        # Verify the source count increases with each message
        assert cached_json["source_count"] == i + 1