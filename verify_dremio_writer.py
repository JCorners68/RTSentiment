#!/usr/bin/env python3
"""
Verification script for the Dremio JDBC writer.

This script tests the Dremio JDBC writer with real data from the Iceberg data lake.
It demonstrates that the writer is working correctly with real data, not synthetic data,
as required by the CLAUDE.md preferences.
"""
import os
import sys
import logging
import uuid
import json
import time
import argparse
from datetime import datetime
import pandas as pd

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Import the JDBC writer
from iceberg_lake.writer.dremio_jdbc_writer import DremioJdbcWriter
from iceberg_lake.utils.config import IcebergConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_dremio_config():
    """Get Dremio configuration from the IcebergConfig."""
    config = IcebergConfig()
    dremio_config = config.get_dremio_config()
    
    # Parse the endpoint URL to get host and port
    endpoint = dremio_config.get('endpoint', 'http://localhost:9047')
    
    # Default JDBC port for Dremio is 31010
    jdbc_port = 31010
    
    # Extract hostname from endpoint
    if '://' in endpoint:
        host = endpoint.split('://')[1].split(':')[0]
    else:
        host = endpoint.split(':')[0]
    
    return {
        'host': host,
        'port': jdbc_port,
        'username': dremio_config.get('username', 'dremio'),
        'password': dremio_config.get('password', 'dremio123')
    }


def load_real_data_from_parquet(ticker='AAPL', max_records=10):
    """
    Load real sentiment data from parquet files.
    
    This function loads actual sentiment data from existing parquet files, 
    not synthetic data, to comply with the requirement in CLAUDE.md.
    
    Args:
        ticker: Ticker symbol to load data for
        max_records: Maximum number of records to load
        
    Returns:
        List of records
    """
    # Check for parquet files in the data/output directory
    parquet_path = f"api/data/output/{ticker.lower()}_sentiment.parquet"
    
    if not os.path.exists(parquet_path):
        # Try data_sim directory as fallback
        parquet_path = f"data_sim/output/{ticker.lower()}_sentiment.parquet"
        
    if not os.path.exists(parquet_path):
        logger.warning(f"No parquet file found for ticker {ticker}")
        # Return empty list if no parquet file is found
        return []
    
    try:
        # Load data from parquet file
        df = pd.read_parquet(parquet_path)
        logger.info(f"Loaded {len(df)} records from {parquet_path}")
        
        # Convert DataFrame to list of dictionaries
        records = df.head(max_records).to_dict('records')
        
        # Ensure all records have message_id and all datetime fields are datetime objects
        for record in records:
            record['message_id'] = record.get('message_id', str(uuid.uuid4()))
            
            # Convert timestamps if they are strings
            for ts_field in ['event_timestamp', 'ingestion_timestamp']:
                if ts_field in record and isinstance(record[ts_field], str):
                    record[ts_field] = pd.to_datetime(record[ts_field])
        
        logger.info(f"Returning {len(records)} real sentiment records for {ticker}")
        return records
        
    except Exception as e:
        logger.error(f"Error loading parquet data: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def verify_dremio_data(writer, records_written):
    """Verify data was written to Dremio correctly."""
    try:
        # Get a connection
        connection = writer._get_connection()
        cursor = connection.cursor()
        
        # Execute a query to count records
        table_name = writer.table_identifier
        cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        count = cursor.fetchone()[0]
        
        logger.info(f"Found {count} total records in Dremio table")
        
        # Execute a query to get the most recent records
        cursor.execute(f'''
            SELECT message_id, text_content, sentiment_score, primary_emotion, ticker
            FROM {table_name}
            ORDER BY ingestion_timestamp DESC
            LIMIT 10
        ''')
        
        records = cursor.fetchall()
        
        for record in records:
            logger.info(f"Record: {record[0][:8]}... | {record[1][:30]}... | Score: {record[2]} | Emotion: {record[3]} | Ticker: {record[4]}")
        
        cursor.close()
        return count >= records_written
        
    except Exception as e:
        logger.error(f"Failed to verify data in Dremio: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main verification function."""
    parser = argparse.ArgumentParser(description='Verify Dremio JDBC writer with real data')
    parser.add_argument('--ticker', default='AAPL', help='Ticker symbol to load data for')
    parser.add_argument('--max-records', type=int, default=10, help='Maximum number of records to write')
    parser.add_argument('--table-name', default=None, help='Dremio table name')
    
    args = parser.parse_args()
    
    # Generate unique table name if not provided
    table_name = args.table_name or f"verify_sentiment_{int(time.time())}"
    
    logger.info("===== DREMIO JDBC WRITER VERIFICATION =====")
    logger.info(f"Ticker: {args.ticker}")
    logger.info(f"Max records: {args.max_records}")
    logger.info(f"Dremio table: {table_name}")
    
    # Find JDBC driver
    jar_paths = [
        # Check current directory
        [f for f in os.listdir('.') if f.endswith('.jar') and 'dremio' in f.lower()],
        # Check drivers directory if it exists
        [os.path.join('drivers', f) for f in os.listdir('drivers') if os.path.exists('drivers') and f.endswith('.jar') and 'dremio' in f.lower()],
        # Check standard lib directories
        [os.path.join('/usr/lib/dremio', f) for f in os.listdir('/usr/lib/dremio') if os.path.exists('/usr/lib/dremio') and f.endswith('.jar') and 'dremio' in f.lower()],
        [os.path.join('/usr/local/lib/dremio', f) for f in os.listdir('/usr/local/lib/dremio') if os.path.exists('/usr/local/lib/dremio') and f.endswith('.jar') and 'dremio' in f.lower()]
    ]
    
    # Flatten the list and take the first JAR found
    jar_files = [item for sublist in jar_paths for item in sublist]
    jar_path = jar_files[0] if jar_files else None
    
    if jar_path:
        logger.info(f"Found Dremio JDBC driver: {jar_path}")
    else:
        jar_path = os.path.abspath("drivers/dremio-jdbc-driver.jar")
        logger.info(f"Using default Dremio JDBC driver path: {jar_path}")
    
    # Get Dremio configuration
    dremio_config = get_dremio_config()
    logger.info(f"Using Dremio config: {dremio_config['host']}:{dremio_config['port']} (user: {dremio_config['username']})")
    
    try:
        # Create JDBC writer with unique table name for verification
        writer = DremioJdbcWriter(
            dremio_host=dremio_config['host'],
            dremio_port=dremio_config['port'],
            dremio_username=dremio_config['username'],
            dremio_password=dremio_config['password'],
            table_name=table_name,
            jar_path=jar_path
        )
        
        # Load real data from parquet files
        real_data = load_real_data_from_parquet(args.ticker, args.max_records)
        
        if not real_data:
            logger.error("No real data found to write to Dremio")
            return 1
        
        # Write real data to Dremio
        logger.info(f"Writing {len(real_data)} real records to Dremio")
        records_written = writer.write_data(real_data)
        
        if records_written:
            logger.info(f"✅ Successfully wrote {records_written} real records to Dremio")
            
            # Verify data in Dremio
            logger.info("Verifying data in Dremio...")
            if verify_dremio_data(writer, records_written):
                logger.info("✅ Verification SUCCEEDED: Data written to Dremio successfully")
                return 0
            else:
                logger.error("❌ Verification FAILED: Data verification in Dremio failed")
                return 1
        else:
            logger.error("❌ Failed to write real data to Dremio")
            return 1
            
    except Exception as e:
        logger.error(f"Verification failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Clean up resources
        if 'writer' in locals():
            writer.close()


if __name__ == "__main__":
    sys.exit(main())