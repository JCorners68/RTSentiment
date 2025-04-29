#!/usr/bin/env python3
"""
End-to-end test for Kafka to Dremio data flow.

This script tests the complete data flow from Kafka to Dremio:
1. Produces sample sentiment data to a Kafka topic
2. Configures the Kafka consumer to process that data
3. Writes the processed data to Dremio via JDBC
4. Verifies the data was written correctly in Dremio

Usage:
    python kafka_to_dremio_test.py --kafka-broker localhost:9092 --kafka-topic sentiment-data
"""
import os
import sys
import argparse
import logging
import time
import uuid
import json
from datetime import datetime, timezone

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import required modules
from iceberg_lake.writer.dremio_jdbc_writer import DremioJdbcWriter
from iceberg_lake.writer.kafka_integration import DremioKafkaIntegration
from iceberg_lake.utils.config import IcebergConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_test_data(num_records=5):
    """Generate test sentiment data."""
    test_data = []
    tickers = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
    emotions = ["positive", "negative", "neutral", "excited", "concerned"]
    source_systems = ["twitter_scraper", "news_scraper", "reddit_scraper"]
    
    current_time = datetime.now(timezone.utc)
    
    for i in range(num_records):
        sentiment_score = (i % 5 - 2) / 2.0  # Values from -1.0 to 1.0
        ticker = tickers[i % len(tickers)]
        emotion = emotions[i % len(emotions)]
        source = source_systems[i % len(source_systems)]
        
        record = {
            "message_id": str(uuid.uuid4()),
            "event_timestamp": current_time.isoformat(),
            "ingestion_timestamp": current_time.isoformat(),
            "source_system": source,
            "text_content": f"Test message {i+1} about {ticker} with {emotion} sentiment.",
            "sentiment_score": sentiment_score,
            "sentiment_magnitude": abs(sentiment_score) * 0.8,
            "primary_emotion": emotion,
            "sarcasm_detection": False,
            "subjectivity_score": 0.3,
            "toxicity_score": 0.1,
            "user_intent": "information_sharing",
            "processing_version": "1.0.0",
            "ticker": ticker,
            "emotion_intensity_vector": {
                "joy": max(0, sentiment_score), 
                "fear": max(0, -sentiment_score)
            },
            "aspect_based_sentiment": {
                "price": sentiment_score,
                "performance": sentiment_score * 0.9
            }
        }
        test_data.append(record)
    
    return test_data


def produce_test_messages(kafka_broker, kafka_topic, test_data):
    """Produce test messages to Kafka topic."""
    try:
        from kafka import KafkaProducer
        
        logger.info(f"Connecting to Kafka at {kafka_broker}")
        producer = KafkaProducer(
            bootstrap_servers=kafka_broker,
            value_serializer=lambda m: json.dumps(m).encode('utf-8')
        )
        
        logger.info(f"Producing {len(test_data)} test records to topic {kafka_topic}")
        for record in test_data:
            producer.send(kafka_topic, record)
            logger.debug(f"Sent message: {record['message_id']}")
        
        producer.flush()
        logger.info("All test records produced to Kafka")
        return True
        
    except Exception as e:
        logger.error(f"Failed to produce test messages to Kafka: {str(e)}")
        return False


def verify_dremio_data(kafka_integration, expected_records):
    """Verify data was written to Dremio correctly."""
    try:
        # Get writer from integration
        writer = kafka_integration.writer
        
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
        
        message_ids = [r['message_id'] for r in expected_records]
        found_ids = [r[0] for r in records]
        
        matched = [id for id in message_ids if id in found_ids]
        
        logger.info(f"Found {len(matched)}/{len(message_ids)} expected records in Dremio")
        
        for record in records:
            logger.info(f"Record: {record[0][:8]}... | {record[1][:30]}... | Score: {record[2]} | Emotion: {record[3]} | Ticker: {record[4]}")
        
        cursor.close()
        return len(matched) >= len(message_ids) * 0.8  # At least 80% match
        
    except Exception as e:
        logger.error(f"Failed to verify data in Dremio: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def get_dremio_config():
    """Get Dremio configuration from IcebergConfig."""
    config = IcebergConfig()
    dremio_config = config.get_dremio_config()
    
    # Default JDBC port for Dremio is 31010
    jdbc_port = 31010
    
    # Extract hostname from endpoint
    endpoint = dremio_config.get('endpoint', 'http://localhost:9047')
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


def main():
    """Run the end-to-end test for Kafka to Dremio data flow."""
    parser = argparse.ArgumentParser(description='Test Kafka to Dremio data flow')
    parser.add_argument('--kafka-broker', default='localhost:9092', help='Kafka broker address')
    parser.add_argument('--kafka-topic', default='sentiment-data', help='Kafka topic to produce/consume')
    parser.add_argument('--test-records', type=int, default=5, help='Number of test records to generate')
    parser.add_argument('--table-name', default=None, help='Dremio table name')
    
    args = parser.parse_args()
    
    # Generate unique table name if not provided
    table_name = args.table_name or f"test_sentiment_{int(time.time())}"
    
    logger.info("====== KAFKA TO DREMIO DATA FLOW TEST ======")
    logger.info(f"Kafka broker: {args.kafka_broker}")
    logger.info(f"Kafka topic: {args.kafka_topic}")
    logger.info(f"Test records: {args.test_records}")
    logger.info(f"Dremio table: {table_name}")
    
    # Generate test data
    test_data = generate_test_data(args.test_records)
    logger.info(f"Generated {len(test_data)} test records")
    
    # Produce test messages to Kafka
    if not produce_test_messages(args.kafka_broker, args.kafka_topic, test_data):
        logger.error("Failed to produce test messages to Kafka. Aborting test.")
        return 1
    
    # Get Dremio configuration
    dremio_config = get_dremio_config()
    logger.info(f"Using Dremio config: {dremio_config['host']}:{dremio_config['port']} (user: {dremio_config['username']})")
    
    # Find JDBC driver
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
        jar_path = os.path.abspath("drivers/dremio-jdbc-driver.jar")
        logger.info(f"Using default Dremio JDBC driver path: {jar_path}")
    
    try:
        # Create JDBC writer with unique table name for the test
        writer = DremioJdbcWriter(
            dremio_host=dremio_config['host'],
            dremio_port=dremio_config['port'],
            dremio_username=dremio_config['username'],
            dremio_password=dremio_config['password'],
            table_name=table_name,
            jar_path=jar_path
        )
        
        # Create Kafka integration
        integration = DremioKafkaIntegration(
            writer=writer,
            kafka_bootstrap_servers=args.kafka_broker,
            topic=args.kafka_topic,
            group_id=f"dremio-test-{int(time.time())}"
        )
        
        # Start processing for a short period
        logger.info("Starting Kafka consumer to process messages...")
        integration.start()
        
        # Wait for messages to be processed
        logger.info("Waiting for messages to be processed...")
        time.sleep(10)
        
        # Stop consumer
        integration.stop()
        logger.info("Stopped Kafka consumer")
        
        # Verify data in Dremio
        logger.info("Verifying data in Dremio...")
        if verify_dremio_data(integration, test_data):
            logger.info("✅ Test SUCCEEDED: Data flowed from Kafka to Dremio successfully")
            return 0
        else:
            logger.error("❌ Test FAILED: Data verification in Dremio failed")
            return 1
            
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Clean up resources
        if 'integration' in locals():
            integration.stop()
        if 'writer' in locals():
            writer.close()


if __name__ == "__main__":
    sys.exit(main())