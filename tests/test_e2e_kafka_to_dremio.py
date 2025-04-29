#!/usr/bin/env python3
"""
End-to-End test for the Kafka to Dremio data flow.

This script tests the complete flow of sentiment data from Kafka to Iceberg via Dremio,
verifying that the entire pipeline works as expected.
"""
import os
import sys
import uuid
import json
import asyncio
import logging
import argparse
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add project root to Python path
sys.path.insert(0, os.path.abspath('.'))

# Import the Kafka integration factory
from iceberg_lake.writer.kafka_integration import create_kafka_integration
from iceberg_lake.utils.config import IcebergConfig

# Optional imports - will be used if available
try:
    from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
    kafka_available = True
except ImportError:
    logger.warning("aiokafka not installed. Kafka publishing will be simulated.")
    kafka_available = False


async def publish_test_message(kafka_topic, bootstrap_servers, test_data):
    """
    Publish a test message to Kafka.
    
    If aiokafka is not available, this will simulate publishing.
    
    Args:
        kafka_topic: Kafka topic to publish to
        bootstrap_servers: Kafka bootstrap servers
        test_data: Test data to publish
        
    Returns:
        dict: Message metadata or simulated metadata
    """
    logger.info(f"Publishing test message to {kafka_topic}...")
    
    if kafka_available:
        try:
            # Create Kafka producer
            producer = AIOKafkaProducer(
                bootstrap_servers=bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8')
            )
            
            # Start producer
            await producer.start()
            
            try:
                # Send message
                metadata = await producer.send_and_wait(kafka_topic, test_data)
                logger.info(f"✓ Message published: partition={metadata.partition}, offset={metadata.offset}")
                return {
                    "topic": metadata.topic,
                    "partition": metadata.partition,
                    "offset": metadata.offset,
                    "timestamp": metadata.timestamp,
                    "simulated": False
                }
            finally:
                # Close producer
                await producer.stop()
                
        except Exception as e:
            logger.error(f"Error publishing to Kafka: {str(e)}")
            logger.info("Falling back to simulated publishing...")
    
    # Simulate publishing if Kafka is not available or there was an error
    logger.info(f"[SIMULATED] Published message to {kafka_topic}")
    return {
        "topic": kafka_topic,
        "partition": 0,
        "offset": 0,
        "timestamp": int(datetime.utcnow().timestamp() * 1000),
        "simulated": True
    }


async def simulate_consumer(test_data, integration):
    """
    Simulate a Kafka consumer by directly passing the test message to the integration.
    
    Args:
        test_data: Test data to process
        integration: Kafka integration instance
        
    Returns:
        bool: True if successful
    """
    logger.info("Simulating Kafka consumer...")
    
    # Process the test message directly
    result = await integration.process_event(test_data)
    if result:
        logger.info("✓ Test message processed successfully")
    else:
        logger.error("✗ Failed to process test message")
        
    # Force a flush to ensure data is written
    written = await integration.flush()
    if written > 0:
        logger.info(f"✓ Flushed {written} messages to Dremio")
    else:
        logger.error("✗ Failed to flush messages to Dremio")
        
    return result and (written > 0)


async def verify_data_in_dremio(test_data, dremio_writer):
    """
    Verify that the test data was written to Dremio.
    
    Args:
        test_data: Test data that was published
        dremio_writer: DremioJdbcWriter instance
        
    Returns:
        bool: True if data was found
    """
    logger.info("Verifying data in Dremio...")
    
    try:
        # Get a connection
        connection = dremio_writer._get_connection()
        cursor = connection.cursor()
        
        # Extract message ID from test data
        message_id = test_data.get("id", "")
        
        # Execute a query to find the record
        cursor.execute(f'''
            SELECT message_id, text_content, sentiment_score, primary_emotion, ticker
            FROM {dremio_writer.table_identifier}
            WHERE message_id = ?
        ''', [message_id])
        
        # Fetch the result
        row = cursor.fetchone()
        
        if row:
            logger.info(f"✓ Found record in Dremio: {row}")
            found = True
        else:
            logger.error(f"✗ Record not found in Dremio for message_id: {message_id}")
            
            # Try a broader query to see if any records exist
            cursor.execute(f'''
                SELECT COUNT(*) FROM {dremio_writer.table_identifier}
            ''')
            count = cursor.fetchone()[0]
            logger.info(f"Total records in table: {count}")
            
            found = False
        
        cursor.close()
        return found
        
    except Exception as e:
        logger.error(f"✗ Error verifying data in Dremio: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def generate_test_data():
    """Generate test data for the E2E test."""
    # Generate a unique ID for this test run
    test_id = str(uuid.uuid4())
    
    # Create test data with all required fields
    return {
        "id": f"e2e_test_{test_id}",
        "timestamp": datetime.utcnow().isoformat(),
        "source": "e2e_test",
        "text": "This is an end-to-end test message for Kafka to Dremio integration.",
        "tickers": ["TEST"],
        "title": "E2E Test Message",
        "url": "https://example.com/e2e_test",
        "model": "e2e_test_model",
        "sentiment_result": {
            "sentiment_score": 0.85,
            "sentiment_magnitude": 0.9,
            "primary_emotion": "positive",
            "emotion_intensity_vector": {
                "joy": 0.85,
                "optimism": 0.9,
                "confidence": 0.7
            },
            "aspect_target_identification": ["test", "integration", "e2e"],
            "aspect_based_sentiment": {
                "test": 0.8,
                "integration": 0.9,
                "e2e": 0.85
            },
            "sarcasm_detection": False,
            "subjectivity_score": 0.2,
            "toxicity_score": 0.0,
            "entity_recognition": [
                {"text": "Kafka", "type": "TECHNOLOGY"},
                {"text": "Dremio", "type": "TECHNOLOGY"}
            ],
            "user_intent": "testing",
            "influence_score": 0.5,
            "processing_version": "e2e_1.0"
        }
    }


async def run_e2e_test(args):
    """Run the end-to-end test."""
    logger.info("==== KAFKA TO DREMIO END-TO-END TEST ====")
    
    # Generate test data
    test_data = generate_test_data()
    logger.info(f"Generated test data with ID: {test_data['id']}")
    
    # In full simulation mode, don't try to create a real integration
    if args.full_simulate:
        logger.info("Running in full simulation mode - skipping actual Dremio connection")
        # Simulate success
        return True
    
    # Create Kafka integration
    config = IcebergConfig()
    integration = create_kafka_integration(writer_type="dremio", config=config)
    
    try:
        # Start the integration
        await integration.start()
        logger.info("Started Kafka integration")
        
        # Extract the Dremio writer for verification
        dremio_writer = integration.writer
        
        # If Kafka is available and not in simulation mode, publish to Kafka
        if kafka_available and not args.simulate:
            # Publish test message to Kafka
            metadata = await publish_test_message(
                args.kafka_topic,
                args.bootstrap_servers,
                test_data
            )
            
            # If using real Kafka, wait for consumer to process
            if not metadata.get("simulated"):
                logger.info(f"Waiting {args.wait_time} seconds for Kafka consumer to process message...")
                await asyncio.sleep(args.wait_time)
        else:
            # Simulate Kafka consumer
            success = await simulate_consumer(test_data, integration)
            if not success:
                logger.error("Simulated consumer failed to process message")
                return False
        
        # Verify data was written to Dremio
        success = await verify_data_in_dremio(test_data, dremio_writer)
        
        if success:
            logger.info("✓ END-TO-END TEST COMPLETED SUCCESSFULLY")
        else:
            logger.error("✗ END-TO-END TEST FAILED - Data not found in Dremio")
            
        return success
        
    except Exception as e:
        logger.error(f"✗ END-TO-END TEST FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Stop the integration
        await integration.stop()
        logger.info("Stopped Kafka integration")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="E2E test for Kafka to Dremio data flow")
    parser.add_argument("--simulate", action="store_true", help="Simulate Kafka publishing and consumer")
    parser.add_argument("--full-simulate", action="store_true", help="Fully simulate both Kafka and Dremio")
    parser.add_argument("--kafka-topic", default="sentiment-test", help="Kafka topic to use")
    parser.add_argument("--bootstrap-servers", default="localhost:9092", help="Kafka bootstrap servers")
    parser.add_argument("--wait-time", type=int, default=5, help="Wait time (seconds) for Kafka consumer")
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_args()
    
    try:
        # Run the E2E test
        success = asyncio.run(run_e2e_test(args))
        if not success:
            sys.exit(1)
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()