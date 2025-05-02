#!/usr/bin/env python3
"""
Local testing script for Phase 4 implementation without Azure.

This script tests the Iceberg data tier with local Dremio and MinIO instead of Azure,
which allows for local testing before the Azure migration.
"""
import os
import sys
import json
import time
import logging
import argparse
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from iceberg_lake.writer.dremio_jdbc_writer import DremioJdbcWriter
import pandas as pd


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


def create_output_dir(output_dir: str) -> str:
    """
    Create a report directory for this test run.
    
    Args:
        output_dir: Base output directory
        
    Returns:
        str: Path to the report directory
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = os.path.join(output_dir, f"test_run_{timestamp}")
    
    try:
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
            logging.info(f"Created report directory: {report_dir}")
    except Exception as e:
        logging.error(f"Failed to create report directory {report_dir}: {str(e)}")
        sys.exit(1)
        
    return report_dir


def test_dremio_connectivity(config: Dict[str, Any]) -> bool:
    """
    Test Dremio JDBC connectivity.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        bool: Whether the test was successful
    """
    logging.info("Testing Dremio JDBC connectivity...")
    
    try:
        # Create Dremio JDBC writer
        writer = DremioJdbcWriter(
            dremio_host=config["dremio"]["host"],
            dremio_port=config["dremio"]["port"],
            dremio_username=config["dremio"]["username"],
            dremio_password=config["dremio"]["password"],
            catalog=config["dremio"]["catalog"],
            namespace=config["dremio"]["namespace"],
            table_name=config["dremio"]["table_name"]
        )
        
        # Test connection
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


def test_table_creation(config: Dict[str, Any]) -> bool:
    """
    Test Iceberg table creation in Dremio.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        bool: Whether the test was successful
    """
    logging.info("Testing Iceberg table creation in Dremio...")
    
    try:
        # Create Dremio JDBC writer
        writer = DremioJdbcWriter(
            dremio_host=config["dremio"]["host"],
            dremio_port=config["dremio"]["port"],
            dremio_username=config["dremio"]["username"],
            dremio_password=config["dremio"]["password"],
            catalog=config["dremio"]["catalog"],
            namespace=config["dremio"]["namespace"],
            table_name=config["dremio"]["table_name"]
        )
        
        # Test table creation
        writer._ensure_table_exists()
        logging.info(f"✅ Iceberg table creation successful: {writer.table_identifier}")
        return True
    except Exception as e:
        logging.error(f"❌ Iceberg table creation failed: {str(e)}")
        return False


def test_sample_write(config: Dict[str, Any]) -> bool:
    """
    Test writing a sample record to Iceberg.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        bool: Whether the test was successful
    """
    logging.info("Testing sample record write to Iceberg...")
    
    try:
        # Create Dremio JDBC writer
        writer = DremioJdbcWriter(
            dremio_host=config["dremio"]["host"],
            dremio_port=config["dremio"]["port"],
            dremio_username=config["dremio"]["username"],
            dremio_password=config["dremio"]["password"],
            catalog=config["dremio"]["catalog"],
            namespace=config["dremio"]["namespace"],
            table_name=config["dremio"]["table_name"]
        )
        
        # Create test record
        from datetime import datetime
        test_record = {
            "message_id": f"test-{datetime.utcnow().isoformat()}",
            "event_timestamp": datetime.utcnow(),
            "ingestion_timestamp": datetime.utcnow(),
            "source_system": "test",
            "text_content": "Local test",
            "sentiment_score": 0.8,
            "sentiment_magnitude": 0.5,
            "primary_emotion": "positive",
            "sarcasm_detection": False,
            "subjectivity_score": 0.2,
            "toxicity_score": 0.0,
            "user_intent": "test",
            "processing_version": "1.0.0"
        }
        
        # Write test record
        written_count = writer.write_data([test_record])
        
        if written_count > 0:
            logging.info(f"✅ Successfully wrote {written_count} record to Iceberg")
            return True
        else:
            logging.error("❌ Failed to write test record to Iceberg")
            return False
    except Exception as e:
        logging.error(f"❌ Sample record write failed: {str(e)}")
        return False


def test_parquet_migration(config: Dict[str, Any], ticker: str) -> bool:
    """
    Test migrating a Parquet file to Iceberg.
    
    Args:
        config: Configuration dictionary
        ticker: Ticker symbol to migrate
        
    Returns:
        bool: Whether the test was successful
    """
    logging.info(f"Testing migration of Parquet file for ticker {ticker}...")
    
    try:
        # Create Dremio JDBC writer
        writer = DremioJdbcWriter(
            dremio_host=config["dremio"]["host"],
            dremio_port=config["dremio"]["port"],
            dremio_username=config["dremio"]["username"],
            dremio_password=config["dremio"]["password"],
            catalog=config["dremio"]["catalog"],
            namespace=config["dremio"]["namespace"],
            table_name=config["dremio"]["table_name"]
        )
        
        # Check if Parquet file exists
        parquet_file = os.path.join(config["test"]["parquet_dir"], f"{ticker}_sentiment.parquet")
        if not os.path.exists(parquet_file):
            logging.error(f"❌ Parquet file not found: {parquet_file}")
            return False
        
        # Read Parquet file
        df = pd.read_parquet(parquet_file)
        logging.info(f"Read {len(df)} records from {parquet_file}")
        
        # Prepare records
        records = []
        for _, row in df.iterrows():
            record = row.to_dict()
            # Process timestamps
            if "event_timestamp" not in record and "timestamp" in record:
                record["event_timestamp"] = record["timestamp"]
            if "ingestion_timestamp" not in record:
                record["ingestion_timestamp"] = datetime.utcnow()
            # Ensure required fields
            record.setdefault("sentiment_score", 0.0)
            record.setdefault("sentiment_magnitude", 0.5)
            record.setdefault("primary_emotion", "neutral")
            record.setdefault("sarcasm_detection", False)
            record.setdefault("subjectivity_score", 0.0)
            record.setdefault("toxicity_score", 0.0)
            record.setdefault("user_intent", "information_seeking")
            record.setdefault("processing_version", "1.0.0")
            records.append(record)
        
        # Write in batches
        batch_size = config["test"]["batch_size"]
        total_written = 0
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            written = writer.write_data(batch)
            total_written += written
            logging.info(f"Wrote batch {i//batch_size + 1}: {written} records")
        
        logging.info(f"✅ Successfully migrated {total_written} of {len(records)} records to Iceberg")
        return total_written > 0
    except Exception as e:
        logging.error(f"❌ Parquet migration failed: {str(e)}")
        return False


def main() -> None:
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(description='Local test for Phase 4 implementation without Azure')
    parser.add_argument('--config', default='config_local.json', help='Path to configuration file')
    parser.add_argument('--ticker', required=True, help='Ticker to migrate')
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
    
    # Create output directory
    output_dir = create_output_dir(config["test"]["output_dir"])
    
    # Save test results
    test_results = {}
    
    # Step 1: Test Dremio connectivity
    logging.info("=== Step 1: Test Dremio connectivity ===")
    connectivity_success = test_dremio_connectivity(config)
    test_results["dremio_connectivity"] = connectivity_success
    
    if not connectivity_success:
        logging.error("Dremio connectivity test failed. Stopping tests.")
        sys.exit(1)
    
    # Step 2: Test table creation
    logging.info("=== Step 2: Test Iceberg table creation ===")
    table_success = test_table_creation(config)
    test_results["table_creation"] = table_success
    
    if not table_success:
        logging.error("Iceberg table creation test failed. Stopping tests.")
        sys.exit(1)
    
    # Step 3: Test sample write
    logging.info("=== Step 3: Test sample record write ===")
    write_success = test_sample_write(config)
    test_results["sample_write"] = write_success
    
    if not write_success:
        logging.error("Sample record write test failed. Stopping tests.")
        sys.exit(1)
    
    # Step 4: Test Parquet migration
    logging.info("=== Step 4: Test Parquet migration ===")
    migration_success = test_parquet_migration(config, args.ticker)
    test_results["parquet_migration"] = migration_success
    
    # Save test results
    results_file = os.path.join(output_dir, "test_results.json")
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "overall_success": all(test_results.values()),
            "tests": test_results
        }, f, indent=2)
    
    # Print overall results
    if all(test_results.values()):
        print("\n✅ All local tests passed successfully!")
        print(f"\nTest results saved to: {results_file}")
        print("\nTo complete verification, please check the following:")
        print("1. Log in to Dremio UI and verify the migrated data exists")
        print("2. Run sample queries in Dremio to verify the data is correct")
        print(f"3. Check the test results in {output_dir}")
        sys.exit(0)
    else:
        print("\n❌ Some local tests failed. Please check the logs.")
        print(f"\nTest results saved to: {results_file}")
        sys.exit(1)


if __name__ == '__main__':
    main()