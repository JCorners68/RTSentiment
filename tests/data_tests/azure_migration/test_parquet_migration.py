#!/usr/bin/env python3
"""
UAT test script for Parquet to Iceberg migration to Azure Blob Storage.

This script verifies that Parquet files can be migrated to Iceberg tables
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

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from iceberg_lake.azure.storage import AzureBlobStorageConfig
from iceberg_lake.azure.auth import AzureServicePrincipalAuth
from iceberg_lake.azure.writer import AzureDremioJdbcWriter
from iceberg_lake.azure.migration import ParquetToIcebergMigrator


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


def test_parquet_migration(
    writer: AzureDremioJdbcWriter, 
    config: Dict[str, Any],
    ticker: Optional[str] = None
) -> bool:
    """
    Test Parquet file migration to Iceberg.
    
    Args:
        writer: Azure Dremio JDBC writer
        config: Configuration dictionary
        ticker: Optional ticker to migrate (migrates all tickers if None)
        
    Returns:
        bool: Whether the test was successful
    """
    # Get configuration values
    parquet_dir = config["test"]["parquet_dir"]
    batch_size = config["test"]["batch_size"]
    max_workers = config["test"]["max_workers"]
    validation_sample_size = config["test"]["validation_sample_size"]
    output_dir = config["test"]["output_dir"]
    
    # Create output directory
    create_output_dir(output_dir)
    
    # Create the migrator
    migrator = ParquetToIcebergMigrator(
        dremio_writer=writer,
        batch_size=batch_size,
        max_workers=max_workers,
        validation_sample_size=validation_sample_size,
        progress_callback=progress_callback
    )
    
    # Start migration
    start_time = time.time()
    
    # Determine the pattern based on ticker
    if ticker:
        pattern = f"{ticker}_sentiment.parquet"
        logging.info(f"Migrating Parquet file for ticker {ticker}...")
    else:
        pattern = "*sentiment.parquet"
        logging.info(f"Migrating all Parquet files...")
    
    # Run migration
    migration_results = migrator.migrate_directory(parquet_dir, pattern)
    
    # Calculate duration
    end_time = time.time()
    duration = end_time - start_time
    
    # Generate report
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(output_dir, f"migration_report_{timestamp}.json")
    migrator.generate_migration_report(report_file)
    
    # Check results
    success_rate = migration_results["processed_files"] / migration_results["total_files"] if migration_results["total_files"] > 0 else 0
    
    # Log results
    logging.info(f"\nMigration complete in {duration:.2f} seconds")
    logging.info(f"Files processed: {migration_results['processed_files']} of {migration_results['total_files']}")
    logging.info(f"Records migrated: {migration_results['migrated_records']} of {migration_results['total_records']}")
    logging.info(f"Failed files: {migration_results['failed_files']}")
    logging.info(f"Success rate: {success_rate:.1%}")
    logging.info(f"Migration report written to: {report_file}")
    
    # Success if at least 90% of files were migrated successfully
    return success_rate >= 0.9


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='UAT test for Parquet to Iceberg migration')
    parser.add_argument('--config', default='config.json', help='Path to configuration file')
    parser.add_argument('--ticker', help='Ticker to migrate (migrates all tickers if not specified)')
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
    
    # Test Parquet migration
    migration_success = test_parquet_migration(writer, config, args.ticker)
    
    # Print overall results
    if migration_success:
        print("\n✅ Parquet migration test passed successfully!")
        print("\nTo complete verification, please check the following:")
        print("1. Log in to Dremio UI and verify the migrated data exists")
        print("2. Run sample queries in Dremio to verify the data is correct")
        print("3. Review the migration report for detailed results")
        sys.exit(0)
    else:
        print("\n❌ Parquet migration test failed. Please check the logs and migration report.")
        sys.exit(1)


if __name__ == '__main__':
    main()