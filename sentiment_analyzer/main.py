import os
import time
import logging
import threading
import argparse
from typing import Dict, Any
from datetime import datetime, timedelta
import json

from sentiment_analyzer.data.redis_manager import RedisSentimentCache
from sentiment_analyzer.data.sp500_tracker import SP500Tracker
from sentiment_analyzer.models.sentiment_model import SentimentModel
from sentiment_analyzer.data.parquet_reader import ParquetReader
from sentiment_analyzer.utils.logging_utils import setup_logging
from sentiment_analyzer.utils.config import load_config, get_default_config

# Set up logging
setup_logging("sentiment_analyzer.log")
logger = logging.getLogger(__name__)

class SentimentAnalyzerService:
    """Main service that continuously updates sentiment scores."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the sentiment analyzer service.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.running = False
        
        # Initialize components
        self.redis_cache = RedisSentimentCache(
            host=config.get("redis_host", "localhost"),
            port=config.get("redis_port", 6379),
            db=config.get("redis_db", 0),
            event_expiry_seconds=config.get("event_expiry", 604800)
        )
        
        self.sp500_tracker = SP500Tracker(
            update_interval_hours=config.get("sp500_update_hours", 24),
            top_n=config.get("top_n_tickers", 10),
            metric=config.get("ranking_metric", "market_cap")
        )
        
        self.sentiment_model = SentimentModel(
            redis_cache=self.redis_cache,
            decay_type=config.get("decay_type", "exponential"),
            decay_half_life=config.get("decay_half_life", 24),
            max_age_hours=config.get("max_age_hours", 168)
        )
        
        self.parquet_reader = ParquetReader(
            data_dir=config.get("parquet_dir", "/home/jonat/WSL_RT_Sentiment/data/output")
        )
        
        # Initialize ticker list
        self.tickers = self.sp500_tracker.get_top_tickers()
        logger.info(f"Tracking top {len(self.tickers)} tickers: {self.tickers}")
        
        # Last update timestamps
        self.last_historical_update = None
        self.historical_update_interval = config.get("historical_update_interval", 3600)  # 1 hour
        
    def _load_historical_data(self):
        """Load historical data from Parquet files into Redis cache."""
        logger.info("Loading historical data from Parquet files...")
        
        for ticker in self.tickers:
            # Get recent data (e.g., last 7 days)
            now = datetime.now()
            max_age_hours = self.sentiment_model.max_age_hours
            
            df = self.parquet_reader.read_ticker_data(
                ticker,
                start_date=now - timedelta(hours=max_age_hours)
            )
            
            if df.empty:
                logger.warning(f"No historical data found for {ticker}")
                continue
                
            # Convert to events and add to Redis
            events = df.to_dict('records')
            count = 0
            
            for event in events:
                # Ensure timestamp is a datetime object
                if isinstance(event.get('timestamp'), str):
                    try:
                        event['timestamp'] = datetime.fromisoformat(event['timestamp'])
                    except ValueError:
                        logger.warning(f"Invalid timestamp format: {event['timestamp']}")
                        continue
                        
                # Add to Redis
                self.redis_cache.add_ticker_event(ticker, event)
                count += 1
                
            # Calculate and store the current sentiment score
            score = self.sentiment_model.calculate_sentiment_score(ticker)
            self.redis_cache.update_ticker_score(ticker, score)
            
            logger.info(f"Loaded {count} historical events for {ticker}, current score: {score:.2f}")
            
        self.last_historical_update = datetime.now()
        
    def start(self):
        """Start the sentiment analyzer service."""
        if self.running:
            logger.warning("Service is already running")
            return
            
        self.running = True
        logger.info("Starting sentiment analyzer service...")
        
        # Load historical data
        self._load_historical_data()
        
        # Start the update thread
        self.update_thread = threading.Thread(target=self._update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        logger.info("Service started successfully")
        
    def stop(self):
        """Stop the sentiment analyzer service."""
        if not self.running:
            logger.warning("Service is not running")
            return
            
        self.running = False
        logger.info("Stopping sentiment analyzer service...")
        
        # Wait for update thread to finish
        if hasattr(self, 'update_thread') and self.update_thread.is_alive():
            self.update_thread.join(timeout=5.0)
            
        logger.info("Service stopped successfully")
        
    def _update_loop(self):
        """Main loop for updating sentiment scores."""
        logger.info("Update loop started")
        
        while self.running:
            try:
                # Update ticker list periodically
                self.tickers = self.sp500_tracker.get_top_tickers()
                
                # Check if we need to refresh historical data
                now = datetime.now()
                if (self.last_historical_update is None or 
                    (now - self.last_historical_update).total_seconds() >= self.historical_update_interval):
                    self._load_historical_data()
                    
                # Sleep for a bit
                time.sleep(self.config.get("update_interval", 60))
                
            except Exception as e:
                logger.error(f"Error in update loop: {e}", exc_info=True)
                time.sleep(10)  # Sleep before retrying
                
        logger.info("Update loop ended")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sentiment Analyzer Service")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config file")
    args = parser.parse_args()
    
    # Load configuration
    config = {}
    try:
        config = load_config(args.config)
    except Exception as e:
        logger.warning(f"Error loading config file: {e}. Using defaults.")
        config = get_default_config()
    
    # Start the service
    service = SentimentAnalyzerService(config)
    
    try:
        service.start()
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    finally:
        service.stop()