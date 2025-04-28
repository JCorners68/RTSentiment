#!/usr/bin/env python3
"""
Example script for using the Iceberg lakehouse integration.

This script demonstrates how to write data to and read data from
the Iceberg table using the PyIceberg library.
"""
import sys
import os
import uuid
import time
from datetime import datetime
from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import (
    StringType, TimestampType, FloatType, 
    BooleanType, NestedField, MapType, 
    IntegerType, ListType, StructType
)

# Import the configuration
sys.path.insert(0, os.path.abspath('.'))
from iceberg_lake.utils.config import IcebergConfig

def create_simple_table(catalog):
    """Create a simple table for testing."""
    # Define a simpler schema for testing
    schema = Schema(
        NestedField(1, "id", StringType(), required=True),
        NestedField(2, "timestamp", TimestampType(), required=True),
        NestedField(3, "message", StringType(), required=True),
        NestedField(4, "score", FloatType(), required=False)
    )
    
    # Create the table
    try:
        table = catalog.create_table(
            identifier=("sentiment", "simple_test"),
            schema=schema,
            properties={
                "format-version": "2"
            }
        )
        print(f"Table created: {table.identifier}")
        return table
    except Exception as e:
        print(f"Error creating table: {str(e)}")
        if "already exists" in str(e).lower():
            print("Table already exists, loading existing table")
            return catalog.load_table(("sentiment", "simple_test"))
        raise

def insert_simple_data(table):
    """Insert simple data into the table."""
    # Sample data
    data = [
        {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(),
            "message": "This is a positive message",
            "score": 0.85
        },
        {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(),
            "message": "This is a negative message",
            "score": -0.35
        }
    ]
    
    # Use the table append API directly
    with table.new_append() as append:
        for record in data:
            append.append(record)
            
    print(f"Inserted {len(data)} rows")

def query_data(table):
    """Query data from the table."""
    # Scan operation
    scan = table.scan()
    
    # Execute and collect
    records = scan.to_arrow()
    
    # Print results
    print(f"\nQuery Results:")
    print(f"Found {len(records)} records")
    for record in records.to_pylist():
        print(f"  - {record['id']}: {record['message']} (score: {record['score']})")

def main():
    """Main function."""
    print("\n==== ICEBERG EXAMPLE ====\n")
    
    try:
        # Load configuration
        config = IcebergConfig()
        catalog_config = config.get_catalog_config()
        
        print(f"Connecting to Iceberg catalog at {catalog_config['uri']}...")
        
        # Override the warehouse location to use local file system
        catalog_properties = {
            "uri": catalog_config['uri'],
            "warehouse": "file:///tmp/warehouse/"
        }
        
        catalog = load_catalog("rest", **catalog_properties)
        
        # Ensure the namespace exists
        try:
            catalog.create_namespace("sentiment")
            print("Created 'sentiment' namespace")
        except Exception as e:
            print(f"Note: {str(e)}")
        
        # Create/load the table
        table = create_simple_table(catalog)
        
        # Insert sample data
        insert_simple_data(table)
        
        # Query data
        query_data(table)
        
        print("\nSuccessfully completed the example.")
        
    except Exception as e:
        import traceback
        print(f"Error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()