"""
Unit tests for RedditScraper.
"""
import pytest
import json
import asyncio
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch, mock_open

from data_acquisition.scrapers.reddit_scraper import RedditScraper

# Sample Reddit API response for testing
SAMPLE_REDDIT_RESPONSE = {
    "kind": "Listing",
    "data": {
        "children": [
            {
                "kind": "t3",
                "data": {
                    "title": "TSLA earnings beat expectations! 🚀",
                    "selftext": "Tesla just reported Q1 earnings and they crushed it. Revenue up 20%, EPS of $2.35 vs $1.95 expected. TSLA to the moon! Thoughts?",
                    "permalink": "/r/wallstreetbets/comments/abc123/tsla_earnings_beat_expectations/",
                    "url": "https://www.reddit.com/r/wallstreetbets/comments/abc123/tsla_earnings_beat_expectations/",
                    "author": "rocket_investor",
                    "score": 420,
                    "upvote_ratio": 0.98,
                    "num_comments": 69,
                    "created_utc": 1650567890,
                    "link_flair_text": "DD",
                    "is_original_content": True
                }
            },
            {
                "kind": "t3",
                "data": {
                    "title": "AAPL and MSFT technical analysis",
                    "selftext": "Let's look at the charts for AAPL and MSFT. Both showing interesting patterns that could signal a breakout.",
                    "permalink": "/r/investing/comments/def456/aapl_and_msft_technical_analysis/",
                    "url": "https://www.reddit.com/r/investing/comments/def456/aapl_and_msft_technical_analysis/",
                    "author": "chart_wizard",
                    "score": 150,
                    "upvote_ratio": 0.85,
                    "num_comments": 32,
                    "created_utc": 1650480000,
                    "link_flair_text": "Analysis",
                    "is_original_content": False
                }
            },
            {
                "kind": "t3",
                "data": {
                    "title": "Market outlook for next week",
                    "selftext": "What's everyone thinking about the market next week? I'm seeing some concerning signals in the bond market.",
                    "permalink": "/r/stocks/comments/ghi789/market_outlook_for_next_week/",
                    "url": "https://www.reddit.com/r/stocks/comments/ghi789/market_outlook_for_next_week/",
                    "author": "market_watcher",
                    "score": 85,
                    "upvote_ratio": 0.77,
                    "num_comments": 41,
                    "created_utc": 1650470000,
                    "link_flair_text": "Discussion",
                    "is_original_content": False
                }
            }
        ],
        "after": "t3_ghi789",
        "before": None
    }
}

@pytest.fixture
def mock_producer():
    """Create a mock event producer."""
    producer = AsyncMock()
    producer.send = AsyncMock()
    return producer

@pytest.fixture
def config():
    """Create a test configuration."""
    return {
        "reddit_polling_interval": 1,  # Fast polling for tests
        "reddit_subreddits": ["wallstreetbets", "investing", "stocks"],
        "reddit_time_filter": "day",
        "reddit_post_limit": 25,
        "reddit_sort_by": "hot"
    }

@pytest.fixture
def reddit_scraper(mock_producer, config):
    """Create a RedditScraper instance for testing."""
    return RedditScraper(mock_producer, config)

@pytest.mark.asyncio
async def test_extract_tickers(reddit_scraper):
    """Test extracting stock tickers from text."""
    # Test with $ prefix format
    text1 = "Just bought some $TSLA and $AAPL shares. Looking at $MSFT next."
    tickers1 = reddit_scraper._extract_tickers(text1)
    assert "TSLA" in tickers1, "Should extract TSLA ticker"
    assert "AAPL" in tickers1, "Should extract AAPL ticker"
    assert "MSFT" in tickers1, "Should extract MSFT ticker"
    
    # Test with standalone uppercase format
    text2 = "NVDA and AMD are my top semiconductor picks for 2025."
    tickers2 = reddit_scraper._extract_tickers(text2)
    assert "NVDA" in tickers2, "Should extract NVDA ticker"
    assert "AMD" in tickers2, "Should extract AMD ticker"
    
    # Test mixed with common words to ignore
    text3 = "IMO YOLO on GME. The DD shows upside. I AM expecting good EPS."
    tickers3 = reddit_scraper._extract_tickers(text3)
    assert "GME" in tickers3, "Should extract GME ticker"
    assert "IMO" not in tickers3, "Should not include common word IMO"
    assert "YOLO" not in tickers3, "Should not include common word YOLO"
    assert "DD" not in tickers3, "Should not include common word DD"
    assert "I" not in tickers3, "Should not include common word I"
    assert "AM" not in tickers3, "Should not include common word AM"
    assert "EPS" not in tickers3, "Should not include common word EPS"

@pytest.mark.asyncio
async def test_format_timestamp(reddit_scraper):
    """Test timestamp formatting."""
    # Test with valid unix timestamp
    ts1 = reddit_scraper._format_timestamp(1650567890)
    assert ts1.endswith("+00:00"), "Should be in ISO format with UTC timezone"
    
    # Test with None/zero
    ts2 = reddit_scraper._format_timestamp(0)
    # Just check it's a string in ISO format
    assert "T" in ts2 and ":" in ts2, "Should return a valid timestamp string"

@pytest.mark.asyncio
async def test_process_posts(reddit_scraper):
    """Test processing Reddit posts."""
    posts = SAMPLE_REDDIT_RESPONSE["data"]["children"]
    subreddit = "wallstreetbets"
    
    # Process the sample posts
    processed_posts = await reddit_scraper._process_posts(posts, subreddit)
    
    # Check the results
    assert len(processed_posts) >= 2, "Should extract at least 2 posts (ones with tickers)"
    
    # Check the first post (TSLA post)
    tsla_post = next((p for p in processed_posts if "TSLA" in p.get("title", "")), None)
    assert tsla_post is not None, "Should find the TSLA post"
    assert "TSLA" in tsla_post["tickers"], "TSLA should be in tickers list"
    assert tsla_post["score"] == 420, "Score should be preserved"
    assert tsla_post["num_comments"] == 69, "Comment count should be preserved"
    assert "engagement" in tsla_post, "Should include engagement data"
    assert tsla_post["engagement"]["likes"] == 420, "Engagement likes should match score"
    
    # Check the second post (AAPL and MSFT post)
    aapl_post = next((p for p in processed_posts if "AAPL" in p.get("title", "")), None)
    assert aapl_post is not None, "Should find the AAPL post"
    assert "AAPL" in aapl_post["tickers"], "AAPL should be in tickers list"
    assert "MSFT" in aapl_post["tickers"], "MSFT should be in tickers list"

@pytest.mark.asyncio
async def test_fetch_subreddit(reddit_scraper):
    """Test fetching posts from a subreddit."""
    # Create a mock session that returns the sample response
    session = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=SAMPLE_REDDIT_RESPONSE)
    session.get = AsyncMock(return_value=mock_response)
    
    # Call the method
    subreddit = "wallstreetbets"
    posts = await reddit_scraper._fetch_subreddit(session, subreddit)
    
    # Check results
    assert len(posts) == 3, "Should return all posts from the sample response"
    assert posts[0]["data"]["title"] == "TSLA earnings beat expectations! 🚀", "First post title should match"
    
    # Verify the URL was constructed correctly
    expected_url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=25"
    session.get.assert_called_once_with(expected_url)

@pytest.mark.asyncio
async def test_scrape(reddit_scraper):
    """Test the full scrape method using mocks for HTTP requests."""
    # Mock the _fetch_subreddit and _process_posts methods
    with patch.object(reddit_scraper, '_fetch_subreddit', new_callable=AsyncMock) as mock_fetch:
        with patch.object(reddit_scraper, '_process_posts', new_callable=AsyncMock) as mock_process:
            with patch.object(reddit_scraper, 'process_data', new_callable=AsyncMock) as mock_process_data:
                # Setup mock responses
                mock_fetch.return_value = SAMPLE_REDDIT_RESPONSE["data"]["children"]
                
                # Setup processed posts
                processed_posts = [
                    {
                        "title": "TSLA earnings beat expectations! 🚀",
                        "content": "Tesla just reported Q1 earnings and they crushed it.",
                        "url": "https://www.reddit.com/r/wallstreetbets/comments/abc123/tsla_earnings_beat_expectations/",
                        "source_name": "Reddit r/wallstreetbets",
                        "tickers": ["TSLA"],
                        "score": 420,
                        "num_comments": 69
                    },
                    {
                        "title": "AAPL and MSFT technical analysis",
                        "content": "Let's look at the charts for AAPL and MSFT.",
                        "url": "https://www.reddit.com/r/investing/comments/def456/aapl_and_msft_technical_analysis/",
                        "source_name": "Reddit r/investing",
                        "tickers": ["AAPL", "MSFT"],
                        "score": 150,
                        "num_comments": 32
                    }
                ]
                mock_process.return_value = processed_posts
                
                # Call the scrape method
                results = await reddit_scraper.scrape()
                
                # Verify the results
                assert len(results) == 6, "Should return 2 posts from each of the 3 subreddits"
                
                # Verify the methods were called with correct arguments
                assert mock_fetch.call_count == 3, "Should fetch from 3 subreddits"
                assert mock_process.call_count == 3, "Should process posts from 3 subreddits"
                assert mock_process_data.call_count == 3, "Should call process_data for 3 subreddits"

@pytest.mark.asyncio
async def test_process_data(reddit_scraper, mock_producer):
    """Test processing data and sending to producer."""
    # Sample processed posts
    posts = [
        {
            "title": "TSLA earnings beat expectations! 🚀",
            "content": "Tesla just reported Q1 earnings and they crushed it.",
            "url": "https://www.reddit.com/r/wallstreetbets/comments/abc123/tsla_earnings_beat_expectations/",
            "source_name": "Reddit r/wallstreetbets",
            "tickers": ["TSLA"],
            "score": 420,
            "num_comments": 69
        }
    ]
    
    # Mock weight calculation to return a specific value
    with patch('data_acquisition.utils.weight_calculator.calculate_weight', return_value=0.8):
        # Process the data
        await reddit_scraper.process_data(posts)
        
        # Verify producer.send was called
        mock_producer.send.assert_called_once()
        
        # Check that metadata was added correctly
        args = mock_producer.send.call_args[0]
        item = args[0]
        priority = args[1]
        
        assert item["source"] == "RedditScraper", "Source should be set to scraper name"
        assert item["source_type"] == "reddit", "Source type should be reddit"
        assert item["weight"] == 0.8, "Weight should be set to mocked value"
        assert priority == "high", "Priority should be high because weight > 0.7"