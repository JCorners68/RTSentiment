"""
Iceberg writer module for the sentiment analysis system.

This module provides a writer for storing sentiment analysis data in Iceberg tables.
"""
import uuid
import logging
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from pyiceberg.catalog import load_catalog
from pyiceberg.exceptions import NoSuchTableError
from pyiceberg.table import Table

from iceberg_lake.schema.iceberg_schema import (
    create_sentiment_schema,
    create_partition_spec,
    create_table_properties
)


class IcebergSentimentWriter:
    """
    Writer for storing sentiment analysis data in Iceberg tables.
    
    This class handles writing sentiment data to Iceberg tables with
    support for all advanced sentiment fields, schema validation,
    and error handling.
    """
    def __init__(
        self, 
        catalog_uri: str, 
        warehouse_location: str, 
        namespace: str = "sentiment", 
        table_name: str = "sentiment_data",
        max_retries: int = 3,
        retry_delay: int = 1000  # milliseconds
    ):
        """
        Initialize Iceberg writer for advanced sentiment data.
        
        Args:
            catalog_uri: URI of the Iceberg catalog
            warehouse_location: Base location for Iceberg data
            namespace: Iceberg namespace
            table_name: Iceberg table name
            max_retries: Maximum number of write retries
            retry_delay: Delay between retries (ms)
        """
        self.logger = logging.getLogger(__name__)
        self.catalog = load_catalog(catalog_uri)
        self.warehouse_location = warehouse_location
        self.namespace = namespace
        self.table_name = table_name
        self.table_identifier = f"{namespace}.{table_name}"
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Ensure the table exists
        self.table = self._ensure_table_exists()
        
    def _ensure_table_exists(self) -> Table:
        """
        Ensure the target Iceberg table exists, create if not.
        
        Returns:
            Table: PyIceberg Table instance
        """
        try:
            table = self.catalog.load_table(self.table_identifier)
            self.logger.info(f"Loaded existing table: {self.table_identifier}")
            return table
        except NoSuchTableError:
            self.logger.info(f"Creating new table: {self.table_identifier}")
            
            # Define schema using function from iceberg_schema.py
            schema = create_sentiment_schema()
            
            # Create partition spec using function from iceberg_schema.py
            partition_spec = create_partition_spec()
            
            # Get table properties
            properties = create_table_properties()
                
            # Create the table
            table = self.catalog.create_table(
                self.table_identifier, 
                schema, 
                partition_spec,
                self.warehouse_location + "/" + self.table_name,
                properties=properties
            )
            
            self.logger.info(f"Created table: {self.table_identifier}")
            return table
    
    def _validate_record(self, record: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate a record against the schema.
        
        Args:
            record: Record to validate
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, error_messages)
        """
        errors = []
        
        # Check required fields
        required_fields = [
            "message_id", "event_timestamp", "ingestion_timestamp", 
            "source_system", "text_content", "sentiment_score",
            "sentiment_magnitude", "primary_emotion", "sarcasm_detection",
            "subjectivity_score", "toxicity_score", "user_intent",
            "processing_version"
        ]
        
        for field in required_fields:
            if field not in record:
                errors.append(f"Missing required field: {field}")
        
        # Check field types
        if "sentiment_score" in record and not isinstance(record["sentiment_score"], (int, float)):
            errors.append(f"Invalid type for sentiment_score: {type(record['sentiment_score'])}")
            
        if "sentiment_magnitude" in record and not isinstance(record["sentiment_magnitude"], (int, float)):
            errors.append(f"Invalid type for sentiment_magnitude: {type(record['sentiment_magnitude'])}")
            
        if "subjectivity_score" in record and not isinstance(record["subjectivity_score"], (int, float)):
            errors.append(f"Invalid type for subjectivity_score: {type(record['subjectivity_score'])}")
            
        if "toxicity_score" in record and not isinstance(record["toxicity_score"], (int, float)):
            errors.append(f"Invalid type for toxicity_score: {type(record['toxicity_score'])}")
            
        if "sarcasm_detection" in record and not isinstance(record["sarcasm_detection"], bool):
            errors.append(f"Invalid type for sarcasm_detection: {type(record['sarcasm_detection'])}")
        
        # Check value ranges
        if "sentiment_score" in record and (record["sentiment_score"] < -1.0 or record["sentiment_score"] > 1.0):
            errors.append(f"sentiment_score out of range [-1.0, 1.0]: {record['sentiment_score']}")
            
        if "sentiment_magnitude" in record and (record["sentiment_magnitude"] < 0.0 or record["sentiment_magnitude"] > 1.0):
            errors.append(f"sentiment_magnitude out of range [0.0, 1.0]: {record['sentiment_magnitude']}")
            
        if "subjectivity_score" in record and (record["subjectivity_score"] < 0.0 or record["subjectivity_score"] > 1.0):
            errors.append(f"subjectivity_score out of range [0.0, 1.0]: {record['subjectivity_score']}")
            
        if "toxicity_score" in record and (record["toxicity_score"] < 0.0 or record["toxicity_score"] > 1.0):
            errors.append(f"toxicity_score out of range [0.0, 1.0]: {record['toxicity_score']}")
        
        return len(errors) == 0, errors
        
    def write_data(self, data: List[Dict[str, Any]]) -> int:
        """
        Write advanced sentiment data to Iceberg table.
        
        Args:
            data: List of sentiment data records with advanced fields
            
        Returns:
            int: Number of records written
        """
        if not data:
            self.logger.warning("No data to write")
            return 0
            
        # Prepare records
        processed_records = []
        skipped_records = 0
        
        for item in data:
            # Validate the record
            is_valid, errors = self._validate_record(item)
            if not is_valid:
                self.logger.warning(f"Skipping invalid record: {errors}")
                skipped_records += 1
                continue
                
            # Generate default message_id if not provided
            if "message_id" not in item:
                item["message_id"] = str(uuid.uuid4())
                
            # Set default timestamps if not provided
            current_time = datetime.utcnow()
            if "event_timestamp" not in item:
                item["event_timestamp"] = item.get("timestamp", current_time)
            if "ingestion_timestamp" not in item:
                item["ingestion_timestamp"] = current_time
                
            # Set default values for required fields if missing
            item.setdefault("source_system", "unknown")
            item.setdefault("text_content", item.get("text", ""))
            item.setdefault("sentiment_score", item.get("sentiment", 0.0))
            item.setdefault("sentiment_magnitude", item.get("confidence", 0.5))
            item.setdefault("primary_emotion", "neutral")
            item.setdefault("sarcasm_detection", False)
            item.setdefault("subjectivity_score", 0.0)
            item.setdefault("toxicity_score", 0.0)
            item.setdefault("user_intent", "information_seeking")
            item.setdefault("processing_version", "1.0.0")
            
            # Add to records
            processed_records.append(item)
        
        if not processed_records:
            self.logger.warning("No valid records to write after validation")
            return 0
            
        # Write with retry logic
        for attempt in range(self.max_retries):
            try:
                # Get a writer from the table
                writer = self.table.new_append()
                
                # Add all records
                for record in processed_records:
                    writer.append(record)
                    
                # Commit the write operation
                writer.commit()
                
                self.logger.info(f"Successfully wrote {len(processed_records)} records (skipped {skipped_records})")
                return len(processed_records)
                
            except Exception as e:
                self.logger.error(f"Write attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    self.logger.info(f"Retrying in {self.retry_delay/1000} seconds...")
                    time.sleep(self.retry_delay / 1000)
                else:
                    self.logger.error(f"Failed to write data after {self.max_retries} attempts")
                    raise
        
        return 0
        
    def write_sentiment_analysis_result(
        self, 
        message_id: str,
        text_content: str,
        source_system: str,
        analysis_result: Dict[str, Any],
        ticker: Optional[str] = None,
        article_title: Optional[str] = None,
        source_url: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> int:
        """
        Write a complete sentiment analysis result with all advanced fields.
        
        Args:
            message_id: Unique identifier for the message
            text_content: Raw text content that was analyzed
            source_system: Source system identifier
            analysis_result: Complete analysis results from ML pipeline
            ticker: Optional stock ticker symbol
            article_title: Optional article title
            source_url: Optional source URL
            model_name: Optional model name/version used
            
        Returns:
            int: Number of records written (0 or 1)
        """
        # Prepare record with all fields from the analysis result
        record = {
            "message_id": message_id,
            "event_timestamp": analysis_result.get("event_timestamp", datetime.utcnow()),
            "ingestion_timestamp": datetime.utcnow(),
            "source_system": source_system,
            "text_content": text_content,
            
            # Core sentiment fields
            "sentiment_score": analysis_result.get("sentiment_score", 0.0),
            "sentiment_magnitude": analysis_result.get("sentiment_magnitude", 0.0),
            "primary_emotion": analysis_result.get("primary_emotion", "neutral"),
            
            # Advanced sentiment fields
            "emotion_intensity_vector": analysis_result.get("emotion_intensity_vector", {}),
            "aspect_target_identification": analysis_result.get("aspect_target_identification", []),
            "aspect_based_sentiment": analysis_result.get("aspect_based_sentiment", {}),
            "sarcasm_detection": analysis_result.get("sarcasm_detection", False),
            "subjectivity_score": analysis_result.get("subjectivity_score", 0.0),
            "toxicity_score": analysis_result.get("toxicity_score", 0.0),
            "entity_recognition": analysis_result.get("entity_recognition", []),
            "user_intent": analysis_result.get("user_intent", "information_seeking"),
            "influence_score": analysis_result.get("influence_score", None),
            
            # Metadata
            "processing_version": analysis_result.get("processing_version", "1.0.0"),
            
            # Financial context
            "ticker": ticker,
            "article_title": article_title,
            "source_url": source_url,
            "model_name": model_name
        }
        
        # Write the record
        return self.write_data([record])