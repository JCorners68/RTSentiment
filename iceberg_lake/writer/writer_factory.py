"""
Writer factory module for Iceberg sentiment data.

This module provides a factory for creating the appropriate Iceberg writer
based on configuration and availability.
"""
import logging
import os
from typing import Optional, Dict, Any

from iceberg_lake.utils.config import IcebergConfig


class WriterFactory:
    """
    Factory for creating Iceberg writers.
    
    This factory can create either a direct PyIceberg writer or a
    Dremio JDBC writer based on configuration and availability.
    """
    
    def __init__(self, config: Optional[IcebergConfig] = None):
        """
        Initialize the writer factory.
        
        Args:
            config: Optional IcebergConfig instance. If not provided,
                   a new instance will be created.
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or IcebergConfig()
    
    def create_writer(self, writer_type: str = "auto"):
        """
        Create an Iceberg writer of the specified type.
        
        Args:
            writer_type: Type of writer to create. Options are:
                        - "auto": Choose the best available writer
                        - "pyiceberg": Use direct PyIceberg writer
                        - "dremio": Use Dremio JDBC writer
        
        Returns:
            An Iceberg writer instance
        """
        # If auto, determine the best writer type
        if writer_type == "auto":
            # Check for Dremio JDBC driver
            jdbc_driver_available = self._check_jdbc_driver_available()
            
            # Use PyIceberg writer by default, unless Dremio is specifically configured
            dremio_config = self.config.get_dremio_config()
            explicitly_configured_for_dremio = all([
                dremio_config.get('endpoint'),
                dremio_config.get('username'),
                dremio_config.get('password')
            ])
            
            if explicitly_configured_for_dremio and jdbc_driver_available:
                writer_type = "dremio"
            else:
                writer_type = "pyiceberg"
        
        # Create the appropriate writer
        if writer_type == "dremio":
            return self._create_dremio_writer()
        else:
            return self._create_pyiceberg_writer()
    
    def _check_jdbc_driver_available(self) -> bool:
        """
        Check if a Dremio JDBC driver is available.
        
        Returns:
            bool: True if driver is available, False otherwise
        """
        try:
            import jaydebeapi
            
            # Check for JAR file in current directory or parent directories
            jar_files = []
            
            # Check current directory
            jar_files.extend([f for f in os.listdir('.') if f.endswith('.jar') and 'dremio' in f.lower()])
            
            # Check if we found any JAR files
            if jar_files:
                self.logger.info(f"Found Dremio JDBC driver: {jar_files[0]}")
                return True
            
            # Try to import the driver directly
            try:
                from jpype import isJVMStarted
                return True
            except ImportError:
                pass
                
            self.logger.warning("No Dremio JDBC driver JAR found. You'll need a driver on the CLASSPATH.")
            return False
            
        except ImportError:
            self.logger.warning("jaydebeapi package not available. Cannot use JDBC writer.")
            return False
    
    def _create_dremio_writer(self):
        """
        Create a Dremio JDBC writer.
        
        Returns:
            DremioJdbcWriter: A configured Dremio JDBC writer
        """
        from iceberg_lake.writer.dremio_jdbc_writer import DremioJdbcWriter
        
        # Get Dremio configuration
        dremio_config = self.config.get_dremio_config()
        catalog_config = self.config.get_catalog_config()
        writer_config = self.config.get_writer_config()
        
        # Parse endpoint URL to get host
        endpoint = dremio_config.get('endpoint', 'http://localhost:9047')
        if '://' in endpoint:
            host = endpoint.split('://')[1].split(':')[0]
        else:
            host = endpoint.split(':')[0]
        
        # Check for jar file
        jar_files = [f for f in os.listdir('.') if f.endswith('.jar') and 'dremio' in f.lower()]
        jar_path = jar_files[0] if jar_files else None
        
        self.logger.info(f"Creating Dremio JDBC writer for {host}:{dremio_config.get('jdbc_port', 31010)}")
        
        # Create and return the writer
        return DremioJdbcWriter(
            dremio_host=host,
            dremio_port=dremio_config.get('jdbc_port', 31010),
            dremio_username=dremio_config.get('username', 'dremio'),
            dremio_password=dremio_config.get('password', 'dremio123'),
            catalog=dremio_config.get('catalog', 'DREMIO'),
            namespace=catalog_config.get('namespace', 'sentiment'),
            table_name=catalog_config.get('table_name', 'sentiment_data'),
            max_retries=writer_config.get('max_retries', 3),
            retry_delay=writer_config.get('retry_delay', 1000),
            jar_path=jar_path
        )
    
    def _create_pyiceberg_writer(self):
        """
        Create a direct PyIceberg writer.
        
        Returns:
            IcebergSentimentWriter: A configured PyIceberg writer
        """
        from iceberg_lake.writer.iceberg_writer import IcebergSentimentWriter
        
        # Get catalog configuration
        catalog_config = self.config.get_catalog_config()
        writer_config = self.config.get_writer_config()
        
        self.logger.info(f"Creating PyIceberg writer for {catalog_config.get('uri')}")
        
        # Create and return the writer
        return IcebergSentimentWriter(
            catalog_uri=catalog_config.get('uri'),
            warehouse_location=catalog_config.get('warehouse_location'),
            namespace=catalog_config.get('namespace', 'sentiment'),
            table_name=catalog_config.get('table_name', 'sentiment_data'),
            max_retries=writer_config.get('max_retries', 3),
            retry_delay=writer_config.get('retry_delay', 1000)
        )