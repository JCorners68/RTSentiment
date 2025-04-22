# data_acquisition/scrapers/news_scraper.py

import logging
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional

import feedparser # For parsing RSS feeds
import newspaper # For downloading and extracting article content
import requests # For simple HTTP requests (consider aiohttp for async)

# Import base class, logger, and configuration
from .scraper_base import ScraperBase, logger
from data_acquisition import config # Import the config module

class NewsScraper(ScraperBase):
    """Scraper for news articles from RSS feeds."""

    def __init__(self, output_base_dir: str = config.BASE_OUTPUT_DIR):
        """Initializes the NewsScraper."""
        super().__init__(output_base_dir)
        self.session = self._setup_session()
        logger.info("News Scraper initialized.")

    def _setup_session(self) -> requests.Session:
        """Sets up a requests session with a user agent."""
        session = requests.Session()
        session.headers.update({"User-Agent": config.NEWS_FETCHER_USER_AGENT})
        return session

    def _get_article_details(self, url: str) -> Optional[Dict]:
        """
        Downloads and parses an article using the newspaper3k library.

        Args:
            url (str): The URL of the news article.

        Returns:
            Optional[Dict]: A dictionary containing article details (text, authors, publish_date)
                           or None if fetching/parsing fails.
        """
        try:
            # Configure newspaper Article object
            article = newspaper.Article(url, request_timeout=config.ARTICLE_DOWNLOAD_TIMEOUT)
            # Set headers for the download request using our session's headers
            article.download(headers=self.session.headers)
            # article.download() # Download the article HTML

            if article.download_state != 2: # 2 means success
                 logger.warning(f"Failed to download article: {url} (State: {article.download_state})")
                 return None

            article.parse() # Parse the HTML to extract data

            # Extract publish date, handling potential timezone issues
            publish_date = article.publish_date
            if publish_date:
                # If no timezone info, assume UTC (common for RSS/news)
                if publish_date.tzinfo is None:
                    publish_date = publish_date.replace(tzinfo=timezone.utc)
            else:
                # Fallback if newspaper3k fails to find a date
                publish_date = datetime.now(timezone.utc)


            details = {
                "text": article.text,
                "authors": article.authors,
                "publish_date": publish_date,
                "top_image": article.top_image,
                "movies": article.movies, # Videos if any
                "keywords": article.keywords # Extracted keywords
            }
            return details
        except newspaper.article.ArticleException as e:
            logger.error(f"newspaper3k failed to process article {url}: {e}")
            return None
        except Exception as e:
            logger.exception(f"Unexpected error getting article details for {url}: {e}")
            return None

    def scrape(self, feed_urls: Optional[List[str]] = None) -> List[Dict]:
        """
        Scrapes news articles from a list of RSS feed URLs.

        Args:
            feed_urls (Optional[List[str]]): A list of RSS feed URLs to scrape.
                                             If None, uses DEFAULT_NEWS_FEEDS from config.

        Returns:
            List[Dict]: A list of dictionaries containing article data.
        """
        if feed_urls is None:
            feed_urls = config.DEFAULT_NEWS_FEEDS

        all_articles_data = []
        logger.info(f"Starting news scrape for {len(feed_urls)} feeds.")

        for url in feed_urls:
            logger.info(f"Parsing feed: {url}")
            try:
                # Parse the feed URL
                feed = feedparser.parse(url)

                if feed.bozo: # Check if the feed was parsed correctly
                     logger.warning(f"Feed parsing resulted in errors for {url}: {feed.bozo_exception}")
                     # Continue to next feed or handle error as needed

                feed_title = feed.feed.title if hasattr(feed.feed, 'title') else "Unknown Feed"
                logger.info(f"Found {len(feed.entries)} entries in feed '{feed_title}'")

                for entry in feed.entries:
                    article_url = entry.get("link")
                    if not article_url:
                        logger.warning(f"Skipping entry with no link in feed {url}: {entry.get('title')}")
                        continue

                    # Use published_parsed or updated_parsed time, fallback to now
                    published_time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
                    if published_time_struct:
                        entry_timestamp = datetime(*published_time_struct[:6], tzinfo=timezone.utc)
                    else:
                        entry_timestamp = datetime.now(timezone.utc) # Fallback

                    # Get additional details using newspaper3k
                    details = self._get_article_details(article_url)

                    # Use details if available, otherwise use feed entry data
                    text_content = details["text"] if details and details.get("text") else entry.get("summary", "")
                    authors = details["authors"] if details and details.get("authors") else [entry.get("author")] if entry.get("author") else []
                    # Prefer newspaper's publish date if found, else use feed's date
                    final_timestamp = details["publish_date"] if details and details.get("publish_date") else entry_timestamp

                    # Create a unique ID - combination of URL or GUID if available
                    entry_id_str = entry.get("id") or article_url
                    # Hash the ID string for a consistent length ID
                    unique_id = hashlib.sha256(entry_id_str.encode('utf-8')).hexdigest()

                    article_data = {
                        "id": unique_id,
                        "timestamp": final_timestamp,
                        "title": entry.get("title", "No Title"),
                        "text": text_content,
                        "authors": authors,
                        "url": article_url,
                        "feed_source_url": url,
                        "feed_title": feed_title,
                        "summary": entry.get("summary"), # Keep original summary too
                        "tags": [tag.term for tag in entry.get("tags", [])], # RSS tags
                        # Add fields from newspaper details if available
                        "top_image": details.get("top_image") if details else None,
                        "keywords": details.get("keywords") if details else None,
                    }
                    all_articles_data.append(article_data)

            except Exception as e:
                logger.exception(f"Failed to process feed {url}: {e}")

        logger.info(f"Finished scraping news feeds. Total articles collected: {len(all_articles_data)}")
        return all_articles_data

# Example usage (optional, for direct script execution)
if __name__ == "__main__":
    scraper = NewsScraper()
    # Example: Scrape specific feeds
    # data = scraper.scrape(feed_urls=["http://feeds.bbci.co.uk/news/business/rss.xml"])
    # Example: Run with defaults from config and save
    scraper.run()

