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
except ImportError:
    # Handle relative imports for local execution
    from sentiment_service.models.finbert import FinBertModel
    from sentiment_service.event_consumers.hipri_consumer import HighPriorityConsumer
    from sentiment_service.event_consumers.stdpri_consumer import StandardPriorityConsumer
    from sentiment_service.utils.cache import RedisClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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
    global sentiment_model, redis_client, hipri_consumer, stdpri_consumer, consumer_tasks
    
    logger.info("Starting Sentiment Analysis Service")
    
    # Initialize FinBERT model
    logger.info("Loading sentiment model...")
    sentiment_model = FinBertModel()
    await sentiment_model.load()
    
    # Initialize Redis connection
    logger.info("Connecting to Redis...")
    redis_host = os.getenv("REDIS_HOST", "redis")
    redis_port = int(os.getenv("REDIS_PORT", "6379"))
    redis_client = RedisClient(host=redis_host, port=redis_port)
    await redis_client.connect()
    
    # Initialize Kafka consumers
    logger.info("Initializing event consumers...")
    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    
    hipri_consumer = HighPriorityConsumer(
        bootstrap_servers=kafka_bootstrap_servers,
        topic="hipri-events",
        group_id="sentiment-analysis",
        sentiment_model=sentiment_model,
        redis_client=redis_client,
    )
    
    stdpri_consumer = StandardPriorityConsumer(
        bootstrap_servers=kafka_bootstrap_servers,
        topic="stdpri-events",
        group_id="sentiment-analysis",
        sentiment_model=sentiment_model,
        redis_client=redis_client,
    )
    
    # Start consumers
    logger.info("Starting event consumers...")
    consumer_tasks = [
        asyncio.create_task(hipri_consumer.start_consuming()),
        asyncio.create_task(stdpri_consumer.start_consuming()),
    ]
    
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
    
    is_healthy = model_loaded and redis_connected and consumers_running
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "components": {
            "model": "loaded" if model_loaded else "not_loaded",
            "redis": "connected" if redis_connected else "disconnected",
            "consumers": "running" if consumers_running else "stopped",
        }
    }

def handle_signals():
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda s, f: sys.exit(0))

if __name__ == "__main__":
    handle_signals()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)