#!/usr/bin/env python3
"""
Test script for the Kafka integration factory.

This script tests the factory function that creates the appropriate
Kafka integration (PyIceberg or Dremio) based on configuration.
"""
import os
import sys
import json
import logging
from unittest.mock import patch, MagicMock

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Import the Kafka integration factory
from iceberg_lake.writer.kafka_integration import create_kafka_integration
from iceberg_lake.writer.dremio_kafka_integration import DremioKafkaIntegration
from iceberg_lake.writer.kafka_integration import IcebergKafkaIntegration


def test_factory_creates_iceberg_integration():
    """Test that factory creates IcebergKafkaIntegration when appropriate."""
    logger.info("Testing creation of IcebergKafkaIntegration...")
    
    # Mock the writer factory to return a mock IcebergSentimentWriter
    with patch('iceberg_lake.writer.writer_factory.WriterFactory') as mock_factory_class:
        # Create mock writer with no jdbc_url attribute (simulating IcebergSentimentWriter)
        mock_writer = MagicMock()
        delattr(mock_writer, 'jdbc_url')  # Ensure this attribute doesn't exist
        
        # Mock factory instance
        mock_factory = MagicMock()
        mock_factory.create_writer.return_value = mock_writer
        mock_factory_class.return_value = mock_factory
        
        # Call the factory function
        integration = create_kafka_integration(writer_type="pyiceberg")
        
        # Verify the correct integration class was created
        assert isinstance(integration, IcebergKafkaIntegration)
        assert integration.writer == mock_writer
        
        logger.info("✓ IcebergKafkaIntegration creation test passed")
        return True


def test_factory_creates_dremio_integration():
    """Test that factory creates DremioKafkaIntegration when appropriate."""
    logger.info("Testing creation of DremioKafkaIntegration...")
    
    # Mock the writer factory to return a mock DremioJdbcWriter
    with patch('iceberg_lake.writer.writer_factory.WriterFactory') as mock_factory_class:
        # Create mock writer with jdbc_url attribute (simulating DremioJdbcWriter)
        mock_writer = MagicMock()
        mock_writer.jdbc_url = "jdbc:dremio:direct=localhost:31010"
        
        # Mock factory instance
        mock_factory = MagicMock()
        mock_factory.create_writer.return_value = mock_writer
        mock_factory_class.return_value = mock_factory
        
        # Call the factory function
        integration = create_kafka_integration(writer_type="dremio")
        
        # Verify the correct integration class was created
        assert isinstance(integration, DremioKafkaIntegration)
        assert integration.writer == mock_writer
        
        logger.info("✓ DremioKafkaIntegration creation test passed")
        return True


def test_factory_with_auto_detection():
    """Test auto detection based on writer type."""
    logger.info("Testing auto detection of integration type...")
    
    # Test both paths with auto detection
    with patch('iceberg_lake.writer.writer_factory.WriterFactory') as mock_factory_class:
        # First test with DremioJdbcWriter
        mock_writer_dremio = MagicMock()
        mock_writer_dremio.jdbc_url = "jdbc:dremio:direct=localhost:31010"
        
        # Mock factory instance
        mock_factory = MagicMock()
        mock_factory.create_writer.return_value = mock_writer_dremio
        mock_factory_class.return_value = mock_factory
        
        # Call the factory function with auto
        integration = create_kafka_integration(writer_type="auto")
        
        # Verify DremioKafkaIntegration was created
        assert isinstance(integration, DremioKafkaIntegration)
        
        # Now test with IcebergSentimentWriter
        mock_writer_iceberg = MagicMock()
        delattr(mock_writer_iceberg, 'jdbc_url')  # Ensure this attribute doesn't exist
        mock_factory.create_writer.return_value = mock_writer_iceberg
        
        # Call the factory function with auto again
        integration = create_kafka_integration(writer_type="auto")
        
        # Verify IcebergKafkaIntegration was created
        assert isinstance(integration, IcebergKafkaIntegration)
        
        logger.info("✓ Auto detection test passed")
        return True


def test_factory_passes_kwargs():
    """Test that factory passes kwargs to integration constructors."""
    logger.info("Testing kwargs passing...")
    
    # Mock the writer factory
    with patch('iceberg_lake.writer.writer_factory.WriterFactory') as mock_factory_class:
        # Create mock writer
        mock_writer = MagicMock()
        mock_writer.jdbc_url = "jdbc:dremio:direct=localhost:31010"
        
        # Mock factory instance
        mock_factory = MagicMock()
        mock_factory.create_writer.return_value = mock_writer
        mock_factory_class.return_value = mock_factory
        
        # Custom kwargs
        custom_kwargs = {
            "batch_size": 200,
            "flush_interval": 45
        }
        
        # Call the factory function with kwargs
        with patch('iceberg_lake.writer.dremio_kafka_integration.DremioKafkaIntegration.__init__', return_value=None) as mock_init:
            integration = create_kafka_integration(writer_type="dremio", **custom_kwargs)
            
            # Verify kwargs were passed correctly
            # First positional arg is the writer, followed by kwargs
            _, kwargs = mock_init.call_args
            assert kwargs.get("batch_size") == 200
            assert kwargs.get("flush_interval") == 45
        
        logger.info("✓ kwargs passing test passed")
        return True


def run_tests():
    """Run all factory tests."""
    logger.info("===== KAFKA INTEGRATION FACTORY TESTS =====")
    
    # Run all tests
    test_results = {
        "iceberg_integration": test_factory_creates_iceberg_integration(),
        "dremio_integration": test_factory_creates_dremio_integration(),
        "auto_detection": test_factory_with_auto_detection(),
        "kwargs_passing": test_factory_passes_kwargs()
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
        run_tests()
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()