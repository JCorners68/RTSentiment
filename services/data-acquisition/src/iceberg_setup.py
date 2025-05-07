"""
Iceberg Setup Module

This module provides utilities for setting up and working with Apache Iceberg tables.
It creates a catalog and required tables for the sentiment analysis platform if they don't exist.
"""

import os
import logging
import uuid
from typing import Optional, Dict, Any

import pyiceberg
from pyiceberg.catalog import Catalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    NestedField, StringType, TimestampType, DoubleType, UUIDType, MapType
)
from pyiceberg.partitioning import PartitionSpec, PartitionField
from pyiceberg.transforms import DayTransform, IdentityTransform

# Import configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def get_iceberg_catalog() -> Catalog:
    """
    Get or create an Iceberg catalog based on configuration.
    
    Returns:
        Catalog: An Iceberg catalog instance
    """
    config = get_config()
    catalog_name = config["iceberg"]["catalog_name"]
    warehouse_path = config["iceberg"]["warehouse"]
    
    # Ensure warehouse directory exists
    os.makedirs(warehouse_path, exist_ok=True)
    
    # Create catalog properties
    catalog_properties = {
        "warehouse": warehouse_path,
        "type": "hadoop"
    }
    
    # Get the catalog
    try:
        logger.info(f"Setting up Iceberg catalog: {catalog_name}")
        return pyiceberg.catalog.load_catalog(catalog_name, **catalog_properties)
    except Exception as e:
        logger.error(f"Error loading Iceberg catalog: {e}")
        raise

def create_sentiment_records_table(catalog: Catalog) -> None:
    """
    Create the sentiment_records table if it doesn't exist.
    
    Args:
        catalog: The Iceberg catalog instance
    """
    table_name = "sentiment_records"
    namespace = get_config()["iceberg"]["catalog_name"]
    full_table_name = f"{namespace}.{table_name}"
    
    # Check if table already exists
    if catalog.table_exists(full_table_name):
        logger.info(f"Table {full_table_name} already exists, skipping creation")
        return
    
    # Define schema
    schema = Schema(
        NestedField(1, "id", UUIDType(), required=True),
        NestedField(2, "ticker", StringType(), required=True),
        NestedField(3, "timestamp", TimestampType(), required=True),
        NestedField(4, "source", StringType(), required=True),
        NestedField(5, "text", StringType(), required=True),
        NestedField(6, "sentiment_score", DoubleType(), required=False),
        NestedField(7, "sentiment_label", StringType(), required=False),
        NestedField(8, "metadata", MapType(StringType(), StringType()), required=True)
    )
    
    # Define partition spec
    partition_spec = PartitionSpec(
        PartitionField(source_id=3, field_id=100, transform=DayTransform(), name="date"),
        PartitionField(source_id=2, field_id=101, transform=IdentityTransform(), name="ticker")
    )
    
    # Create table
    try:
        logger.info(f"Creating table: {full_table_name}")
        catalog.create_table(
            identifier=full_table_name,
            schema=schema,
            partition_spec=partition_spec
        )
        logger.info(f"Successfully created table: {full_table_name}")
    except Exception as e:
        logger.error(f"Error creating table {full_table_name}: {e}")
        raise

def create_market_events_table(catalog: Catalog) -> None:
    """
    Create the market_events table if it doesn't exist.
    
    Args:
        catalog: The Iceberg catalog instance
    """
    table_name = "market_events"
    namespace = get_config()["iceberg"]["catalog_name"]
    full_table_name = f"{namespace}.{table_name}"
    
    # Check if table already exists
    if catalog.table_exists(full_table_name):
        logger.info(f"Table {full_table_name} already exists, skipping creation")
        return
    
    # Define schema
    schema = Schema(
        NestedField(1, "id", UUIDType(), required=True),
        NestedField(2, "ticker", StringType(), required=True),
        NestedField(3, "timestamp", TimestampType(), required=True),
        NestedField(4, "event_type", StringType(), required=True),
        NestedField(5, "title", StringType(), required=True),
        NestedField(6, "summary", StringType(), required=True),
        NestedField(7, "url", StringType(), required=True),
        NestedField(8, "source", StringType(), required=True),
        NestedField(9, "metadata", MapType(StringType(), StringType()), required=True)
    )
    
    # Define partition spec
    partition_spec = PartitionSpec(
        PartitionField(source_id=3, field_id=100, transform=DayTransform(), name="date"),
        PartitionField(source_id=2, field_id=101, transform=IdentityTransform(), name="ticker")
    )
    
    # Create table
    try:
        logger.info(f"Creating table: {full_table_name}")
        catalog.create_table(
            identifier=full_table_name,
            schema=schema,
            partition_spec=partition_spec
        )
        logger.info(f"Successfully created table: {full_table_name}")
    except Exception as e:
        logger.error(f"Error creating table {full_table_name}: {e}")
        raise

def get_table(table_name: str) -> Optional[Any]:
    """
    Get a reference to an Iceberg table.
    
    Args:
        table_name: The name of the table without the namespace
    
    Returns:
        The Iceberg table instance or None if it doesn't exist
    """
    try:
        catalog = get_iceberg_catalog()
        namespace = get_config()["iceberg"]["catalog_name"]
        full_table_name = f"{namespace}.{table_name}"
        
        if catalog.table_exists(full_table_name):
            return catalog.load_table(full_table_name)
        return None
    except Exception as e:
        logger.error(f"Error getting table {table_name}: {e}")
        return None

def generate_uuid() -> uuid.UUID:
    """
    Generate a new UUID for record IDs.
    
    Returns:
        UUID: A new UUID
    """
    return uuid.uuid4()

def initialize_iceberg() -> bool:
    """
    Initialize the Iceberg catalog and tables.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    try:
        catalog = get_iceberg_catalog()
        create_sentiment_records_table(catalog)
        create_market_events_table(catalog)
        logger.info("Iceberg initialization completed successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Iceberg: {e}")
        return False

def main():
    """
    Main function to initialize the Iceberg setup.
    """
    if initialize_iceberg():
        print("Iceberg catalog and tables successfully initialized")
        
        # Verify tables were created
        catalog = get_iceberg_catalog()
        namespace = get_config()["iceberg"]["catalog_name"]
        
        # List tables to verify
        print("\nVerifying created tables:")
        for table in [f"{namespace}.sentiment_records", f"{namespace}.market_events"]:
            if catalog.table_exists(table):
                print(f"✓ Table '{table}' successfully created")
            else:
                print(f"✗ Table '{table}' not found")
    else:
        print("Failed to initialize Iceberg catalog and tables")

if __name__ == "__main__":
    main()