"""
Base class for all scrapers in the data acquisition service.
"""
import logging
import json
import os
import asyncio
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from utils.cache_manager import DeduplicationCache

logger = logging.getLogger(__name__)

class BaseScraper:
    """Base class for all scrapers."""
    
    def __init__(self, producer, config):
        """
        Initialize the scraper with event producer and configuration.
        
        Args:
            producer: Event producer for publishing events
            config: Configuration dictionary
        """
        self.producer = producer
        self.config = config
        self.name = self.__class__.__name__
        self.running = False
        
        # Setup data directories for real data
        self.output_dir = os.path.join(os.getcwd(), "data", "output", "real")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Setup cache directory for real data
        self.cache_dir = os.path.join(os.getcwd(), "data", "cache", "real_data", "deduplication")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Initialize deduplication cache
        cache_file = os.path.join(self.cache_dir, f"{self.name.lower()}_hashes.json")
        self.cache = DeduplicationCache(cache_file, max_age_days=self.config.get("cache_max_age_days", 30))
        
        # Initialize metrics
        self.metrics = {
            "unique_items_total": 0,
            "cache_hits_total": 0,
            "cache_hits_created": time.time()
        }
        
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape data from source. Must be implemented by subclasses.
        
        Returns:
            List of dictionaries containing scraped data
        """
        raise NotImplementedError
    
    def is_duplicate(self, item: Dict[str, Any]) -> bool:
        """
        Check if an item is a duplicate based on cached hashes.
        
        Args:
            item: Item to check
            
        Returns:
            True if duplicate, False otherwise
        """
        # Use cache manager to check if item has been seen before
        return self.cache.has_seen(item)
    
    def mark_as_seen(self, item: Dict[str, Any]) -> bool:
        """
        Mark an item as seen in the cache.
        
        Args:
            item: Item to mark as seen
            
        Returns:
            Success indicator
        """
        # Use cache manager to mark item as seen
        return self.cache.mark_seen(item)
        
    async def process_data(self, data: List[Dict[str, Any]]):
        """
        Process scraped data, save to Parquet, and send to event producer.
        Filters out duplicates based on content hashing.
        
        Args:
            data: List of dictionaries containing scraped data
        """
        if not data:
            logger.info(f"{self.name}: No data to process")
            return
        
        # Filter out duplicates
        unique_items = []
        cache_hits = 0
        
        for item in data:
            # Add metadata
            item["source"] = self.name
            
            # Check if item is a duplicate
            if self.is_duplicate(item):
                cache_hits += 1
                continue
                
            # Mark as seen and add to unique items
            self.mark_as_seen(item)
            unique_items.append(item)
        
        # Update metrics
        self.metrics["unique_items_total"] += len(unique_items)
        self.metrics["cache_hits_total"] += cache_hits
        
        logger.info(f"{self.name}: Found {len(unique_items)} unique items, {cache_hits} cache hits")
        
        # Process unique items
        for item in unique_items:
            # Determine priority based on source, engagement, or other factors
            priority = self._determine_priority(item)
            
            # Send to Kafka via event producer
            await self.producer.send(item, priority)
            
        # Save data to Parquet files
        if unique_items:
            self._save_to_parquet(unique_items)
            logger.info(f"{self.name}: Processed {len(unique_items)} unique items")
    
    def _determine_priority(self, item: Dict[str, Any]) -> str:
        """
        Determine priority of an item based on various factors.
        
        Args:
            item: Dictionary containing data item
            
        Returns:
            Priority level ("high" or "standard")
        """
        # Default implementation - subclasses can override for custom logic
        
        # Check if item has a weight
        if "weight" in item and item["weight"] > 0.7:
            return "high"
            
        # Check for high engagement in social media posts
        engagement = item.get("engagement", {})
        if engagement:
            engagement_score = (
                engagement.get("likes", 0) + 
                engagement.get("comments", 0) * 2 + 
                engagement.get("shares", 0) * 3
            )
            if engagement_score > 1000:
                return "high"
                
        # Default to standard priority
        return "standard"
    
    def _save_to_parquet(self, data: List[Dict[str, Any]]) -> bool:
        """
        Save data to Parquet files, organized by ticker.
        
        Args:
            data: List of dictionaries containing data items
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Group data by ticker
            ticker_groups = {}
            multi_ticker_data = []
            
            for item in data:
                tickers = item.get("tickers", [])
                
                # For items without tickers, use a default ticker
                if not tickers:
                    tickers = ["MARKET"]  # Use a generic MARKET ticker for general market news
                    
                # Items with multiple tickers go to both individual files
                # and the multi-ticker file
                if len(tickers) > 1:
                    multi_ticker_data.append(item)
                
                # Add to each ticker's group
                for ticker in tickers:
                    # Clean ticker symbol
                    ticker = ticker.upper().strip()
                    
                    # Prepare data for Parquet file
                    parquet_item = {
                        "timestamp": item.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        "ticker": ticker,
                        "sentiment": item.get("sentiment_score", 0.0),
                        "confidence": item.get("confidence", 0.5),
                        "source": item.get("source", self.name),
                        "model": item.get("model", "unknown"),
                        "article_id": item.get("id", str(uuid.uuid4())),
                        "article_title": item.get("title", "")
                    }
                    
                    # Add to ticker group
                    if ticker not in ticker_groups:
                        ticker_groups[ticker] = []
                    ticker_groups[ticker].append(parquet_item)
            
            # Save data for each ticker
            for ticker, items in ticker_groups.items():
                self._append_to_parquet_file(f"{ticker.lower()}_sentiment.parquet", items)
                
            # Save multi-ticker data
            if multi_ticker_data:
                # Convert to parquet format
                parquet_items = []
                for item in multi_ticker_data:
                    for ticker in item.get("tickers", []):
                        ticker = ticker.upper().strip()
                        parquet_item = {
                            "timestamp": item.get("timestamp", datetime.now(timezone.utc).isoformat()),
                            "ticker": ticker,
                            "sentiment": item.get("sentiment_score", 0.0),
                            "confidence": item.get("confidence", 0.5),
                            "source": item.get("source", self.name),
                            "model": item.get("model", "unknown"),
                            "article_id": item.get("id", str(uuid.uuid4())),
                            "article_title": item.get("title", "")
                        }
                        parquet_items.append(parquet_item)
                
                self._append_to_parquet_file("multi_ticker_sentiment.parquet", parquet_items)
                
            return True
        except Exception as e:
            logger.error(f"Error saving to Parquet: {e}")
            return False
    
    def _append_to_parquet_file(self, filename: str, items: List[Dict[str, Any]]) -> bool:
        """
        Append data to a Parquet file.
        
        Args:
            filename: Name of the Parquet file
            items: List of dictionaries to append
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not items:
                logger.debug(f"No items to append to {filename}")
                return True
                
            file_path = os.path.join(self.output_dir, filename)
            
            # Convert to pandas DataFrame
            df = pd.DataFrame(items)
            
            # Make sure timestamp is in the proper format
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%dT%H:%M:%S")
            
            try:
                # Check if file exists to decide between append and create
                if os.path.exists(file_path):
                    # Read existing file
                    existing_table = pq.read_table(file_path)
                    existing_df = existing_table.to_pandas()
                    
                    # Concatenate with new data
                    combined_df = pd.concat([existing_df, df], ignore_index=True)
                    
                    # Write back to file
                    table = pa.Table.from_pandas(combined_df)
                    pq.write_table(table, file_path)
                    logger.debug(f"Appended {len(items)} items to existing {filename}")
                else:
                    # Create new file
                    table = pa.Table.from_pandas(df)
                    pq.write_table(table, file_path)
                    logger.debug(f"Created new file {filename} with {len(items)} items")
            except Exception as e:
                # Fallback: overwrite the file if append fails
                logger.warning(f"Fallback: overwriting {filename} due to error: {e}")
                table = pa.Table.from_pandas(df)
                pq.write_table(table, file_path)
                logger.debug(f"Overwrote {filename} with {len(items)} items")
                
            return True
        except Exception as e:
            logger.error(f"Error handling Parquet file {filename}: {e}")
            return False
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get scraper metrics.
        
        Returns:
            Dictionary with metrics
        """
        # Return metrics in a format suitable for monitoring
        metric_type = self.__class__.__name__.lower().replace("scraper", "")
        return {
            f"scraper_unique_items_total{{source=\"{metric_type}\"}}": self.metrics["unique_items_total"],
            f"scraper_cache_hits_total{{source=\"{metric_type}\"}}": self.metrics["cache_hits_total"],
            f"scraper_cache_hits_created{{source=\"{metric_type}\"}}": self.metrics["cache_hits_created"]
        }
            
    async def start(self):
        """Start the scraper operation."""
        logger.info(f"Starting {self.name}")
        self.running = True
        
        # Start regular scraping loop
        while self.running:
            try:
                # Scrape data
                data = await self.scrape()
                
                # Process scraped data
                if data:
                    await self.process_data(data)
                
            except Exception as e:
                logger.error(f"Error in {self.name}: {e}", exc_info=True)
            
            # Wait for next cycle
            interval = self.config.get(f"{self.name.lower()}_interval", 60)  # Default 60 seconds
            logger.debug(f"{self.name}: Waiting {interval} seconds until next scrape")
            await asyncio.sleep(interval)
    
    async def stop(self):
        """Stop the scraper operation."""
        logger.info(f"Stopping {self.name}")
        self.running = False

# Import time module at the top level
import time