"""
Dremio JDBC writer module for the sentiment analysis system.

This module provides a writer for storing sentiment analysis data in Iceberg tables
via Dremio's JDBC interface, as recommended in Phase 2 of the data tier plan.
"""
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import jaydebeapi

from iceberg_lake.schema.iceberg_schema import create_sentiment_schema


class DremioJdbcWriter:
    """
    Writer for storing sentiment analysis data in Iceberg tables via Dremio JDBC.
    
    This class implements the Phase 2 approach from the data tier plan, using
    JDBC to write to Dremio instead of direct PyIceberg interaction.
    """
    
    def __init__(
        self,
        dremio_host: str,
        dremio_port: int,
        dremio_username: str,
        dremio_password: str,
        catalog: str = "DREMIO",
        namespace: str = "sentiment",
        table_name: str = "sentiment_data",
        max_retries: int = 3,
        retry_delay: int = 1000,  # milliseconds
        jar_path: Optional[str] = None,
        driver_class: str = "com.dremio.jdbc.Driver"
    ):
        """
        Initialize Dremio JDBC writer for advanced sentiment data.
        
        Args:
            dremio_host: Dremio server hostname
            dremio_port: Dremio JDBC port (usually 31010)
            dremio_username: Dremio username
            dremio_password: Dremio password
            catalog: Dremio catalog name
            namespace: Schema/namespace for the table
            table_name: Table name for sentiment data
            max_retries: Maximum number of write retries
            retry_delay: Delay between retries (ms)
            jar_path: Path to Dremio JDBC driver JAR file (optional)
            driver_class: JDBC driver class name
        """
        self.logger = logging.getLogger(__name__)
        
        # Connection parameters
        self.dremio_host = dremio_host
        self.dremio_port = dremio_port
        self.dremio_username = dremio_username
        self.dremio_password = dremio_password
        self.catalog = catalog
        self.namespace = namespace
        self.table_name = table_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.jar_path = jar_path
        self.driver_class = driver_class
        
        # Construct the JDBC URL for Dremio
        self.jdbc_url = f"jdbc:dremio:direct={dremio_host}:{dremio_port}"
        
        # Construct the full table identifier
        self.table_identifier = f'"{catalog}"."{namespace}"."{table_name}"'
        
        # Initialize connection pool
        self.connection = None
        
        # Verify JDBC driver availability first
        self._verify_jdbc_driver()
        
        # Ensure the table exists
        self._ensure_table_exists()
    
    def _verify_jdbc_driver(self) -> None:
        """
        Verify that the Dremio JDBC driver is available.
        
        Raises:
            RuntimeError: If the driver is not found
        """
        import jpype
        import os
        
        # Check if jar_path is provided
        if self.jar_path and os.path.exists(self.jar_path):
            self.logger.info(f"Using provided JDBC driver: {self.jar_path}")
            return
            
        # Check multiple locations for the driver
        jar_paths = [
            # Check current directory
            [f for f in os.listdir('.') if f.endswith('.jar') and 'dremio' in f.lower()],
            # Check drivers directory if it exists
            [os.path.join('drivers', f) for f in os.listdir('drivers') if os.path.exists('drivers') and f.endswith('.jar') and 'dremio' in f.lower()],
            # Check standard lib directories
            [os.path.join('/usr/lib/dremio', f) for f in os.listdir('/usr/lib/dremio') if os.path.exists('/usr/lib/dremio') and f.endswith('.jar') and 'dremio' in f.lower()],
            [os.path.join('/usr/local/lib/dremio', f) for f in os.listdir('/usr/local/lib/dremio') if os.path.exists('/usr/local/lib/dremio') and f.endswith('.jar') and 'dremio' in f.lower()]
        ]
        
        # Flatten the list and take the first JAR found
        jar_files = [item for sublist in jar_paths for item in sublist]
        
        if jar_files:
            self.jar_path = jar_files[0]
            self.logger.info(f"Found Dremio JDBC driver: {self.jar_path}")
            return
            
        # Try to load the driver class directly from classpath
        try:
            if not jpype.isJVMStarted():
                jpype.startJVM()
            driver_class = jpype.JClass(self.driver_class)
            self.logger.info(f"Found Dremio JDBC driver class in classpath: {self.driver_class}")
            return
        except Exception as e:
            self.logger.warning(f"Could not load driver class from classpath: {str(e)}")
        
        raise RuntimeError(
            "Dremio JDBC driver not found. Please run scripts/setup_dremio_jdbc.sh to download and set up the driver, "
            "or provide the jar_path parameter with the path to the driver JAR file."
        )
    
    def _get_connection(self) -> jaydebeapi.Connection:
        """
        Get a JDBC connection to Dremio.
        
        Returns:
            Connection: JDBC connection object
        """
        if self.connection is None:
            try:
                self.logger.info(f"Connecting to Dremio JDBC: {self.jdbc_url}")
                
                connection_properties = {
                    "user": self.dremio_username,
                    "password": self.dremio_password
                }
                
                if self.jar_path:
                    # Connect using the provided JAR file
                    self.connection = jaydebeapi.connect(
                        self.driver_class,
                        self.jdbc_url,
                        [self.dremio_username, self.dremio_password],
                        self.jar_path
                    )
                else:
                    # Connect using the driver on the classpath
                    self.connection = jaydebeapi.connect(
                        self.driver_class,
                        self.jdbc_url,
                        [self.dremio_username, self.dremio_password]
                    )
                
                self.connection.jconn.setAutoCommit(False)
                self.logger.info("Connected to Dremio JDBC successfully")
            
            except Exception as e:
                self.logger.error(f"Failed to connect to Dremio JDBC: {str(e)}")
                raise
        
        return self.connection
    
    def _ensure_table_exists(self) -> None:
        """
        Ensure the target Iceberg table exists in Dremio, create if not.
        """
        connection = self._get_connection()
        cursor = connection.cursor()
        
        try:
            # Check if table exists
            self.logger.info(f"Checking if table exists: {self.table_identifier}")
            
            # Use Dremio's INFORMATION_SCHEMA to check for table existence
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_CATALOG = '{self.catalog}'
                AND TABLE_SCHEMA = '{self.namespace}'
                AND TABLE_NAME = '{self.table_name}'
            """)
            
            count = cursor.fetchone()[0]
            
            if count == 0:
                self.logger.info(f"Table does not exist. Creating table: {self.table_identifier}")
                self._create_table(cursor)
            else:
                self.logger.info(f"Table exists: {self.table_identifier}")
        
        except Exception as e:
            self.logger.error(f"Error checking/creating table: {str(e)}")
            connection.rollback()
            raise
        finally:
            cursor.close()
    
    def _create_table(self, cursor) -> None:
        """
        Create the Iceberg table in Dremio.
        
        Args:
            cursor: JDBC cursor
        """
        # Create the schema/namespace if it doesn't exist
        cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.catalog}"."{self.namespace}"')
        
        # Get the Iceberg schema definition
        schema = create_sentiment_schema()
        
        # Map PyIceberg schema to SQL column definitions
        column_defs = []
        for field in schema.fields:
            col_name = field.name
            
            # Map PyIceberg types to SQL types
            if field.field_type.type_name == "string":
                col_type = "VARCHAR"
            elif field.field_type.type_name == "timestamp":
                col_type = "TIMESTAMP"
            elif field.field_type.type_name == "float":
                col_type = "DOUBLE"
            elif field.field_type.type_name == "boolean":
                col_type = "BOOLEAN"
            elif field.field_type.type_name.startswith("map"):
                col_type = "VARCHAR"  # Store as JSON string
            elif field.field_type.type_name.startswith("list"):
                col_type = "VARCHAR"  # Store as JSON string
            else:
                col_type = "VARCHAR"  # Default to VARCHAR for unknown types
            
            nullable = "" if field.required else "NULL"
            column_defs.append(f'"{col_name}" {col_type} {nullable}')
        
        # Create the table with Iceberg format
        create_table_sql = f"""
        CREATE TABLE {self.table_identifier} (
            {', '.join(column_defs)}
        )
        WITH (
            type = 'ICEBERG',
            format = 'PARQUET',
            location = '{self.namespace}.{self.table_name}'
        )
        """
        
        self.logger.debug(f"Creating table with SQL: {create_table_sql}")
        cursor.execute(create_table_sql)
        self.logger.info(f"Created table: {self.table_identifier}")
    
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
    
    def _prepare_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare a record for insertion, handling default values and type conversions.
        
        Args:
            record: Raw record
            
        Returns:
            Dict[str, Any]: Prepared record
        """
        import json
        
        # Make a copy to avoid modifying the original
        prepared = record.copy()
        
        # Generate default message_id if not provided
        if "message_id" not in prepared:
            prepared["message_id"] = str(uuid.uuid4())
            
        # Set default timestamps if not provided
        current_time = datetime.utcnow()
        if "event_timestamp" not in prepared:
            prepared["event_timestamp"] = prepared.get("timestamp", current_time)
        if "ingestion_timestamp" not in prepared:
            prepared["ingestion_timestamp"] = current_time
            
        # Set default values for required fields if missing
        prepared.setdefault("source_system", "unknown")
        prepared.setdefault("text_content", prepared.get("text", ""))
        prepared.setdefault("sentiment_score", prepared.get("sentiment", 0.0))
        prepared.setdefault("sentiment_magnitude", prepared.get("confidence", 0.5))
        prepared.setdefault("primary_emotion", "neutral")
        prepared.setdefault("sarcasm_detection", False)
        prepared.setdefault("subjectivity_score", 0.0)
        prepared.setdefault("toxicity_score", 0.0)
        prepared.setdefault("user_intent", "information_seeking")
        prepared.setdefault("processing_version", "1.0.0")
        
        # Convert complex types to JSON strings
        if "emotion_intensity_vector" in prepared and isinstance(prepared["emotion_intensity_vector"], dict):
            prepared["emotion_intensity_vector"] = json.dumps(prepared["emotion_intensity_vector"])
            
        if "aspect_target_identification" in prepared and isinstance(prepared["aspect_target_identification"], list):
            prepared["aspect_target_identification"] = json.dumps(prepared["aspect_target_identification"])
            
        if "aspect_based_sentiment" in prepared and isinstance(prepared["aspect_based_sentiment"], dict):
            prepared["aspect_based_sentiment"] = json.dumps(prepared["aspect_based_sentiment"])
            
        if "entity_recognition" in prepared and isinstance(prepared["entity_recognition"], list):
            prepared["entity_recognition"] = json.dumps(prepared["entity_recognition"])
        
        # Convert boolean values
        if "sarcasm_detection" in prepared:
            prepared["sarcasm_detection"] = 1 if prepared["sarcasm_detection"] else 0
        
        return prepared
    
    def write_data(self, data: List[Dict[str, Any]]) -> int:
        """
        Write advanced sentiment data to Iceberg table via Dremio JDBC.
        
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
                
            # Prepare the record
            processed = self._prepare_record(item)
            processed_records.append(processed)
        
        if not processed_records:
            self.logger.warning("No valid records to write after validation")
            return 0
            
        # Write with retry logic
        for attempt in range(self.max_retries):
            connection = None
            cursor = None
            
            try:
                connection = self._get_connection()
                cursor = connection.cursor()
                
                # Prepare the INSERT statement
                fields = processed_records[0].keys()
                field_list = ', '.join([f'"{field}"' for field in fields])
                value_placeholders = ', '.join(['?' for _ in fields])
                
                insert_sql = f"INSERT INTO {self.table_identifier} ({field_list}) VALUES ({value_placeholders})"
                self.logger.debug(f"Insert SQL: {insert_sql}")
                
                # Prepare batch parameters
                batch_params = []
                for record in processed_records:
                    # Extract values in the same order as the fields
                    params = [record.get(field) for field in fields]
                    batch_params.append(params)
                
                # Execute batch insert
                cursor.executemany(insert_sql, batch_params)
                connection.commit()
                
                self.logger.info(f"Successfully wrote {len(processed_records)} records (skipped {skipped_records})")
                return len(processed_records)
                
            except Exception as e:
                self.logger.error(f"Write attempt {attempt + 1} failed: {str(e)}")
                if connection:
                    connection.rollback()
                
                if attempt < self.max_retries - 1:
                    self.logger.info(f"Retrying in {self.retry_delay/1000} seconds...")
                    time.sleep(self.retry_delay / 1000)
                else:
                    self.logger.error(f"Failed to write data after {self.max_retries} attempts")
                    raise
            finally:
                if cursor:
                    cursor.close()
        
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
        Write a complete sentiment analysis result with all advanced fields via Dremio JDBC.
        
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
    
    def close(self) -> None:
        """Close the JDBC connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                self.logger.info("Closed JDBC connection")
            except Exception as e:
                self.logger.error(f"Error closing JDBC connection: {str(e)}")