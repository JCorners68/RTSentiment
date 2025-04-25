"""
News website scraper implementation.
"""
import logging
import aiohttp
import re
import os
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime, timezone

from .base import BaseScraper

logger = logging.getLogger(__name__)

class NewsScraper(BaseScraper):
    """
    Scraper for financial news websites.
    """
    
    def __init__(self, producer, config):
        """
        Initialize the news scraper.
        
        Args:
            producer: Event producer to send data
            config: Configuration dictionary
        """
        self.producer = producer
        self.config = config
        self.name = self.__class__.__name__
        self.interval = config.get("polling_interval", 60)  # Default: 60 seconds
        self.running = False
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        # Setup data directories
        self.output_dir = os.path.join(os.getcwd(), "data", "output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"Initialized {self.name}")
    
    async def process_data(self, data: List[Dict[str, Any]]):
        """
        Process scraped data and send to event producer.
        
        Args:
            data: List of scraped data items
        """
        from ..utils.weight_calculator import calculate_weight
        
        for item in data:
            # Add metadata
            item["source"] = self.name
            item["source_type"] = "scraper"
            
            # Calculate weight
            try:
                item["weight"] = calculate_weight(item)
            except (ImportError, NameError):
                # If weight_calculator is not available, use a default weight
                item["weight"] = 0.5
            
            # Determine priority
            priority = "high" if item.get("weight", 0) > 0.7 else "standard"
            
            # Send to appropriate topic
            await self.producer.send(item, priority)
            logger.debug(f"Sent item to {priority} priority topic: {item.get('title', '')}")
        
        # Save to Parquet files
        self._save_to_parquet(data)
        logger.info(f"Saved {len(data)} news articles to Parquet files")
    
    async def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape financial news from configured sources.
        
        Returns:
            List of dictionaries containing news data
        """
        results = []
        sources = self.config.get("sources", [])
        
        async with aiohttp.ClientSession(headers=self.headers) as session:
            for source in sources:
                try:
                    source_data = await self._scrape_source(session, source)
                    
                    # Process the data through the event producer
                    if source_data:
                        await self.process_data(source_data)
                        
                    results.extend(source_data)
                    logger.info(f"Scraped {len(source_data)} articles from {source['name']}")
                except Exception as e:
                    logger.error(f"Error scraping {source['name']}: {str(e)}", exc_info=True)
        
        logger.info(f"Scraped {len(results)} news items total")
        return results
    
    async def _scrape_source(self, session: aiohttp.ClientSession, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape a specific news source.
        
        Args:
            session: HTTP client session
            source: Source configuration
            
        Returns:
            List of news items from the source
        """
        # Get the URL to scrape
        url = source["url"]
        
        # Fetch the page
        async with session.get(url) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch {source['name']}: HTTP {response.status}")
                return []
                
            # Parse the HTML content
            html_content = await response.text()
            articles = await self._parse_articles(html_content, source)
            
            # Extract article data
            results = []
            for article in articles:
                try:
                    # Extract article data
                    article_data = {
                        "title": self._extract_title(article, source),
                        "content": self._extract_summary(article, source),
                        "url": self._extract_url(article, source, base_url=url),
                        "source_name": source["name"],
                        "timestamp": self._extract_timestamp(article, source),
                        "tickers": self._extract_tickers(article, source)
                    }
                    
                    # Only add articles with valid title and URL
                    if article_data["title"] and article_data["url"]:
                        results.append(article_data)
                except Exception as e:
                    logger.warning(f"Failed to extract article data: {str(e)}")
                    continue
            
            return results

    async def _parse_articles(self, html_content: str, source: Dict[str, Any]) -> List[Any]:
        """
        Parse the HTML content to find article elements.
        
        Args:
            html_content: HTML content of the page
            source: Source configuration
            
        Returns:
            List of article elements
        """
        # Different sources have different article patterns
        soup = BeautifulSoup(html_content, 'html.parser')
        source_name = source["name"].lower()
        
        articles = []
        
        # Updated selectors for various financial news sites
        # Try multiple selectors for each site to improve resilience
        if "financial times" in source_name:
            # Modern FT selectors
            selectors = [
                'div.o-teaser', 
                'div.o-teaser__content',
                'div[data-trackable="story-card"]',
                'li.o-teaser-collection__item',
                'article.o-teaser'
            ]
            for selector in selectors:
                articles.extend(soup.select(selector))
                
        elif "wall street journal" in source_name:
            # Updated WSJ selectors
            selectors = [
                'article.WSJTheme--story--',
                'article.css-xp4jfu',
                'div.WSJTheme--story--',
                'div.article-wrap',
                'div.wsj-card'
            ]
            for selector in selectors:
                articles.extend(soup.select(selector))
                
        elif "bloomberg" in source_name:
            # Bloomberg selectors
            selectors = [
                'article.story-package-module__story',
                'article.story-list-story',
                'div.story-package-module__story',
                'div.story-list-item',
                'div[data-type="article"]'
            ]
            for selector in selectors:
                articles.extend(soup.select(selector))
                
        elif "yahoo finance" in source_name:
            # Yahoo Finance selectors
            selectors = [
                'div.Ov\\(h\\).Pend\\(44px\\)',
                'div.js-stream-content',
                'li.js-stream-content',
                'div.Pos\\(r\\)',
                'div.finance-list-item'
            ]
            for selector in selectors:
                try:
                    articles.extend(soup.select(selector))
                except Exception:
                    # Some complex selectors might fail
                    continue
                    
        elif "cnbc" in source_name:
            # CNBC selectors
            selectors = [
                'div.Card-standardBreakerCard',
                'div.Card-card',
                'div.RiverCard-container',
                'div.Card',
                'div.SearchResult-searchResult'
            ]
            for selector in selectors:
                articles.extend(soup.select(selector))
                
        elif "marketwatch" in source_name:
            # MarketWatch selectors
            selectors = [
                'div.article__content',
                'div.element--article',
                'div.collection__elements',
                'div.story__body',
                'div.story'
            ]
            for selector in selectors:
                articles.extend(soup.select(selector))
                
        elif "reuters" in source_name:
            # Reuters selectors
            selectors = [
                'article[data-testid="stack-article-card"]',
                'li.news-feed-item',
                'div.news-card',
                'article.story',
                'div.item'
            ]
            for selector in selectors:
                articles.extend(soup.select(selector))
                
        # If no articles found with specific selectors, try generic approaches
        if not articles:
            # Generic article finder for other sources
            # Look for common article patterns
            logger.info(f"No specific selectors matched for {source['name']}, trying generic selectors")
            article_candidates = []
            article_candidates.extend(soup.select('article'))
            article_candidates.extend(soup.select('div.article'))
            article_candidates.extend(soup.select('.story'))
            article_candidates.extend(soup.select('.news-item'))
            article_candidates.extend(soup.select('[data-article-id]'))
            article_candidates.extend(soup.select('[data-story-id]'))
            
            # If still nothing found, try to find by tag and class patterns
            if not article_candidates:
                logger.info(f"No generic article selectors matched for {source['name']}, searching div elements")
                for div in soup.find_all('div'):
                    classes = div.get('class', [])
                    if any(c for c in classes if 'article' in c.lower() or 'story' in c.lower() or 'news' in c.lower()):
                        article_candidates.append(div)
            
            articles = article_candidates
        
        # Smart fallback: if we still have no articles, look for divs containing title-like elements
        if not articles:
            logger.warning(f"No articles found for {source['name']}, using smart fallback method")
            # Look for divs with h2/h3 elements - likely to be article containers
            for div in soup.find_all('div'):
                if div.find('h2') or div.find('h3'):
                    # Check if it has a paragraph too - more likely to be an article
                    if div.find('p'):
                        articles.append(div)
            
            # If that didn't work, try to find any elements with links and text
            if not articles:
                logger.warning(f"Smart fallback failed for {source['name']}, using basic fallback")
                for div in soup.find_all(['div', 'li'], limit=10):
                    # Only consider divs with some paragraph text and a link
                    if div.find('a') and div.text and len(div.text.strip()) > 50:
                        articles.append(div)
        
        logger.info(f"Found {len(articles)} potential articles for {source['name']}")
        return articles

    def _extract_title(self, article, source) -> str:
        """Extract article title."""
        title_tag = article.find('h1') or article.find('h2') or article.find('h3')
        if title_tag:
            return title_tag.get_text().strip()
        
        # If no heading tag found, look for elements with title-like classes
        title_candidates = article.select('[class*=title], [class*=headline], [class*=heading]')
        if title_candidates:
            return title_candidates[0].get_text().strip()
        
        return ""

    def _extract_summary(self, article, source) -> str:
        """Extract article summary/content."""
        # Look for dedicated summary elements first
        summary_candidates = []
        summary_candidates.extend(article.select('p[class*=summary]'))
        summary_candidates.extend(article.select('p[class*=description]'))
        summary_candidates.extend(article.select('p[class*=teaser]'))
        summary_candidates.extend(article.select('.summary'))
        
        # If nothing specific found, take the first paragraph
        if not summary_candidates:
            summary_candidates = article.find_all('p', limit=1)
        
        if summary_candidates:
            return summary_candidates[0].get_text().strip()
            
        # Fallback: return a short text from the article
        text = article.get_text().strip()
        return text[:200] + ('...' if len(text) > 200 else '')

    def _extract_url(self, article, source, base_url) -> str:
        """Extract article URL."""
        # Find the first anchor tag that might be the article link
        link_tag = article.find('a')
        if not link_tag:
            return ""
            
        href = link_tag.get('href', '')
        if not href:
            return ""
            
        # Handle relative URLs
        if href.startswith('/'):
            # Parse base URL to get the domain
            domain = '/'.join(base_url.split('/')[:3])  # http(s)://domain.com
            return domain + href
        elif not href.startswith(('http://', 'https://')):
            return base_url.rstrip('/') + '/' + href.lstrip('/')
            
        return href

    def _extract_timestamp(self, article, source) -> str:
        """Extract article timestamp."""
        # Look for time elements
        time_tag = article.find('time')
        if time_tag:
            datetime_str = time_tag.get('datetime') or time_tag.get_text().strip()
            if datetime_str:
                try:
                    # Try to parse the datetime
                    dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    return dt.isoformat()
                except (ValueError, TypeError):
                    pass
        
        # Look for elements with date-related classes
        date_candidates = article.select('[class*=date], [class*=time], [class*=timestamp]')
        if date_candidates:
            date_text = date_candidates[0].get_text().strip()
            # For simplicity, just return the text - in production would parse this
            return date_text
        
        # Fallback to current time
        return datetime.now(timezone.utc).isoformat()

    def _extract_tickers(self, article, source) -> List[str]:
        """Extract stock tickers mentioned in the article."""
        # Simple regex pattern to find potential stock tickers (uppercase letters)
        text = article.get_text()
        
        # Basic ticker pattern: 1-5 uppercase letters, optionally preceded by $ symbol
        ticker_pattern = r'\$?([A-Z]{1,5})\b'
        
        # Find all potential tickers
        potential_tickers = re.findall(ticker_pattern, text)
        
        # Filter out common words that could be mistaken for tickers
        common_words = {'A', 'I', 'IT', 'IS', 'BE', 'AM', 'PM', 'CEO', 'CFO', 'CTO', 'USA', 'UK', 'EU'}
        tickers = [ticker for ticker in potential_tickers if ticker not in common_words]
        
        return tickers[:10]  # Limit to 10 tickers to avoid noise

    async def start(self):
        """Start the scraper."""
        self.running = True
        logger.info(f"Started {self.name}")
        
    async def stop(self):
        """Stop the scraper."""
        self.running = False
        logger.info(f"Stopped {self.name}")