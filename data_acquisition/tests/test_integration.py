"""
Integration tests for data acquisition components.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json

from data_acquisition.utils.event_producer import EventProducer
from data_acquisition.scrapers.news_scraper import NewsScraper
from data_acquisition.subscription.bloomberg import BloombergReceiver

# Sample HTML for testing
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Financial News Test</title>
</head>
<body>
    <div class="article">
        <h2>AAPL Stock Analysis: What's Next for Apple</h2>
        <p>Analysts weigh in on Apple's future growth prospects.</p>
        <a href="/news/apple-analysis">Read more</a>
    </div>
</body>
</html>
"""

@pytest.fixture
def config():
    """Create a test configuration."""
    return {
        "kafka_bootstrap_servers": "kafka:9092",
        "high_priority_topic": "sentiment-events-high",
        "standard_priority_topic": "sentiment-events-standard",
        "polling_interval": 1,  # Fast polling for tests
        "sources": [
            {
                "name": "Test News",
                "url": "https://test-news.example.com"
            }
        ]
    }

@pytest.fixture
def mock_producer():
    """Create a mock event producer."""
    producer = AsyncMock(spec=EventProducer)
    producer.send = AsyncMock()
    return producer

@pytest.mark.asyncio
async def test_news_to_event_flow(config, mock_producer):
    """Test the flow from news scraping to event production."""
    # For this test, we'll bypass the HTTP request and directly test
    # the processing flow by mocking _scrape_source
    
    # Create a news scraper
    news_scraper = NewsScraper(mock_producer, config)
    
    # Create sample article data that would be produced by _scrape_source
    sample_article = {
        "title": "AAPL Stock Analysis: What's Next for Apple",
        "content": "Analysts weigh in on Apple's future growth prospects.",
        "url": "https://test-news.example.com/news/apple-analysis",
        "source_name": "Test News",
        "timestamp": "2025-04-21T12:34:56Z",
        "tickers": ["AAPL"]
    }
    
    # Mock the _scrape_source method to avoid making actual HTTP requests
    with patch.object(news_scraper, '_scrape_source', new_callable=AsyncMock) as mock_scrape_source:
        # Set up the mock to return sample data
        mock_scrape_source.return_value = [sample_article]
        
        # Call the scrape method - this will use our mocked _scrape_source
        results = await news_scraper.scrape()
        
        # Verify that _scrape_source was called
        assert mock_scrape_source.called, "_scrape_source should have been called"
        
        # Verify that at least one article was scraped
        assert len(results) == 1, "Should have scraped one article"
        
        # Verify that the producer was called
        assert mock_producer.send.called, "EventProducer.send should have been called"
        
        # Check the content of what was sent to the producer
        call_args = mock_producer.send.call_args[0]
        event_data = call_args[0]
        
        # Verify the event data has the expected fields
        assert "title" in event_data, "Event should have a title"
        assert "AAPL" in event_data["title"], "Article should be about AAPL"
        assert "tickers" in event_data, "Event should have tickers"
        assert "AAPL" in event_data["tickers"], "Tickers should include AAPL"
        assert "source" in event_data, "Event should have source metadata"
        assert "weight" in event_data, "Event should have weight calculated"

@pytest.mark.asyncio
async def test_subscription_to_event_flow(config, mock_producer):
    """Test the flow from subscription to event production."""
    # Create a Bloomberg receiver
    receiver = BloombergReceiver(mock_producer, config)
    
    # Create a sample message that the receiver would process
    sample_message = {
        "title": "Bloomberg Alert: TSLA Earnings Beat Expectations",
        "content": "Tesla reported Q1 earnings above analyst expectations.",
        "source_name": "Bloomberg",
        "tickers": ["TSLA"]
    }
    
    # Process the message
    await receiver.process_message(sample_message)
    
    # Verify the producer was called
    mock_producer.send.assert_called_once()
    
    # Check the content of what was sent to the producer
    call_args = mock_producer.send.call_args[0]
    event_data = call_args[0]
    
    # Verify the event data contains our message plus metadata
    assert event_data["title"] == sample_message["title"], "Event title should match message title"
    assert "source" in event_data, "Event should have source metadata"
    assert "source_type" in event_data, "Event should have source_type metadata"
    assert "weight" in event_data, "Event should have weight calculated"
    assert event_data["source_type"] == "subscription", "Source type should be subscription"