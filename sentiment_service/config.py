import os
import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Configuration defaults
DEFAULT_CONFIG = {
    # Feature flags
    "AUTOSTART_LISTENERS": True,  # Whether to automatically start event listeners
    
    # Service configuration
    "KAFKA_BOOTSTRAP_SERVERS": "kafka:9092",
    "REDIS_HOST": "redis",
    "REDIS_PORT": 6379,
    
    # Consumer configuration
    "CONSUMER_GROUP_ID": "sentiment-analysis",
    "HIPRI_TOPIC": "hipri-events",
    "STDPRI_TOPIC": "stdpri-events",
    
    # Circuit breaker configuration
    "CIRCUIT_BREAKER_THRESHOLD": 3,
    "CIRCUIT_BREAKER_RESET_TIME": 60,  # seconds
    "MAX_RETRIES": 5,
    "RETRY_INTERVAL": 5,  # seconds
    
    # Logging configuration
    "LOG_LEVEL": "INFO",
}

def get_config() -> Dict[str, Any]:
    """
    Load configuration from environment variables with defaults.
    
    Environment variables override default values.
    Boolean values should be specified as "true" or "false" in env vars.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    config = DEFAULT_CONFIG.copy()
    
    # Override with environment variables
    for key in config:
        env_value = os.getenv(key)
        if env_value is not None:
            # Handle different types
            if isinstance(config[key], bool):
                config[key] = env_value.lower() == "true"
            elif isinstance(config[key], int):
                config[key] = int(env_value)
            elif isinstance(config[key], float):
                config[key] = float(env_value)
            else:
                config[key] = env_value
    
    return config

async def load_config_from_redis(redis_client) -> Dict[str, Any]:
    """
    Load configuration from Redis.
    
    Args:
        redis_client: Redis client
        
    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    if not redis_client or not redis_client.is_connected:
        return {}
        
    redis_config = {}
    
    # Get all keys with prefix "config:"
    try:
        keys = await redis_client.client.keys("config:*")
        
        for key in keys:
            # Strip the prefix
            config_key = key.replace("config:", "")
            value = await redis_client.get(key)
            
            if value is not None:
                # Convert to appropriate type based on default config
                if config_key in DEFAULT_CONFIG:
                    if isinstance(DEFAULT_CONFIG[config_key], bool):
                        redis_config[config_key] = value.lower() == "true"
                    elif isinstance(DEFAULT_CONFIG[config_key], int):
                        redis_config[config_key] = int(value)
                    elif isinstance(DEFAULT_CONFIG[config_key], float):
                        redis_config[config_key] = float(value)
                    else:
                        redis_config[config_key] = value
                else:
                    # If not in defaults, add as string
                    redis_config[config_key] = value
                    
        logger.info(f"Loaded {len(redis_config)} configuration values from Redis")
    except Exception as e:
        logger.error(f"Error loading configuration from Redis: {str(e)}")
    
    return redis_config

async def save_config_to_redis(redis_client, config_dict: Dict[str, Any]):
    """
    Save configuration to Redis.
    
    Args:
        redis_client: Redis client
        config_dict (Dict[str, Any]): Configuration dictionary
    """
    if not redis_client or not redis_client.is_connected:
        return
        
    try:
        for key, value in config_dict.items():
            # Convert to string
            if isinstance(value, bool):
                value = str(value).lower()
            else:
                value = str(value)
                
            await redis_client.set(f"config:{key}", value)
            
        logger.info(f"Saved {len(config_dict)} configuration values to Redis")
    except Exception as e:
        logger.error(f"Error saving configuration to Redis: {str(e)}")

# Global configuration object
config = get_config()