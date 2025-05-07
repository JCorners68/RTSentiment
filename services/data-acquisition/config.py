"""
Configuration file for API keys and service settings
This file centralizes all API keys and configuration settings for the data acquisition service.

IMPORTANT: Do not commit this file with actual API keys to the repository.
Use environment variables or a secure vault for production deployment.
"""

import os
from typing import Dict, Any

# API Keys - Default to environment variables or placeholder values
FINNHUB_API_KEY = os.environ.get("FINNHUB_API_KEY", "cvpf6bpr01qve7iojidgcvpf6bpr01qve7iojie0")
ALPHA_VANTAGE_API_KEY = os.environ.get("ALPHA_VANTAGE_API_KEY", "YO6HAEMWSHY2UP0L")
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "your_reddit_client_id_here")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "your_reddit_client_secret_here")
YAHOO_FINANCE_API_KEY = os.environ.get("YAHOO_FINANCE_API_KEY", "your_yahoo_finance_api_key_here")  # For Gold subscription

# Service Configuration
ICEBERG_WAREHOUSE = os.environ.get("ICEBERG_WAREHOUSE", "/home/jonat/real_senti/data/iceberg/warehouse")
ICEBERG_CATALOG_NAME = os.environ.get("ICEBERG_CATALOG_NAME", "sentimark")

# Data Source Settings
RSS_FEEDS = [
    "https://www.reutersagency.com/feed/?best-topics=business&post_type=best",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "https://finance.yahoo.com/news/rssindex",
    "https://seekingalpha.com/market_currents.xml"
]

REDDIT_SUBREDDITS = ["wallstreetbets", "stocks", "investing", "finance"]

# S&P 500 Tickers (Sample - to be replaced with full list or dynamic fetching)
SP500_TICKERS = [
    "AAPL", "MSFT", "AMZN", "META", "GOOGL", "GOOG", "TSLA", "NVDA", "BRK.A", "BRK.B",
    "UNH", "JNJ", "XOM", "JPM", "V", "PG", "HD", "CVX", "MA", "LLY"
]

# Redis Configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))

# Caching Settings
CACHE_TTL_SECONDS = 3600  # 1 hour

# Rate Limiting Settings
FINNHUB_RATE_LIMIT = 60  # Requests per minute
ALPHA_VANTAGE_RATE_LIMIT = 300  # Requests per minute (Premium)
REDDIT_RATE_LIMIT = 60  # Requests per minute
YAHOO_RATE_LIMIT = 100  # Requests per minute (Gold)

# Logging Configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Feature Flags
FEATURES = {
    "use_redis_cache": True,
    "use_iceberg_backend": False,  # Set to True in production
    "enable_sentiment_analysis": True,
    "enable_real_time_processing": False,
    "enable_yahoo_gold": False,  # Will be enabled after POC
}

# Data Collection Settings
DEFAULT_HISTORICAL_DAYS = 30
DEFAULT_BATCH_SIZE = 10

# Return configuration as a dictionary for easier access
def get_config() -> Dict[str, Any]:
    """Return the configuration as a dictionary"""
    return {
        "api_keys": {
            "finnhub": FINNHUB_API_KEY,
            "alpha_vantage": ALPHA_VANTAGE_API_KEY,
            "reddit": {
                "client_id": REDDIT_CLIENT_ID,
                "client_secret": REDDIT_CLIENT_SECRET,
            },
            "yahoo_finance": YAHOO_FINANCE_API_KEY,
        },
        "iceberg": {
            "warehouse": ICEBERG_WAREHOUSE,
            "catalog_name": ICEBERG_CATALOG_NAME,
        },
        "data_sources": {
            "rss_feeds": RSS_FEEDS,
            "reddit_subreddits": REDDIT_SUBREDDITS,
            "sp500_tickers": SP500_TICKERS,
        },
        "redis": {
            "host": REDIS_HOST,
            "port": REDIS_PORT,
            "db": REDIS_DB,
        },
        "caching": {
            "ttl_seconds": CACHE_TTL_SECONDS,
        },
        "rate_limits": {
            "finnhub": FINNHUB_RATE_LIMIT,
            "alpha_vantage": ALPHA_VANTAGE_RATE_LIMIT,
            "reddit": REDDIT_RATE_LIMIT,
            "yahoo": YAHOO_RATE_LIMIT,
        },
        "logging": {
            "level": LOG_LEVEL,
            "format": LOG_FORMAT,
        },
        "features": FEATURES,
        "collection_settings": {
            "historical_days": DEFAULT_HISTORICAL_DAYS,
            "batch_size": DEFAULT_BATCH_SIZE,
        },
    }