#!/usr/bin/env python3
"""
Test script for the Iceberg writer integration.

This script tests the connection to the Iceberg REST catalog and the
MinIO S3 storage, and verifies that we can write and read data.
"""
import os
import sys
import uuid
import json
from datetime import datetime

sys.path.insert(0, os.path.abspath('.'))
from iceberg_lake.utils.config import IcebergConfig

def test_rest_catalog_connection():
    """Test connection to the Iceberg REST catalog."""
    print("\n1. Testing connection to Iceberg REST catalog...")
    
    try:
        from pyiceberg.catalog import load_catalog
        from pyiceberg.io.pyarrow import PyArrowFileIO
        
        # Get config
        config = IcebergConfig()
        catalog_config = config.get_catalog_config()
        
        # Connect to REST catalog
        catalog_properties = {
            "uri": catalog_config['uri'],
            "warehouse": catalog_config['warehouse_location']
        }
        
        # Load catalog
        catalog = load_catalog("rest", **catalog_properties)
        
        # List namespaces
        namespaces = catalog.list_namespaces()
        print(f"   ✓ Connected to REST catalog")
        print(f"   ✓ Available namespaces: {namespaces}")
        
        return catalog
        
    except Exception as e:
        print(f"   ✗ Failed to connect to REST catalog: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def test_minio_connection():
    """Test connection to MinIO S3 storage."""
    print("\n2. Testing connection to MinIO S3 storage...")
    
    try:
        import boto3
        from botocore.client import Config
        
        # Get config
        config = IcebergConfig()
        minio_config = config.get_minio_config()
        
        # Connect to MinIO
        session = boto3.session.Session()
        s3_client = session.client(
            's3',
            endpoint_url=minio_config['endpoint_url'],
            aws_access_key_id=minio_config['access_key'],
            aws_secret_access_key=minio_config['secret_key'],
            config=Config(signature_version='s3v4'),
            region_name=minio_config['region']
        )
        
        # List buckets
        buckets = s3_client.list_buckets()
        bucket_names = [bucket['Name'] for bucket in buckets['Buckets']]
        
        print(f"   ✓ Connected to MinIO S3")
        print(f"   ✓ Available buckets: {bucket_names}")
        
        # Check if our warehouse bucket exists
        warehouse_bucket = minio_config['bucket']
        if warehouse_bucket in bucket_names:
            print(f"   ✓ Warehouse bucket '{warehouse_bucket}' exists")
        else:
            print(f"   ✗ Warehouse bucket '{warehouse_bucket}' does not exist")
            print(f"     Creating bucket '{warehouse_bucket}'...")
            s3_client.create_bucket(Bucket=warehouse_bucket)
            print(f"   ✓ Created warehouse bucket '{warehouse_bucket}'")
        
        return s3_client
        
    except Exception as e:
        print(f"   ✗ Failed to connect to MinIO S3: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def create_test_table(catalog):
    """Create a test table."""
    print("\n3. Creating test table...")
    
    try:
        from pyiceberg.schema import Schema
        from pyiceberg.types import NestedField, StringType, TimestampType, FloatType
        
        # Get config
        config = IcebergConfig()
        catalog_config = config.get_catalog_config()
        
        # Define schema
        schema = Schema(
            NestedField(1, "id", StringType(), required=True),
            NestedField(2, "timestamp", TimestampType(), required=True),
            NestedField(3, "message", StringType(), required=True),
            NestedField(4, "score", FloatType(), required=False)
        )
        
        # Create or load table
        namespace = catalog_config['namespace']
        table_name = "test_table"
        
        try:
            # Try to load existing table
            table = catalog.load_table(f"{namespace}.{table_name}")
            print(f"   ✓ Test table already exists")
        except Exception:
            # Create a new table
            table = catalog.create_table(
                identifier=(namespace, table_name),
                schema=schema,
                properties={
                    "format-version": "2",
                    "write.parquet.compression-codec": "gzip"
                }
            )
            print(f"   ✓ Created test table: {namespace}.{table_name}")
        
        return table
        
    except Exception as e:
        print(f"   ✗ Failed to create test table: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def write_test_data(table):
    """Write test data to the table."""
    print("\n4. Writing test data...")
    
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
        from pyiceberg.io.pyarrow import PyArrowFileIO
        
        # Create some test data
        test_data = [
            {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(),
                "message": "Test message 1",
                "score": 0.75
            },
            {
                "id": str(uuid.uuid4()),
                "timestamp": datetime.now(),
                "message": "Test message 2",
                "score": -0.25
            }
        ]
        
        # Convert to PyArrow table
        arrow_data = {
            "id": [record["id"] for record in test_data],
            "timestamp": [record["timestamp"] for record in test_data],
            "message": [record["message"] for record in test_data],
            "score": [record["score"] for record in test_data]
        }
        
        arrow_table = pa.Table.from_pydict(arrow_data)
        
        # Use PyArrow to write
        with table.new_append() as append:
            output_file = append.create_file()
            with PyArrowFileIO().new_output(output_file.file_path) as output:
                pq.write_table(arrow_table, output)
            append.add_file(output_file)
        
        print(f"   ✓ Wrote {len(test_data)} records to test table")
        
    except Exception as e:
        print(f"   ✗ Failed to write test data: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def read_test_data(table):
    """Read test data from the table."""
    print("\n5. Reading test data...")
    
    try:
        # Scan operation
        scan = table.scan()
        
        # Execute and collect
        arrow_table = scan.to_arrow()
        
        # Print results
        print(f"   ✓ Read {len(arrow_table)} records from test table")
        for record in arrow_table.to_pylist():
            print(f"     - {record['id']}: {record['message']} (score: {record['score']})")
        
    except Exception as e:
        print(f"   ✗ Failed to read test data: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def main():
    """Main test function."""
    print("===== ICEBERG WRITER TEST =====")
    
    # Test REST catalog connection
    catalog = test_rest_catalog_connection()
    
    # Test MinIO connection
    s3_client = test_minio_connection()
    
    # Create test table
    table = create_test_table(catalog)
    
    # Write test data
    write_test_data(table)
    
    # Read test data
    read_test_data(table)
    
    print("\n===== TEST COMPLETED SUCCESSFULLY =====")

if __name__ == "__main__":
    main()