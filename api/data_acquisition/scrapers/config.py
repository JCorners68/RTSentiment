# data_acquisition/config.py

import os
from dotenv import load_dotenv

# Load environment variables from .env file in the project root
# Adjust the path if your .env file is located elsewhere relative to this config file
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env') # Assumes config.py is in data_acquisition/
load_dotenv(dotenv_path=dotenv_path)

# --- General Settings ---
BASE_OUTPUT_DIR = os.getenv("BASE_OUTPUT_DIR", "data/raw") # Base directory for saving raw data

# --- Scraper Specific Settings ---

# Reddit Scraper
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "RTSentiment Scraper v1.0 by YourUsername")
# Default list of subreddits if none are provided to the scrape method
DEFAULT_SUBREDDITS = ["wallstreetbets", "investing", "stocks", "finance", "StockMarket"]
REDDIT_SCRAPE_LIMIT = int(os.getenv("REDDIT_SCRAPE_LIMIT", 100)) # Max posts per subreddit per run

# Twitter Scraper
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
# Default query if none is provided
DEFAULT_TWITTER_QUERY = "#stockmarket lang:en -is:retweet"
TWITTER_SCRAPE_LIMIT = int(os.getenv("TWITTER_SCRAPE_LIMIT", 100)) # Max tweets per run (API limits apply)

# News Scraper
# List of default RSS feeds to scrape
DEFAULT_NEWS_FEEDS = [
    "http://feeds.reuters.com/reuters/businessNews",
    "http://feeds.reuters.com/reuters/technologyNews",
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml", # WSJ Markets
    "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml", # WSJ US Business
    "https://www.cnbc.com/id/100003114/device/rss/rss.html", # CNBC Top News
    "https://www.ft.com/rss/home", # Financial Times
    "https://seekingalpha.com/feed.xml", # Seeking Alpha
]
# User agent for fetching articles (some sites block default Python user agents)
NEWS_FETCHER_USER_AGENT = os.getenv("NEWS_FETCHER_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
# Timeout for fetching article content (seconds)
ARTICLE_DOWNLOAD_TIMEOUT = int(os.getenv("ARTICLE_DOWNLOAD_TIMEOUT", 15))


# --- Add other configurations as needed ---
# e.g., Rate limits, specific API endpoints, etc.

# You can add validation logic here as well if needed
# Example:
# if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
#     print("Warning: Reddit API credentials not found in environment variables.")

