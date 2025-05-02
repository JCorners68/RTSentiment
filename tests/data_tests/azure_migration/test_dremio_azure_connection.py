#!/usr/bin/env python3
"""
UAT test script for Dremio JDBC connection with Azure Blob Storage.

This script verifies that Dremio can connect to Iceberg tables in Azure Blob Storage
via JDBC and create/query tables successfully.
"""
import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from iceberg_lake.azure.storage import AzureBlobStorageConfig
from iceberg_lake.azure.auth import AzureServicePrincipalAuth
from iceberg_lake.azure.writer import AzureDremioJdbcWriter


def setup_logging(verbose: bool = False) -> None:
    """
    Set up logging configuration.
    
    Args:
        verbose: Whether to enable verbose logging
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load configuration from {config_path}: {str(e)}")
        sys.exit(1)


def create_azure_dremio_writer(config: Dict[str, Any]) -> AzureDremioJdbcWriter:
    """
    Create an Azure-specific Dremio JDBC writer.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        AzureDremioJdbcWriter: Writer instance
    """
    # Create Azure Blob Storage configuration
    azure_config = AzureBlobStorageConfig(
        connection_string=config["azure"].get("connection_string"),
        account_name=config["azure"].get("account_name"),
        account_key=config["azure"].get("account_key"),
        container_name=config["azure"].get("container_name"),
        folder_path=config["azure"].get("folder_path"),
        service_principal_id=config["azure"].get("service_principal_id"),
        service_principal_secret=config["azure"].get("service_principal_secret"),
        tenant_id=config["azure"].get("tenant_id")
    )
    
    # Create service principal authentication
    sp_auth = AzureServicePrincipalAuth(
        client_id=config["azure"].get("service_principal_id"),
        client_secret=config["azure"].get("service_principal_secret"),
        tenant_id=config["azure"].get("tenant_id")
    )
    
    # Create Azure-specific Dremio JDBC writer
    writer = AzureDremioJdbcWriter(
        dremio_host=config["dremio"]["host"],
        dremio_port=config["dremio"]["port"],
        dremio_username=config["dremio"]["username"],
        dremio_password=config["dremio"]["password"],
        catalog=config["dremio"]["catalog"],
        namespace=config["dremio"]["namespace"],
        table_name=config["dremio"]["table_name"],
        azure_storage_config=azure_config,
        azure_service_principal_auth=sp_auth
    )
    
    return writer


def test_dremio_jdbc_connection(writer: AzureDremioJdbcWriter) -> bool:
    """
    Test Dremio JDBC connection.
    
    Args:
        writer: Azure Dremio JDBC writer
        
    Returns:
        bool: Whether the test was successful
    """
    logging.info("Testing Dremio JDBC connection...")
    
    try:
        # Test connection using internal method
        connection = writer._get_connection()
        if connection:
            logging.info("✅ Dremio JDBC connection successful")
            return True
        else:
            logging.error("❌ Dremio JDBC connection failed")
            return False
    except Exception as e:
        logging.error(f"❌ Dremio JDBC connection failed: {str(e)}")
        return False


def test_dremio_table_creation(writer: AzureDremioJdbcWriter) -> bool:
    """
    Test Dremio JDBC table creation.
    
    Args:
        writer: Azure Dremio JDBC writer
        
    Returns:
        bool: Whether the test was successful
    """
    logging.info("Testing Dremio table creation...")
    
    try:
        # Test table creation using internal method
        writer._ensure_table_exists()
        logging.info(f"✅ Dremio table creation successful: {writer.table_identifier}")
        return True
    except Exception as e:
        logging.error(f"❌ Dremio table creation failed: {str(e)}")
        return False


def test_end_to_end_functionality(writer: AzureDremioJdbcWriter) -> bool:
    """
    Test end-to-end functionality.
    
    Args:
        writer: Azure Dremio JDBC writer
        
    Returns:
        bool: Whether the test was successful
    """
    logging.info("Testing end-to-end functionality...")
    
    try:
        # Test end-to-end functionality
        success, message = writer.test_end_to_end()
        
        if success:
            logging.info(f"✅ End-to-end test successful: {message}")
            return True
        else:
            logging.error(f"❌ End-to-end test failed: {message}")
            return False
    except Exception as e:
        logging.error(f"❌ End-to-end test failed: {str(e)}")
        return False


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='UAT test for Dremio JDBC connection with Azure')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    
    # Determine the config path
    if not os.path.isabs(args.config):
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), args.config))
    else:
        config_path = args.config
        
    # Load configuration
    config = load_config(config_path)
    
    # Create writer
    writer = create_azure_dremio_writer(config)
    
    # Test JDBC connection
    connection_success = test_dremio_jdbc_connection(writer)
    
    # Test table creation (if connection successful)
    table_success = False
    if connection_success:
        table_success = test_dremio_table_creation(writer)
    
    # Test end-to-end functionality (if connection and table successful)
    e2e_success = False
    if connection_success and table_success:
        e2e_success = test_end_to_end_functionality(writer)
    
    # Print overall results
    if connection_success and table_success and e2e_success:
        print("\n✅ All Dremio JDBC tests passed successfully!")
        print("\nTo complete verification, please check the following:")
        print("1. Log in to Dremio UI and verify the table exists")
        print("2. Run a sample query in Dremio to verify the test record exists")
        print("3. Verify the table is properly configured with Azure Blob Storage")
        sys.exit(0)
    else:
        print("\n❌ Some Dremio JDBC tests failed. Please check the logs.")
        sys.exit(1)


if __name__ == '__main__':
    main()