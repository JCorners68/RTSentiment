"""
Prometheus metrics for the API service.
"""
import os
import time
from typing import Callable, List, Optional

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_fastapi_instrumentator.metrics import Info

# Define custom metrics
API_HEALTH_STATUS = Gauge(
    "api_health_status", 
    "Health status of the API (1 = healthy, 0 = unhealthy)"
)

DB_CONNECTION_ERRORS = Counter(
    "api_database_connection_errors", 
    "Number of database connection errors"
)

REDIS_CONNECTION_ERRORS = Counter(
    "api_redis_connection_errors", 
    "Number of Redis connection errors"
)

API_UPTIME = Gauge(
    "api_uptime_seconds", 
    "API service uptime in seconds"
)

ACTIVE_REQUESTS = Gauge(
    "api_active_requests", 
    "Number of currently active HTTP requests"
)

SENTIMENT_EVENTS_TOTAL = Counter(
    "api_sentiment_events_total", 
    "Total number of sentiment events processed",
    ["source", "priority"]
)

SENTIMENT_QUERY_TIME = Histogram(
    "api_sentiment_query_duration_seconds",
    "Sentiment query duration in seconds",
    ["endpoint", "ticker"]
)

# Custom metrics for the instrumentator
def active_requests_count(metric_name: str = "api_active_requests") -> Callable[[Info], None]:
    ACTIVE = Gauge(metric_name, "Number of active requests")
    
    def instrumentation(info: Info) -> None:
        if info.response is not None:
            ACTIVE.dec()
        else:
            ACTIVE.inc()
            
    return instrumentation

def query_ticker_metrics() -> Callable[[Info], None]:
    def instrumentation(info: Info) -> None:
        request: Request = info.request
        response: Response = info.response
        
        if request.url.path.startswith("/sentiment/ticker/"):
            ticker = request.url.path.split("/")[-1]
            SENTIMENT_QUERY_TIME.labels(
                endpoint="ticker_query",
                ticker=ticker
            ).observe(info.duration)
            
    return instrumentation

# Expose metrics endpoint
def setup_metrics(app: FastAPI) -> None:
    """Setup Prometheus metrics instrumentation."""
    
    # Record API uptime
    start_time = time.time()
    
    @app.on_event("startup")
    async def startup_event():
        # Set health status to healthy on startup
        API_HEALTH_STATUS.set(1)
        
        # Start update task for uptime metric
        def update_uptime():
            while True:
                uptime = time.time() - start_time
                API_UPTIME.set(uptime)
                time.sleep(60)  # Update every minute
                
        import threading
        threading.Thread(target=update_uptime, daemon=True).start()
    
    # Define custom metrics for FastAPI
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/metrics", "/health"],
    )
    
    # Add default metrics
    instrumentator.add(metrics.default())
    instrumentator.add(metrics.latency())
    instrumentator.add(metrics.requests_inprogress())
    
    # Add custom metrics
    instrumentator.add(active_requests_count())
    instrumentator.add(query_ticker_metrics())
    
    # Instrument app
    instrumentator.instrument(app).expose(app)
    
    # Add convenience functions to app state
    app.state.metrics = {
        "api_health_status": API_HEALTH_STATUS,
        "db_connection_errors": DB_CONNECTION_ERRORS,
        "redis_connection_errors": REDIS_CONNECTION_ERRORS,
        "sentiment_events_total": SENTIMENT_EVENTS_TOTAL,
        "sentiment_query_time": SENTIMENT_QUERY_TIME
    }
    
    return instrumentator