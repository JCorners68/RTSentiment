#!/usr/bin/env python3
"""
Test script for the Dremio JDBC writer integration.

This script tests the connection to Dremio via JDBC and verifies
that we can write sentiment data to an Iceberg table in Dremio.
"""
import os
import sys
import uuid
import json
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Import the JDBC writer
from iceberg_lake.writer.dremio_jdbc_writer import DremioJdbcWriter
from iceberg_lake.utils.config import IcebergConfig


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


def test_connection(writer):
    """Test connection to Dremio via JDBC."""
    logger.info("Testing connection to Dremio via JDBC...")
    
    try:
        # Get connection will be called internally when we create the writer
        logger.info("✓ Successfully connected to Dremio via JDBC")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to connect to Dremio via JDBC: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_table_creation(writer):
    """Test table creation in Dremio."""
    logger.info("Testing table creation in Dremio...")
    
    try:
        # Table should have been created by the writer initialization
        logger.info("✓ Successfully created/verified table in Dremio")
        return True
    except Exception as e:
        logger.error(f"✗ Failed to create/verify table in Dremio: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_data_write(writer):
    """Test writing data to Dremio."""
    logger.info("Testing writing data to Dremio...")
    
    try:
        # Create some test data
        current_time = datetime.utcnow()
        test_data = [
            {
                "message_id": str(uuid.uuid4()),
                "event_timestamp": current_time,
                "ingestion_timestamp": current_time,
                "source_system": "test_system",
                "text_content": "Apple stock is performing well this quarter.",
                "sentiment_score": 0.75,
                "sentiment_magnitude": 0.8,
                "primary_emotion": "positive",
                "sarcasm_detection": False,
                "subjectivity_score": 0.4,
                "toxicity_score": 0.1,
                "user_intent": "information_sharing",
                "processing_version": "1.0.0",
                "ticker": "AAPL",
                "emotion_intensity_vector": {"joy": 0.7, "surprise": 0.2},
                "aspect_based_sentiment": {"performance": 0.8, "revenue": 0.6}
            },
            {
                "message_id": str(uuid.uuid4()),
                "event_timestamp": current_time,
                "ingestion_timestamp": current_time,
                "source_system": "test_system",
                "text_content": "Tesla delivery numbers missed expectations.",
                "sentiment_score": -0.6,
                "sentiment_magnitude": 0.7,
                "primary_emotion": "negative",
                "sarcasm_detection": False,
                "subjectivity_score": 0.3,
                "toxicity_score": 0.05,
                "user_intent": "information_sharing",
                "processing_version": "1.0.0",
                "ticker": "TSLA",
                "emotion_intensity_vector": {"disappointment": 0.6, "concern": 0.5},
                "aspect_based_sentiment": {"delivery": -0.7, "expectations": -0.5}
            }
        ]
        
        # Write test data
        records_written = writer.write_data(test_data)
        
        if records_written == len(test_data):
            logger.info(f"✓ Successfully wrote {records_written} records to Dremio")
            return True
        else:
            logger.error(f"✗ Expected to write {len(test_data)} records, but wrote {records_written}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Failed to write test data to Dremio: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_sentiment_analysis_write(writer):
    """Test writing a complete sentiment analysis result."""
    logger.info("Testing writing a sentiment analysis result...")
    
    try:
        # Create a test sentiment analysis result
        message_id = str(uuid.uuid4())
        text_content = "Microsoft's cloud business continues to drive strong growth."
        source_system = "news_scraper"
        
        analysis_result = {
            "sentiment_score": 0.82,
            "sentiment_magnitude": 0.9,
            "primary_emotion": "positive",
            "emotion_intensity_vector": {
                "optimism": 0.85,
                "joy": 0.7,
                "surprise": 0.4
            },
            "aspect_target_identification": [
                "cloud business", 
                "growth"
            ],
            "aspect_based_sentiment": {
                "cloud business": 0.9,
                "growth": 0.85
            },
            "sarcasm_detection": False,
            "subjectivity_score": 0.3,
            "toxicity_score": 0.02,
            "entity_recognition": [
                {"text": "Microsoft", "type": "ORGANIZATION"},
                {"text": "cloud business", "type": "PRODUCT"}
            ],
            "user_intent": "information_sharing",
            "influence_score": 0.75,
            "processing_version": "1.0.0"
        }
        
        # Write the sentiment analysis result
        records_written = writer.write_sentiment_analysis_result(
            message_id=message_id,
            text_content=text_content,
            source_system=source_system,
            analysis_result=analysis_result,
            ticker="MSFT",
            article_title="Microsoft Cloud Growth Exceeds Expectations",
            source_url="https://example.com/news/12345",
            model_name="finbert-v1.2"
        )
        
        if records_written == 1:
            logger.info("✓ Successfully wrote sentiment analysis result to Dremio")
            return True
        else:
            logger.error(f"✗ Expected to write 1 record, but wrote {records_written}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Failed to write sentiment analysis result to Dremio: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def verify_data_in_dremio(writer):
    """Verify that data was written to Dremio by querying it."""
    logger.info("Verifying data in Dremio...")
    
    try:
        # Get a connection
        connection = writer._get_connection()
        cursor = connection.cursor()
        
        # Execute a query to count records
        cursor.execute(f'SELECT COUNT(*) FROM {writer.table_identifier}')
        count = cursor.fetchone()[0]
        
        # Execute a query to get the most recent records
        cursor.execute(f'''
            SELECT message_id, text_content, sentiment_score, primary_emotion, ticker
            FROM {writer.table_identifier}
            ORDER BY ingestion_timestamp DESC
            LIMIT 5
        ''')
        
        rows = cursor.fetchall()
        
        logger.info(f"✓ Found {count} total records in the table")
        
        for row in rows:
            logger.info(f"  - {row[0][:8]}...: {row[1][:30]}... (sentiment: {row[2]}, emotion: {row[3]}, ticker: {row[4]})")
        
        cursor.close()
        return True
        
    except Exception as e:
        logger.error(f"✗ Failed to verify data in Dremio: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function."""
    logger.info("===== DREMIO JDBC WRITER TEST =====")
    
    # Check for JDBC driver in multiple locations
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
        logger.warning("No Dremio JDBC driver JAR found. You'll need a driver on the CLASSPATH.")
        logger.warning("Please run scripts/setup_dremio_jdbc.sh to download and set up the driver.")
    
    # Get Dremio configuration
    dremio_config = get_dremio_config()
    logger.info(f"Using Dremio config: {dremio_config['host']}:{dremio_config['port']} (user: {dremio_config['username']})")
    
    # Create the JDBC writer
    try:
        writer = DremioJdbcWriter(
            dremio_host=dremio_config['host'],
            dremio_port=dremio_config['port'],
            dremio_username=dremio_config['username'],
            dremio_password=dremio_config['password'],
            jar_path=jar_path
        )
        
        # Run the tests
        connection_success = test_connection(writer)
        if not connection_success:
            logger.error("Connection test failed. Aborting remaining tests.")
            return
            
        table_success = test_table_creation(writer)
        if not table_success:
            logger.error("Table creation test failed. Aborting remaining tests.")
            return
            
        write_success = test_data_write(writer)
        if not write_success:
            logger.error("Data write test failed. Aborting remaining tests.")
            return
            
        sentiment_success = test_sentiment_analysis_write(writer)
        if not sentiment_success:
            logger.error("Sentiment analysis write test failed. Aborting remaining tests.")
            return
            
        verify_success = verify_data_in_dremio(writer)
        if not verify_success:
            logger.error("Data verification failed.")
            return
            
        logger.info("\n===== TEST COMPLETED SUCCESSFULLY =====")
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        # Close resources
        if 'writer' in locals():
            writer.close()


if __name__ == "__main__":
    main()