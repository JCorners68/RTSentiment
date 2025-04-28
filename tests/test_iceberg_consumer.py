"""
Test module for the Iceberg Kafka integration.

This module tests the integration between Kafka and Iceberg
for real-time sentiment data processing.
"""
import asyncio
import json
import os
import pytest
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import modules to test
from sentiment_service.event_consumers.iceberg_consumer import IcebergConsumer
from iceberg_lake.writer.iceberg_writer import IcebergSentimentWriter
from iceberg_lake.writer.kafka_integration import IcebergKafkaIntegration
from iceberg_lake.utils.config import IcebergConfig

# Create mock classes
class MockRedisClient:
    async def get(self, key):
        return None
    
    async def set(self, key, value, expire=None):
        return True
    
    async def sadd(self, key, value):
        return True
    
    def get_current_time(self):
        return datetime.now().timestamp()

class MockMessage:
    def __init__(self, value):
        self.value = value


@pytest.mark.asyncio
async def test_iceberg_kafka_integration_init():
    """Test initialization of the Iceberg Kafka integration."""
    # Create mock writer
    mock_writer = MagicMock()
    
    # Create integration
    integration = IcebergKafkaIntegration(
        iceberg_writer=mock_writer,
        batch_size=10,
        flush_interval=5
    )
    
    # Verify initialization
    assert integration.writer == mock_writer
    assert integration.batch_size == 10
    assert integration.flush_interval == 5
    assert not integration.running
    assert len(integration.event_buffer) == 0


@pytest.mark.asyncio
async def test_iceberg_kafka_integration_process_event():
    """Test processing of events in the Iceberg Kafka integration."""
    # Create mock writer
    mock_writer = MagicMock()
    mock_writer.write_data.return_value = 1
    
    # Create integration
    integration = IcebergKafkaIntegration(
        iceberg_writer=mock_writer,
        batch_size=2,  # Small batch size for testing
        flush_interval=5
    )
    
    # Start integration
    await integration.start()
    
    # Test event processing
    event1 = {
        "id": "test-event-1",
        "text": "Test event 1",
        "source": "test",
        "tickers": ["AAPL"],
        "timestamp": datetime.now().isoformat()
    }
    
    event2 = {
        "id": "test-event-2",
        "text": "Test event 2",
        "source": "test",
        "tickers": ["MSFT"],
        "timestamp": datetime.now().isoformat()
    }
    
    # Process events
    result1 = await integration.process_event(event1)
    assert result1 is True
    assert len(integration.event_buffer) == 1
    
    # Process second event to trigger flush
    result2 = await integration.process_event(event2)
    assert result2 is True
    
    # Wait for flush to complete
    await asyncio.sleep(0.1)
    
    # Verify writer was called
    mock_writer.write_data.assert_called_once()
    
    # Clean up
    await integration.stop()


@pytest.mark.asyncio
@patch('sentiment_service.event_consumers.iceberg_consumer.IcebergSentimentWriter')
@patch('sentiment_service.event_consumers.iceberg_consumer.IcebergConfig')
async def test_iceberg_consumer_init(mock_config_class, mock_writer_class):
    """Test initialization of the Iceberg consumer."""
    # Create mock instances
    mock_config = MagicMock()
    mock_config.get_catalog_config.return_value = {
        "uri": "test-uri",
        "warehouse_location": "test-location",
        "namespace": "test-namespace",
        "table_name": "test-table"
    }
    mock_config.get_writer_config.return_value = {
        "max_retries": 3,
        "retry_delay": 1000
    }
    mock_config_class.return_value = mock_config
    
    mock_writer = MagicMock()
    mock_writer_class.return_value = mock_writer
    
    # Create consumer
    consumer = IcebergConsumer(
        bootstrap_servers="test-server",
        topic="test-topic",
        group_id="test-group",
        redis_client=MockRedisClient(),
        batch_size=10,
        flush_interval=5
    )
    
    # Verify initialization
    assert consumer.bootstrap_servers == "test-server"
    assert consumer.topic == "test-topic"
    assert consumer.group_id == "test-group"
    assert consumer.batch_size == 10
    assert consumer.flush_interval == 5
    assert consumer.iceberg_config is not None
    assert consumer.iceberg_writer is None
    assert consumer.iceberg_integration is None


@pytest.mark.asyncio
@patch('sentiment_service.event_consumers.iceberg_consumer.IcebergKafkaIntegration')
@patch('sentiment_service.event_consumers.iceberg_consumer.IcebergSentimentWriter')
@patch('sentiment_service.event_consumers.iceberg_consumer.IcebergConfig')
@patch('sentiment_service.event_consumers.base_consumer.BaseConsumer.connect')
@patch('sentiment_service.event_consumers.base_consumer.BaseConsumer.analyze_sentiment')
async def test_iceberg_consumer_process_message(
    mock_analyze_sentiment, 
    mock_base_connect,
    mock_config_class, 
    mock_writer_class, 
    mock_integration_class
):
    """Test message processing in the Iceberg consumer."""
    # Set up mocks
    mock_base_connect.return_value = True
    
    mock_config = MagicMock()
    mock_config.get_catalog_config.return_value = {
        "uri": "test-uri",
        "warehouse_location": "test-location",
        "namespace": "test-namespace",
        "table_name": "test-table"
    }
    mock_config.get_writer_config.return_value = {
        "max_retries": 3,
        "retry_delay": 1000
    }
    mock_config_class.return_value = mock_config
    
    mock_writer = MagicMock()
    mock_writer_class.return_value = mock_writer
    
    mock_integration = MagicMock()
    mock_integration_class.return_value = mock_integration
    mock_integration.start = MagicMock(return_value=None)
    mock_integration.process_event = MagicMock(return_value=True)
    
    # Create sample sentiment result
    sentiment_result = {
        "sentiment_score": 0.8,
        "sentiment_label": "positive",
        "probabilities": {
            "positive": 0.8,
            "neutral": 0.15,
            "negative": 0.05
        }
    }
    mock_analyze_sentiment.return_value = [sentiment_result]
    
    # Create consumer
    consumer = IcebergConsumer(
        bootstrap_servers="test-server",
        topic="test-topic",
        group_id="test-group",
        redis_client=MockRedisClient(),
        batch_size=10,
        flush_interval=5
    )
    
    # Initialize connection and writer
    await consumer.connect()
    consumer.iceberg_integration = mock_integration
    
    # Create test message
    message = MockMessage({
        "id": "test-event",
        "type": "earnings_report",
        "source": "bloomberg",
        "tickers": ["AAPL", "MSFT"],
        "text": "Apple and Microsoft reported strong earnings.",
        "timestamp": datetime.now().isoformat()
    })
    
    # Process message
    await consumer.process_message(message)
    
    # Verify message was processed
    mock_integration.process_event.assert_called_once()
    
    # Clean up
    await consumer.stop_consuming()


if __name__ == "__main__":
    pytest.main(["-v", __file__])