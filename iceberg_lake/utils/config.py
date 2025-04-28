"""
Configuration utilities for the Iceberg lakehouse integration.

This module provides configuration loading and validation for the Iceberg lakehouse.
"""
import os
import json
import logging
from typing import Dict, Any, Optional


class IcebergConfig:
    """Configuration manager for Iceberg lakehouse integration."""
    
    DEFAULT_CONFIG = {
        "catalog": {
            "uri": "http://localhost:8181",
            "warehouse_location": "file:///tmp/warehouse/",
            "namespace": "sentiment",
            "table_name": "sentiment_data"
        },
        "minio": {
            "endpoint_url": "http://localhost:9000",
            "access_key": "minioadmin",
            "secret_key": "minioadmin",
            "region": "us-east-1",
            "bucket": "warehouse"
        },
        "dremio": {
            "endpoint": "http://dremio:9047",
            "username": "dremio",
            "password": "dremio123",
            "jdbc_port": 31010,
            "catalog": "DREMIO"
        },
        "writer": {
            "max_retries": 3,
            "retry_delay": 1000
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.config = self.DEFAULT_CONFIG.copy()
        
        # Load from file if provided
        if config_path and os.path.exists(config_path):
            self._load_from_file(config_path)
            
        # Override with environment variables
        self._load_from_env()
        
        # Validate the configuration
        self._validate_config()
        
    def _load_from_file(self, config_path: str) -> None:
        """
        Load configuration from a JSON file.
        
        Args:
            config_path: Path to configuration file
        """
        try:
            with open(config_path, 'r') as f:
                file_config = json.load(f)
                
            # Merge with default config
            self._merge_configs(self.config, file_config)
            self.logger.info(f"Loaded configuration from {config_path}")
            
        except Exception as e:
            self.logger.warning(f"Failed to load config from {config_path}: {str(e)}")
    
    def _load_from_env(self) -> None:
        """Load configuration from environment variables."""
        # Catalog settings
        if os.environ.get('ICEBERG_CATALOG_URI'):
            self.config['catalog']['uri'] = os.environ.get('ICEBERG_CATALOG_URI')
            
        if os.environ.get('ICEBERG_WAREHOUSE_LOCATION'):
            self.config['catalog']['warehouse_location'] = os.environ.get('ICEBERG_WAREHOUSE_LOCATION')
            
        if os.environ.get('ICEBERG_NAMESPACE'):
            self.config['catalog']['namespace'] = os.environ.get('ICEBERG_NAMESPACE')
            
        if os.environ.get('ICEBERG_TABLE_NAME'):
            self.config['catalog']['table_name'] = os.environ.get('ICEBERG_TABLE_NAME')
        
        # MinIO settings
        if os.environ.get('MINIO_ENDPOINT_URL'):
            self.config['minio']['endpoint_url'] = os.environ.get('MINIO_ENDPOINT_URL')
            
        if os.environ.get('MINIO_ACCESS_KEY'):
            self.config['minio']['access_key'] = os.environ.get('MINIO_ACCESS_KEY')
            
        if os.environ.get('MINIO_SECRET_KEY'):
            self.config['minio']['secret_key'] = os.environ.get('MINIO_SECRET_KEY')
            
        if os.environ.get('MINIO_REGION'):
            self.config['minio']['region'] = os.environ.get('MINIO_REGION')
            
        if os.environ.get('MINIO_BUCKET'):
            self.config['minio']['bucket'] = os.environ.get('MINIO_BUCKET')
        
        # Dremio settings
        if os.environ.get('DREMIO_ENDPOINT'):
            self.config['dremio']['endpoint'] = os.environ.get('DREMIO_ENDPOINT')
            
        if os.environ.get('DREMIO_USERNAME'):
            self.config['dremio']['username'] = os.environ.get('DREMIO_USERNAME')
            
        if os.environ.get('DREMIO_PASSWORD'):
            self.config['dremio']['password'] = os.environ.get('DREMIO_PASSWORD')
            
        if os.environ.get('DREMIO_JDBC_PORT'):
            self.config['dremio']['jdbc_port'] = int(os.environ.get('DREMIO_JDBC_PORT'))
            
        if os.environ.get('DREMIO_CATALOG'):
            self.config['dremio']['catalog'] = os.environ.get('DREMIO_CATALOG')
        
        # Writer settings
        if os.environ.get('ICEBERG_WRITER_MAX_RETRIES'):
            self.config['writer']['max_retries'] = int(os.environ.get('ICEBERG_WRITER_MAX_RETRIES'))
            
        if os.environ.get('ICEBERG_WRITER_RETRY_DELAY'):
            self.config['writer']['retry_delay'] = int(os.environ.get('ICEBERG_WRITER_RETRY_DELAY'))
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """
        Recursively merge two configuration dictionaries.
        
        Args:
            base: Base configuration to update
            override: Configuration to override base with
        """
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_configs(base[key], value)
            else:
                base[key] = value
    
    def _validate_config(self) -> None:
        """Validate the configuration."""
        required_keys = [
            ('catalog', 'uri'),
            ('catalog', 'warehouse_location'),
            ('catalog', 'namespace'),
            ('catalog', 'table_name'),
            ('minio', 'endpoint_url'),
            ('minio', 'access_key'),
            ('minio', 'secret_key'),
            ('dremio', 'endpoint'),
            ('dremio', 'username'),
            ('dremio', 'password')
        ]
        
        for section, key in required_keys:
            if section not in self.config or key not in self.config[section]:
                raise ValueError(f"Missing required configuration: {section}.{key}")
    
    def get_catalog_config(self) -> Dict[str, Any]:
        """
        Get Iceberg catalog configuration.
        
        Returns:
            Dict[str, Any]: Catalog configuration
        """
        return self.config['catalog']
    
    def get_minio_config(self) -> Dict[str, Any]:
        """
        Get MinIO configuration.
        
        Returns:
            Dict[str, Any]: MinIO configuration
        """
        return self.config['minio']
    
    def get_dremio_config(self) -> Dict[str, Any]:
        """
        Get Dremio configuration.
        
        Returns:
            Dict[str, Any]: Dremio configuration
        """
        return self.config['dremio']
    
    def get_writer_config(self) -> Dict[str, Any]:
        """
        Get writer configuration.
        
        Returns:
            Dict[str, Any]: Writer configuration
        """
        return self.config['writer']
    
    def get_full_config(self) -> Dict[str, Any]:
        """
        Get full configuration.
        
        Returns:
            Dict[str, Any]: Full configuration
        """
        return self.config