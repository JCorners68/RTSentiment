#!/usr/bin/env python3
"""
UAT test script for Azure Blob Storage setup.

This script verifies that Azure Blob Storage can be properly configured
for use with Iceberg tables via Dremio.
"""
import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from iceberg_lake.azure.storage import AzureBlobStorageConfig, AzureBlobStorageManager
from iceberg_lake.azure.auth import AzureServicePrincipalAuth


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


def test_azure_blob_storage(config: Dict[str, Any]) -> bool:
    """
    Test Azure Blob Storage configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        bool: Whether the test was successful
    """
    logging.info("Testing Azure Blob Storage configuration...")
    
    # Create configuration
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
    
    # Create storage manager
    storage_manager = AzureBlobStorageManager(azure_config)
    
    # Test connectivity
    success, message = storage_manager.test_connectivity()
    
    if success:
        logging.info(f"✅ Azure Blob Storage test successful: {message}")
        
        # Show storage location
        location = storage_manager.get_dremio_storage_location()
        logging.info(f"✅ Dremio storage location: {location}")
        
        # Get Dremio source configuration
        dremio_config = storage_manager.configure_dremio_source()
        logging.info(f"✅ Dremio source configuration: {json.dumps(dremio_config, indent=2)}")
        
        return True
    else:
        logging.error(f"❌ Azure Blob Storage test failed: {message}")
        return False


def test_service_principal_auth(config: Dict[str, Any]) -> bool:
    """
    Test service principal authentication.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        bool: Whether the test was successful
    """
    # Skip if service principal credentials not provided
    if not (config["azure"].get("service_principal_id") and 
            config["azure"].get("service_principal_secret") and 
            config["azure"].get("tenant_id")):
        logging.info("Skipping service principal authentication test - credentials not provided")
        return True
    
    logging.info("Testing Azure service principal authentication...")
    
    # Create service principal auth
    sp_auth = AzureServicePrincipalAuth(
        client_id=config["azure"].get("service_principal_id"),
        client_secret=config["azure"].get("service_principal_secret"),
        tenant_id=config["azure"].get("tenant_id")
    )
    
    # Test authentication
    success, message = sp_auth.test_authentication()
    
    if success:
        logging.info(f"✅ Azure service principal authentication test successful: {message}")
        return True
    else:
        logging.error(f"❌ Azure service principal authentication test failed: {message}")
        return False


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='UAT test for Azure Blob Storage setup')
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
    
    # Test Azure Blob Storage
    storage_success = test_azure_blob_storage(config)
    
    # Test service principal authentication
    auth_success = test_service_principal_auth(config)
    
    # Print overall results
    if storage_success and auth_success:
        print("\n✅ All Azure setup tests passed successfully!")
        print("\nTo complete verification, please check the following:")
        print("1. Verify the container exists in your Azure Storage account")
        print("2. Verify the folder structure has been created")
        print("3. Verify the Dremio storage location is correct")
        sys.exit(0)
    else:
        print("\n❌ Some Azure setup tests failed. Please check the logs.")
        sys.exit(1)


if __name__ == '__main__':
    main()