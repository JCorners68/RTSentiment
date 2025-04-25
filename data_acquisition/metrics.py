"""
Prometheus metrics for the Data Acquisition Service.
"""
import time
import threading
import logging
import asyncio
import os
import json
import glob
from typing import Dict, Any, List, Optional
from aiohttp import web

from prometheus_client import Counter, Gauge, Histogram, start_http_server, generate_latest

logger = logging.getLogger(__name__)

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

API_CALLS = Counter(
    "scraper_api_calls_total", 
    "External API calls by endpoint",
    ["source", "endpoint"]
)

API_ERRORS = Counter(
    "scraper_api_errors_total", 
    "External API errors by endpoint",
    ["source", "endpoint", "status_code"]
)

ITEMS_BY_TICKER = Counter(
    "scraper_items_by_ticker", 
    "Scraped items by ticker symbol",
    ["source", "ticker"]
)

RUN_DURATION = Histogram(
    "scraper_run_duration_seconds", 
    "Full scraper run duration",
    ["source"]
)

SCHEDULED_RUNS = Counter(
    "scraper_scheduled_runs_total", 
    "Total scheduled scraper runs",
    ["source"]
)

MANUAL_RUNS = Counter(
    "scraper_manual_runs_total", 
    "Total manual scraper runs",
    ["source"]
)

LAST_RUN_TIMESTAMP = Gauge(
    "scraper_last_successful_run_timestamp", 
    "Unix timestamp of last successful run",
    ["source"]
)

UPTIME = Gauge(
    "scraper_uptime_seconds", 
    "Scraper service uptime in seconds"
)

UNIQUE_ITEMS = Gauge(
    "scraper_unique_items_total",
    "Total unique items scraped (after deduplication)",
    ["source"]
)

# Start metrics server (legacy)
def start_metrics_server(port: int = 8080):
    """Start Prometheus metrics server."""
    print(f"Starting metrics server on port {port}")
    start_http_server(port)
    
    # Track uptime
    start_time = time.time()
    
    def update_uptime():
        while True:
            uptime = time.time() - start_time
            UPTIME.set(uptime)
            time.sleep(60)  # Update every minute
    
    threading.Thread(target=update_uptime, daemon=True).start()

# Helper functions
def record_scrape(source: str, items_count: int, duration: float):
    """Record a scrape operation."""
    ITEMS_SCRAPED.labels(source=source).inc(items_count)
    PROCESSING_DURATION.labels(source=source).observe(duration)
    LAST_RUN_TIMESTAMP.labels(source=source).set(time.time())
    
def record_scheduled_run(source: str):
    """Record a scheduled run."""
    SCHEDULED_RUNS.labels(source=source).inc()
    
def record_manual_run(source: str):
    """Record a manual run."""
    MANUAL_RUNS.labels(source=source).inc()
    
def record_error(source: str, error_type: str):
    """Record a scraper error."""
    SCRAPER_ERRORS.labels(source=source, error_type=error_type).inc()
    
def record_cache_hit(source: str):
    """Record a cache hit."""
    CACHE_HITS.labels(source=source).inc()
    
def record_cache_miss(source: str):
    """Record a cache miss."""
    CACHE_MISSES.labels(source=source).inc()
    
def record_api_call(source: str, endpoint: str):
    """Record an API call."""
    API_CALLS.labels(source=source, endpoint=endpoint).inc()
    
def record_api_error(source: str, endpoint: str, status_code: int):
    """Record an API error."""
    API_ERRORS.labels(source=source, endpoint=endpoint, status_code=status_code).inc()
    
def record_ticker_item(source: str, ticker: str):
    """Record an item for a ticker."""
    ITEMS_BY_TICKER.labels(source=source, ticker=ticker).inc()
    
def record_unique_items(source: str, count: int):
    """Set the gauge for unique items after deduplication."""
    UNIQUE_ITEMS.labels(source=source).set(count)
    
def track_run_duration(source: str):
    """Context manager to track run duration."""
    class RunTracker:
        def __enter__(self):
            self.start_time = time.time()
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            duration = time.time() - self.start_time
            RUN_DURATION.labels(source=source).observe(duration)
            if exc_type is not None:
                record_error(source, exc_type.__name__)
            else:
                LAST_RUN_TIMESTAMP.labels(source=source).set(time.time())
                
    return RunTracker()

class MetricsServer:
    """
    Metrics server for the data acquisition service.
    Collects and exposes metrics from scrapers.
    """
    
    def __init__(self, scrapers=None, host='0.0.0.0', port=8085):
        """
        Initialize the metrics server.
        
        Args:
            scrapers: List of scraper instances to collect metrics from
            host: Host to bind to
            port: Port to listen on
        """
        self.scrapers = scrapers or []
        self.host = host
        self.port = port
        self.app = web.Application()
        self.app.add_routes([web.get('/metrics', self.metrics_handler)])
        self.app.add_routes([web.get('/health', self.health_handler)])
        self.runner = None
        self.site = None
        self.uptime_start = time.time()
        
    async def start(self):
        """Start the metrics server."""
        logger.info(f"Starting metrics server on {self.host}:{self.port}")
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        
        # Start background task to update metrics
        asyncio.create_task(self._update_metrics_periodically())
        
    async def stop(self):
        """Stop the metrics server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Metrics server stopped")
    
    def add_scraper(self, scraper):
        """
        Add a scraper to collect metrics from.
        
        Args:
            scraper: Scraper instance with get_metrics method
        """
        if scraper not in self.scrapers:
            self.scrapers.append(scraper)
    
    def remove_scraper(self, scraper):
        """
        Remove a scraper from metrics collection.
        
        Args:
            scraper: Scraper instance to remove
        """
        if scraper in self.scrapers:
            self.scrapers.remove(scraper)
    
    async def _update_metrics_periodically(self):
        """Update cache metrics periodically."""
        while True:
            try:
                # Update cache metrics
                self._update_cache_metrics()
                
                # Update scraper metrics
                for scraper in self.scrapers:
                    if hasattr(scraper, 'metrics'):
                        source_type = scraper.__class__.__name__.lower().replace('scraper', '')
                        
                        # Update unique items count
                        unique_items = scraper.metrics.get('unique_items_total', 0)
                        record_unique_items(source_type, unique_items)
            except Exception as e:
                logger.error(f"Error updating metrics: {e}")
                
            # Sleep for 60 seconds
            await asyncio.sleep(60)
    
    def _update_cache_metrics(self):
        """Update metrics from cache files."""
        try:
            # Check cache files
            cache_dir = os.path.join(os.getcwd(), "data", "cache", "deduplication")
            if os.path.exists(cache_dir):
                for cache_file in os.listdir(cache_dir):
                    if not cache_file.endswith('.json'):
                        continue
                        
                    try:
                        source = cache_file.replace('_hashes.json', '').replace('scraper', '')
                        file_path = os.path.join(cache_dir, cache_file)
                        
                        with open(file_path, 'r') as f:
                            cache_data = json.load(f)
                            
                        items_count = len(cache_data.get('items', {}))
                        # Set cache hits gauge
                        CACHE_HITS.labels(source=source).inc(0)  # Ensure metric exists
                    except Exception as e:
                        logger.error(f"Error reading cache file {cache_file}: {e}")
        except Exception as e:
            logger.error(f"Error updating cache metrics: {e}")
            
    async def metrics_handler(self, request):
        """
        Handle requests to the /metrics endpoint.
        
        Args:
            request: Web request
            
        Returns:
            Web response with Prometheus metrics
        """
        # Get metrics from Prometheus client
        prometheus_metrics = generate_latest().decode('utf-8')
        
        # Add scraper-specific metrics
        custom_metrics = []
        
        # Set uptime metric
        uptime_seconds = time.time() - self.uptime_start
        custom_metrics.append(f"scraper_uptime_seconds {uptime_seconds}")
        
        # Add metrics from each scraper
        for scraper in self.scrapers:
            if hasattr(scraper, 'get_metrics'):
                try:
                    metrics = scraper.get_metrics()
                    for key, value in metrics.items():
                        if key not in prometheus_metrics:
                            custom_metrics.append(f"{key} {value}")
                except Exception as e:
                    logger.error(f"Error getting metrics from {scraper.__class__.__name__}: {e}")
        
        # Combine metrics
        all_metrics = prometheus_metrics
        if custom_metrics:
            all_metrics += "\n" + "\n".join(custom_metrics)
            
        return web.Response(text=all_metrics, content_type='text/plain')
    
    async def health_handler(self, request):
        """
        Handle requests to the /health endpoint.
        
        Args:
            request: Web request
            
        Returns:
            Web response with health status
        """
        return web.json_response({
            "status": "healthy",
            "uptime_seconds": time.time() - self.uptime_start,
            "scraper_count": len(self.scrapers),
            "scrapers": [s.__class__.__name__ for s in self.scrapers]
        })