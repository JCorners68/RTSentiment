"""
Prometheus metrics for the Sentiment Analysis Service.
"""
import time
from typing import Callable, Dict, Any

from fastapi import FastAPI, Request, Response
from prometheus_client import Counter, Gauge, Histogram, Summary
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_fastapi_instrumentator.metrics import Info

# Define custom metrics
MODEL_INFERENCE_DURATION = Histogram(
    "model_inference_duration_seconds", 
    "Model inference duration in seconds",
    ["model_name"]
)

MODEL_PROCESSED_MESSAGES = Counter(
    "model_processed_messages_total", 
    "Total processed messages by model and source",
    ["model_name", "source"]
)

MODEL_PROCESSING_ERRORS = Counter(
    "model_processing_errors_total", 
    "Total processing errors by model",
    ["model_name", "error_type"]
)

MODEL_AVERAGE_SENTIMENT = Gauge(
    "model_average_sentiment_score", 
    "Average sentiment score by ticker",
    ["ticker", "model_name", "timeframe"]
)

MODEL_MEMORY_USAGE = Gauge(
    "model_memory_usage_bytes", 
    "Model memory usage in bytes",
    ["model_name"]
)

MODEL_GPU_MEMORY_USAGE = Gauge(
    "model_gpu_memory_usage_bytes", 
    "GPU memory usage by model in bytes",
    ["model_name", "gpu_id"]
)

MODEL_QUEUE_SIZE = Gauge(
    "model_queue_size", 
    "Current processing queue size",
    ["priority"]
)

MODEL_AVG_PROCESSING_TIME = Gauge(
    "model_average_processing_time", 
    "Average processing time in last minute",
    ["model_name"]
)

SERVICE_UPTIME = Gauge(
    "sentiment_service_uptime_seconds", 
    "Sentiment service uptime in seconds"
)

def setup_metrics(app: FastAPI) -> None:
    """Setup Prometheus metrics instrumentation."""
    
    # Record service uptime
    start_time = time.time()
    
    @app.on_event("startup")
    async def startup_event():
        # Start update task for uptime metric
        def update_uptime():
            while True:
                uptime = time.time() - start_time
                SERVICE_UPTIME.set(uptime)
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
    
    # Instrument app
    instrumentator.instrument(app).expose(app)
    
    # Add convenience functions to app state
    app.state.metrics = {
        "model_inference_duration": MODEL_INFERENCE_DURATION,
        "model_processed_messages": MODEL_PROCESSED_MESSAGES,
        "model_processing_errors": MODEL_PROCESSING_ERRORS,
        "model_average_sentiment": MODEL_AVERAGE_SENTIMENT,
        "model_memory_usage": MODEL_MEMORY_USAGE,
        "model_gpu_memory_usage": MODEL_GPU_MEMORY_USAGE,
        "model_queue_size": MODEL_QUEUE_SIZE,
        "model_avg_processing_time": MODEL_AVG_PROCESSING_TIME
    }
    
    return instrumentator

# Helper function to track model inference time
def track_inference_time(func):
    """Decorator to track model inference time."""
    def wrapper(*args, **kwargs):
        model_name = kwargs.get("model_name", "unknown")
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            MODEL_INFERENCE_DURATION.labels(model_name=model_name).observe(
                time.time() - start_time
            )
            return result
        except Exception as e:
            MODEL_PROCESSING_ERRORS.labels(
                model_name=model_name, 
                error_type=type(e).__name__
            ).inc()
            raise
    return wrapper

# Helper for tracking memory usage
def update_memory_usage(model_name: str, memory_bytes: int, gpu_id: str = None):
    """Update memory usage metrics."""
    MODEL_MEMORY_USAGE.labels(model_name=model_name).set(memory_bytes)
    if gpu_id is not None:
        MODEL_GPU_MEMORY_USAGE.labels(model_name=model_name, gpu_id=gpu_id).set(memory_bytes)

# Track processed messages
def record_processed_message(model_name: str, source: str):
    """Record a processed message."""
    MODEL_PROCESSED_MESSAGES.labels(model_name=model_name, source=source).inc()

# Update sentiment by ticker
def update_sentiment_by_ticker(ticker: str, score: float, model_name: str, timeframe: str = "latest"):
    """Update the average sentiment for a ticker."""
    MODEL_AVERAGE_SENTIMENT.labels(
        ticker=ticker, 
        model_name=model_name,
        timeframe=timeframe
    ).set(score)

# Update queue size
def update_queue_size(priority: str, size: int):
    """Update the queue size for a priority level."""
    MODEL_QUEUE_SIZE.labels(priority=priority).set(size)