import json
import os
import logging

logger = logging.getLogger(__name__)

def load_config(config_path):
    """
    Load configuration from a JSON file.
    
    Args:
        config_path: Path to config JSON file
        
    Returns:
        Dictionary with configuration values
    """
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Error loading config from {config_path}: {e}")
        return {}
        
def get_default_config():
    """
    Get default configuration values.
    
    Returns:
        Dictionary with default configuration
    """
    return {
        # Redis configuration
        "redis_host": "localhost",
        "redis_port": 6379,
        "redis_db": 0,
        "event_expiry": 604800,  # 7 days in seconds
        
        # Sentiment model configuration
        "decay_type": "exponential",
        "decay_half_life": 24,  # hours
        "max_age_hours": 168,  # 7 days
        
        # SP500 tracker configuration
        "sp500_update_hours": 24,
        "top_n_tickers": 10,
        "ranking_metric": "market_cap",
        
        # Update intervals
        "update_interval": 60,  # seconds
        "historical_update_interval": 3600,  # 1 hour
        
        # Data paths
        "parquet_dir": "/home/jonat/WSL_RT_Sentiment/data/output"
    }