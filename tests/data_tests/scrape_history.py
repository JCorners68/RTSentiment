#!/usr/bin/env python
"""
Script to scrape historical data between specified date ranges.
"""
import argparse
import datetime
import os
import asyncio
import aiohttp
import json
import logging
import hashlib
import threading
import time
from typing import Dict, List, Any, Optional, Set

# Import Prometheus metrics
try:
    from prometheus_client import Counter, Gauge, Histogram, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    print("Warning: prometheus_client not installed. Metrics will not be reported.")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define Prometheus metrics if available
if PROMETHEUS_AVAILABLE:
    # Scraper metrics
    ITEMS_SCRAPED = Counter(
        "scraper_items_scraped_total", 
        "Total items scraped by source",
        ["source"]
    )
    PROCESSING_DURATION = Histogram(
        "scraper_processing_duration_seconds", 
        "Scraper processing time",
        ["source"]
    )
    DUPLICATES_REMOVED = Counter(
        "scraper_duplicates_removed_total", 
        "Total duplicate items removed by source",
        ["source"]
    )
    UNIQUE_ITEMS = Gauge(
        "scraper_unique_items_total", 
        "Total unique items scraped by source",
        ["source"]
    )
    SCRAPER_ERRORS = Counter(
        "scraper_errors_total", 
        "Total scraper errors by source and type",
        ["source", "error_type"]
    )
    CACHE_HITS = Counter(
        "scraper_cache_hits_total", 
        "Cache hits when retrieving data",
        ["source"]
    )
    
    # Define start metrics server function
    def start_metrics_server(port: int = 8080, addr: str = '0.0.0.0'):
        """Start Prometheus metrics server."""
        logger.info(f"Starting Prometheus metrics server on {addr}:{port}")
        start_http_server(port, addr)
        
    # We'll start the server in the main function based on command line arguments
else:
    # Define dummy functions if prometheus_client is not available
    def increment_counter(name, value=1, **labels):
        pass
        
    def set_gauge(name, value, **labels):
        pass
        
    def observe_histogram(name, value, **labels):
        pass

class HistoricalScraper:
    """Scraper for historical data from various sources."""
    
    def __init__(self, source: str, start_date: str, end_date: str):
        """Initialize the scraper with date range and source."""
        self.source = source
        self.start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
        self.end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        self.headers = {
            "User-Agent": "python:real-time-sentiment:v1.0 (historical scraper)",
            "Accept": "application/json"
        }
        self.results = []
        self.item_hashes = set()  # Store hashes of processed items to detect duplicates
        
        # Determine base directory - handle both direct execution and package import
        base_dir = os.getcwd()
        logger.info(f"Current working directory: {base_dir}")
        
        # Create paths for output and cache directories
        self.output_dir = os.path.join(base_dir, "data", "output", "historical")
        self.cache_dir = os.path.join(base_dir, "data", "cache", "historical")
        self.dedup_file = os.path.join(base_dir, "data", "cache", "deduplication", f"{source}_hashes.json")
        
        # Ensure directories exist
        try:
            os.makedirs(self.output_dir, exist_ok=True)
            logger.info(f"Output directory: {self.output_dir}")
        except Exception as e:
            logger.error(f"Failed to create output directory: {e}")
            # Fallback to temp directory if we can't create the output directory
            self.output_dir = os.path.join("/tmp", "rt_sentiment", "output")
            os.makedirs(self.output_dir, exist_ok=True)
            logger.info(f"Using fallback output directory: {self.output_dir}")
            
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"Cache directory: {self.cache_dir}")
        except Exception as e:
            logger.error(f"Failed to create cache directory: {e}")
            # Fallback to temp directory if we can't create the cache directory
            self.cache_dir = os.path.join("/tmp", "rt_sentiment", "cache")
            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"Using fallback cache directory: {self.cache_dir}")
            
        # Create deduplication directory
        os.makedirs(os.path.dirname(self.dedup_file), exist_ok=True)
        
        # Load existing hash records to prevent duplicates
        self._load_deduplication_hashes()
    
    async def run(self) -> int:
        """Run the scraper and return count of items scraped."""
        logger.info(f"Starting historical scraping for {self.source} from {self.start_date.date()} to {self.end_date.date()}")
        
        if self.source == 'news':
            count = await self.scrape_news()
        elif self.source == 'reddit':
            count = await self.scrape_reddit()
        else:
            raise ValueError(f"Unsupported source: {self.source}")
        
        # Save results to file
        self._save_results()
        
        return count
    
    async def scrape_news(self) -> int:
        """Scrape historical news articles."""
        logger.info("Scraping historical news articles")
        
        # Track processing time if Prometheus is available
        start_time = time.time()
        
        # For this example, we'll use a free financial news API
        # In production, you would use your actual premium news APIs with API keys
        
        # Generate date range
        current_date = self.start_date
        all_articles = []
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            while current_date <= self.end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                cache_file = os.path.join(self.cache_dir, f"news_{date_str}.json")
                
                # Check cache first
                if os.path.exists(cache_file):
                    with open(cache_file, 'r') as f:
                        articles = json.load(f)
                        logger.info(f"Loaded {len(articles)} articles for {date_str} from cache")
                        
                        # Record cache hit in Prometheus
                        if PROMETHEUS_AVAILABLE:
                            CACHE_HITS.labels(source="news").inc()
                else:
                    # Example API URL - would be replaced with actual news API
                    # This is a mock for demonstration - you'd use a real API
                    try:
                        # Simulating API call - in real implementation, you'd use actual API endpoints
                        # Example: url = f"https://newsapi.org/v2/everything?q=finance&from={date_str}&to={date_str}&apiKey={API_KEY}"
                        
                        # For simulation, we'll generate 5-15 mock articles per day
                        import random
                        article_count = random.randint(5, 15)
                        articles = []
                        
                        for i in range(article_count):
                            articles.append({
                                "title": f"Financial News Article {i+1} for {date_str}",
                                "source": "Historical News Scraper",
                                "published_at": f"{date_str}T{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:00Z",
                                "content": f"This is simulated content for article {i+1} on {date_str}",
                                "url": f"https://example.com/news/{date_str}/{i+1}"
                            })
                        
                        # Cache the results
                        with open(cache_file, 'w') as f:
                            json.dump(articles, f)
                        
                        logger.info(f"Scraped {len(articles)} articles for {date_str}")
                    except Exception as e:
                        logger.error(f"Error scraping news for {date_str}: {e}")
                        
                        # Record error in Prometheus
                        if PROMETHEUS_AVAILABLE:
                            SCRAPER_ERRORS.labels(source="news", error_type=type(e).__name__).inc()
                        
                        articles = []
                
                all_articles.extend(articles)
                current_date += datetime.timedelta(days=1)
        
        self.results = all_articles
        total_count = len(all_articles)
        
        # Record metrics in Prometheus
        if PROMETHEUS_AVAILABLE:
            ITEMS_SCRAPED.labels(source="news").inc(total_count)
            processing_time = time.time() - start_time
            PROCESSING_DURATION.labels(source="news").observe(processing_time)
            logger.info(f"Recorded metrics - items: {total_count}, processing_time: {processing_time:.2f}s")
        
        return total_count
    
    async def scrape_reddit(self) -> int:
        """Scrape historical Reddit posts."""
        logger.info("Scraping historical Reddit posts")
        
        # Track processing time if Prometheus is available
        start_time = time.time()
        
        # For this example, we'll use simulated Reddit data
        # In production, you'd use the Pushshift API or Reddit API with authentication
        
        # Generate date range
        current_date = self.start_date
        all_posts = []
        
        # Define subreddits of interest
        subreddits = ["wallstreetbets", "investing", "stocks"]
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            while current_date <= self.end_date:
                date_str = current_date.strftime('%Y-%m-%d')
                cache_file = os.path.join(self.cache_dir, f"reddit_{date_str}.json")
                
                # Check cache first
                if os.path.exists(cache_file):
                    with open(cache_file, 'r') as f:
                        posts = json.load(f)
                        logger.info(f"Loaded {len(posts)} Reddit posts for {date_str} from cache")
                        
                        # Record cache hit in Prometheus
                        if PROMETHEUS_AVAILABLE:
                            CACHE_HITS.labels(source="reddit").inc()
                else:
                    # Example API URL for Pushshift (historical Reddit data)
                    # In real implementation, you'd use actual API endpoints
                    try:
                        # Simulating API call - in real implementation, you'd use actual API endpoints
                        # For simulation, we'll generate 10-30 mock posts per day
                        import random
                        posts = []
                        
                        for subreddit in subreddits:
                            post_count = random.randint(3, 10)  # 3-10 posts per subreddit
                            
                            for i in range(post_count):
                                posts.append({
                                    "title": f"[r/{subreddit}] Financial Discussion Post {i+1} for {date_str}",
                                    "subreddit": subreddit,
                                    "created_utc": f"{date_str}T{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:00Z",
                                    "selftext": f"This is simulated content for Reddit post {i+1} on {date_str} in r/{subreddit}",
                                    "permalink": f"/r/{subreddit}/comments/{date_str}{i}",
                                    "score": random.randint(1, 1000),
                                    "num_comments": random.randint(0, 200)
                                })
                        
                        # Cache the results
                        with open(cache_file, 'w') as f:
                            json.dump(posts, f)
                        
                        logger.info(f"Scraped {len(posts)} Reddit posts for {date_str}")
                    except Exception as e:
                        logger.error(f"Error scraping Reddit for {date_str}: {e}")
                        
                        # Record error in Prometheus
                        if PROMETHEUS_AVAILABLE:
                            SCRAPER_ERRORS.labels(source="reddit", error_type=type(e).__name__).inc()
                        
                        posts = []
                
                all_posts.extend(posts)
                current_date += datetime.timedelta(days=1)
        
        self.results = all_posts
        total_count = len(all_posts)
        
        # Record metrics in Prometheus
        if PROMETHEUS_AVAILABLE:
            ITEMS_SCRAPED.labels(source="reddit").inc(total_count)
            processing_time = time.time() - start_time
            PROCESSING_DURATION.labels(source="reddit").observe(processing_time)
            logger.info(f"Recorded metrics - items: {total_count}, processing_time: {processing_time:.2f}s")
            
        return total_count
    
    def _load_deduplication_hashes(self):
        """Load existing item hashes to prevent duplicate data."""
        if os.path.exists(self.dedup_file):
            try:
                with open(self.dedup_file, 'r') as f:
                    hash_list = json.load(f)
                    self.item_hashes = set(hash_list)
                    logger.info(f"Loaded {len(self.item_hashes)} existing item hashes for deduplication")
            except Exception as e:
                logger.error(f"Error loading deduplication hashes: {e}")
                self.item_hashes = set()
        else:
            logger.info("No existing deduplication file found, starting fresh")
            self.item_hashes = set()
    
    def _save_deduplication_hashes(self):
        """Save current item hashes to prevent duplicate data in future runs."""
        try:
            with open(self.dedup_file, 'w') as f:
                json.dump(list(self.item_hashes), f)
            logger.info(f"Saved {len(self.item_hashes)} item hashes for deduplication")
        except Exception as e:
            logger.error(f"Error saving deduplication hashes: {e}")
    
    def _get_item_hash(self, item: Dict[str, Any]) -> str:
        """Generate a unique hash for an item based on its content."""
        # For news articles, use title, source, and published_at
        if self.source == 'news':
            hash_content = f"{item.get('title', '')}{item.get('source', '')}{item.get('published_at', '')}"
        # For Reddit posts, use title, subreddit, created_utc, and permalink
        elif self.source == 'reddit':
            hash_content = f"{item.get('title', '')}{item.get('subreddit', '')}{item.get('created_utc', '')}{item.get('permalink', '')}"
        else:
            # Generic hash for other source types
            hash_content = json.dumps(item, sort_keys=True)
        
        # Create SHA-256 hash of the content
        return hashlib.sha256(hash_content.encode('utf-8')).hexdigest()
    
    def _deduplicate_items(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate items based on content hash."""
        unique_items = []
        duplicate_count = 0
        
        for item in items:
            item_hash = self._get_item_hash(item)
            if item_hash not in self.item_hashes:
                self.item_hashes.add(item_hash)
                unique_items.append(item)
            else:
                duplicate_count += 1
        
        if duplicate_count > 0:
            logger.info(f"Removed {duplicate_count} duplicate items")
            
            # Record duplicates in Prometheus
            if PROMETHEUS_AVAILABLE and duplicate_count > 0:
                DUPLICATES_REMOVED.labels(source=self.source).inc(duplicate_count)
        
        return unique_items
            
    def _save_results(self):
        """Save results to output file."""
        if not self.results:
            logger.warning("No results to save")
            return
        
        # Deduplicate results before saving
        unique_results = self._deduplicate_items(self.results)
        
        if len(unique_results) < len(self.results):
            logger.info(f"Deduplicated results: {len(self.results)} -> {len(unique_results)} items")
            self.results = unique_results
        
        # Save deduplication hashes for future runs
        self._save_deduplication_hashes()
        
        # Record total unique items in Prometheus
        if PROMETHEUS_AVAILABLE:
            UNIQUE_ITEMS.labels(source=self.source).set(len(self.results))
        
        # Save to both output directory and test_results directory
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 1. Save to normal output directory (for application usage)
        output_file = os.path.join(
            self.output_dir, 
            f"{self.source}_{self.start_date.strftime('%Y%m%d')}_to_{self.end_date.strftime('%Y%m%d')}_{timestamp}.json"
        )
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Saved {len(self.results)} items to {output_file}")
        
        # 2. Save to test_results directory (for test reporting)
        date_str = datetime.datetime.now().strftime('%y%m%d')
        
        # Create test_results directory if it doesn't exist
        test_results_dir = os.path.join(os.getcwd(), "tests", "test_results")
        os.makedirs(test_results_dir, exist_ok=True)
        
        # Find the next available sequence number
        seq_num = 1
        while True:
            test_filename = f"scrape_results_{date_str}_{seq_num}.json"
            if not os.path.exists(os.path.join(test_results_dir, test_filename)):
                break
            seq_num += 1
        
        test_output_file = os.path.join(test_results_dir, test_filename)
        
        with open(test_output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"Saved test results to {test_output_file}")

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Scrape historical data between date ranges',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape Reddit posts between April 1-15, 2025
  python tests/scrape_history.py --start_date 2025-04-01 --end_date 2025-04-15 --source reddit

  # Scrape news articles for the last 30 days
  python tests/scrape_history.py --start_date 2025-03-24 --end_date 2025-04-23 --source news
  
  # Scrape news articles without deduplication
  python tests/scrape_history.py --start_date 2025-03-24 --end_date 2025-04-23 --source news --no-dedup
  
  # Scrape with Prometheus metrics on port 8081
  python tests/scrape_history.py --start_date 2025-03-24 --end_date 2025-04-23 --source news --metrics-port 8081
"""
    )
    parser.add_argument('--start_date', type=str, required=True, 
                        help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end_date', type=str, required=True, 
                        help='End date in YYYY-MM-DD format')
    parser.add_argument('--source', type=str, choices=['news', 'reddit'], required=True,
                        help='Source to scrape (news or reddit)')
    parser.add_argument('--no-dedup', action='store_true',
                        help='Disable deduplication (will process and save all items, even duplicates)')
    parser.add_argument('--reset-dedup', action='store_true',
                        help='Reset deduplication history (start fresh with no remembered items)')
    parser.add_argument('--metrics-port', type=int, default=8080,
                        help='Port to expose Prometheus metrics on (default: 8080)')
    parser.add_argument('--no-metrics', action='store_true',
                        help='Disable Prometheus metrics completely')
    
    return parser.parse_args()

async def main():
    """Main function."""
    args = parse_args()
    
    # Handle Prometheus metrics options
    if PROMETHEUS_AVAILABLE and not args.no_metrics:
        try:
            # Start the metrics server in a background thread
            metrics_thread = threading.Thread(
                target=start_metrics_server, 
                args=(args.metrics_port, '0.0.0.0'), 
                daemon=True
            )
            metrics_thread.start()
            logger.info(f"Prometheus metrics server started on 0.0.0.0:{args.metrics_port}")
            print(f"Prometheus metrics available at http://localhost:{args.metrics_port}/metrics")
        except Exception as e:
            logger.error(f"Failed to start Prometheus metrics server: {e}")
    elif args.no_metrics:
        logger.info("Prometheus metrics disabled by command line option")
    elif not PROMETHEUS_AVAILABLE:
        logger.warning("Prometheus client not installed. Install with: pip install prometheus-client")
    
    # Parse and validate dates
    try:
        start_date = args.start_date
        end_date = args.end_date
        
        # Validate date format
        datetime.datetime.strptime(start_date, '%Y-%m-%d')
        datetime.datetime.strptime(end_date, '%Y-%m-%d')
        
        # Ensure start_date <= end_date
        if start_date > end_date:
            raise ValueError("Start date must be before or equal to end date")
    except ValueError as e:
        logger.error(f"Date error: {e}")
        return
    
    # Initialize and run scraper
    scraper = HistoricalScraper(args.source, start_date, end_date)
    
    # Handle deduplication options
    if args.reset_dedup:
        logger.info("Resetting deduplication history as requested")
        scraper.item_hashes = set()
        
    if args.no_dedup:
        # If deduplication is disabled, replace the deduplicate method with a pass-through
        logger.info("Deduplication disabled as requested")
        original_deduplicate = scraper._deduplicate_items
        
        # Replace with function that returns items unchanged
        def no_dedup(items):
            logger.info("Skipping deduplication as requested")
            return items
            
        scraper._deduplicate_items = no_dedup
    
    # Run the scraper
    initial_count = await scraper.run()
    
    # Get final count after deduplication
    final_count = len(scraper.results)
    dedup_count = initial_count - final_count if not args.no_dedup else 0
    
    print(f"\n{'=' * 50}")
    print(f"Historical Scraping Complete")
    print(f"Source: {args.source}")
    print(f"Date Range: {start_date} to {end_date}")
    print(f"Total Items Scraped: {initial_count}")
    if not args.no_dedup:
        print(f"Unique Items (after deduplication): {final_count}")
        print(f"Duplicates Removed: {dedup_count}")
    print(f"{'=' * 50}\n")
    
    # Keep the process running for a while if metrics are enabled
    # This gives Prometheus time to scrape the metrics
    if PROMETHEUS_AVAILABLE and not args.no_metrics:
        print("Keeping process alive for metrics collection. Press Ctrl+C to exit.")
        print(f"Process is listening for metrics on http://0.0.0.0:{args.metrics_port}/metrics")
        try:
            # Wait for 5 minutes to allow Prometheus to scrape the metrics
            for i in range(30):
                await asyncio.sleep(10)
                print(f"Still running... (waited {(i+1)*10} seconds)")
        except KeyboardInterrupt:
            print("Exiting...")
    
    # Return the counts for potential further processing
    return {
        "total_items": initial_count,
        "unique_items": final_count,
        "duplicates_removed": dedup_count
    }

if __name__ == "__main__":
    asyncio.run(main())