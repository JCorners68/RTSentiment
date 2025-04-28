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
    return Schema(
        # Basic Fields
        NestedField.required(1, "message_id", StringType()),
        NestedField.required(2, "event_timestamp", TimestampType.with_timezone()),
        NestedField.required(3, "ingestion_timestamp", TimestampType.with_timezone()),
        NestedField.required(4, "source_system", StringType()),
        NestedField.required(5, "text_content", StringType()),
        
        # Core Sentiment Fields
        NestedField.required(6, "sentiment_score", FloatType()),
        NestedField.required(7, "sentiment_magnitude", FloatType()),
        NestedField.required(8, "primary_emotion", StringType()),
        
        # Advanced Sentiment Fields
        NestedField.optional(9, "emotion_intensity_vector", 
                           MapType.of(StringType(), FloatType())),
        NestedField.optional(10, "aspect_target_identification", 
                           ListType.of_required(StringType())),
        NestedField.optional(11, "aspect_based_sentiment", 
                           MapType.of(StringType(), FloatType())),
        NestedField.required(12, "sarcasm_detection", BooleanType()),
        NestedField.required(13, "subjectivity_score", FloatType()),
        NestedField.required(14, "toxicity_score", FloatType()),
        
        # Entity Recognition
        NestedField.optional(15, "entity_recognition", 
                           ListType.of_required(
                               StructType.of(
                                   NestedField.required(1, "text", StringType()),
                                   NestedField.required(2, "type", StringType())
                               )
                           )),
        
        # Intent and Influence
        NestedField.required(16, "user_intent", StringType()),
        NestedField.optional(17, "influence_score", FloatType()),
        
        # Metadata
        NestedField.required(18, "processing_version", StringType()),
        
        # Financial Context
        NestedField.optional(19, "ticker", StringType()),
        NestedField.optional(20, "article_title", StringType()),
        NestedField.optional(21, "source_url", StringType()),
        NestedField.optional(22, "model_name", StringType()),
    )


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
    return PartitionSpec(
        PartitionField(source_id=2, field_id=100, transform=YearTransform(), name="year"),
        PartitionField(source_id=2, field_id=101, transform=MonthTransform(), name="month"),
        PartitionField(source_id=2, field_id=102, transform=DayTransform(), name="day"),
        PartitionField(source_id=19, field_id=103, transform=IdentityTransform(), name="ticker"),
        PartitionField(source_id=4, field_id=104, transform=IdentityTransform(), name="source_system")
    )


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