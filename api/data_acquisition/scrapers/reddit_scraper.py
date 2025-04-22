import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

import praw # Import the PRAW library

from .scraper_base import ScraperBase, logger # Import base class and logger

class RedditScraper(ScraperBase):
    """Scraper for Reddit using PRAW."""

    def __init__(self, output_base_dir: str = "data/raw"):
        super().__init__(output_base_dir)
        self.reddit = self._authenticate()
        if self.reddit:
             logger.info("Reddit API authentication successful.")
        else:
             logger.error("Reddit API authentication failed. Check .env variables.")


    def _authenticate(self) -> Optional[praw.Reddit]:
        """Authenticate with the Reddit API using credentials from environment variables."""
        try:
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            user_agent = os.getenv("REDDIT_USER_AGENT", "RTSentiment Scraper by u/YourUsername") # Default user agent

            if not all([client_id, client_secret, user_agent]):
                logger.error("Missing Reddit API credentials in environment variables (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT).")
                return None

            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                user_agent=user_agent,
                # Optional: Add username/password for script app type or refresh token for web app
                # username=os.getenv("REDDIT_USERNAME"),
                # password=os.getenv("REDDIT_PASSWORD"),
                # refresh_token=os.getenv("REDDIT_REFRESH_TOKEN"),
            )
            # Test authentication (optional, accessing user triggers auth check for some types)
            # logger.info(f"Authenticated as Reddit user: {reddit.user.me()}")
            return reddit
        except Exception as e:
            logger.exception(f"Error during Reddit authentication: {e}")
            return None

    def scrape(self, subreddits: List[str] = None, limit_per_subreddit: int = 100) -> List[Dict]:
        """
        Scrapes posts from specified subreddits.

        Args:
            subreddits (List[str], optional): List of subreddit names to scrape.
                                             Defaults to ["wallstreetbets", "investing", "stocks"].
            limit_per_subreddit (int, optional): Max number of posts per subreddit. Defaults to 100.

        Returns:
            List[Dict]: List of dictionaries containing post data.
        """
        if not self.reddit:
             logger.error("Reddit client not authenticated. Cannot scrape.")
             return []

        if subreddits is None:
            subreddits = ["wallstreetbets", "investing", "stocks"] # Default list

        all_posts_data = []
        logger.info(f"Starting scrape for subreddits: {subreddits} with limit {limit_per_subreddit}")

        for sub_name in subreddits:
            try:
                logger.info(f"Scraping subreddit: r/{sub_name}")
                subreddit = self.reddit.subreddit(sub_name)
                # Fetch 'new' posts, adjust sort method as needed (e.g., 'hot', 'top')
                posts = subreddit.new(limit=limit_per_subreddit)

                count = 0
                for post in posts:
                    post_data = {
                        "id": post.id,
                        "timestamp": datetime.utcfromtimestamp(post.created_utc),
                        "title": post.title,
                        "text": post.selftext, # Body text (empty for link posts)
                        "author": post.author.name if post.author else "[deleted]",
                        "subreddit": sub_name,
                        "url": post.permalink, # Relative URL, use post.url for direct link if link post
                        "score": post.score,
                        "num_comments": post.num_comments,
                        "flair": post.link_flair_text,
                        # Add more fields as needed
                    }
                    all_posts_data.append(post_data)
                    count += 1
                logger.info(f"Scraped {count} posts from r/{sub_name}")

            except praw.exceptions.PRAWException as e:
                 logger.error(f"PRAW error scraping r/{sub_name}: {e}")
            except Exception as e:
                logger.exception(f"An unexpected error occurred scraping r/{sub_name}: {e}") # Log traceback

        logger.info(f"Finished scraping. Total posts collected: {len(all_posts_data)}")
        return all_posts_data

# Example usage (optional, for direct script execution)
if __name__ == "__main__":
    scraper = RedditScraper(output_base_dir="data/raw_reddit")
    # Example: Scrape specific subreddits
    # data = scraper.scrape(subreddits=["technology", "python"], limit_per_subreddit=50)
    # Example: Run with defaults and save
    scraper.run()