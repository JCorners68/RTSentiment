#!/usr/bin/env python3
"""
Test script for the Iceberg writer factory.

This script tests the writer factory and demonstrates how to use
both the PyIceberg and Dremio JDBC writers.
"""
import os
import sys
import uuid
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Import writer factory
from iceberg_lake.writer.writer_factory import WriterFactory


def create_test_data():
    """Create test sentiment data records."""
    current_time = datetime.utcnow()
    return [
        {
            "message_id": str(uuid.uuid4()),
            "event_timestamp": current_time,
            "ingestion_timestamp": current_time,
            "source_system": "factory_test",
            "text_content": "The market outlook is improving based on economic indicators.",
            "sentiment_score": 0.65,
            "sentiment_magnitude": 0.7,
            "primary_emotion": "positive",
            "sarcasm_detection": False,
            "subjectivity_score": 0.3,
            "toxicity_score": 0.1,
            "user_intent": "information_sharing",
            "processing_version": "1.0.0",
            "ticker": "SPY",
            "emotion_intensity_vector": {"optimism": 0.7, "confidence": 0.6},
            "aspect_based_sentiment": {"market": 0.7, "outlook": 0.6}
        }
    ]


def test_writer_factory_auto():
    """Test writer factory with automatic selection."""
    logger.info("\n=== Testing writer factory with automatic selection ===")
    
    try:
        # Create factory
        factory = WriterFactory()
        
        # Get writer (auto select)
        writer = factory.create_writer(writer_type="auto")
        
        # Log which writer type was selected
        writer_type = writer.__class__.__name__
        logger.info(f"Factory selected writer: {writer_type}")
        
        # Test the writer
        data = create_test_data()
        records_written = writer.write_data(data)
        
        logger.info(f"Wrote {records_written} records with {writer_type}")
        
        # Close the writer
        if hasattr(writer, 'close'):
            writer.close()
        
        return True
    except Exception as e:
        logger.error(f"Auto writer test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_writer_factory_dremio():
    """Test writer factory with explicit Dremio selection."""
    logger.info("\n=== Testing writer factory with Dremio JDBC selection ===")
    
    try:
        # Create factory
        factory = WriterFactory()
        
        # Get writer (force Dremio)
        try:
            writer = factory.create_writer(writer_type="dremio")
            
            # Test the writer
            data = create_test_data()
            records_written = writer.write_data(data)
            
            logger.info(f"Wrote {records_written} records with DremioJdbcWriter")
            
            # Close the writer
            writer.close()
            
            return True
        except Exception as e:
            logger.warning(f"Dremio writer test skipped: {str(e)}")
            return False
    except Exception as e:
        logger.error(f"Dremio writer test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_writer_factory_pyiceberg():
    """Test writer factory with explicit PyIceberg selection."""
    logger.info("\n=== Testing writer factory with PyIceberg selection ===")
    
    try:
        # Create factory
        factory = WriterFactory()
        
        # Get writer (force PyIceberg)
        writer = factory.create_writer(writer_type="pyiceberg")
        
        # Test the writer
        data = create_test_data()
        records_written = writer.write_data(data)
        
        logger.info(f"Wrote {records_written} records with IcebergSentimentWriter")
        
        return True
    except Exception as e:
        logger.error(f"PyIceberg writer test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    logger.info("===== ICEBERG WRITER FACTORY TEST =====")
    
    # Test with auto selection
    auto_success = test_writer_factory_auto()
    
    # Test with explicit Dremio selection
    dremio_success = test_writer_factory_dremio()
    
    # Test with explicit PyIceberg selection
    pyiceberg_success = test_writer_factory_pyiceberg()
    
    # Print summary
    logger.info("\n===== TEST SUMMARY =====")
    logger.info(f"Auto selection test: {'SUCCESS' if auto_success else 'FAILED'}")
    logger.info(f"Dremio writer test: {'SUCCESS' if dremio_success else 'FAILED/SKIPPED'}")
    logger.info(f"PyIceberg writer test: {'SUCCESS' if pyiceberg_success else 'FAILED'}")
    
    if auto_success and (dremio_success or pyiceberg_success):
        logger.info("\n===== TEST COMPLETED SUCCESSFULLY =====")
        return 0
    else:
        logger.error("\n===== TEST FAILED =====")
        return 1


if __name__ == "__main__":
    sys.exit(main())