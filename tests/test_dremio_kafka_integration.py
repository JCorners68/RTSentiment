#!/usr/bin/env python3
"""
Test script for the Dremio Kafka integration.

This script tests the integration between Kafka consumers and the DremioJdbcWriter,
verifying that sentiment data can be streamed from Kafka to Iceberg via Dremio.
"""
import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Import the Dremio Kafka integration
from iceberg_lake.writer.dremio_kafka_integration import DremioKafkaIntegration
from iceberg_lake.writer.dremio_jdbc_writer import DremioJdbcWriter


def create_mock_dremio_writer():
    """Create a mock DremioJdbcWriter for testing."""
    writer = MagicMock(spec=DremioJdbcWriter)
    writer.write_data.return_value = 1  # Simulate successful write
    return writer


def generate_test_event(ticker=None):
    """Generate a test Kafka event with sentiment data."""
    return {
        "id": f"msg_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "timestamp": datetime.utcnow().isoformat(),
        "source": "test_source",
        "text": "This is a test message about sentiment analysis.",
        "tickers": [ticker] if ticker else [],
        "title": "Test Message",
        "url": "https://example.com/test",
        "model": "test_model",
        "sentiment_result": {
            "sentiment_score": 0.75,
            "sentiment_magnitude": 0.85,
            "primary_emotion": "positive",
            "emotion_intensity_vector": {
                "joy": 0.8,
                "surprise": 0.3,
                "trust": 0.6
            },
            "aspect_target_identification": ["sentiment", "analysis"],
            "aspect_based_sentiment": {
                "sentiment": 0.8,
                "analysis": 0.7
            },
            "sarcasm_detection": False,
            "subjectivity_score": 0.4,
            "toxicity_score": 0.05,
            "entity_recognition": [
                {"text": "sentiment analysis", "type": "CONCEPT"}
            ],
            "user_intent": "information_sharing",
            "influence_score": 0.3,
            "processing_version": "test_1.0"
        }
    }


async def test_process_event():
    """Test processing a single event."""
    logger.info("Testing processing a single event...")
    
    # Create mock writer and integration
    mock_writer = create_mock_dremio_writer()
    integration = DremioKafkaIntegration(mock_writer, batch_size=5, flush_interval=10)
    
    # Start the integration
    await integration.start()
    
    try:
        # Generate test event
        test_event = generate_test_event(ticker="TEST")
        
        # Process event
        result = await integration.process_event(test_event)
        logger.info(f"Event processing result: {result}")
        
        # Verify event was buffered (not yet written)
        assert len(integration.event_buffer) == 1
        assert mock_writer.write_data.call_count == 0
        
        # Manually flush buffer
        count = await integration.flush()
        logger.info(f"Flush result: {count}")
        
        # Verify write was called
        assert mock_writer.write_data.call_count == 1
        assert len(integration.event_buffer) == 0
        
        logger.info("✓ Single event processing test passed")
        return True
        
    finally:
        # Stop the integration
        await integration.stop()


async def test_batch_processing():
    """Test processing a batch of events."""
    logger.info("Testing batch processing...")
    
    # Create mock writer and integration
    mock_writer = create_mock_dremio_writer()
    integration = DremioKafkaIntegration(mock_writer, batch_size=3, flush_interval=30)
    
    # Start the integration
    await integration.start()
    
    try:
        # Generate test events
        tickers = ["AAPL", "TSLA", "GOOG", "MSFT"]
        
        # Process events
        for ticker in tickers:
            test_event = generate_test_event(ticker=ticker)
            result = await integration.process_event(test_event)
            logger.info(f"Processed event for {ticker}, result: {result}")
            
            # Verify automatic flush when batch size reached
            if ticker == "GOOG":  # Third ticker - should trigger flush
                await asyncio.sleep(0.1)  # Give time for async task to run
                assert mock_writer.write_data.call_count == 1
        
        # Verify remaining events
        assert len(integration.event_buffer) == 1  # MSFT should be buffered
        
        # Manually flush
        count = await integration.flush()
        logger.info(f"Final flush result: {count}")
        
        # Verify all writes
        assert mock_writer.write_data.call_count == 2
        
        logger.info("✓ Batch processing test passed")
        return True
        
    finally:
        # Stop the integration
        await integration.stop()


async def test_auto_flush():
    """Test automatic flushing after interval."""
    logger.info("Testing automatic flush after interval...")
    
    # Create mock writer and integration
    mock_writer = create_mock_dremio_writer()
    integration = DremioKafkaIntegration(mock_writer, batch_size=10, flush_interval=2)  # Short interval for testing
    
    # Start the integration
    await integration.start()
    
    try:
        # Generate test event
        test_event = generate_test_event(ticker="AUTO")
        
        # Process event
        result = await integration.process_event(test_event)
        logger.info(f"Event processing result: {result}")
        
        # Verify event was buffered (not yet written)
        assert len(integration.event_buffer) == 1
        assert mock_writer.write_data.call_count == 0
        
        # Wait for auto-flush interval
        logger.info("Waiting for auto-flush interval (2 seconds)...")
        await asyncio.sleep(3)  # Longer than flush interval
        
        # Verify write was called automatically
        assert mock_writer.write_data.call_count == 1
        assert len(integration.event_buffer) == 0
        
        logger.info("✓ Auto-flush test passed")
        return True
        
    finally:
        # Stop the integration
        await integration.stop()


async def run_tests():
    """Run all integration tests."""
    logger.info("===== DREMIO KAFKA INTEGRATION TESTS =====")
    
    # Run all tests
    test_results = {
        "process_event": await test_process_event(),
        "batch_processing": await test_batch_processing(),
        "auto_flush": await test_auto_flush()
    }
    
    # Print summary
    logger.info("\n===== TEST RESULTS =====")
    for test_name, result in test_results.items():
        logger.info(f"{test_name}: {'✓ PASSED' if result else '✗ FAILED'}")
    
    all_passed = all(test_results.values())
    logger.info(f"\nOverall result: {'✓ ALL TESTS PASSED' if all_passed else '✗ SOME TESTS FAILED'}")
    
    return all_passed


def main():
    """Main test function."""
    try:
        # Run the test suite
        asyncio.run(run_tests())
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()