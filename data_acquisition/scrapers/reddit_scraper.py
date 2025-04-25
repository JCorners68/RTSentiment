"""
Reddit scraper implementation for financial subreddits.
"""
import logging
import asyncio
import re
import aiohttp
import time
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from urllib.parse import urljoin, quote

from .base import BaseScraper

logger = logging.getLogger(__name__)

class RedditScraper(BaseScraper):
    """
    Scraper for financial subreddits like r/wallstreetbets, r/investing, etc.
    Uses the Reddit JSON API to fetch posts.
    """
    
    def __init__(self, producer, config):
        """
        Initialize the Reddit scraper.
        
        Args:
            producer: Event producer to send data
            config: Configuration dictionary
        """
        self.producer = producer
        self.config = config
        self.name = self.__class__.__name__
        self.interval = config.get("reddit_polling_interval", 60)  # Default: 60 seconds
        self.running = False
        
        # Reddit specific settings
        self.subreddits = config.get("reddit_subreddits", ["wallstreetbets", "investing", "stocks"])
        self.time_filter = config.get("reddit_time_filter", "day")  # hour, day, week, month, year, all
        self.post_limit = config.get("reddit_post_limit", 25)  # Max posts to fetch per subreddit
        self.sort_by = config.get("reddit_sort_by", "hot")  # hot, new, top, rising
        
        # Reddit requires a User-Agent header
        self.headers = {
            "User-Agent": "python:real-time-sentiment:v1.0 (by /u/yourUsername)",
            "Accept": "application/json"
        }
        
        # Use authentication if provided
        self.client_id = config.get("reddit_client_id", "")
        self.client_secret = config.get("reddit_client_secret", "")
        self.auth_token = None
        self.token_expiry = 0
        
        # Setup data directories
        self.output_dir = os.path.join(os.getcwd(), "data", "output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"Initialized {self.name} for subreddits: {', '.join(self.subreddits)}")
        
    async def _get_auth_token(self, session):
        """
        Get authentication token for Reddit API if client credentials are provided.
        
        Args:
            session: aiohttp session to use for API calls
            
        Returns:
            Boolean indicating if authentication was successful
        """
        # Skip if no credentials
        if not self.client_id or not self.client_secret:
            return False
            
        # If token is still valid, no need to refresh
        if self.auth_token and time.time() < self.token_expiry:
            return True
            
        try:
            auth_url = "https://www.reddit.com/api/v1/access_token"
            auth = aiohttp.BasicAuth(self.client_id, self.client_secret)
            data = {
                "grant_type": "client_credentials",
                "device_id": "DO_NOT_TRACK_THIS_DEVICE"
            }
            
            async with session.post(auth_url, auth=auth, data=data) as response:
                if response.status != 200:
                    logger.error(f"Failed to authenticate with Reddit API: {response.status}")
                    return False
                    
                token_data = await response.json()
                self.auth_token = token_data.get("access_token")
                expires_in = token_data.get("expires_in", 3600)
                self.token_expiry = time.time() + expires_in - 60  # Refresh 60 seconds before expiry
                
                # Update headers with token
                self.headers["Authorization"] = f"Bearer {self.auth_token}"
                logger.info("Successfully authenticated with Reddit API")
                return True
                
        except Exception as e:
            logger.error(f"Error authenticating with Reddit API: {str(e)}")
            return False
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape financial data from Reddit subreddits.
        
        Returns:
            List of dictionaries containing Reddit post data
        """
        results = []
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            # Authenticate if credentials provided
            if self.client_id and self.client_secret:
                auth_success = await self._get_auth_token(session)
                if not auth_success:
                    logger.warning("Proceeding without Reddit API authentication - rate limits will be stricter")
            
            # Process each subreddit
            for subreddit in self.subreddits:
                try:
                    posts = await self._fetch_subreddit(session, subreddit)
                    
                    # Process and extract data from posts
                    subreddit_data = await self._process_posts(posts, subreddit)
                    
                    # Process the data through the event producer
                    if subreddit_data:
                        await self.process_data(subreddit_data)
                        
                    results.extend(subreddit_data)
                    logger.info(f"Scraped {len(subreddit_data)} posts from r/{subreddit}")
                    
                    # Respect Reddit's rate limiting
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error scraping subreddit r/{subreddit}: {str(e)}", exc_info=True)
        
        logger.info(f"Scraped {len(results)} Reddit posts total")
        return results
    
    async def _fetch_subreddit(self, session, subreddit: str) -> List[Dict[str, Any]]:
        """
        Fetch posts from a specific subreddit.
        Uses multiple fallback mechanisms to improve resilience.
        
        Args:
            session: aiohttp session
            subreddit: Name of the subreddit
            
        Returns:
            List of posts from the subreddit
        """
        results = []
        
        # Try multiple approaches to fetch Reddit data
        # 1. First try the official API (OAuth or public JSON API)
        results = await self._fetch_subreddit_api(session, subreddit)
        
        # 2. If that fails, try the old.reddit.com JSON endpoint
        if not results:
            logger.info(f"Trying old.reddit.com for r/{subreddit}")
            results = await self._fetch_subreddit_old(session, subreddit)
        
        # 3. If that also fails, try to scrape the HTML page
        if not results:
            logger.info(f"Trying HTML scraping for r/{subreddit}")
            results = await self._fetch_subreddit_html(session, subreddit)
            
        # Log the outcome
        logger.info(f"Fetched {len(results)} posts from r/{subreddit}")
        return results
        
    async def _fetch_subreddit_api(self, session, subreddit: str) -> List[Dict[str, Any]]:
        """
        Fetch posts from a subreddit using the official API.
        
        Args:
            session: aiohttp session
            subreddit: Name of the subreddit
            
        Returns:
            List of posts from the subreddit
        """
        # Determine if we're using authenticated or unauthenticated API
        if self.auth_token:
            # OAuth API endpoint
            base_url = "https://oauth.reddit.com"
        else:
            # Public JSON API
            base_url = "https://www.reddit.com"
        
        # Construct URL for subreddit posts
        url = f"{base_url}/r/{subreddit}/{self.sort_by}.json?limit={self.post_limit}"
        
        # Add time filter for 'top' sort
        if self.sort_by == "top":
            url += f"&t={self.time_filter}"
        
        try:
            # Add a unique seed to avoid cached responses
            random_seed = int(time.time())
            full_url = f"{url}&seed={random_seed}"
            
            # Add some delay to avoid rate limiting
            await asyncio.sleep(1)
            
            # Make the request
            response = await session.get(full_url)
            
            if response.status != 200:
                logger.warning(f"Failed to fetch r/{subreddit}: HTTP {response.status}")
                return []
            
            data = await response.json()
            
            # Extract posts from response
            if 'data' in data and 'children' in data['data']:
                return data['data']['children']
            else:
                logger.warning(f"Unexpected response format from r/{subreddit}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching r/{subreddit} via API: {str(e)}")
            return []
            
    async def _fetch_subreddit_old(self, session, subreddit: str) -> List[Dict[str, Any]]:
        """
        Fetch posts from a subreddit using old.reddit.com.
        Sometimes more reliable than the main API endpoint.
        
        Args:
            session: aiohttp session
            subreddit: Name of the subreddit
            
        Returns:
            List of posts from the subreddit
        """
        # Use old.reddit.com instead
        url = f"https://old.reddit.com/r/{subreddit}/{self.sort_by}.json?limit={self.post_limit}"
        
        # Add time filter for 'top' sort
        if self.sort_by == "top":
            url += f"&t={self.time_filter}"
            
        try:
            # Add a unique seed to avoid cached responses
            random_seed = int(time.time())
            full_url = f"{url}&seed={random_seed}"
            
            # Add some delay to avoid rate limiting
            await asyncio.sleep(1)
            
            # Make the request
            response = await session.get(full_url)
            
            if response.status != 200:
                logger.warning(f"Failed to fetch r/{subreddit} from old.reddit.com: HTTP {response.status}")
                return []
            
            data = await response.json()
            
            # Extract posts from response
            if 'data' in data and 'children' in data['data']:
                return data['data']['children']
            else:
                logger.warning(f"Unexpected response format from old.reddit.com/r/{subreddit}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching r/{subreddit} via old.reddit.com: {str(e)}")
            return []
            
    async def _fetch_subreddit_html(self, session, subreddit: str) -> List[Dict[str, Any]]:
        """
        Fallback approach: scrape the subreddit HTML page.
        Use this when the JSON API fails.
        
        Args:
            session: aiohttp session
            subreddit: Name of the subreddit
            
        Returns:
            List of posts in a format similar to the API response
        """
        url = f"https://www.reddit.com/r/{subreddit}/{self.sort_by}"
        
        # Add time parameter for 'top' sort
        if self.sort_by == "top":
            url += f"?t={self.time_filter}"
            
        try:
            # Use a different user agent to avoid blocking
            custom_headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
            
            # Add some delay to avoid rate limiting
            await asyncio.sleep(2)
            
            # Make the request
            response = await session.get(url, headers=custom_headers)
            
            if response.status != 200:
                logger.warning(f"Failed to fetch HTML for r/{subreddit}: HTTP {response.status}")
                return []
            
            # Parse the HTML
            html_content = await response.text()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract posts from HTML
            posts = []
            
            # Find post containers - different selectors for different Reddit versions
            post_elements = soup.select('div[data-testid="post-container"]')
            
            if not post_elements:
                post_elements = soup.select('.thing')
                
            if not post_elements:
                post_elements = soup.select('div[class*="Post"]')
                
            if not post_elements:
                # Last resort: find div elements with many children
                for div in soup.find_all('div'):
                    if len(div.find_all()) > 10 and div.get('id') and 't3_' in div.get('id', ''):
                        post_elements.append(div)
            
            # Process each post element
            for post_elem in post_elements:
                try:
                    # Extract the post ID
                    post_id = post_elem.get('id', '') or post_elem.get('data-fullname', '')
                    
                    # Find title element
                    title_elem = post_elem.select_one('h1, h2, h3') or post_elem.select_one('a[data-click-id="body"]')
                    title = title_elem.text.strip() if title_elem else ""
                    
                    # Find post URL
                    url_elem = post_elem.select_one('a[data-click-id="body"]') or post_elem.select_one('a.title')
                    post_url = url_elem.get('href', '') if url_elem else ""
                    
                    # Make sure URL is absolute
                    if post_url and post_url.startswith('/'):
                        post_url = f"https://www.reddit.com{post_url}"
                    
                    # Find post text content
                    text_elem = post_elem.select_one('[data-click-id="text"]') or post_elem.select_one('.md')
                    selftext = text_elem.text.strip() if text_elem else ""
                    
                    # Find score
                    score_elem = post_elem.select_one('[id*="vote-arrows"]') or post_elem.select_one('.score')
                    score_text = score_elem.text.strip() if score_elem else "0"
                    
                    # Parse score (e.g., "1.2k" to 1200)
                    score = 0
                    if score_text:
                        try:
                            if 'k' in score_text.lower():
                                score = int(float(score_text.lower().replace('k', '')) * 1000)
                            else:
                                score = int(score_text.replace(',', ''))
                        except (ValueError, TypeError):
                            score = 0
                    
                    # Find author
                    author_elem = post_elem.select_one('a[href*="/user/"]')
                    author = author_elem.text.strip() if author_elem else "[deleted]"
                    
                    # Create a post object similar to the API response
                    post_data = {
                        "data": {
                            "id": post_id.replace('t3_', ''),
                            "title": title,
                            "selftext": selftext,
                            "author": author,
                            "score": score,
                            "permalink": post_url.replace('https://www.reddit.com', ''),
                            "created_utc": time.time(),  # Use current time
                            "num_comments": 0,
                            "upvote_ratio": 0.5
                        }
                    }
                    
                    posts.append(post_data)
                    
                except Exception as e:
                    logger.warning(f"Error extracting post data from HTML: {e}")
                    continue
            
            return posts
                
        except Exception as e:
            logger.error(f"Error scraping HTML for r/{subreddit}: {str(e)}")
            return []
    
    async def _process_posts(self, posts: List[Dict[str, Any]], subreddit: str) -> List[Dict[str, Any]]:
        """
        Process Reddit posts and extract relevant information.
        
        Args:
            posts: List of posts from Reddit API
            subreddit: Name of the subreddit
            
        Returns:
            List of processed post data
        """
        results = []
        
        for post in posts:
            # Skip non-post items
            if 'data' not in post:
                continue
                
            post_data = post['data']
            
            # Skip posts without titles
            if 'title' not in post_data:
                continue
                
            # Extract relevant data
            try:
                # Basic post data
                processed_post = {
                    "title": post_data.get('title', ''),
                    "content": post_data.get('selftext', ''),
                    "url": f"https://www.reddit.com{post_data.get('permalink', '')}",
                    "source_name": f"Reddit r/{subreddit}",
                    "timestamp": self._format_timestamp(post_data.get('created_utc', 0)),
                    "author": post_data.get('author', '[deleted]'),
                    "score": post_data.get('score', 0),
                    "upvote_ratio": post_data.get('upvote_ratio', 0.5),
                    "num_comments": post_data.get('num_comments', 0),
                    "flair": post_data.get('link_flair_text', ''),
                    "is_original_content": post_data.get('is_original_content', False)
                }
                
                # Extract tickers from title and text
                processed_post["tickers"] = self._extract_tickers(
                    f"{processed_post['title']} {processed_post['content']}"
                )
                
                # Add engagement data for weight calculation
                processed_post["engagement"] = {
                    "likes": processed_post["score"],
                    "comments": processed_post["num_comments"],
                    "ratio": processed_post["upvote_ratio"]
                }
                
                # Only add posts with tickers or highly engaged posts
                if processed_post["tickers"] or processed_post["score"] > 100 or processed_post["num_comments"] > 20:
                    results.append(processed_post)
                
            except Exception as e:
                logger.warning(f"Error processing Reddit post: {str(e)}")
                continue
                
        return results
    
    def _extract_tickers(self, text: str) -> List[str]:
        """
        Extract potential stock tickers from text.
        Handles common Reddit formats like $AAPL, TSLA, etc.
        
        Args:
            text: Text to search for tickers
            
        Returns:
            List of unique tickers found
        """
        # Common words that might be mistaken for tickers
        common_words = {
            'A', 'I', 'IT', 'IS', 'BE', 'AM', 'PM', 'CEO', 'CFO', 'CTO',
            'USA', 'UK', 'EU', 'DD', 'IMO', 'YOLO', 'FOMO', 'EPS', 'ATH',
            'IPO', 'CEO', 'CTO', 'TLDR', 'FUD', 'HODL', 'MOON'
        }
        
        # For Reddit, look for both $TICKER format and standalone tickers
        # Define regex patterns for tickers: $AAPL or AAPL (1-5 capital letters)
        ticker_patterns = [
            r'\$([A-Z]{1,5})\b',  # $AAPL format
            r'\b([A-Z]{1,5})\b'   # AAPL format (standalone uppercase 1-5 letters)
        ]
        
        # Find all potential tickers
        potential_tickers = []
        for pattern in ticker_patterns:
            matches = re.findall(pattern, text)
            potential_tickers.extend(matches)
        
        # Filter out common words and duplicates
        tickers = []
        for ticker in potential_tickers:
            if ticker not in common_words and ticker not in tickers:
                tickers.append(ticker)
        
        return tickers
    
    def _format_timestamp(self, unix_timestamp: float) -> str:
        """
        Convert Unix timestamp to ISO format.
        
        Args:
            unix_timestamp: Unix timestamp from Reddit API
            
        Returns:
            ISO formatted datetime string
        """
        if not unix_timestamp:
            return datetime.now(timezone.utc).isoformat()
            
        try:
            dt = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
            return dt.isoformat()
        except (ValueError, TypeError):
            return datetime.now(timezone.utc).isoformat()
    
    async def process_data(self, data: List[Dict[str, Any]]):
        """
        Process scraped data and send to event producer.
        
        Args:
            data: List of scraped data items
        """
        # Import properly from root module
        try:
            from utils.weight_calculator import calculate_weight
        except ImportError:
            # Fallback to direct import if module structure is different
            import sys
            import os
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from utils.weight_calculator import calculate_weight
        
        for item in data:
            # Add metadata
            item["source"] = self.name
            item["source_type"] = "reddit"
            
            # Calculate weight
            try:
                item["weight"] = calculate_weight(item)
            except Exception as e:
                logger.warning(f"Error calculating weight: {str(e)}")
                # If weight_calculator is not available, use a default weight
                item["weight"] = 0.5
            
            # Determine priority
            priority = "high" if item.get("weight", 0) > 0.7 else "standard"
            
            # Send to appropriate topic
            await self.producer.send(item, priority)
            logger.debug(f"Sent item to {priority} priority topic: {item.get('title', '')}")
        
        # Save to Parquet files
        self._save_to_parquet(data)
        logger.info(f"Saved {len(data)} Reddit posts to Parquet files")
    
    async def start(self):
        """Start the scraper."""
        logger.info(f"Starting {self.name}")
        self.running = True
        
        # Start regular scraping loop
        while self.running:
            try:
                await self.scrape()
            except Exception as e:
                logger.error(f"Error in Reddit scraping cycle: {str(e)}", exc_info=True)
            
            # Wait for next cycle
            await asyncio.sleep(self.interval)
    
    async def stop(self):
        """Stop the scraper."""
        logger.info(f"Stopping {self.name}")
        self.running = False