#!/usr/bin/env python3
"""
Prometheus metrics server for Parquet sentiment data.
Reads Parquet files and exposes their data as Prometheus metrics.
"""
import os
import time
import logging
import argparse
import glob
import threading
from datetime import datetime, timedelta
import pandas as pd
from prometheus_client import Counter, Gauge, start_http_server

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define metrics - recreating with different namespace
SENTIMENT_VALUE = Gauge(
    "sentiment_analysis_value", 
    "Sentiment value by ticker",
    ["ticker", "source", "model"]
)

SENTIMENT_COUNT = Gauge(
    "sentiment_analysis_count", 
    "Number of sentiment records by ticker",
    ["ticker", "source"]
)

CONFIDENCE_VALUE = Gauge(
    "sentiment_analysis_confidence", 
    "Confidence level of sentiment analysis by ticker",
    ["ticker", "source", "model"]
)

PARQUET_FILE_COUNT = Gauge(
    "parquet_analysis_file_count", 
    "Number of Parquet files by type",
    ["type"]
)

LAST_UPDATE_TIME = Gauge(
    "sentiment_analysis_last_update_timestamp", 
    "Timestamp of the last data update",
    ["ticker"]
)

# Add a simple test metric to verify prometheus is working
TEST_METRIC = Gauge("parquet_test_metric", "Test metric to verify prometheus integration")
TEST_METRIC.set(42.0)  # Set a static value

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Start a Prometheus metrics server for Parquet sentiment data'
    )
    parser.add_argument('--port', type=int, default=8082,
                        help='Port to expose Prometheus metrics on (default: 8082)')
    parser.add_argument('--parquet-dir', type=str, default='./data/output',
                        help='Directory containing Parquet files (default: ./data/output)')
    parser.add_argument('--update-interval', type=int, default=60,
                        help='Update interval in seconds (default: 60)')
    return parser.parse_args()

def load_parquet_metrics(parquet_dir):
    """
    Load metrics from Parquet files.
    
    Args:
        parquet_dir: Directory containing Parquet files
    """
    # Reset metrics
    SENTIMENT_VALUE._metrics = {}
    SENTIMENT_COUNT._metrics = {}
    CONFIDENCE_VALUE._metrics = {}
    
    # Find all Parquet files
    parquet_files = glob.glob(os.path.join(parquet_dir, "*.parquet"))
    ticker_files = [f for f in parquet_files if not f.endswith("multi_ticker_sentiment.parquet")]
    
    # Update file count metrics
    PARQUET_FILE_COUNT.labels(type="ticker").set(len(ticker_files))
    PARQUET_FILE_COUNT.labels(type="total").set(len(parquet_files))
    
    logger.info(f"Found {len(parquet_files)} Parquet files in {parquet_dir}")
    
    # Debug: Print first few files to verify paths
    for i, file in enumerate(parquet_files[:5]):
        logger.debug(f"File {i}: {file}")
    
    # Process each Parquet file
    for file_path in parquet_files:
        try:
            # Extract ticker from filename
            filename = os.path.basename(file_path)
            ticker = filename.replace("_sentiment.parquet", "").upper()
            
            # Load Parquet file
            df = pd.read_parquet(file_path)
            if df.empty:
                logger.warning(f"Empty Parquet file: {file_path}")
                continue
            
            # Debug: Print schema and sample data
            logger.debug(f"File: {file_path}, Columns: {df.columns}")
            logger.debug(f"File: {file_path}, Sample: {df.head(1)}")
            
            # Group by source and calculate metrics
            for source, group in df.groupby('source'):
                # Count records by ticker and source
                count = len(group)
                SENTIMENT_COUNT.labels(ticker=ticker, source=source).set(count)
                logger.debug(f"Setting SENTIMENT_COUNT for {ticker}/{source}: {count}")
                
                # Also add a source-only metric for easier aggregation
                try:
                    # Get existing count or default to 0
                    current = SENTIMENT_COUNT.labels(ticker="ALL", source=source)._value.get()
                    SENTIMENT_COUNT.labels(ticker="ALL", source=source).set(current + count)
                except Exception as e:
                    logger.debug(f"Exception getting ALL count: {e}")
                    SENTIMENT_COUNT.labels(ticker="ALL", source=source).set(count)
                
                # Calculate average sentiment by ticker, source, and model
                for model, model_group in group.groupby('model'):
                    avg_sentiment = model_group['sentiment'].mean()
                    avg_confidence = model_group['confidence'].mean()
                    
                    logger.debug(f"Setting SENTIMENT_VALUE for {ticker}/{source}/{model}: {avg_sentiment}")
                    SENTIMENT_VALUE.labels(ticker=ticker, source=source, model=model).set(avg_sentiment)
                    CONFIDENCE_VALUE.labels(ticker=ticker, source=source, model=model).set(avg_confidence)
            
            # Set last update timestamp
            if 'timestamp' in df.columns:
                try:
                    latest_timestamp = df['timestamp'].max()
                    if isinstance(latest_timestamp, str):
                        dt = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00'))
                        LAST_UPDATE_TIME.labels(ticker=ticker).set(dt.timestamp())
                except Exception as e:
                    logger.error(f"Error processing timestamp for {file_path}: {e}")
            
            logger.info(f"Processed {file_path} - {count} records")
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
    
    # Process multi-ticker file specially
    multi_file = os.path.join(parquet_dir, "multi_ticker_sentiment.parquet")
    if os.path.exists(multi_file):
        try:
            df = pd.read_parquet(multi_file)
            if not df.empty:
                # Group by ticker and source
                ticker_groups = df.groupby('ticker')
                for ticker, ticker_group in ticker_groups:
                    for source, source_group in ticker_group.groupby('source'):
                        # Count records
                        count = len(source_group)
                        SENTIMENT_COUNT.labels(ticker=ticker, source=source).set(count)
                        
                        # Also add a source-only metric for easier aggregation
                        try:
                            # Get existing count or default to 0
                            current = SENTIMENT_COUNT.labels(ticker="ALL", source=source)._value.get()
                            SENTIMENT_COUNT.labels(ticker="ALL", source=source).set(current + count)
                        except Exception:
                            SENTIMENT_COUNT.labels(ticker="ALL", source=source).set(count)
                        
                        # Calculate metrics by model
                        for model, model_group in source_group.groupby('model'):
                            avg_sentiment = model_group['sentiment'].mean()
                            avg_confidence = model_group['confidence'].mean()
                            
                            SENTIMENT_VALUE.labels(ticker=ticker, source=source, model=model).set(avg_sentiment)
                            CONFIDENCE_VALUE.labels(ticker=ticker, source=source, model=model).set(avg_confidence)
                        
                        # Set last update timestamp
                        if 'timestamp' in source_group.columns:
                            try:
                                latest_timestamp = source_group['timestamp'].max()
                                if isinstance(latest_timestamp, str):
                                    dt = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00'))
                                    LAST_UPDATE_TIME.labels(ticker=ticker).set(dt.timestamp())
                            except Exception as e:
                                logger.error(f"Error processing timestamp for multi-ticker {ticker}: {e}")
                
                logger.info(f"Processed multi-ticker file with {len(df)} records")
        except Exception as e:
            logger.error(f"Error processing multi-ticker file: {e}")

def update_metrics_loop(parquet_dir, interval):
    """
    Update metrics in a loop.
    
    Args:
        parquet_dir: Directory containing Parquet files
        interval: Update interval in seconds
    """
    while True:
        try:
            load_parquet_metrics(parquet_dir)
        except Exception as e:
            logger.error(f"Error updating metrics: {e}")
        
        time.sleep(interval)

def main():
    """Main function."""
    args = parse_args()
    
    # Start the metrics server
    start_http_server(args.port, '0.0.0.0')
    logger.info(f"Prometheus metrics server started on 0.0.0.0:{args.port}")
    print(f"Prometheus metrics available at http://localhost:{args.port}/metrics")
    
    # Initial load
    load_parquet_metrics(args.parquet_dir)
    
    # Start update thread
    update_thread = threading.Thread(
        target=update_metrics_loop,
        args=(args.parquet_dir, args.update_interval),
        daemon=True
    )
    update_thread.start()
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down metrics server")

if __name__ == "__main__":
    main()