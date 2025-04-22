import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

import tweepy # Import the Tweepy library

from .scraper_base import ScraperBase, logger # Import base class and logger

# --- IMPORTANT NOTE ---
# As of recent changes (2023+), Twitter/X API access is heavily restricted
# and often requires paid subscriptions for meaningful data retrieval.
# Free tier access is very limited.
# Web scraping Twitter is against their Terms of Service and likely to break.
# This code assumes you have appropriate API access (e.g., Elevated or Academic v2, or a paid plan).
# You WILL need to adapt this based on your specific API access level and endpoint availability.
# The 'Bearer Token' is commonly used for v2 endpoints.
# ----------------------

class TwitterScraper(ScraperBase):
    """Scraper for Twitter/X using Tweepy (requires appropriate API access)."""

    def __init__(self, output_base_dir: str = "data/raw"):
        super().__init__(output_base_dir)
        self.client = self._authenticate()
        if self.client:
            logger.info("Twitter API authentication successful (using Bearer Token).")
        else:
             logger.error("Twitter API authentication failed. Check .env variable TWITTER_BEARER_TOKEN.")

    def _authenticate(self) -> Optional[tweepy.Client]:
        """Authenticate with the Twitter API v2 using a Bearer Token."""
        try:
            bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

            if not bearer_token:
                logger.error("Missing Twitter API Bearer Token in environment variable (TWITTER_BEARER_TOKEN).")
                return None

            # Using tweepy.Client for API v2
            client = tweepy.Client(bearer_token=bearer_token, wait_on_rate_limit=True) # wait_on_rate_limit automatically handles rate limit pauses

            # Test authentication by making a simple call (e.g., fetching own user info if applicable, or a test search)
            # Replace 'elonmusk' with a valid Twitter user ID or handle if needed for testing
            # try:
            #    test_user = client.get_user(username='elonmusk')
            #    logger.info(f"Successfully fetched test user data for {test_user.data.name}")
            # except Exception as test_err:
            #     logger.warning(f"Could not verify Twitter auth with test call: {test_err}")

            return client
        except Exception as e:
            logger.exception(f"Error during Twitter authentication: {e}")
            return None

    def scrape(self, query: str = None, max_results: int = 100) -> List[Dict]:
        """
        Scrapes tweets matching a query using the Twitter API v2 search endpoint.

        Args:
            query (str, optional): The search query. See Twitter API v2 docs for syntax.
                                   Defaults to "#stockmarket lang:en -is:retweet".
            max_results (int, optional): Maximum number of tweets to retrieve (per request, pagination might be needed for more).
                                       Twitter API v2 limits might apply (e.g., 100 for recent search). Defaults to 100.


        Returns:
            List[Dict]: List of dictionaries containing tweet data.
        """
        if not self.client:
            logger.error("Twitter client not authenticated. Cannot scrape.")
            return []

        if query is None:
             # Example query: tweets about stockmarket in English, excluding retweets
            query = "#stockmarket lang:en -is:retweet"

        all_tweets_data = []
        logger.info(f"Starting Twitter scrape for query: '{query}' with max results {max_results}")

        try:
             # Define which fields you want in the response
             # Refer to Tweepy/Twitter API v2 docs for available fields
            tweet_fields = ["created_at", "public_metrics", "author_id", "lang", "entities"]
            user_fields = ["username", "name", "public_metrics"] # Fields for the author object

            # Make the API call using search_recent_tweets (or search_all_tweets if you have Academic/paid access)
            # Note: search_recent_tweets only covers ~last 7 days.
            response = self.client.search_recent_tweets(
                query,
                max_results=min(max_results, 100), # Adjust max_results per API limits (10-100 for recent)
                tweet_fields=tweet_fields,
                user_fields=user_fields,
                expansions=["author_id"] # To get user object details
            )

            # --- Handling the response ---
            if response.data: # Check if any tweets were returned
                logger.info(f"Received {len(response.data)} tweets in the response.")

                # Create a lookup dictionary for user data if expansions were used
                users = {user.id: user for user in response.includes.get('users', [])}

                for tweet in response.data:
                    author = users.get(tweet.author_id)
                    tweet_data = {
                        "id": tweet.id_str, # Use string ID
                        "timestamp": tweet.created_at,
                        "text": tweet.text,
                        "author_id": tweet.author_id,
                        "author_username": author.username if author else None,
                        "author_name": author.name if author else None,
                        "lang": tweet.lang,
                        "retweet_count": tweet.public_metrics.get('retweet_count', 0),
                        "reply_count": tweet.public_metrics.get('reply_count', 0),
                        "like_count": tweet.public_metrics.get('like_count', 0),
                        "quote_count": tweet.public_metrics.get('quote_count', 0),
                        # Extract hashtags, mentions, urls if needed from entities
                        "hashtags": [tag['tag'] for tag in tweet.entities.get('hashtags', [])],
                        "mentions": [mention['username'] for mention in tweet.entities.get('mentions', [])],
                        "urls": [url['expanded_url'] for url in tweet.entities.get('urls', [])],
                        "url": f"https://twitter.com/{author.username if author else 'i'}/status/{tweet.id_str}"
                        # Add more fields as needed
                    }
                    all_tweets_data.append(tweet_data)
            else:
                 logger.info("No tweets found matching the query.")

            # --- Pagination (Basic Example) ---
            # To get more than `max_results`, you'd need to handle pagination using `response.meta.get('next_token')`
            # next_token = response.meta.get('next_token')
            # while next_token and len(all_tweets_data) < total_desired_limit:
            #      response = self.client.search_recent_tweets(..., pagination_token=next_token)
            #      # ... process response ...
            #      next_token = response.meta.get('next_token')
            # logger.info(f"Pagination finished or limit reached.")

        except tweepy.errors.TweepyException as e:
            logger.error(f"Tweepy API error during search: {e}")
            # Handle specific errors like rate limits, authentication errors etc.
            if isinstance(e, tweepy.errors.RateLimitError):
                logger.warning("Rate limit exceeded. Tweepy should wait if configured, but logging anyway.")
            elif isinstance(e, tweepy.errors.Forbidden):
                 logger.error(f"Forbidden error (403): Check API key permissions/access level for query '{query}'.")
        except Exception as e:
            logger.exception(f"An unexpected error occurred during Twitter search: {e}") # Log traceback

        logger.info(f"Finished scraping Twitter. Total tweets collected: {len(all_tweets_data)}")
        return all_tweets_data

# Example usage (optional, for direct script execution)
if __name__ == "__main__":
    scraper = TwitterScraper(output_base_dir="data/raw_twitter")
    # Example: Scrape tweets containing 'nvidia'
    # data = scraper.scrape(query="#nvidia lang:en -is:retweet", max_results=50)
    # Example: Run with defaults and save
    scraper.run()