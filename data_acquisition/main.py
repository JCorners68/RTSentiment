"""
Main entry point for the data acquisition service.
Sets up and runs periodic web scrapers.
"""
import os
import asyncio
import logging
import json
import signal
import sys
import time
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import scraper classes
from scrapers.news_scraper import NewsScraper
from scrapers.reddit_scraper import RedditScraper
from utils.event_producer import EventProducer

# Try to import metrics server
try:
    from metrics import MetricsServer, record_unique_items, CACHE_HITS, UNIQUE_ITEMS
    metrics_available = True
except ImportError:
    logger.warning("Metrics module not available, metrics server will not be started")
    metrics_available = False

# Global variables to track running tasks
scrapers = []
scraper_tasks = []
metrics_server = None

async def initialize_scrapers():
    """
    Initialize all scrapers based on the configuration.
    """
    global scrapers, scraper_tasks, metrics_server

    # Load configuration
    config_path = os.getenv("SCRAPER_CONFIG_PATH", "config/scraper_config.json")
    logger.info(f"Loading configuration from {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load configuration: {e}")
        # Use default minimal config
        config = {
            "kafka_bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
            "high_priority_topic": os.getenv("HIPRI_TOPIC", "sentiment-events-high"),
            "standard_priority_topic": os.getenv("STDPRI_TOPIC", "sentiment-events-standard"),
            "polling_interval": 300,
            "news_polling_interval": 600,
            "reddit_polling_interval": 300,
            "sources": [
                {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news"},
                {"name": "MarketWatch", "url": "https://www.marketwatch.com/latest-news"}
            ]
        }
        logger.warning("Using default configuration")

    # Create event producer
    producer = EventProducer(
        bootstrap_servers=config.get("kafka_bootstrap_servers", "kafka:9092"),
        high_priority_topic=config.get("high_priority_topic", "sentiment-events-high"),
        standard_priority_topic=config.get("standard_priority_topic", "sentiment-events-standard")
    )
    
    # Initialize scrapers
    news_scraper = NewsScraper(producer, config)
    scrapers.append(news_scraper)
    
    # Reddit scraper (if enabled)
    if config.get("enable_reddit", True):
        try:
            reddit_scraper = RedditScraper(producer, config)
            scrapers.append(reddit_scraper)
        except Exception as e:
            logger.error(f"Failed to initialize Reddit scraper: {e}")
    
    # Start metrics server if available
    if metrics_available:
        try:
            # Create metrics server
            metrics_server = MetricsServer(
                scrapers=scrapers,
                host='0.0.0.0',
                port=int(os.getenv("METRICS_PORT", "8085"))
            )
            
            # Start metrics server
            await metrics_server.start()
            logger.info("Started metrics server")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
    
    # Start all scrapers
    for scraper in scrapers:
        await scraper.start()
        logger.info(f"Started {scraper.name}")
    
    return scrapers

async def run_scraper(scraper, interval=60):
    """
    Run a scraper periodically at the specified interval.
    
    Args:
        scraper: The scraper instance to run
        interval: Time in seconds between runs
    """
    while True:
        try:
            logger.info(f"Running {scraper.name}")
            await scraper.scrape()
            logger.info(f"Completed {scraper.name} run, sleeping for {interval} seconds")
        except Exception as e:
            logger.error(f"Error in {scraper.name}: {e}", exc_info=True)
        
        # Sleep until next run
        await asyncio.sleep(interval)

async def start_scraper_tasks():
    """
    Start periodic tasks for all scrapers.
    """
    global scrapers, scraper_tasks
    
    # Initialize scrapers if not done yet
    if not scrapers:
        scrapers = await initialize_scrapers()
    
    # Run each scraper at its configured interval
    for scraper in scrapers:
        interval = getattr(scraper, "interval", 60)  # Default to 60 seconds
        task = asyncio.create_task(run_scraper(scraper, interval))
        scraper_tasks.append(task)
        logger.info(f"Scheduled {scraper.name} to run every {interval} seconds")
    
    return scraper_tasks

async def shutdown():
    """
    Gracefully shut down all scrapers and tasks.
    """
    global scrapers, scraper_tasks, metrics_server
    
    # Stop all scraper tasks
    for task in scraper_tasks:
        task.cancel()
    
    if scraper_tasks:
        await asyncio.gather(*scraper_tasks, return_exceptions=True)
    
    # Stop all scrapers
    for scraper in scrapers:
        await scraper.stop()
    
    # Stop metrics server if running
    if metrics_server:
        try:
            await metrics_server.stop()
            logger.info("Metrics server shut down")
        except Exception as e:
            logger.error(f"Error shutting down metrics server: {e}")
    
    logger.info("All scrapers and tasks shut down")

async def main():
    """
    Main entry point for the scraper service.
    """
    # Create data directories if they don't exist
    os.makedirs("data/output", exist_ok=True)
    os.makedirs("data/cache/deduplication", exist_ok=True)
    os.makedirs("data/logs", exist_ok=True)
    
    logger.info("Web scraper service started")
    
    # Start all scraper tasks
    tasks = await start_scraper_tasks()
    
    # Keep the service running until interrupted
    try:
        # Wait for all tasks to complete (they should run forever)
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Tasks cancelled")
    finally:
        await shutdown()

if __name__ == "__main__":
    # Set up signal handlers for graceful shutdown
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for s in signals:
        loop.add_signal_handler(
            s, lambda s=s: asyncio.create_task(shutdown())
        )
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        loop.close()
        logger.info("Web scraper service stopped")