#!/usr/bin/env python3
"""
Example script demonstrating the integration between Kafka and Iceberg.

This script shows how to set up a streaming pipeline that processes
sentiment events from Kafka and stores them in an Iceberg data lake.
"""
import asyncio
import json
import os
import sys
import logging
import uuid
from datetime import datetime
from pathlib import Path

# Ensure project root is in path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import Iceberg modules
from iceberg_lake.utils.config import IcebergConfig
from iceberg_lake.writer.iceberg_writer import IcebergSentimentWriter
from iceberg_lake.writer.kafka_integration import IcebergKafkaIntegration

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def simulate_kafka_events(integration, num_events=10, delay=1.0):
    """
    Simulate Kafka events for testing.
    
    Args:
        integration: IcebergKafkaIntegration instance
        num_events: Number of events to simulate
        delay: Delay between events in seconds
    """
    logger.info(f"Simulating {num_events} Kafka events with {delay}s delay")
    
    # Sample tickers
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]
    
    # Sample sources
    sources = ["bloomberg", "reuters", "wsj", "cnbc", "ft", "reddit"]
    
    # Sample event types
    event_types = [
        "earnings_report", "breaking_news", "analyst_rating", 
        "press_release", "social_media", "financial_filing"
    ]
    
    # Sample texts
    texts = [
        "Company reported strong quarterly earnings, beating analyst expectations.",
        "Stock price declined following disappointing guidance for next quarter.",
        "Analysts raised their price target citing strong growth prospects.",
        "Company announced a new product line that could drive significant revenue.",
        "Investors are concerned about rising costs and margin pressure.",
        "The CEO announced plans to step down by the end of the year.",
        "Regulatory concerns are weighing on the stock price today.",
        "A major shareholder increased their stake in the company.",
        "The company announced a stock buyback program.",
        "Quarterly results showed improved profit margins despite headwinds."
    ]
    
    # Generate and process events
    for i in range(num_events):
        # Select random values
        ticker = tickers[i % len(tickers)]
        source = sources[i % len(sources)]
        event_type = event_types[i % len(event_types)]
        text = texts[i % len(texts)]
        
        # Create sample event
        event = {
            "id": f"test-event-{uuid.uuid4()}",
            "type": event_type,
            "source": source,
            "tickers": [ticker],
            "text": text,
            "title": f"{ticker} {event_type.replace('_', ' ')}",
            "url": f"https://example.com/{ticker.lower()}/{i}",
            "timestamp": datetime.utcnow().isoformat(),
            "sentiment_result": {
                "sentiment_score": (i % 5 - 2) / 2,  # Range from -1.0 to 1.0
                "sentiment_label": "positive" if i % 5 > 2 else "negative" if i % 5 < 2 else "neutral",
                "sentiment_magnitude": 0.5 + (i % 5) / 10  # Range from 0.5 to 0.9
            }
        }
        
        # Process event
        logger.info(f"Processing event {i+1}/{num_events}: {ticker} ({event_type})")
        await integration.process_event(event)
        
        # Wait before next event
        await asyncio.sleep(delay)
    
    logger.info(f"Completed simulating {num_events} events")


async def main():
    """Main function to demonstrate Kafka to Iceberg streaming."""
    try:
        logger.info("Starting Kafka to Iceberg streaming example")
        
        # Load configuration
        config_path = os.environ.get("ICEBERG_CONFIG_PATH")
        config = IcebergConfig(config_path)
        
        # Set up Iceberg writer
        catalog_config = config.get_catalog_config()
        writer_config = config.get_writer_config()
        
        logger.info(f"Connecting to Iceberg catalog at {catalog_config['uri']}")
        
        # Create writer
        writer = IcebergSentimentWriter(
            catalog_uri=catalog_config["uri"],
            warehouse_location=catalog_config["warehouse_location"],
            namespace=catalog_config["namespace"],
            table_name=catalog_config["table_name"],
            max_retries=writer_config.get("max_retries", 3),
            retry_delay=writer_config.get("retry_delay", 1000)
        )
        
        # Create integration
        integration = IcebergKafkaIntegration(
            iceberg_writer=writer,
            batch_size=5,  # Small batch size for demo
            flush_interval=10  # 10 seconds for demo
        )
        
        # Start integration
        await integration.start()
        logger.info("Iceberg Kafka integration started")
        
        # Simulate Kafka events
        num_events = int(os.environ.get("NUM_EVENTS", "10"))
        delay = float(os.environ.get("EVENT_DELAY", "1.0"))
        await simulate_kafka_events(integration, num_events, delay)
        
        # Ensure all events are written
        await integration.flush()
        
        # Clean up
        await integration.stop()
        logger.info("Iceberg Kafka integration stopped")
        
        logger.info("Kafka to Iceberg streaming example completed successfully")
    
    except Exception as e:
        logger.error(f"Error in streaming example: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())