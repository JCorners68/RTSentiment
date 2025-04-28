"""
Iceberg schema definitions for the sentiment analysis system.

This module defines the schema for the Iceberg tables used for storing
sentiment analysis data in the RT Sentiment system.
"""
from typing import Dict, Any

from pyiceberg.schema import Schema
from pyiceberg.types import (
    NestedField, 
    StringType, 
    TimestampType, 
    FloatType, 
    BooleanType, 
    ListType, 
    MapType, 
    StructType
)
from pyiceberg.partitioning import PartitionSpec, PartitionField
from pyiceberg.transforms import (
    IdentityTransform, 
    DayTransform, 
    MonthTransform, 
    YearTransform
)


def create_sentiment_schema() -> Schema:
    """
    Create Iceberg schema for advanced sentiment analysis data.
    
    Returns:
        Schema: PyIceberg schema for sentiment data
    """
    # In PyIceberg 0.9.0, we need to create fields using Schema.NestedField
    # and pass them to the Schema constructor
    fields = [
        # Basic Fields
        Schema.NestedField(field_id=1, name="message_id", field_type=StringType(), required=True),
        Schema.NestedField(field_id=2, name="event_timestamp", field_type=TimestampType(), required=True),
        Schema.NestedField(field_id=3, name="ingestion_timestamp", field_type=TimestampType(), required=True),
        Schema.NestedField(field_id=4, name="source_system", field_type=StringType(), required=True),
        Schema.NestedField(field_id=5, name="text_content", field_type=StringType(), required=True),
        
        # Core Sentiment Fields
        Schema.NestedField(field_id=6, name="sentiment_score", field_type=FloatType(), required=True),
        Schema.NestedField(field_id=7, name="sentiment_magnitude", field_type=FloatType(), required=True),
        Schema.NestedField(field_id=8, name="primary_emotion", field_type=StringType(), required=True),
        
        # Advanced Sentiment Fields
        Schema.NestedField(field_id=9, name="emotion_intensity_vector", 
                          field_type=MapType(StringType(), FloatType()), required=False),
        Schema.NestedField(field_id=10, name="aspect_target_identification", 
                          field_type=ListType(StringType()), required=False),
        Schema.NestedField(field_id=11, name="aspect_based_sentiment", 
                          field_type=MapType(StringType(), FloatType()), required=False),
        Schema.NestedField(field_id=12, name="sarcasm_detection", field_type=BooleanType(), required=True),
        Schema.NestedField(field_id=13, name="subjectivity_score", field_type=FloatType(), required=True),
        Schema.NestedField(field_id=14, name="toxicity_score", field_type=FloatType(), required=True),
        
        # Entity Recognition
        Schema.NestedField(field_id=15, name="entity_recognition", 
                         field_type=ListType(
                             StructType([
                                 Schema.NestedField(field_id=1, name="text", field_type=StringType(), required=True),
                                 Schema.NestedField(field_id=2, name="type", field_type=StringType(), required=True)
                             ])
                         ), required=False),
        
        # Intent and Influence
        Schema.NestedField(field_id=16, name="user_intent", field_type=StringType(), required=True),
        Schema.NestedField(field_id=17, name="influence_score", field_type=FloatType(), required=False),
        
        # Metadata
        Schema.NestedField(field_id=18, name="processing_version", field_type=StringType(), required=True),
        
        # Financial Context
        Schema.NestedField(field_id=19, name="ticker", field_type=StringType(), required=False),
        Schema.NestedField(field_id=20, name="article_title", field_type=StringType(), required=False),
        Schema.NestedField(field_id=21, name="source_url", field_type=StringType(), required=False),
        Schema.NestedField(field_id=22, name="model_name", field_type=StringType(), required=False),
    ]
    
    return Schema(fields)


def create_partition_spec() -> PartitionSpec:
    """
    Create partition specification for sentiment data.
    
    The partitioning strategy is optimized for:
    - Time-based queries (daily, monthly, yearly)
    - Ticker-specific queries
    - Source-specific queries
    
    Returns:
        PartitionSpec: PyIceberg partition specification
    """
    # Create a simple partition spec by event timestamp (field ID 2) and ticker (field ID 19)
    partition_fields = [
        # Partition by year/month/day from the event_timestamp field (ID 2)
        PartitionField(source_id=2, field_id=100, transform="year", name="year"),
        PartitionField(source_id=2, field_id=101, transform="month", name="month"),
        PartitionField(source_id=2, field_id=102, transform="day", name="day"),
        # Partition by ticker (ID 19) and source (ID 4)
        PartitionField(source_id=19, field_id=103, transform="identity", name="ticker"),
        PartitionField(source_id=4, field_id=104, transform="identity", name="source_system")
    ]
    
    return PartitionSpec(fields=partition_fields)


def create_table_properties() -> Dict[str, Any]:
    """
    Create table properties for sentiment data.
    
    Sets optimized table properties for:
    - Compression
    - File size targets
    - Metadata management
    
    Returns:
        Dict[str, Any]: Dictionary of table properties
    """
    return {
        # Compression options
        "write.compression.codec": "zstd",
        
        # Write properties
        "write.target-file-size-bytes": "536870912",  # 512 MB target file size
        "write.parquet.row-group-size-bytes": "134217728",  # 128 MB row groups
        
        # Metadata properties
        "commit.retry.num-retries": "3",
        "commit.retry.min-delay-ms": "100",
        "commit.retry.max-delay-ms": "5000",
        
        # Data maintenance
        "write.metadata.delete-after-commit.enabled": "true",
        "write.metadata.previous-versions-max": "10",
        
        # Object storage optimization
        "write.object-storage.enabled": "true",
        
        # Table description
        "table_description": "Advanced sentiment analysis data from multiple sources",
        "comment": "RT Sentiment Analysis data with advanced fields for financial analysis"
    }