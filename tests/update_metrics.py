#!/usr/bin/env python3
"""
Continuously update the metrics server with new data.
This script simulates scraper activity by periodically sending
new metrics to the metrics server.
"""
import time
import argparse
import random
import sys
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# Define metrics
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

CACHE_MISSES = Counter(
    "scraper_cache_misses_total", 
    "Cache misses when retrieving data",
    ["source"]
)

SCRAPER_LAST_RUN = Gauge(
    "scraper_last_run_timestamp", 
    "Timestamp of last scraper run",
    ["source"]
)

SCRAPER_LAST_SUCCESSFUL_RUN = Gauge(
    "scraper_last_successful_run_timestamp", 
    "Timestamp of last successful scraper run",
    ["source"]
)

SCRAPER_ITEMS_BY_TICKER = Gauge(
    "scraper_items_by_ticker", 
    "Number of scraped items by ticker",
    ["source", "ticker"]
)

SCRAPER_UPTIME = Gauge(
    "scraper_uptime_seconds", 
    "Scraper service uptime in seconds"
)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Start a metrics server with continuous updates'
    )
    parser.add_argument('--port', type=int, default=8082,
                        help='Port to expose Prometheus metrics on (default: 8082)')
    parser.add_argument('--interval', type=int, default=10,
                        help='Interval in seconds between updates (default: 10)')
    parser.add_argument('--verbose', action='store_true',
                        help='Print verbose output')
    return parser.parse_args()

def simulate_scraper_activity(sources=None, verbose=False):
    """Simulate scraper activity by updating metrics."""
    if sources is None:
        sources = ["news", "reddit", "twitter"]
    
    for source in sources:
        # Simulate scraping new items
        items_count = random.randint(5, 20)
        ITEMS_SCRAPED.labels(source=source).inc(items_count)
        
        # Simulate processing time
        processing_time = random.uniform(0.1, 2.0)
        PROCESSING_DURATION.labels(source=source).observe(processing_time)
        
        # Simulate duplicate removal
        duplicates = random.randint(0, 5)
        DUPLICATES_REMOVED.labels(source=source).inc(duplicates)
        
        # Update unique items
        unique_items = UNIQUE_ITEMS.labels(source=source)._value.get() or 0
        unique_items += (items_count - duplicates)
        UNIQUE_ITEMS.labels(source=source).set(unique_items)
        
        # Simulate cache hits/misses
        cache_hits = random.randint(0, 10)
        cache_misses = random.randint(0, 5)
        CACHE_HITS.labels(source=source).inc(cache_hits)
        CACHE_MISSES.labels(source=source).inc(cache_misses)
        
        # Simulate occasional errors - reduce to 1% chance
        if random.random() < 0.01:  # 1% chance of error
            error_types = ["timeout", "parsing", "connection"]
            error_type = random.choice(error_types)
            SCRAPER_ERRORS.labels(source=source, error_type=error_type).inc()
            # Don't update successful timestamp if there was an error
        else:
            # Update last successful run timestamp (only if no error)
            SCRAPER_LAST_SUCCESSFUL_RUN.labels(source=source).set(time.time())
        
        # Update last run timestamp (always update regardless of errors)
        SCRAPER_LAST_RUN.labels(source=source).set(time.time())
        
        # Simulate items by ticker
        tickers = ["AAPL", "GOOGL", "MSFT", "AMZN", "META", "TSLA", "NVDA", "INTC", "AMD", "NFLX", "DIS", "PYPL", "BABA", "UBER", "LYFT"]
        for _ in range(3):  # Add some random ticker data
            ticker = random.choice(tickers)
            count = random.randint(1, 5)
            # Get current value or default to 0
            current = SCRAPER_ITEMS_BY_TICKER.labels(source=source, ticker=ticker)._value.get() or 0
            # Increment by new count
            SCRAPER_ITEMS_BY_TICKER.labels(source=source, ticker=ticker).set(current + count)
        
        if verbose:
            print(f"[{source}] Scraped {items_count} items, {duplicates} duplicates, {unique_items} unique total")

def main():
    """Main function."""
    args = parse_args()
    
    # Start the metrics server
    start_http_server(args.port, '0.0.0.0')
    print(f"Prometheus metrics server started on http://0.0.0.0:{args.port}/metrics")
    
    # Track uptime
    start_time = time.time()
    
    # Update metrics periodically
    try:
        counter = 0
        while True:
            # Update uptime
            uptime = time.time() - start_time
            SCRAPER_UPTIME.set(uptime)
            
            # Simulate scraper activity
            simulate_scraper_activity(verbose=args.verbose)
            
            counter += 1
            if args.verbose or counter % 6 == 0:  # Print every minute with default interval
                print(f"Metrics updated (uptime: {uptime:.1f}s)")
            
            # Sleep for the specified interval
            time.sleep(args.interval)
            
    except KeyboardInterrupt:
        print("\nShutting down metrics server")
    
if __name__ == "__main__":
    main()