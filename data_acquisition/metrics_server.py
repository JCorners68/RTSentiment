#!/usr/bin/env python3
"""
Standalone Prometheus metrics server for the data acquisition system.
This script provides a long-running metrics server that can be scraped by Prometheus.
"""
import os
import time
import logging
import argparse
import asyncio
import glob
import json
from typing import Dict, List, Any

from metrics import MetricsServer, record_unique_items, CACHE_HITS, RECORDS_SCRAPED, UNIQUE_ITEMS

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Start a Prometheus metrics server for data acquisition'
    )
    parser.add_argument('--port', type=int, default=8085,
                        help='Port to expose Prometheus metrics on (default: 8085)')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to bind to (default: 0.0.0.0)')
    return parser.parse_args()

def load_initial_metrics():
    """
    Load initial metrics from cached data.
    This allows the metrics server to display historical data even without running the scraper.
    """
    # Get base directory
    base_dir = os.getcwd()
    
    # Paths to check
    data_dir = os.path.join(base_dir, "data", "output")
    historical_dir = os.path.join(base_dir, "data", "output", "historical")
    cache_dir = os.path.join(base_dir, "data", "cache", "deduplication")
    
    # Count parquet files in output directory
    parquet_files = glob.glob(os.path.join(data_dir, "*.parquet"))
    ticker_counts = {}
    
    for file_path in parquet_files:
        ticker = os.path.basename(file_path).replace("_sentiment.parquet", "")
        ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
    
    # Count items in historical directory
    if os.path.exists(historical_dir):
        files = os.listdir(historical_dir)
        news_files = [f for f in files if f.startswith("news_")]
        reddit_files = [f for f in files if f.startswith("reddit_")]
        
        # Record counts
        record_unique_items("news", len(news_files))
        record_unique_items("reddit", len(reddit_files))
        
        # Update the total records counter
        total_records = len(news_files) + len(reddit_files)
        RECORDS_SCRAPED.inc(total_records)
        
        logger.info(f"Loaded initial metrics - news files: {len(news_files)}, reddit files: {len(reddit_files)}, total records: {total_records}")
    
    # Check cache files
    if os.path.exists(cache_dir):
        for cache_file in os.listdir(cache_dir):
            if not cache_file.endswith('.json'):
                continue
                
            try:
                file_path = os.path.join(cache_dir, cache_file)
                with open(file_path, 'r') as f:
                    cache_data = json.load(f)
                    
                source = cache_file.replace('_hashes.json', '').replace('scraper', '')
                items_count = len(cache_data.get('items', {}))
                
                # Record items count
                UNIQUE_ITEMS.labels(source=source).set(items_count)
                
                # Record cache hits
                CACHE_HITS.labels(source=source).inc(0)  # Ensure metric exists
                
                logger.info(f"Loaded cache metrics for {source}: {items_count} items")
            except Exception as e:
                logger.error(f"Error reading cache file {cache_file}: {e}")

async def update_metrics_periodically(metrics_server):
    """Update custom metrics periodically."""
    # Initial load of metrics
    load_initial_metrics()
    
    while True:
        try:
            # Check cache files
            base_dir = os.getcwd()
            cache_dir = os.path.join(base_dir, "data", "cache", "deduplication")
            
            if os.path.exists(cache_dir):
                for cache_file in os.listdir(cache_dir):
                    if not cache_file.endswith('.json'):
                        continue
                        
                    try:
                        file_path = os.path.join(cache_dir, cache_file)
                        with open(file_path, 'r') as f:
                            cache_data = json.load(f)
                            
                        source = cache_file.replace('_hashes.json', '').replace('scraper', '')
                        items_count = len(cache_data.get('items', {}))
                        
                        # Update items count
                        UNIQUE_ITEMS.labels(source=source).set(items_count)
                    except Exception as e:
                        logger.error(f"Error updating metrics from {cache_file}: {e}")
        except Exception as e:
            logger.error(f"Error in metrics update: {e}")
            
        # Sleep for 60 seconds
        await asyncio.sleep(60)

async def main_async():
    """Async main function."""
    args = parse_args()
    
    # Create metrics server
    metrics_server = MetricsServer(host=args.host, port=args.port)
    
    # Start metrics server
    await metrics_server.start()
    logger.info(f"Prometheus metrics server started on {args.host}:{args.port}")
    print(f"Prometheus metrics available at http://localhost:{args.port}/metrics")
    
    # Start metrics update task
    update_task = asyncio.create_task(update_metrics_periodically(metrics_server))
    
    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        # Handle graceful shutdown
        update_task.cancel()
        await metrics_server.stop()
    except KeyboardInterrupt:
        # Handle Ctrl+C
        update_task.cancel()
        await metrics_server.stop()
        logger.info("Shutting down metrics server")

def main():
    """Main function."""
    # Run the async main
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main_async())
    except KeyboardInterrupt:
        logger.info("Shutting down metrics server")
    finally:
        loop.close()

if __name__ == "__main__":
    main()