import asyncio
import logging
import os
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from prometheus_client import make_asgi_app

try:
    from models.finbert import FinBertModel
    from event_consumers.hipri_consumer import HighPriorityConsumer
    from event_consumers.stdpri_consumer import StandardPriorityConsumer
    from utils.cache import RedisClient
    from config import config
except ImportError:
    # Handle relative imports for local execution
    from sentiment_service.models.finbert import FinBertModel
    from sentiment_service.event_consumers.hipri_consumer import HighPriorityConsumer
    from sentiment_service.event_consumers.stdpri_consumer import StandardPriorityConsumer
    from sentiment_service.utils.cache import RedisClient
    from sentiment_service.config import config

# Configure logging
logging.basicConfig(
    level=getattr(logging, config["LOG_LEVEL"]),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances
sentiment_model = None
redis_client = None
hipri_consumer = None
stdpri_consumer = None
consumer_tasks = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: load model and start consumers
    await startup()
    yield
    # Shutdown: close connections and stop consumers
    await shutdown()

app = FastAPI(
    title="Sentiment Analysis Service",
    description="Service for processing financial text and generating sentiment scores",
    version="1.0.0",
    lifespan=lifespan,
)

# Add Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

async def startup():
    global sentiment_model, redis_client, hipri_consumer, stdpri_consumer, consumer_tasks, config
    
    logger.info("Starting Sentiment Analysis Service")
    
    # Initialize FinBERT model
    logger.info("Loading sentiment model...")
    sentiment_model = FinBertModel()
    await sentiment_model.load()
    
    # Initialize Redis connection
    logger.info("Connecting to Redis...")
    redis_host = config["REDIS_HOST"]
    redis_port = config["REDIS_PORT"]
    redis_client = RedisClient(host=redis_host, port=redis_port)
    await redis_client.connect()
    
    # Load config from Redis if available
    from config import load_config_from_redis, save_config_to_redis
    
    if redis_client.is_connected:
        redis_config = await load_config_from_redis(redis_client)
        if redis_config:
            # Update config with values from Redis
            for key, value in redis_config.items():
                if key in config:
                    config[key] = value
            logger.info(f"Loaded {len(redis_config)} configuration settings from Redis")
        else:
            # No config in Redis, save current config
            await save_config_to_redis(redis_client, config)
    
    # Configure logging level from updated config
    logging.getLogger().setLevel(getattr(logging, config["LOG_LEVEL"]))
    
    # Initialize Kafka consumers
    logger.info("Initializing event consumers...")
    kafka_bootstrap_servers = config["KAFKA_BOOTSTRAP_SERVERS"]
    
    hipri_consumer = HighPriorityConsumer(
        bootstrap_servers=kafka_bootstrap_servers,
        topic=config["HIPRI_TOPIC"],
        group_id=config["CONSUMER_GROUP_ID"],
        sentiment_model=sentiment_model,
        redis_client=redis_client,
    )
    
    stdpri_consumer = StandardPriorityConsumer(
        bootstrap_servers=kafka_bootstrap_servers,
        topic=config["STDPRI_TOPIC"],
        group_id=config["CONSUMER_GROUP_ID"],
        sentiment_model=sentiment_model,
        redis_client=redis_client,
    )
    
    # Start consumers if autostart is enabled
    if config["AUTOSTART_LISTENERS"]:
        logger.info(f"Autostarting event consumers (AUTOSTART_LISTENERS={config['AUTOSTART_LISTENERS']})...")
        consumer_tasks = [
            asyncio.create_task(hipri_consumer.start_consuming()),
            asyncio.create_task(stdpri_consumer.start_consuming()),
        ]
        logger.info("Event consumers started")
    else:
        logger.info(f"Autostart disabled (AUTOSTART_LISTENERS={config['AUTOSTART_LISTENERS']}) - event consumers ready but not started")
        consumer_tasks = []
    
    logger.info("Sentiment Analysis Service started successfully")

async def shutdown():
    logger.info("Shutting down Sentiment Analysis Service")
    
    # Stop consumers
    if hipri_consumer:
        await hipri_consumer.stop_consuming()
    if stdpri_consumer:
        await stdpri_consumer.stop_consuming()
    
    # Cancel tasks
    for task in consumer_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # Close Redis connection
    if redis_client:
        await redis_client.close()
    
    logger.info("Sentiment Analysis Service shut down successfully")

@app.get("/")
async def root():
    return {"message": "Sentiment Analysis Service"}

@app.get("/health")
async def health_check():
    model_loaded = sentiment_model is not None and sentiment_model.is_loaded
    redis_connected = redis_client is not None and redis_client.is_connected
    consumers_running = all(not task.done() for task in consumer_tasks) if consumer_tasks else False
    
    # If autostart is disabled, don't consider consumers in health check
    if not config["AUTOSTART_LISTENERS"] and not consumer_tasks:
        is_healthy = model_loaded and redis_connected
    else:
        is_healthy = model_loaded and redis_connected and consumers_running
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "components": {
            "model": "loaded" if model_loaded else "not_loaded",
            "redis": "connected" if redis_connected else "disconnected",
            "consumers": "running" if consumers_running else "stopped",
            "autostart_enabled": config["AUTOSTART_LISTENERS"],
        }
    }

@app.post("/consumers/start")
async def start_consumers():
    """Manually start event consumers if they're not already running."""
    global consumer_tasks
    
    if consumer_tasks and all(not task.done() for task in consumer_tasks):
        return {"status": "already_running", "message": "Consumers are already running"}
    
    # Stop any existing tasks that might be in error state
    for task in consumer_tasks:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    # Start new consumer tasks
    logger.info("Manually starting event consumers...")
    consumer_tasks = [
        asyncio.create_task(hipri_consumer.start_consuming()),
        asyncio.create_task(stdpri_consumer.start_consuming()),
    ]
    logger.info("Event consumers started")
    
    return {"status": "started", "message": "Consumers started successfully"}

@app.post("/consumers/stop")
async def stop_consumers():
    """Manually stop event consumers."""
    global consumer_tasks
    
    if not consumer_tasks:
        return {"status": "already_stopped", "message": "Consumers are not running"}
    
    # Stop consumers gracefully
    logger.info("Manually stopping event consumers...")
    if hipri_consumer:
        await hipri_consumer.stop_consuming()
    if stdpri_consumer:
        await stdpri_consumer.stop_consuming()
    
    # Cancel tasks
    for task in consumer_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    consumer_tasks = []
    logger.info("Event consumers stopped")
    
    return {"status": "stopped", "message": "Consumers stopped successfully"}

@app.get("/config")
async def get_config():
    """Get current configuration values."""
    return {"config": config}

@app.post("/config/toggle-autostart")
async def toggle_autostart():
    """Toggle the AUTOSTART_LISTENERS setting."""
    from config import save_config_to_redis
    
    # Toggle the autostart setting
    config["AUTOSTART_LISTENERS"] = not config["AUTOSTART_LISTENERS"]
    
    # Update Redis with the new setting if available
    if redis_client and redis_client.is_connected:
        await save_config_to_redis(redis_client, {"AUTOSTART_LISTENERS": config["AUTOSTART_LISTENERS"]})
    
    # Automatically start/stop based on new setting
    if config["AUTOSTART_LISTENERS"] and not consumer_tasks:
        # Start consumers if not already running
        await start_consumers()
    
    return {
        "autostart_enabled": config["AUTOSTART_LISTENERS"],
        "current_state": "running" if consumer_tasks else "stopped"
    }

def handle_signals():
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda s, f: sys.exit(0))

if __name__ == "__main__":
    handle_signals()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)