"""
Test module for the Iceberg lakehouse integration.

This module provides tests for the Iceberg schema, writer, and query layer.
"""
import os
import sys
import unittest
from datetime import datetime
import uuid
from typing import Dict, Any, List

# Add iceberg_lake to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from iceberg_lake.utils.config import IcebergConfig
from iceberg_lake.schema.iceberg_schema import (
    create_sentiment_schema,
    create_partition_spec,
    create_table_properties
)
from iceberg_lake.writer.iceberg_writer import IcebergSentimentWriter


class TestIcebergSchema(unittest.TestCase):
    """Tests for the Iceberg schema."""
    
    def test_schema_creation(self):
        """Test that the schema can be created."""
        schema = create_sentiment_schema()
        self.assertIsNotNone(schema)
        
        # Check that required fields are present
        field_names = [field.name for field in schema.fields]
        required_fields = [
            "message_id", "event_timestamp", "ingestion_timestamp", 
            "source_system", "text_content", "sentiment_score",
            "sentiment_magnitude", "primary_emotion"
        ]
        for field in required_fields:
            self.assertIn(field, field_names)
    
    def test_partition_spec_creation(self):
        """Test that the partition spec can be created."""
        partition_spec = create_partition_spec()
        self.assertIsNotNone(partition_spec)
        
        # Check that expected partitions are present
        field_names = [field.name for field in partition_spec.fields]
        expected_fields = ["year", "month", "day", "ticker", "source_system"]
        for field in expected_fields:
            self.assertIn(field, field_names)
    
    def test_table_properties_creation(self):
        """Test that the table properties can be created."""
        properties = create_table_properties()
        self.assertIsNotNone(properties)
        
        # Check that essential properties are present
        essential_props = [
            "write.compression.codec",
            "write.target-file-size-bytes",
            "write.parquet.row-group-size-bytes"
        ]
        for prop in essential_props:
            self.assertIn(prop, properties)


class TestIcebergConfig(unittest.TestCase):
    """Tests for the Iceberg configuration."""
    
    def test_default_config(self):
        """Test that default configuration works."""
        config = IcebergConfig()
        self.assertIsNotNone(config)
        
        # Check that all sections are present
        expected_sections = ["catalog", "minio", "dremio", "writer"]
        for section in expected_sections:
            self.assertIn(section, config.get_full_config())

    def test_env_overrides(self):
        """Test that environment variables override defaults."""
        # Set some environment variables
        os.environ["ICEBERG_CATALOG_URI"] = "http://test-iceberg-rest:8181"
        os.environ["MINIO_ACCESS_KEY"] = "test-access-key"
        
        config = IcebergConfig()
        
        # Check that values were overridden
        self.assertEqual(
            config.get_catalog_config()["uri"], 
            "http://test-iceberg-rest:8181"
        )
        self.assertEqual(
            config.get_minio_config()["access_key"], 
            "test-access-key"
        )
        
        # Clean up
        del os.environ["ICEBERG_CATALOG_URI"]
        del os.environ["MINIO_ACCESS_KEY"]


# Note: The following test requires a running Iceberg environment
# It's marked with a separate class so it can be skipped if needed
@unittest.skip("Requires running Iceberg environment")
class TestIcebergWriter(unittest.TestCase):
    """Tests for the Iceberg writer (requires running environment)."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a config for testing
        self.config = IcebergConfig()
        
        # Create a writer
        catalog_config = self.config.get_catalog_config()
        self.writer = IcebergSentimentWriter(
            catalog_uri=catalog_config["uri"],
            warehouse_location=catalog_config["warehouse_location"],
            namespace=catalog_config["namespace"],
            table_name=f"test_sentiment_{uuid.uuid4().hex[:8]}"  # Unique table for testing
        )
    
    def test_write_single_record(self):
        """Test writing a single record."""
        # Create a test record
        record = {
            "message_id": str(uuid.uuid4()),
            "event_timestamp": datetime.utcnow(),
            "ingestion_timestamp": datetime.utcnow(),
            "source_system": "test",
            "text_content": "This is a test message for Iceberg integration",
            "sentiment_score": 0.75,
            "sentiment_magnitude": 0.85,
            "primary_emotion": "positive",
            "sarcasm_detection": False,
            "subjectivity_score": 0.6,
            "toxicity_score": 0.1,
            "user_intent": "information_seeking",
            "processing_version": "test-1.0.0",
            "ticker": "TEST"
        }
        
        # Write the record
        result = self.writer.write_data([record])
        
        # Check that one record was written
        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()