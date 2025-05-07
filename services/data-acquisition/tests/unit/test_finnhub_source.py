"""
Unit tests for the Finnhub data source module.

This module contains comprehensive unit tests for the FinnhubDataSource class,
testing API calls, data processing, error handling, rate limiting, and Redis caching.
"""

import os
import json
import asyncio
import datetime
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from typing import Dict, Any, List

import pytest
import pytest_asyncio
import httpx
import pandas as pd
from pyiceberg.table import Table

# Add parent directory to path to import config
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.finnhub_source import FinnhubDataSource, RateLimiter, cache_result


# Test data fixtures
@pytest.fixture
def mock_config():
    """Return a mock configuration for testing."""
    return {
        "api_keys": {
            "finnhub": "test_api_key"
        },
        "rate_limits": {
            "finnhub": 60
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 0
        },
        "features": {
            "use_redis_cache": True,
            "use_iceberg_backend": True
        },
        "data_sources": {
            "sp500_tickers": ["AAPL", "MSFT", "GOOGL"]
        }
    }


@pytest.fixture
def mock_news_data():
    """Return mock company news data for testing."""
    return [
        {
            "datetime": 1615900800,  # Timestamp
            "headline": "Test Headline 1",
            "summary": "Test Summary 1",
            "url": "https://example.com/news/1",
            "source": "Test Source"
        },
        {
            "datetime": 1615900900,
            "headline": "Test Headline 2",
            "summary": "Test Summary 2",
            "url": "https://example.com/news/2",
            "source": "Test Source"
        }
    ]


@pytest.fixture
def mock_earnings_data():
    """Return mock earnings data for testing."""
    return {
        "earningsCalendar": [
            {
                "date": "2023-01-01",
                "epsActual": 1.5,
                "epsEstimate": 1.2,
                "hour": "amc",
                "quarter": 1,
                "revenueActual": 10000000,
                "revenueEstimate": 9500000,
                "symbol": "AAPL",
                "year": 2023
            },
            {
                "date": "2022-10-01",
                "epsActual": 1.3,
                "epsEstimate": 1.1,
                "hour": "amc",
                "quarter": 4,
                "revenueActual": 9500000,
                "revenueEstimate": 9000000,
                "symbol": "AAPL",
                "year": 2022
            }
        ]
    }


@pytest.fixture
def mock_sentiment_data():
    """Return mock sentiment data for testing."""
    return {
        "buzz": {
            "articlesInLastWeek": 100,
            "buzz": 0.8,
            "weeklyAverage": 0.5
        },
        "companyNewsScore": 0.7,
        "sectorAverageNewsScore": 0.6,
        "sector": "Technology",
        "symbol": "AAPL"
    }


# Fixture for an initialized FinnhubDataSource with mocks
@pytest_asyncio.fixture
async def mock_finnhub_source(mock_config):
    """Return a mock FinnhubDataSource instance with dependencies mocked."""
    with patch('src.finnhub_source.get_config', return_value=mock_config), \
         patch('src.finnhub_source.finnhub.Client'), \
         patch('src.finnhub_source.httpx.AsyncClient'), \
         patch('src.finnhub_source.redis.Redis'), \
         patch('src.finnhub_source.get_table'):
        
        source = FinnhubDataSource()
        
        # Mock rate limiter to avoid sleeping during tests
        source.rate_limiter.wait = AsyncMock()
        
        # Mock Redis client methods
        source.redis_client.get = Mock(return_value=None)
        source.redis_client.setex = Mock()
        
        # Mock Iceberg tables
        source.sentiment_table = Mock(spec=Table)
        source.market_events_table = Mock(spec=Table)
        
        # Set up append context managers for Iceberg tables
        source.sentiment_table.newAppend.return_value.__enter__.return_value = Mock()
        source.market_events_table.newAppend.return_value.__enter__.return_value = Mock()
        
        # Patch the UUID generation to be deterministic
        with patch('src.finnhub_source.generate_uuid', return_value=uuid.UUID('12345678-1234-5678-1234-567812345678')):
            yield source


# Fixture for testing Redis caching
@pytest.fixture
def mock_redis_cache_enabled(mock_finnhub_source):
    """Return a FinnhubDataSource with Redis caching enabled."""
    mock_finnhub_source.use_redis_cache = True
    return mock_finnhub_source


# Tests for the RateLimiter class
@pytest.mark.asyncio
async def test_rate_limiter_wait():
    """Test that rate limiter properly throttles requests."""
    with patch('src.finnhub_source.time.time') as mock_time, \
         patch('src.finnhub_source.asyncio.sleep') as mock_sleep:
        
        # Setup the time mock to simulate time passage
        mock_time.side_effect = [0, 0, 0.2]  # Initialize, check, after sleep
        mock_sleep.return_value = None
        
        # Create rate limiter with 30 requests per minute (1 request per 2 seconds)
        limiter = RateLimiter(30)
        
        # First request should be immediate
        await limiter.wait()
        assert mock_sleep.call_count == 0
        
        # Reset mock
        mock_sleep.reset_mock()
        
        # Make the second request right after (should throttle)
        mock_time.side_effect = [0.1, 0.1, 2.0]  # Last request, now, after sleep
        await limiter.wait()
        
        # Should sleep to maintain interval
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] > 0


@pytest.mark.asyncio
async def test_rate_limiter_window_reset():
    """Test that rate limiter resets after the window expires."""
    with patch('src.finnhub_source.time.time') as mock_time, \
         patch('src.finnhub_source.asyncio.sleep') as mock_sleep:
        
        # Create rate limiter with 10 requests per minute
        limiter = RateLimiter(10)
        limiter.request_count = 10  # Max out the requests
        limiter.window_start_time = 0  # Window starts at 0
        
        # Simulate time passage of 61 seconds (window should reset)
        mock_time.return_value = 61.0
        mock_sleep.return_value = None
        
        # This should reset the counter and not sleep
        await limiter.wait()
        
        assert limiter.request_count == 1  # Reset to 0 then incremented
        assert limiter.window_start_time == 61.0  # New window starts at current time
        assert mock_sleep.call_count == 0  # Should not sleep


@pytest.mark.asyncio
async def test_rate_limiter_max_requests():
    """Test rate limiter handles reaching max requests in a window."""
    with patch('src.finnhub_source.time.time') as mock_time, \
         patch('src.finnhub_source.asyncio.sleep') as mock_sleep:
        
        # Create rate limiter with 10 requests per minute
        limiter = RateLimiter(10)
        limiter.request_count = 10  # Max out the requests
        limiter.window_start_time = 30.0  # Window started 30 seconds ago
        
        # Current time is 40 seconds in
        mock_time.return_value = 40.0
        mock_sleep.return_value = None
        
        # Should wait until window expires
        await limiter.wait()
        
        # Should sleep for the remaining time in the window
        mock_sleep.assert_called_once()
        assert mock_sleep.call_args[0][0] == pytest.approx(50.0, 0.1)  # 60s window - 10s elapsed


# Tests for the cache_result decorator
@pytest.mark.asyncio
async def test_cache_result_no_cache():
    """Test cache_result when Redis cache is disabled."""
    # Create a mock class and method with the decorator
    class TestClass:
        def __init__(self):
            self.use_redis_cache = False
            self.redis_client = None
            
        @cache_result(ttl=3600)
        async def test_method(self, arg1, arg2=None):
            return {"result": "test", "arg1": arg1, "arg2": arg2}
    
    # Call the method
    test = TestClass()
    result = await test.test_method("value1", arg2="value2")
    
    assert result == {"result": "test", "arg1": "value1", "arg2": "value2"}


@pytest.mark.asyncio
async def test_cache_result_cache_hit(mock_redis_cache_enabled):
    """Test cache_result when cache hit occurs."""
    # Setup mock Redis get to return a cache hit
    cached_data = {"result": "cached", "arg1": "value1", "arg2": "value2"}
    mock_redis_cache_enabled.redis_client.get.return_value = json.dumps(cached_data)
    
    # Create a test method with the decorator
    @cache_result(ttl=3600)
    async def test_method(self, arg1, arg2=None):
        # This shouldn't be called if cache hit
        assert False, "Original method called when cache hit"
        return {"result": "original", "arg1": arg1, "arg2": arg2}
    
    # Add the method to our mock source
    mock_redis_cache_enabled.test_method = test_method.__get__(mock_redis_cache_enabled)
    
    # Call the method
    result = await mock_redis_cache_enabled.test_method("value1", arg2="value2")
    
    # The result should be the cached value
    assert result == cached_data
    mock_redis_cache_enabled.redis_client.get.assert_called_once()
    mock_redis_cache_enabled.redis_client.setex.assert_not_called()


@pytest.mark.asyncio
async def test_cache_result_cache_miss(mock_redis_cache_enabled):
    """Test cache_result when cache miss occurs."""
    # Setup mock Redis get to return cache miss
    mock_redis_cache_enabled.redis_client.get.return_value = None
    
    # Create a test method with the decorator
    @cache_result(ttl=3600)
    async def test_method(self, arg1, arg2=None):
        return {"result": "original", "arg1": arg1, "arg2": arg2}
    
    # Add the method to our mock source
    mock_redis_cache_enabled.test_method = test_method.__get__(mock_redis_cache_enabled)
    
    # Call the method
    result = await mock_redis_cache_enabled.test_method("value1", arg2="value2")
    
    # Should return original result
    assert result == {"result": "original", "arg1": "value1", "arg2": "value2"}
    
    # Should try cache and then store the result
    mock_redis_cache_enabled.redis_client.get.assert_called_once()
    mock_redis_cache_enabled.redis_client.setex.assert_called_once()


@pytest.mark.asyncio
async def test_cache_result_cache_error(mock_redis_cache_enabled):
    """Test cache_result handles Redis errors gracefully."""
    # Setup Redis to raise an exception when setting cache
    mock_redis_cache_enabled.redis_client.get.return_value = None
    mock_redis_cache_enabled.redis_client.setex.side_effect = Exception("Redis error")
    
    # Create a test method with the decorator
    @cache_result(ttl=3600)
    async def test_method(self, arg1, arg2=None):
        return {"result": "original", "arg1": arg1, "arg2": arg2}
    
    # Add the method to our mock source
    mock_redis_cache_enabled.test_method = test_method.__get__(mock_redis_cache_enabled)
    
    # Call the method - should not raise exception
    result = await mock_redis_cache_enabled.test_method("value1", arg2="value2")
    
    # Should return original result despite Redis error
    assert result == {"result": "original", "arg1": "value1", "arg2": "value2"}


# Tests for FinnhubDataSource API methods
@pytest.mark.asyncio
async def test_get_company_news_success(mock_finnhub_source, mock_news_data):
    """Test successful company news retrieval."""
    # Mock the response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_news_data
    
    # Set up the mock HTTP client
    mock_finnhub_source.async_client.get.return_value = mock_response
    
    # Call the method
    result = await mock_finnhub_source.get_company_news("AAPL")
    
    # Verify the API was called with correct parameters
    mock_finnhub_source.async_client.get.assert_called_once()
    call_args = mock_finnhub_source.async_client.get.call_args[0][0]
    assert call_args == "/company-news"
    
    # Verify rate limiter was used
    mock_finnhub_source.rate_limiter.wait.assert_called_once()
    
    # Check the returned data
    assert len(result) == 2
    assert all(item["ticker"] == "AAPL" for item in result)
    assert "datetime" in result[0]
    assert isinstance(result[0]["datetime"], str)  # Should be converted to ISO format


@pytest.mark.asyncio
async def test_get_company_news_error(mock_finnhub_source):
    """Test company news error handling."""
    # Mock the response with an error
    mock_response = MagicMock()
    mock_response.status_code = 429  # Rate limit error
    mock_response.json.return_value = {"error": "Rate limit exceeded"}
    
    # Set up the mock HTTP client
    mock_finnhub_source.async_client.get.return_value = mock_response
    
    # Mock the error handler
    mock_finnhub_source._handle_api_error = AsyncMock()
    
    # Call the method
    result = await mock_finnhub_source.get_company_news("AAPL")
    
    # Verify the error handler was called
    mock_finnhub_source._handle_api_error.assert_called_once()
    
    # Should return an empty list on error
    assert result == []


@pytest.mark.asyncio
async def test_get_company_news_exception(mock_finnhub_source):
    """Test company news exception handling."""
    # Make the API call raise an exception
    mock_finnhub_source.async_client.get.side_effect = Exception("Network error")
    
    # Call the method - should not raise an exception
    result = await mock_finnhub_source.get_company_news("AAPL")
    
    # Should return an empty list on exception
    assert result == []


@pytest.mark.asyncio
async def test_get_company_earnings_success(mock_finnhub_source, mock_earnings_data):
    """Test successful company earnings retrieval."""
    # Mock the response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_earnings_data
    
    # Set up the mock HTTP client
    mock_finnhub_source.async_client.get.return_value = mock_response
    
    # Call the method
    result = await mock_finnhub_source.get_company_earnings("AAPL", limit=2)
    
    # Verify the API was called with correct parameters
    mock_finnhub_source.async_client.get.assert_called_once()
    call_args = mock_finnhub_source.async_client.get.call_args[0][0]
    assert call_args == "/stock/earnings"
    
    # Verify parameters
    params = mock_finnhub_source.async_client.get.call_args[1]["params"]
    assert params["symbol"] == "AAPL"
    assert params["limit"] == 2
    
    # Verify rate limiter was used
    mock_finnhub_source.rate_limiter.wait.assert_called_once()
    
    # Check the returned data
    assert len(result) == 2
    assert all(item["ticker"] == "AAPL" for item in result)
    assert "timestamp" in result[0]  # Should have timestamp converted from date


@pytest.mark.asyncio
async def test_get_sentiment_data_success(mock_finnhub_source, mock_sentiment_data):
    """Test successful sentiment data retrieval."""
    # Mock the response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_sentiment_data
    
    # Set up the mock HTTP client
    mock_finnhub_source.async_client.get.return_value = mock_response
    
    # Call the method
    result = await mock_finnhub_source.get_sentiment_data("AAPL")
    
    # Verify the API was called with correct parameters
    mock_finnhub_source.async_client.get.assert_called_once()
    call_args = mock_finnhub_source.async_client.get.call_args[0][0]
    assert call_args == "/news-sentiment"
    
    # Verify parameters
    params = mock_finnhub_source.async_client.get.call_args[1]["params"]
    assert params["symbol"] == "AAPL"
    
    # Verify rate limiter was used
    mock_finnhub_source.rate_limiter.wait.assert_called_once()
    
    # Check the returned data
    assert "ticker" in result
    assert result["ticker"] == "AAPL"
    assert "timestamp" in result  # Should add timestamp


# Tests for data processing methods
@pytest.mark.asyncio
async def test_process_news_to_events(mock_finnhub_source, mock_news_data):
    """Test processing news items into market events."""
    # Add ticker to the mock data
    for item in mock_news_data:
        item["ticker"] = "AAPL"
    
    # Call the method
    events = await mock_finnhub_source.process_news_to_events(mock_news_data)
    
    # Check the events
    assert len(events) == 2
    assert all(event["ticker"] == "AAPL" for event in events)
    assert all(event["event_type"] == "news" for event in events)
    assert all("id" in event for event in events)
    assert all("timestamp" in event for event in events)
    assert all("title" in event for event in events)
    assert all("summary" in event for event in events)
    assert all("metadata" in event for event in events)


@pytest.mark.asyncio
async def test_process_earnings_to_events(mock_finnhub_source, mock_earnings_data):
    """Test processing earnings items into market events."""
    # Create sample data with tickers
    earnings_items = []
    for item in mock_earnings_data["earningsCalendar"]:
        earnings_items.append({"ticker": "AAPL", **item})
    
    # Call the method
    events = await mock_finnhub_source.process_earnings_to_events(earnings_items)
    
    # Check the events
    assert len(events) == 2
    assert all(event["ticker"] == "AAPL" for event in events)
    assert all(event["event_type"] == "earnings" for event in events)
    assert all("id" in event for event in events)
    assert all("timestamp" in event for event in events)
    assert all("title" in event for event in events)
    assert all("summary" in event for event in events)
    assert all("metadata" in event for event in events)


@pytest.mark.asyncio
async def test_process_sentiment_to_records(mock_finnhub_source, mock_sentiment_data):
    """Test processing sentiment data into sentiment records."""
    # Add ticker and timestamp to sentiment data
    sentiment_data = {
        "ticker": "AAPL",
        "timestamp": datetime.datetime.now().isoformat(),
        **mock_sentiment_data
    }
    
    # Call the method
    records = await mock_finnhub_source.process_sentiment_to_records(sentiment_data)
    
    # Should create multiple records for different sentiment aspects
    assert len(records) == 3  # Buzz, news, and sector
    assert all(record["ticker"] == "AAPL" for record in records)
    assert all("id" in record for record in records)
    assert all("timestamp" in record for record in records)
    assert all("source" in record for record in records)
    assert all("text" in record for record in records)
    assert all("sentiment_score" in record for record in records)
    assert all("sentiment_label" in record for record in records)
    assert all("metadata" in record for record in records)


# Tests for Iceberg write operations
@pytest.mark.asyncio
async def test_write_to_sentiment_records_success(mock_finnhub_source):
    """Test successfully writing sentiment records to Iceberg."""
    # Create test records
    records = [
        {
            "ticker": "AAPL",
            "text": "Test sentiment 1",
            "sentiment_score": 0.7,
            "sentiment_label": "positive",
            "source": "test",
            "timestamp": datetime.datetime.now().isoformat(),
            "metadata": {"key": "value"}
        },
        {
            "ticker": "MSFT",
            "text": "Test sentiment 2",
            "sentiment_score": 0.3,
            "sentiment_label": "negative",
            "source": "test",
            "timestamp": datetime.datetime.now().isoformat(),
            "metadata": {"key": "value"}
        }
    ]
    
    # Mock the DataFrame conversion and append operation
    with patch('src.finnhub_source.pd.DataFrame') as mock_df:
        # Call the method
        result = await mock_finnhub_source.write_to_sentiment_records(records)
        
        # Verify success
        assert result is True
        
        # Check that DataFrame was created and written
        mock_df.assert_called_once()
        mock_finnhub_source.sentiment_table.newAppend.assert_called_once()
        mock_finnhub_source.sentiment_table.newAppend().__enter__().writeDF.assert_called_once()
        mock_finnhub_source.sentiment_table.newAppend().__enter__().commit.assert_called_once()


@pytest.mark.asyncio
async def test_write_to_sentiment_records_no_iceberg(mock_finnhub_source):
    """Test behavior when Iceberg is disabled."""
    # Disable Iceberg
    mock_finnhub_source.use_iceberg = False
    
    # Call the method with some records
    result = await mock_finnhub_source.write_to_sentiment_records([{"ticker": "AAPL", "text": "Test"}])
    
    # Should return False and not attempt to write
    assert result is False
    mock_finnhub_source.sentiment_table.newAppend.assert_not_called()


@pytest.mark.asyncio
async def test_write_to_sentiment_records_no_records(mock_finnhub_source):
    """Test behavior when no records are provided."""
    # Call the method with empty list
    result = await mock_finnhub_source.write_to_sentiment_records([])
    
    # Should return True but not attempt to write
    assert result is True
    mock_finnhub_source.sentiment_table.newAppend.assert_not_called()


@pytest.mark.asyncio
async def test_write_to_sentiment_records_error(mock_finnhub_source):
    """Test error handling when writing sentiment records."""
    # Create a record
    records = [{"ticker": "AAPL", "text": "Test"}]
    
    # Make the append operation raise an exception
    mock_finnhub_source.sentiment_table.newAppend.side_effect = Exception("Iceberg error")
    
    # Call the method
    result = await mock_finnhub_source.write_to_sentiment_records(records)
    
    # Should handle the error and return False
    assert result is False


@pytest.mark.asyncio
async def test_write_to_market_events_success(mock_finnhub_source):
    """Test successfully writing market events to Iceberg."""
    # Create test events
    events = [
        {
            "ticker": "AAPL",
            "event_type": "news",
            "title": "Test event 1",
            "summary": "Test summary 1",
            "url": "https://example.com/1",
            "source": "test",
            "timestamp": datetime.datetime.now().isoformat(),
            "metadata": {"key": "value"}
        },
        {
            "ticker": "MSFT",
            "event_type": "earnings",
            "title": "Test event 2",
            "summary": "Test summary 2",
            "url": "https://example.com/2",
            "source": "test",
            "timestamp": datetime.datetime.now().isoformat(),
            "metadata": {"key": "value"}
        }
    ]
    
    # Mock the DataFrame conversion and append operation
    with patch('src.finnhub_source.pd.DataFrame') as mock_df:
        # Call the method
        result = await mock_finnhub_source.write_to_market_events(events)
        
        # Verify success
        assert result is True
        
        # Check that DataFrame was created and written
        mock_df.assert_called_once()
        mock_finnhub_source.market_events_table.newAppend.assert_called_once()
        mock_finnhub_source.market_events_table.newAppend().__enter__().writeDF.assert_called_once()
        mock_finnhub_source.market_events_table.newAppend().__enter__().commit.assert_called_once()


# Tests for combined operations
@pytest.mark.asyncio
async def test_collect_data_for_ticker_success(mock_finnhub_source, mock_news_data, mock_earnings_data, mock_sentiment_data):
    """Test successful data collection for a ticker."""
    # Mock all the API responses
    mock_finnhub_source.get_company_news = AsyncMock(return_value=mock_news_data)
    mock_finnhub_source.get_company_earnings = AsyncMock(return_value=mock_earnings_data["earningsCalendar"])
    mock_finnhub_source.get_sentiment_data = AsyncMock(return_value={**mock_sentiment_data, "ticker": "AAPL"})
    
    # Mock the processing and writing methods
    events = [{"id": "123", "ticker": "AAPL", "event_type": "news", "title": "Test"}]
    mock_finnhub_source.process_news_to_events = AsyncMock(return_value=events)
    mock_finnhub_source.process_earnings_to_events = AsyncMock(return_value=[])
    
    records = [{"id": "456", "ticker": "AAPL", "text": "Test", "sentiment_score": 0.5}]
    mock_finnhub_source.process_sentiment_to_records = AsyncMock(return_value=records)
    
    mock_finnhub_source.write_to_market_events = AsyncMock(return_value=True)
    mock_finnhub_source.write_to_sentiment_records = AsyncMock(return_value=True)
    
    # Call the method
    success, counts = await mock_finnhub_source.collect_data_for_ticker("AAPL", historical_days=7)
    
    # Verify success
    assert success is True
    assert counts["news_items"] > 0
    assert counts["earnings_items"] > 0
    assert counts["sentiment_records"] > 0
    assert counts["market_events"] > 0
    
    # Verify all API methods were called
    mock_finnhub_source.get_company_news.assert_called_once()
    mock_finnhub_source.get_company_earnings.assert_called_once()
    mock_finnhub_source.get_sentiment_data.assert_called_once()
    
    # Verify processing methods were called
    mock_finnhub_source.process_news_to_events.assert_called_once()
    mock_finnhub_source.process_earnings_to_events.assert_called_once()
    mock_finnhub_source.process_sentiment_to_records.assert_called_once()
    
    # Verify write methods were called
    mock_finnhub_source.write_to_market_events.assert_called_once()
    mock_finnhub_source.write_to_sentiment_records.assert_called_once()


@pytest.mark.asyncio
async def test_collect_data_for_ticker_error(mock_finnhub_source):
    """Test error handling in data collection for a ticker."""
    # Make one of the API calls raise an exception
    mock_finnhub_source.get_company_news = AsyncMock(side_effect=Exception("API error"))
    
    # Call the method
    success, counts = await mock_finnhub_source.collect_data_for_ticker("AAPL")
    
    # Should handle the error and return False
    assert success is False
    assert all(count == 0 for count in counts.values())


@pytest.mark.asyncio
async def test_batch_collect_historical_data(mock_finnhub_source):
    """Test batch collection of historical data."""
    # Mock the collect_data_for_ticker method
    mock_finnhub_source.collect_data_for_ticker = AsyncMock()
    
    # Make it return success for first ticker, failure for second
    mock_finnhub_source.collect_data_for_ticker.side_effect = [
        (True, {"news_items": 10, "earnings_items": 4, "sentiment_records": 3, "market_events": 14}),
        (False, {"news_items": 0, "earnings_items": 0, "sentiment_records": 0, "market_events": 0}),
        (True, {"news_items": 5, "earnings_items": 2, "sentiment_records": 3, "market_events": 7})
    ]
    
    # Call the method with a small set of tickers
    result = await mock_finnhub_source.batch_collect_historical_data(
        tickers=["AAPL", "MSFT", "GOOGL"],
        days=30,
        batch_size=2
    )
    
    # Verify results
    assert result["success_count"] == 2
    assert result["failure_count"] == 1
    assert result["total_tickers"] == 3
    assert result["total_news"] == 15
    assert result["total_earnings"] == 6
    assert result["total_sentiment_records"] == 6
    assert result["total_market_events"] == 21
    
    # Verify collect_data_for_ticker was called for each ticker
    assert mock_finnhub_source.collect_data_for_ticker.call_count == 3


@pytest.mark.asyncio
async def test_real_time_update(mock_finnhub_source):
    """Test real-time data updates."""
    # Mock the batch_collect_historical_data method
    mock_finnhub_source.batch_collect_historical_data = AsyncMock(return_value={
        "success_count": 2,
        "failure_count": 0,
        "total_tickers": 2,
        "total_news": 10,
        "total_sentiment_records": 6,
        "total_earnings": 0,
        "total_market_events": 10
    })
    
    # Call the method
    result = await mock_finnhub_source.real_time_update(
        tickers=["AAPL", "MSFT"],
        lookback_hours=24
    )
    
    # Verify the batch collect method was called with the right parameters
    mock_finnhub_source.batch_collect_historical_data.assert_called_once()
    call_args = mock_finnhub_source.batch_collect_historical_data.call_args
    assert call_args[1]["tickers"] == ["AAPL", "MSFT"]
    assert call_args[1]["days"] == 1  # 24 hours = 1 day
    assert call_args[1]["batch_size"] == 10
    
    # Verify results were passed through
    assert result["success_count"] == 2
    assert result["total_news"] == 10


@pytest.mark.asyncio
async def test_handle_api_error(mock_finnhub_source):
    """Test API error handling."""
    # Create mock response with different status codes
    rate_limit_response = MagicMock()
    rate_limit_response.status_code = 429
    rate_limit_response.json.return_value = {"error": "Rate limit exceeded"}
    
    server_error_response = MagicMock()
    server_error_response.status_code = 500
    server_error_response.json.return_value = {"error": "Internal server error"}
    
    client_error_response = MagicMock()
    client_error_response.status_code = 400
    client_error_response.json.return_value = {"error": "Invalid request"}
    
    # Mock asyncio.sleep
    with patch('src.finnhub_source.asyncio.sleep') as mock_sleep:
        # Test rate limit error
        await mock_finnhub_source._handle_api_error(rate_limit_response, "AAPL", "test_endpoint")
        mock_sleep.assert_called_once()
        mock_sleep.reset_mock()
        
        # Test server error
        await mock_finnhub_source._handle_api_error(server_error_response, "AAPL", "test_endpoint")
        mock_sleep.assert_called_once()
        mock_sleep.reset_mock()
        
        # Test client error
        await mock_finnhub_source._handle_api_error(client_error_response, "AAPL", "test_endpoint")
        mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_search_company(mock_finnhub_source):
    """Test company search functionality."""
    # Mock response data
    search_results = {
        "count": 2,
        "result": [
            {
                "description": "APPLE INC",
                "displaySymbol": "AAPL",
                "symbol": "AAPL",
                "type": "Common Stock",
                "primaryExchange": "NASDAQ"
            },
            {
                "description": "APPLE HOSPITALITY REIT INC",
                "displaySymbol": "APLE",
                "symbol": "APLE",
                "type": "Common Stock",
                "primaryExchange": "NYSE"
            }
        ]
    }
    
    # Mock the response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = search_results
    
    # Set up the mock HTTP client
    mock_finnhub_source.async_client.get.return_value = mock_response
    
    # Call the method
    result = await mock_finnhub_source.search_company("apple")
    
    # Verify the API was called with correct parameters
    mock_finnhub_source.async_client.get.assert_called_once()
    call_args = mock_finnhub_source.async_client.get.call_args[0][0]
    assert call_args == "/search"
    
    # Verify parameters
    params = mock_finnhub_source.async_client.get.call_args[1]["params"]
    assert params["q"] == "apple"
    
    # Verify rate limiter was used
    mock_finnhub_source.rate_limiter.wait.assert_called_once()
    
    # Check the returned data
    assert len(result) == 2
    assert result[0]["symbol"] == "AAPL"
    assert result[1]["symbol"] == "APLE"


@pytest.mark.asyncio
async def test_initialize_iceberg_tables(mock_finnhub_source):
    """Test initialization of Iceberg tables."""
    # Mock get_table to simulate tables not existing yet
    with patch('src.finnhub_source.get_table', side_effect=[None, None]), \
         patch('src.finnhub_source.get_iceberg_catalog') as mock_get_catalog, \
         patch('src.iceberg_setup.create_sentiment_records_table') as mock_create_sentiment, \
         patch('src.iceberg_setup.create_market_events_table') as mock_create_market:
        
        # Reset the tables
        mock_finnhub_source.sentiment_table = None
        mock_finnhub_source.market_events_table = None
        
        # Call the initialization method
        mock_finnhub_source._initialize_iceberg_tables()
        
        # Verify catalog was fetched
        mock_get_catalog.assert_called_once()
        
        # Verify tables were created
        mock_create_sentiment.assert_called_once()
        mock_create_market.assert_called_once()


@pytest.mark.asyncio
async def test_close(mock_finnhub_source):
    """Test cleanup of resources."""
    # Mock the async client close method
    mock_finnhub_source.async_client.aclose = AsyncMock()
    
    # Call the close method
    await mock_finnhub_source.close()
    
    # Verify resources were closed
    mock_finnhub_source.async_client.aclose.assert_called_once()
    mock_finnhub_source.redis_client.close.assert_called_once()


def test_get_sentiment_label():
    """Test sentiment score to label conversion."""
    source = FinnhubDataSource()
    
    # Test different score ranges
    assert source._get_sentiment_label(0.1) == "very_negative"
    assert source._get_sentiment_label(0.3) == "negative"
    assert source._get_sentiment_label(0.5) == "neutral"
    assert source._get_sentiment_label(0.7) == "positive"
    assert source._get_sentiment_label(0.9) == "very_positive"
    
    # Test edge cases
    assert source._get_sentiment_label(0.0) == "very_negative"
    assert source._get_sentiment_label(0.2) == "very_negative"
    assert source._get_sentiment_label(0.4) == "negative"
    assert source._get_sentiment_label(0.6) == "neutral"
    assert source._get_sentiment_label(0.8) == "positive"
    assert source._get_sentiment_label(1.0) == "very_positive"