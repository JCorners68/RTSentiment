import asyncio
import json
import logging
from abc import ABC, abstractmethod
from aiokafka import AIOKafkaConsumer
from typing import List, Dict, Any, Optional

from utils.cache import RedisClient
from utils.api_client import ApiClient
from models.model_factory import ModelFactory, ModelType

logger = logging.getLogger(__name__)

class BaseConsumer(ABC):
    """Base class for event consumers with model routing capabilities."""
    
    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        group_id: str,
        redis_client: RedisClient,
        default_model_type: ModelType = ModelType.FINBERT,
    ):
        """
        Initialize the consumer.
        
        Args:
            bootstrap_servers (str): Kafka bootstrap servers
            topic (str): Kafka topic to consume from
            group_id (str): Consumer group
            redis_client (RedisClient): Redis client instance
            default_model_type (ModelType): Default model type to use
        """
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.redis_client = redis_client
        self.default_model_type = default_model_type
        self.model_factory = ModelFactory()
        self.api_client = ApiClient()
        self.consumer = None
        self.running = False
        
        # Circuit breaker configuration
        self.retry_interval = 5  # seconds
        self.max_retries = 5
        self.circuit_breaker_failures = 0
        self.circuit_breaker_threshold = 3
        self.circuit_breaker_reset_time = 60  # seconds
        self.circuit_breaker_timer = None
    
    async def connect(self):
        """Connect to Kafka/Event Hub."""
        try:
            logger.info(f"Connecting to Kafka topic {self.topic}...")
            self.consumer = AIOKafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=False,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )
            await self.consumer.start()
            logger.info(f"Connected to Kafka topic {self.topic}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Kafka topic {self.topic}: {str(e)}")
            return False
    
    async def start_consuming(self):
        """Start consuming events."""
        self.running = True
        retries = 0
        
        while self.running:
            if self.consumer is None or not self.consumer._client.cluster.ready:
                if retries >= self.max_retries:
                    logger.error(f"Failed to connect after {retries} retries. Giving up.")
                    break
                
                logger.info(f"Attempting to connect (retry {retries+1}/{self.max_retries})...")
                if await self.connect():
                    retries = 0
                else:
                    retries += 1
                    await asyncio.sleep(self.retry_interval)
                    continue
            
            try:
                async for message in self.consumer:
                    if not self.running:
                        break
                    
                    try:
                        await self.process_message(message)
                        await self.consumer.commit()
                        self.circuit_breaker_failures = 0
                    except Exception as e:
                        logger.error(f"Error processing message: {str(e)}")
                        self.circuit_breaker_failures += 1
                        
                        if self.circuit_breaker_failures >= self.circuit_breaker_threshold:
                            logger.warning("Circuit breaker triggered. Pausing consumption.")
                            self.circuit_breaker_timer = asyncio.create_task(self.reset_circuit_breaker())
                            await self.circuit_breaker_timer
            except Exception as e:
                logger.error(f"Error consuming messages: {str(e)}")
                await asyncio.sleep(self.retry_interval)
    
    async def stop_consuming(self):
        """Stop consuming events."""
        self.running = False
        if self.consumer:
            logger.info(f"Stopping consumer for topic {self.topic}...")
            await self.consumer.stop()
            self.consumer = None
            logger.info(f"Consumer for topic {self.topic} stopped")
            
        # Close API client
        if self.api_client:
            await self.api_client.close()
    
    async def reset_circuit_breaker(self):
        """Reset the circuit breaker after a delay."""
        await asyncio.sleep(self.circuit_breaker_reset_time)
        self.circuit_breaker_failures = 0
        logger.info("Circuit breaker reset. Resuming consumption.")
    
    @abstractmethod
    async def process_message(self, message):
        """
        Process a message from the event stream.
        To be implemented by subclasses.
        """
        pass
    
    async def select_model_for_event(self, event: Dict[str, Any]) -> ModelType:
        """
        Select the appropriate model based on event characteristics.
        
        Args:
            event (Dict[str, Any]): Event data
            
        Returns:
            ModelType: Selected model type
        """
        # Default model for most cases
        model_type = self.default_model_type
        
        # Check if this is a premium user event
        if event.get("premium_tier", False):
            weight = event.get("weight", 1.0)
            text_length = len(event.get("text", ""))
            
            # For important events with long text, use more sophisticated models
            if weight > 1.5 and text_length > 500 and event.get("premium_tier") == "professional":
                # For highest tier, use the most powerful model
                model_type = ModelType.LLAMA4_SCOUT
            elif weight > 1.2 and event.get("premium_tier") in ["premium", "professional"]:
                # For medium to high tier, use FinGPT
                model_type = ModelType.FINGPT
        
        # Check for special event types that might benefit from advanced models
        event_type = event.get("type", "").lower()
        if event_type in ["earnings_report", "financial_filing", "analyst_report"] and event.get("premium_tier"):
            # Documents can benefit from longer context windows
            model_type = ModelType.FINGPT
        
        # Check if we are targeting specific tickers for premium analysis
        premium_tickers = await self.get_premium_tickers()
        if any(ticker in premium_tickers for ticker in event.get("tickers", [])):
            model_type = ModelType.FINGPT
            
        return model_type
    
    async def get_premium_tickers(self) -> List[str]:
        """
        Get list of tickers that receive premium analysis.
        
        Returns:
            List[str]: List of premium tickers
        """
        # This could be fetched from Redis or a configuration service
        premium_tickers_str = await self.redis_client.get("config:premium_tickers")
        if premium_tickers_str:
            try:
                return json.loads(premium_tickers_str)
            except json.JSONDecodeError:
                logger.error("Failed to parse premium tickers from Redis")
        
        # Default premium tickers if none configured
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]
    
    async def analyze_sentiment(self, texts: List[str], model_type: ModelType = None) -> List[Dict[str, Any]]:
        """
        Analyze sentiment of texts using selected model.
        
        Args:
            texts (List[str]): List of texts to analyze
            model_type (ModelType, optional): Model type to use. Defaults to default model.
            
        Returns:
            List[Dict[str, Any]]: List of sentiment results
        """
        if model_type is None:
            model_type = self.default_model_type
            
        # Get model for specified type
        model = await self.model_factory.get_model(model_type)
        
        # Analyze sentiment
        try:
            results = await model.predict(texts)
            # Log which model was used
            logger.debug(f"Used {model_type.name} for sentiment analysis of {len(texts)} texts")
            return results
        except Exception as e:
            logger.error(f"Error analyzing sentiment with {model_type.name}: {str(e)}")
            
            # If not already using the default model, fall back to it
            if model_type != self.default_model_type:
                logger.info(f"Falling back to {self.default_model_type.name} for sentiment analysis")
                fallback_model = await self.model_factory.get_model(self.default_model_type)
                return await fallback_model.predict(texts)
            else:
                # Re-raise the exception if we're already using the default model
                raise
    
    async def update_redis_cache(self, ticker: str, sentiment_score: float, weight: float = 1.0, model_type: ModelType = None):
        """
        Update sentiment score in Redis cache.
        
        Args:
            ticker (str): Stock ticker symbol
            sentiment_score (float): Sentiment score (-1 to +1)
            weight (float): Weight of the sentiment score (default: 1.0)
            model_type (ModelType, optional): Model type used for analysis
        """
        # Get current sentiment state from Redis
        current = await self.redis_client.get(f"sentiment:{ticker}")
        if current:
            current = json.loads(current)
            current_score = current.get("score", 0.0)
            current_weight = current.get("weight", 0.0)
            current_count = current.get("count", 0)
            
            # Calculate weighted average
            total_weight = current_weight + weight
            new_score = ((current_score * current_weight) + (sentiment_score * weight)) / total_weight
            
            # Update values
            current["score"] = new_score
            current["weight"] = total_weight
            current["count"] = current_count + 1
            current["last_updated"] = asyncio.get_event_loop().time()
            
            # Track model usage if provided
            if model_type:
                model_counts = current.get("model_counts", {})
                model_name = model_type.name
                model_counts[model_name] = model_counts.get(model_name, 0) + 1
                current["model_counts"] = model_counts
        else:
            # Initialize new entry
            current = {
                "ticker": ticker,
                "score": sentiment_score,
                "weight": weight,
                "count": 1,
                "last_updated": asyncio.get_event_loop().time()
            }
            
            # Track model usage if provided
            if model_type:
                current["model_counts"] = {model_type.name: 1}
        
        # Store in Redis
        await self.redis_client.set(f"sentiment:{ticker}", json.dumps(current))
        logger.debug(f"Updated sentiment for {ticker}: {current['score']:.4f}")
        
        # Also update the ticker list if needed
        await self.redis_client.sadd("tickers", ticker)