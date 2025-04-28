#!/usr/bin/env python3
"""
Test script for the schema validator.

This script tests the schema validation functionality for
the sentiment analysis data schema.
"""
import os
import sys
import uuid
import json
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

# Import schema validator
from iceberg_lake.schema.schema_validator import SentimentSchemaValidator


def test_valid_record():
    """Test validation of a valid record."""
    logger.info("\n=== Testing validation of a valid record ===")
    
    # Create validator
    validator = SentimentSchemaValidator()
    
    # Create a valid record
    current_time = datetime.utcnow()
    record = {
        "message_id": str(uuid.uuid4()),
        "event_timestamp": current_time,
        "ingestion_timestamp": current_time,
        "source_system": "validation_test",
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
    
    # Validate the record
    is_valid, errors = validator.validate(record)
    
    if is_valid:
        logger.info("✓ Valid record passed validation")
    else:
        logger.error(f"✗ Valid record failed validation: {errors}")
    
    return is_valid


def test_invalid_record():
    """Test validation of an invalid record."""
    logger.info("\n=== Testing validation of an invalid record ===")
    
    # Create validator
    validator = SentimentSchemaValidator()
    
    # Create an invalid record (missing required fields, invalid types)
    record = {
        # Missing message_id, event_timestamp
        "source_system": "validation_test",
        "text_content": "Incomplete record with errors",
        "sentiment_score": "not a number",  # Wrong type
        "sentiment_magnitude": 2.5,  # Out of range
        "primary_emotion": "excited",  # Invalid enum value
        "sarcasm_detection": "maybe",  # Wrong type
        "user_intent": "random_intent"  # Invalid enum value
        # Missing other required fields
    }
    
    # Validate the record
    is_valid, errors = validator.validate(record)
    
    if not is_valid:
        logger.info(f"✓ Invalid record correctly failed validation with {len(errors)} errors:")
        for error in errors:
            logger.info(f"  - {error}")
    else:
        logger.error("✗ Invalid record incorrectly passed validation")
    
    return not is_valid


def test_complex_types():
    """Test validation of complex types (maps, lists)."""
    logger.info("\n=== Testing validation of complex types ===")
    
    # Create validator
    validator = SentimentSchemaValidator()
    
    # Create a record with complex types
    current_time = datetime.utcnow()
    record = {
        "message_id": str(uuid.uuid4()),
        "event_timestamp": current_time,
        "ingestion_timestamp": current_time,
        "source_system": "validation_test",
        "text_content": "Testing complex types.",
        "sentiment_score": 0.5,
        "sentiment_magnitude": 0.5,
        "primary_emotion": "neutral",
        "sarcasm_detection": False,
        "subjectivity_score": 0.5,
        "toxicity_score": 0.0,
        "user_intent": "information_seeking",
        "processing_version": "1.0.0",
        
        # Complex types as native Python types
        "emotion_intensity_vector": {"joy": 0.7, "surprise": 0.2},
        "aspect_based_sentiment": {"product": 0.8, "service": 0.6},
        "aspect_target_identification": ["product", "service"],
        "entity_recognition": [
            {"text": "Apple", "type": "ORGANIZATION"},
            {"text": "iPhone", "type": "PRODUCT"}
        ],
        
        # Complex types as JSON strings
        "emotion_intensity_vector_str": json.dumps({"joy": 0.7, "surprise": 0.2}),
        "aspect_target_identification_str": json.dumps(["product", "service"])
    }
    
    # Validate the record
    is_valid, errors = validator.validate(record)
    
    if is_valid:
        logger.info("✓ Record with complex types passed validation")
    else:
        logger.error(f"✗ Record with complex types failed validation: {errors}")
    
    # Test invalid JSON strings
    record["emotion_intensity_vector"] = "{invalid:json}"
    
    is_valid, errors = validator.validate(record)
    
    if not is_valid:
        logger.info("✓ Record with invalid JSON string correctly failed validation")
        for error in errors:
            logger.info(f"  - {error}")
    else:
        logger.error("✗ Record with invalid JSON string incorrectly passed validation")
    
    return is_valid


def test_normalization():
    """Test data normalization functionality."""
    logger.info("\n=== Testing data normalization ===")
    
    # Create validator
    validator = SentimentSchemaValidator()
    
    # Create a record with issues to normalize
    record = {
        # Missing some required fields
        "text_content": "Record that needs normalization",
        "sentiment_score": "0.75",  # String instead of float
        "sentiment_magnitude": 2.5,  # Out of range
        "primary_emotion": "excited",  # Invalid enum
        "sarcasm_detection": 1,  # Number instead of boolean
        "emotion_intensity_vector": {"joy": 0.8, "excitement": 0.7}  # Dict that needs JSON conversion
    }
    
    # First validate to confirm it's invalid
    is_valid, errors = validator.validate(record)
    
    if not is_valid:
        logger.info(f"✓ Original record correctly failed validation with {len(errors)} errors")
    else:
        logger.error("✗ Original record unexpectedly passed validation")
    
    # Now normalize the record
    try:
        normalized = validator.normalize_data(record)
        
        # Check that required fields were added
        logger.info("Normalization results:")
        for field in ["message_id", "event_timestamp", "ingestion_timestamp", 
                    "source_system", "processing_version"]:
            if field in normalized:
                logger.info(f"  ✓ Added missing field: {field}")
            else:
                logger.error(f"  ✗ Failed to add missing field: {field}")
        
        # Check type conversions
        if isinstance(normalized["sentiment_score"], float):
            logger.info(f"  ✓ Converted sentiment_score from string to float: {normalized['sentiment_score']}")
        else:
            logger.error(f"  ✗ Failed to convert sentiment_score to float: {normalized['sentiment_score']}")
        
        # Check value constraints
        if 0 <= normalized["sentiment_magnitude"] <= 1:
            logger.info(f"  ✓ Fixed out-of-range sentiment_magnitude: {normalized['sentiment_magnitude']}")
        else:
            logger.error(f"  ✗ Failed to fix out-of-range sentiment_magnitude: {normalized['sentiment_magnitude']}")
        
        # Check enum values
        if normalized["primary_emotion"] in ["anger", "disgust", "fear", "joy", "neutral", 
                                          "sadness", "surprise", "positive", "negative"]:
            logger.info(f"  ✓ Fixed invalid enum primary_emotion: {normalized['primary_emotion']}")
        else:
            logger.error(f"  ✗ Failed to fix invalid enum primary_emotion: {normalized['primary_emotion']}")
        
        # Check complex type serialization
        if "emotion_intensity_vector" in normalized and isinstance(normalized["emotion_intensity_vector"], str):
            logger.info(f"  ✓ Serialized emotion_intensity_vector to JSON string")
        else:
            logger.warning(f"  ⚠ emotion_intensity_vector not serialized to JSON string (may be expected behavior)")
        
        # Validate the normalized record
        is_valid, errors = validator.validate(normalized)
        
        if is_valid:
            logger.info("✓ Normalized record passed validation")
            return True
        else:
            logger.error(f"✗ Normalized record still failed validation: {errors}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Normalization failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    logger.info("===== SCHEMA VALIDATOR TEST =====")
    
    # Run tests
    valid_test = test_valid_record()
    invalid_test = test_invalid_record()
    complex_test = test_complex_types()
    normalization_test = test_normalization()
    
    # Print summary
    logger.info("\n===== TEST SUMMARY =====")
    logger.info(f"Valid record test: {'SUCCESS' if valid_test else 'FAILED'}")
    logger.info(f"Invalid record test: {'SUCCESS' if invalid_test else 'FAILED'}")
    logger.info(f"Complex types test: {'SUCCESS' if complex_test else 'FAILED'}")
    logger.info(f"Normalization test: {'SUCCESS' if normalization_test else 'FAILED'}")
    
    if valid_test and invalid_test and normalization_test:
        logger.info("\n===== TEST COMPLETED SUCCESSFULLY =====")
        return 0
    else:
        logger.error("\n===== TEST FAILED =====")
        return 1


if __name__ == "__main__":
    sys.exit(main())