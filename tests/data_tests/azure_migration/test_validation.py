#!/usr/bin/env python3
"""
UAT test script for migration validation.

This script validates the integrity of data migrated from Parquet to Iceberg tables
in Azure Blob Storage via Dremio.
"""
import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, Any, Optional
from datetime import datetime

import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from iceberg_lake.azure.storage import AzureBlobStorageConfig
from iceberg_lake.azure.auth import AzureServicePrincipalAuth
from iceberg_lake.azure.writer import AzureDremioJdbcWriter
from iceberg_lake.azure.validation import MigrationValidator


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


def create_output_dir(output_dir: str) -> None:
    """
    Create the output directory if it doesn't exist.
    
    Args:
        output_dir: Path to the output directory
    """
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logging.info(f"Created output directory: {output_dir}")
    except Exception as e:
        logging.error(f"Failed to create output directory {output_dir}: {str(e)}")
        sys.exit(1)


def progress_callback(message: str, progress: float) -> None:
    """
    Callback function for progress updates.
    
    Args:
        message: Progress message
        progress: Progress value (0.0 to 1.0)
    """
    print(f"\r[{progress:.1%}] {message}", end="")
    sys.stdout.flush()


def test_migration_validation(
    writer: AzureDremioJdbcWriter, 
    config: Dict[str, Any],
    parquet_file: str
) -> bool:
    """
    Test migration validation.
    
    Args:
        writer: Azure Dremio JDBC writer
        config: Configuration dictionary
        parquet_file: Path to the Parquet file to validate
        
    Returns:
        bool: Whether the test was successful
    """
    # Get configuration values
    validation_sample_size = config["test"]["validation_sample_size"]
    output_dir = config["test"]["output_dir"]
    
    # Create output directory
    create_output_dir(output_dir)
    
    # Create the validator
    validator = MigrationValidator(
        dremio_writer=writer,
        validation_sample_size=validation_sample_size,
        progress_callback=progress_callback
    )
    
    # Start validation
    start_time = time.time()
    
    # Construct the fully qualified table name
    table_name = f"{writer.catalog}.{writer.namespace}.{writer.table_name}"
    
    # Run validation
    logging.info(f"Validating migration of Parquet file: {parquet_file}")
    is_valid, validation_results = validator.validate_parquet_file(parquet_file, table_name)
    
    # Calculate duration
    end_time = time.time()
    duration = end_time - start_time
    
    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(output_dir, f"validation_report_{timestamp}.json")
    validator.generate_validation_report(validation_results, report_file)
    
    # Log results
    logging.info(f"\nValidation complete in {duration:.2f} seconds")
    logging.info(f"Validation result: {'✅ Valid' if is_valid else '❌ Invalid'}")
    
    if is_valid:
        logging.info("All validation checks passed:")
        if validation_results.get("row_count_validation", {}).get("is_valid"):
            logging.info(f"✅ Row count validation: {validation_results['row_count_validation']['source_count']} rows")
        if validation_results.get("statistical_validation", {}).get("is_valid"):
            logging.info(f"✅ Statistical validation passed")
        if validation_results.get("sample_validation", {}).get("is_valid"):
            match_percentage = validation_results.get("sample_validation", {}).get("match_percentage", 0)
            logging.info(f"✅ Sample validation: {match_percentage:.1f}% match rate")
    else:
        logging.error("Validation failed:")
        if not validation_results.get("row_count_validation", {}).get("is_valid"):
            source_count = validation_results.get("row_count_validation", {}).get("source_count", 0)
            target_count = validation_results.get("row_count_validation", {}).get("target_count", 0)
            logging.error(f"❌ Row count mismatch: source={source_count}, target={target_count}")
        if not validation_results.get("statistical_validation", {}).get("is_valid"):
            logging.error(f"❌ Statistical validation failed")
        if not validation_results.get("sample_validation", {}).get("is_valid"):
            match_percentage = validation_results.get("sample_validation", {}).get("match_percentage", 0)
            logging.error(f"❌ Sample validation failed: {match_percentage:.1f}% match rate")
    
    logging.info(f"Validation report written to: {report_file}")
    
    return is_valid


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='UAT test for migration validation')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--parquet-file', required=True, help='Path to the Parquet file to validate')
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
    
    # Test migration validation
    validation_success = test_migration_validation(writer, config, args.parquet_file)
    
    # Print overall results
    if validation_success:
        print("\n✅ Migration validation test passed successfully!")
        print("\nTo complete verification, please check the following:")
        print("1. Review the validation report for detailed results")
        print("2. Verify row counts match between source and target")
        print("3. Verify statistical metrics match between source and target")
        print("4. Verify sampled records match between source and target")
        sys.exit(0)
    else:
        print("\n❌ Migration validation test failed. Please check the logs and validation report.")
        sys.exit(1)


if __name__ == '__main__':
    main()