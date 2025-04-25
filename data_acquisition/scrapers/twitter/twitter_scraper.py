"""
Twitter/X scraper for the data acquisition pipeline.
"""
import logging
import asyncio
import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from data_acquisition.scrapers.base import BaseScraper
from data_acquisition.utils.weight_calculator import calculate_weight

logger = logging.getLogger(__name__)

class TwitterScraper(BaseScraper):
    """Scraper for Twitter/X financial content."""
    
    def __init__(self, producer, config):
        """
        Initialize the Twitter/X scraper with event producer and configuration.
        
        Args:
            producer: Event producer for publishing events
            config: Configuration dictionary
        """
        super().__init__(producer, config)
        
        # Extract Twitter/X specific configuration
        twitter_config = config.get("twitter_scraper", {})
        self.api_key = twitter_config.get("api_key", os.environ.get("TWITTER_API_KEY", ""))
        self.api_secret = twitter_config.get("api_secret", os.environ.get("TWITTER_API_SECRET", ""))
        self.bearer_token = twitter_config.get("bearer_token", os.environ.get("TWITTER_BEARER_TOKEN", ""))
        
        self.search_queries = twitter_config.get("search_queries", ["$AAPL", "$TSLA", "stock market"])
        self.accounts_to_follow = twitter_config.get("accounts_to_follow", [])
        self.tweet_limit = twitter_config.get("tweet_limit", 100)
        self.interval = twitter_config.get("polling_interval", 180)  # Default 3 minutes
        
        # Setup headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "User-Agent": "FinancialSentimentTracker/1.0"
        }
        
        # Setup cache for tweet IDs to avoid duplicates
        self.cache_dir = os.path.join(os.getcwd(), "data", "cache", "deduplication")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.cache_file = os.path.join(self.cache_dir, "twitter_hashes.json")
        self.tweet_cache = self._load_tweet_cache()
        
        logger.info(f"Initialized {self.name} with {len(self.search_queries)} search queries and {len(self.accounts_to_follow)} accounts to follow")
    
    def _load_tweet_cache(self) -> Dict[str, str]:
        """
        Load tweet cache from file to avoid duplicates.
        
        Returns:
            Dictionary of tweet IDs and their hash values
        """
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error loading tweet cache: {e}")
            return {}
    
    def _save_tweet_cache(self):
        """Save tweet cache to file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.tweet_cache, f)
        except Exception as e:
            logger.error(f"Error saving tweet cache: {e}")
    
    async def _authenticate(self) -> bool:
        """
        Authenticate with Twitter/X API if needed.
        
        Returns:
            True if authentication is successful, False otherwise
        """
        if not self.bearer_token:
            # If no bearer token is provided, attempt to get one using API key and secret
            if not (self.api_key and self.api_secret):
                logger.error("No Twitter API credentials provided")
                return False
            
            try:
                auth_url = "https://api.twitter.com/oauth2/token"
                auth_data = {"grant_type": "client_credentials"}
                auth_headers = {
                    "Authorization": f"Basic {self.api_key}:{self.api_secret}",
                    "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(auth_url, data=auth_data, headers=auth_headers) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            self.bearer_token = response_data.get("access_token")
                            self.headers["Authorization"] = f"Bearer {self.bearer_token}"
                            logger.info("Successfully authenticated with Twitter/X API")
                            return True
                        else:
                            logger.error(f"Failed to authenticate with Twitter/X API: {response.status}")
                            return False
            except Exception as e:
                logger.error(f"Error authenticating with Twitter/X API: {e}")
                return False
        
        return True  # Already authenticated
    
    async def _search_tweets(self, session, query) -> List[Dict[str, Any]]:
        """
        Search for tweets matching a specific query.
        
        Args:
            session: aiohttp client session
            query: Search query string
            
        Returns:
            List of tweet data dictionaries
        """
        tweets = []
        
        try:
            # Twitter API v2 search endpoint
            search_url = "https://api.twitter.com/2/tweets/search/recent"
            params = {
                "query": query,
                "max_results": self.tweet_limit,
                "tweet.fields": "created_at,public_metrics,entities",
                "expansions": "author_id",
                "user.fields": "name,username,verified"
            }
            
            async with session.get(search_url, params=params, headers=self.headers) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    # Process response data
                    tweet_data = response_data.get("data", [])
                    users = {user["id"]: user for user in response_data.get("includes", {}).get("users", [])}
                    
                    for tweet in tweet_data:
                        # Skip if we've seen this tweet before
                        if tweet["id"] in self.tweet_cache:
                            continue
                        
                        # Add to cache
                        self.tweet_cache[tweet["id"]] = datetime.now(timezone.utc).isoformat()
                        
                        # Get user data
                        user = users.get(tweet.get("author_id", ""))
                        
                        # Extract cashtags/tickers
                        tickers = []
                        if "entities" in tweet and "cashtags" in tweet["entities"]:
                            tickers = [f"${tag['tag'].upper()}" for tag in tweet["entities"]["cashtags"]]
                        
                        # Extract other entities if no cashtags found
                        if not tickers and "entities" in tweet and "hashtags" in tweet["entities"]:
                            # Look for stock tickers in hashtags (heuristic approach)
                            for tag in tweet["entities"]["hashtags"]:
                                tag_text = tag["tag"].upper()
                                # If the tag looks like a stock ticker (1-5 capital letters)
                                if len(tag_text) <= 5 and tag_text.isalpha() and tag_text.isupper():
                                    tickers.append(tag_text)
                        
                        # Extract metrics
                        metrics = tweet.get("public_metrics", {})
                        
                        # Prepare tweet data
                        processed_tweet = {
                            "id": tweet["id"],
                            "text": tweet["text"],
                            "tickers": tickers,
                            "source": "Twitter",
                            "source_name": f"{user.get('name', '')} (@{user.get('username', '')})" if user else "Unknown",
                            "url": f"https://twitter.com/user/status/{tweet['id']}",
                            "timestamp": tweet.get("created_at", datetime.now(timezone.utc).isoformat()),
                            "engagement": {
                                "likes": metrics.get("like_count", 0),
                                "retweets": metrics.get("retweet_count", 0),
                                "replies": metrics.get("reply_count", 0),
                                "quotes": metrics.get("quote_count", 0)
                            }
                        }
                        
                        tweets.append(processed_tweet)
                else:
                    logger.error(f"Twitter API error for query '{query}': {response.status}")
        except Exception as e:
            logger.error(f"Error searching tweets for query '{query}': {e}")
        
        return tweets
    
    async def _get_user_tweets(self, session, username) -> List[Dict[str, Any]]:
        """
        Get tweets from a specific user.
        
        Args:
            session: aiohttp client session
            username: Twitter username
            
        Returns:
            List of tweet data dictionaries
        """
        tweets = []
        
        try:
            # First, get user ID from username
            lookup_url = f"https://api.twitter.com/2/users/by/username/{username}"
            
            async with session.get(lookup_url, headers=self.headers) as response:
                if response.status == 200:
                    user_data = await response.json()
                    user_id = user_data.get("data", {}).get("id")
                    
                    if not user_id:
                        logger.error(f"Could not find user ID for username '{username}'")
                        return tweets
                    
                    # Now get user's tweets
                    tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
                    params = {
                        "max_results": self.tweet_limit,
                        "tweet.fields": "created_at,public_metrics,entities",
                        "expansions": "author_id",
                        "user.fields": "name,username,verified"
                    }
                    
                    async with session.get(tweets_url, params=params, headers=self.headers) as tweets_response:
                        if tweets_response.status == 200:
                            response_data = await tweets_response.json()
                            
                            # Process response data
                            tweet_data = response_data.get("data", [])
                            users = {user["id"]: user for user in response_data.get("includes", {}).get("users", [])}
                            
                            for tweet in tweet_data:
                                # Skip if we've seen this tweet before
                                if tweet["id"] in self.tweet_cache:
                                    continue
                                
                                # Add to cache
                                self.tweet_cache[tweet["id"]] = datetime.now(timezone.utc).isoformat()
                                
                                # Get user data
                                user = users.get(tweet.get("author_id", ""))
                                
                                # Extract cashtags/tickers
                                tickers = []
                                if "entities" in tweet and "cashtags" in tweet["entities"]:
                                    tickers = [f"${tag['tag'].upper()}" for tag in tweet["entities"]["cashtags"]]
                                
                                # Extract other entities if no cashtags found
                                if not tickers and "entities" in tweet and "hashtags" in tweet["entities"]:
                                    # Look for stock tickers in hashtags (heuristic approach)
                                    for tag in tweet["entities"]["hashtags"]:
                                        tag_text = tag["tag"].upper()
                                        # If the tag looks like a stock ticker (1-5 capital letters)
                                        if len(tag_text) <= 5 and tag_text.isalpha() and tag_text.isupper():
                                            tickers.append(tag_text)
                                
                                # Extract metrics
                                metrics = tweet.get("public_metrics", {})
                                
                                # Prepare tweet data
                                processed_tweet = {
                                    "id": tweet["id"],
                                    "text": tweet["text"],
                                    "tickers": tickers,
                                    "source": "Twitter",
                                    "source_name": f"{user.get('name', '')} (@{user.get('username', '')})" if user else "Unknown",
                                    "url": f"https://twitter.com/user/status/{tweet['id']}",
                                    "timestamp": tweet.get("created_at", datetime.now(timezone.utc).isoformat()),
                                    "engagement": {
                                        "likes": metrics.get("like_count", 0),
                                        "retweets": metrics.get("retweet_count", 0),
                                        "replies": metrics.get("reply_count", 0),
                                        "quotes": metrics.get("quote_count", 0)
                                    }
                                }
                                
                                tweets.append(processed_tweet)
                        else:
                            logger.error(f"Twitter API error getting tweets for user '{username}': {tweets_response.status}")
                else:
                    logger.error(f"Twitter API error looking up user '{username}': {response.status}")
        except Exception as e:
            logger.error(f"Error getting tweets for user '{username}': {e}")
        
        return tweets
    
    def _extract_tickers(self, tweet_text: str) -> List[str]:
        """
        Extract stock tickers from tweet text if not already extracted from entities.
        
        Args:
            tweet_text: Tweet text content
            
        Returns:
            List of stock ticker symbols
        """
        import re
        
        # Regular expression to find cash tags ($AAPL, $TSLA, etc.)
        cashtag_pattern = r'\$([A-Za-z]{1,5})\b'
        
        # Find all matches
        matches = re.findall(cashtag_pattern, tweet_text)
        
        # Convert to uppercase and deduplicate
        tickers = list(set([match.upper() for match in matches]))
        
        return tickers
    
    def _calculate_engagement(self, tweet: Dict[str, Any]) -> float:
        """
        Calculate engagement score for a tweet.
        
        Args:
            tweet: Tweet data dictionary
            
        Returns:
            Engagement score (0.0 to 1.0)
        """
        engagement = tweet.get("engagement", {})
        
        # Calculate weighted engagement score
        likes = engagement.get("likes", 0)
        retweets = engagement.get("retweets", 0) * 2  # Retweets weighted higher
        replies = engagement.get("replies", 0) * 1.5  # Replies weighted medium
        quotes = engagement.get("quotes", 0) * 3      # Quotes weighted highest
        
        total_engagement = likes + retweets + replies + quotes
        
        # Normalize to 0-1 scale (sigmoid function)
        import math
        normalized_score = 1 / (1 + math.exp(-total_engagement / 1000))
        
        return normalized_score
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape Twitter/X for financial content.
        
        Returns:
            List of tweet data dictionaries
        """
        tweets = []
        
        # Authenticate if needed
        if not await self._authenticate():
            logger.error("Twitter authentication failed")
            return tweets
        
        async with aiohttp.ClientSession() as session:
            # Search for tweets by query
            for query in self.search_queries:
                logger.info(f"Searching Twitter for query: {query}")
                query_tweets = await self._search_tweets(session, query)
                tweets.extend(query_tweets)
                logger.info(f"Found {len(query_tweets)} tweets for query '{query}'")
                
                # Avoid rate limits
                await asyncio.sleep(1)
            
            # Get tweets from specific accounts
            for account in self.accounts_to_follow:
                logger.info(f"Getting tweets from account: {account}")
                account_tweets = await self._get_user_tweets(session, account)
                tweets.extend(account_tweets)
                logger.info(f"Found {len(account_tweets)} tweets from account '{account}'")
                
                # Avoid rate limits
                await asyncio.sleep(1)
        
        # Save updated tweet cache
        self._save_tweet_cache()
        
        # Process tweets to ensure all have tickers
        processed_tweets = []
        for tweet in tweets:
            # If no tickers were extracted from entities, try to extract from text
            if not tweet.get("tickers"):
                tweet["tickers"] = self._extract_tickers(tweet["text"])
            
            # Calculate weight/priority if not already set
            if "weight" not in tweet:
                engagement_score = self._calculate_engagement(tweet)
                tweet["weight"] = calculate_weight(
                    text=tweet["text"],
                    source="Twitter",
                    engagement_score=engagement_score
                )
            
            # Only include tweets that mention at least one ticker
            if tweet.get("tickers"):
                processed_tweets.append(tweet)
        
        logger.info(f"Scraped {len(processed_tweets)} relevant tweets from Twitter/X")
        return processed_tweets
    
    async def process_data(self, data: List[Dict[str, Any]]):
        """
        Process scraped Twitter/X data, save to Parquet, and send to event producer.
        
        Args:
            data: List of dictionaries containing scraped data
        """
        await super().process_data(data)