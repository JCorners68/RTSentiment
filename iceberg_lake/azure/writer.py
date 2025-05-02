"""
Azure-specific Dremio JDBC writer for Iceberg tables in Azure Blob Storage.

This module extends the base DremioJdbcWriter to support Azure Blob Storage
as the backend for Iceberg tables, with Azure-specific configuration and optimization.
"""
import logging
import time
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import jaydebeapi

from iceberg_lake.writer.dremio_jdbc_writer import DremioJdbcWriter
from iceberg_lake.azure.storage import AzureBlobStorageConfig, AzureBlobStorageManager
from iceberg_lake.azure.auth import AzureServicePrincipalAuth


class AzureDremioJdbcWriter(DremioJdbcWriter):
    """
    Azure-specific extension of DremioJdbcWriter for Iceberg tables in Azure Blob Storage.
    
    This class extends the base DremioJdbcWriter to add Azure-specific functionality,
    including Azure Blob Storage configuration and service principal authentication.
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
        driver_class: str = "com.dremio.jdbc.Driver",
        azure_storage_config: Optional[AzureBlobStorageConfig] = None,
        azure_service_principal_auth: Optional[AzureServicePrincipalAuth] = None,
        custom_table_properties: Optional[Dict[str, str]] = None
    ):
        """
        Initialize Azure-specific DremioJdbcWriter for advanced sentiment data.
        
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
            azure_storage_config: Azure Blob Storage configuration
            azure_service_principal_auth: Azure service principal authentication
            custom_table_properties: Additional table properties for Azure optimization
        """
        self.logger = logging.getLogger(__name__)
        
        # Initialize Azure components
        self.azure_storage_config = azure_storage_config or AzureBlobStorageConfig.from_env()
        self.azure_service_principal_auth = azure_service_principal_auth or AzureServicePrincipalAuth()
        self.azure_storage_manager = AzureBlobStorageManager(self.azure_storage_config)
        
        # Table properties optimized for Azure Blob Storage
        self.azure_table_properties = {
            # Azure-specific performance optimizations
            "write.metadata.compression-codec": "gzip",  # Better for cloud storage
            "write.parquet.compression-codec": "zstd",  # Better compression for Parquet
            "write.metadata.metrics.default": "truncate(16)",  # Truncate string metrics for efficiency
            
            # Cloud storage specific settings
            "write.object-storage.enabled": "true",
            "write.object-storage.path": self.azure_storage_config.folder_path,
            
            # Azure Blob-specific properties
            "write.azure.account": self.azure_storage_config.account_name,
            "write.azure.container": self.azure_storage_config.container_name,
            
            # Merge custom properties if provided
            **(custom_table_properties or {})
        }
        
        # Prepare storage location
        try:
            # Configure the Azure storage container and folder
            self.azure_storage_manager.create_folder_structure()
            
            # Get storage location for Iceberg tables
            self.storage_location = self.azure_storage_manager.get_dremio_storage_location()
            self.logger.info(f"Using Azure storage location: {self.storage_location}")
        except Exception as e:
            self.logger.warning(f"Failed to configure Azure storage: {str(e)}")
            self.storage_location = None
        
        # Initialize the base DremioJdbcWriter
        super().__init__(
            dremio_host=dremio_host,
            dremio_port=dremio_port,
            dremio_username=dremio_username,
            dremio_password=dremio_password,
            catalog=catalog,
            namespace=namespace,
            table_name=table_name,
            max_retries=max_retries,
            retry_delay=retry_delay,
            jar_path=jar_path,
            driver_class=driver_class
        )
    
    def _create_table(self, cursor) -> None:
        """
        Create the Iceberg table in Dremio with Azure-specific optimizations.
        
        This method overrides the base implementation to add Azure-specific
        table properties and storage location.
        
        Args:
            cursor: JDBC cursor
        """
        # Create the schema/namespace if it doesn't exist
        cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{self.catalog}"."{self.namespace}"')
        
        # Get the Iceberg schema definition from the base class
        from iceberg_lake.schema.iceberg_schema import create_sentiment_schema
        schema = create_sentiment_schema()
        
        # Map PyIceberg schema to SQL column definitions
        column_defs = []
        for field in schema.fields:
            col_name = field.name
            
            # Map PyIceberg types to SQL types (unchanged from base implementation)
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
        
        # Build table properties string with Azure optimizations
        table_properties = []
        table_properties.append("type = 'ICEBERG'")
        table_properties.append("format = 'PARQUET'")
        
        # Add storage location if available
        if self.storage_location:
            table_properties.append(f"location = '{self.storage_location}'")
        else:
            # Fall back to default location from base implementation
            table_properties.append(f"location = '{self.namespace}.{self.table_name}'")
        
        # Add Azure-specific table properties
        for key, value in self.azure_table_properties.items():
            table_properties.append(f"'{key}' = '{value}'")
        
        # Create the table with Iceberg format using IF NOT EXISTS
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.table_identifier} (
            {', '.join(column_defs)}
        )
        WITH (
            {', '.join(table_properties)}
        )
        """
        
        self.logger.debug(f"Creating table with SQL: {create_table_sql}")
        cursor.execute(create_table_sql)
        self.logger.info(f"Created table: {self.table_identifier}")
        
    def test_azure_connectivity(self) -> Tuple[bool, str]:
        """
        Test connectivity to Azure Blob Storage.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            return self.azure_storage_manager.test_connectivity()
        except Exception as e:
            return False, f"Error testing Azure connectivity: {str(e)}"
    
    def test_end_to_end(self) -> Tuple[bool, str]:
        """
        Test end-to-end functionality (Azure + Dremio).
        
        This method tests both Azure connectivity and Dremio JDBC connectivity,
        including table creation and a simple write operation.
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Test Azure connectivity
            azure_success, azure_message = self.test_azure_connectivity()
            if not azure_success:
                return False, f"Azure connectivity test failed: {azure_message}"
                
            # Test Dremio connectivity via JDBC
            connection = self._get_connection()
            if not connection:
                return False, "Failed to connect to Dremio via JDBC"
                
            # Ensure table exists
            self._ensure_table_exists()
            
            # Try to write a test record
            test_record = {
                "message_id": f"test-{datetime.utcnow().isoformat()}",
                "event_timestamp": datetime.utcnow(),
                "ingestion_timestamp": datetime.utcnow(),
                "source_system": "test",
                "text_content": "Azure E2E test",
                "sentiment_score": 0.0,
                "sentiment_magnitude": 0.5,
                "primary_emotion": "neutral",
                "sarcasm_detection": False,
                "subjectivity_score": 0.0,
                "toxicity_score": 0.0,
                "user_intent": "test",
                "processing_version": "test"
            }
            
            success = self.write_data([test_record]) > 0
            if not success:
                return False, "Failed to write test record"
                
            return True, "End-to-end test successful"
            
        except Exception as e:
            return False, f"End-to-end test failed: {str(e)}"