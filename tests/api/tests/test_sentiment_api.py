import pytest
import os
import sys
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, mock_open
import json

# Add the parent directory to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.main import app
from api.routes.stats import MessageStatsResponse, MessageCategoryStats

# Create test client
client = TestClient(app)

# Mock user for authentication
mock_user = {
    "id": "test-user-id",
    "username": "testuser",
    "email": "test@example.com",
    "subscription_tier": "PROFESSIONAL"
}

@pytest.fixture
def mock_auth():
    """Mock authentication to bypass auth requirements in tests."""
    with patch("api.services.auth_service.get_current_user") as mock:
        mock.return_value = MagicMock(**mock_user)
        yield mock

@pytest.fixture
def mock_sentiment_service():
    """Mock the sentiment service to avoid actual API calls."""
    with patch("api.services.sentiment_service.SentimentService") as mock:
        instance = mock.return_value
        
        # Mock the get_ticker_sentiment method
        instance.get_ticker_sentiment.return_value = {
            "ticker": "AAPL",
            "sentiment": "positive",
            "score": 0.75,
            "confidence": 0.85,
            "source_count": 120,
            "timestamp": "2024-04-21T12:00:00"
        }
        
        # Mock the get_all_tickers method
        instance.get_all_tickers.return_value = ["AAPL", "MSFT", "GOOGL", "AMZN", "FB"]
        
        # Mock the get_top_sentiment method
        instance.get_top_sentiment.return_value = [
            {
                "ticker": "AAPL",
                "sentiment": "positive",
                "score": 0.75,
                "confidence": 0.85,
                "source_count": 120,
                "timestamp": "2024-04-21T12:00:00"
            },
            {
                "ticker": "MSFT",
                "sentiment": "positive",
                "score": 0.68,
                "confidence": 0.82,
                "source_count": 95,
                "timestamp": "2024-04-21T12:00:00"
            }
        ]
        
        # Mock the analyze_text_sentiment method
        instance.analyze_text_sentiment.return_value = {
            "text": "Apple's latest quarterly results exceeded expectations.",
            "sentiment": "positive",
            "score": 0.65,
            "confidence": 0.78,
            "entities": [
                {"name": "Apple", "ticker": "AAPL", "sentiment": "positive", "score": 0.7}
            ]
        }
        
        yield instance

@pytest.fixture
def mock_db_session():
    """Mock database session for testing API endpoints that use context manager."""
    with patch("api.routes.stats.get_db") as mock_get_db:
        # Create mock session
        mock_session = MagicMock()
        
        # Setup mock query results for statistics
        mock_high_count_query = MagicMock()
        mock_high_count_query.scalar.return_value = 250
        
        mock_high_avg_time_query = MagicMock()
        mock_high_avg_time_query.scalar.return_value = 0.045
        
        mock_std_count_query = MagicMock()
        mock_std_count_query.scalar.return_value = 750
        
        mock_std_avg_time_query = MagicMock()
        mock_std_avg_time_query.scalar.return_value = 0.12
        
        mock_sent_count_query = MagicMock()
        mock_sent_count_query.scalar.return_value = 1000
        
        mock_sent_avg_time_query = MagicMock()
        mock_sent_avg_time_query.scalar.return_value = 0.085
        
        # Setup mock query results for metadata
        mock_sources_query = MagicMock()
        mock_sources_query.all.return_value = [("news",), ("reddit",), ("twitter",)]
        
        mock_models_query = MagicMock()
        mock_models_query.all.return_value = [("finbert",), ("fingpt",), ("llama4_scout",)]
        
        mock_priorities_query = MagicMock()
        mock_priorities_query.all.return_value = [("high",), ("standard",)]
        
        # Configure mock session to return appropriate values for different queries
        mock_session.query.side_effect = lambda *args, **kwargs: {
            # Stats endpoint queries
            "high_count": mock_high_count_query,
            "high_avg_time": mock_high_avg_time_query,
            "std_count": mock_std_count_query, 
            "std_avg_time": mock_std_avg_time_query,
            "sent_count": mock_sent_count_query,
            "sent_avg_time": mock_sent_avg_time_query,
            # Metadata endpoint queries
            "sources": mock_sources_query,
            "models": mock_models_query,
            "priorities": mock_priorities_query
        }.get(args[0].__name__, MagicMock())
        
        # Configure context manager behavior
        mock_get_db.return_value.__enter__.return_value = mock_session
        mock_get_db.return_value.__exit__.return_value = None
        
        yield mock_session

def test_get_ticker_sentiment(mock_auth, mock_sentiment_service):
    """Test getting sentiment for a specific ticker."""
    response = client.get("/sentiment/ticker/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert data["sentiment"] == "positive"
    assert data["score"] == 0.75

def test_get_available_tickers(mock_auth, mock_sentiment_service):
    """Test getting list of available tickers."""
    response = client.get("/sentiment/tickers")
    assert response.status_code == 200
    data = response.json()
    assert "AAPL" in data
    assert len(data) == 5

def test_get_top_sentiment(mock_auth, mock_sentiment_service):
    """Test getting top sentiment tickers."""
    response = client.get("/sentiment/top?limit=2&sort_by=score&order=desc")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["ticker"] == "AAPL"
    assert data[0]["score"] > data[1]["score"]

def test_analyze_text_sentiment(mock_auth, mock_sentiment_service):
    """Test custom text sentiment analysis."""
    text = "Apple's latest quarterly results exceeded expectations."
    response = client.post("/sentiment/analyze", params={"text": text})
    assert response.status_code == 200
    data = response.json()
    assert data["text"] == text
    assert data["sentiment"] == "positive"
    assert data["entities"][0]["ticker"] == "AAPL"

def test_get_sentiment_stats(mock_db_session):
    """Test getting system statistics."""
    # Setup test data with patch
    with patch("api.routes.stats.SentimentEvent"):
        response = client.get("/sentiment/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Verify the response structure
        assert "high_priority" in data
        assert "standard_priority" in data
        assert "sentiment_results" in data
        
        # Verify high priority stats
        assert data["high_priority"]["count"] == 250
        assert data["high_priority"]["average_processing_time"] == 0.045
        assert data["high_priority"]["messages_per_minute"] > 0
        
        # Verify standard priority stats
        assert data["standard_priority"]["count"] == 750
        assert data["standard_priority"]["average_processing_time"] == 0.12
        
        # Verify sentiment results stats
        assert data["sentiment_results"]["count"] == 1000
        assert data["sentiment_results"]["average_processing_time"] == 0.085

def test_get_metadata(mock_db_session):
    """Test getting metadata for UI filtering."""
    # Setup test data with patch
    with patch("api.routes.stats.SentimentEvent"):
        response = client.get("/sentiment/metadata")
        assert response.status_code == 200
        data = response.json()
        
        # Verify the response structure
        assert "sources" in data
        assert "models" in data
        assert "priorities" in data
        
        # Verify sources
        assert "news" in data["sources"]
        assert "reddit" in data["sources"]
        assert "twitter" in data["sources"]
        assert len(data["sources"]) == 3
        
        # Verify models
        assert "finbert" in data["models"]
        assert "fingpt" in data["models"]
        assert "llama4_scout" in data["models"]
        assert len(data["models"]) == 3
        
        # Verify priorities
        assert "high" in data["priorities"]
        assert "standard" in data["priorities"]
        assert len(data["priorities"]) == 2

def test_query_sentiment_events():
    """Test querying sentiment events with various filters."""
    # Mock response data
    mock_events = [
        {
            "id": 1,
            "event_id": "event-123",
            "timestamp": "2024-04-23T15:30:00",
            "source": "news",
            "priority": "high",
            "model": "finbert",
            "sentiment_score": 0.85,
            "sentiment_label": "positive"
        },
        {
            "id": 2,
            "event_id": "event-456",
            "timestamp": "2024-04-23T14:45:00",
            "source": "reddit",
            "priority": "standard",
            "model": "fingpt",
            "sentiment_score": -0.42,
            "sentiment_label": "negative"
        }
    ]
    
    # Create request body
    query_params = {
        "sources": ["news", "reddit"],
        "limit": 10
    }
    
    # Mock the database query
    with patch("api.routes.sentiment.query_sentiment_data", return_value=mock_events):
        response = client.post("/sentiment/query", json=query_params)
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert len(data) == 2
        assert data[0]["source"] == "news"
        assert data[0]["sentiment_score"] == 0.85
        assert data[0]["sentiment_label"] == "positive"
        assert data[1]["source"] == "reddit"
        assert data[1]["sentiment_score"] == -0.42
        assert data[1]["sentiment_label"] == "negative"

def test_create_sentiment_event():
    """Test creating a new sentiment event."""
    # Create request data
    event_data = {
        "source": "test",
        "priority": "high",
        "text": "Apple reported strong quarterly results",
        "model": "finbert",
        "sentiment_score": 0.78,
        "sentiment_label": "positive",
        "processing_time": 0.05,
        "event_id": "test-event-123",
        "ticker_sentiments": [{"AAPL": 0.78}]
    }
    
    # Mock database session with patch
    with patch("api.routes.sentiment.SentimentEvent") as MockSentimentEvent:
        mock_event = MagicMock()
        mock_event.id = 1
        mock_event.event_id = event_data["event_id"]
        mock_event.timestamp = "2024-04-23T16:00:00"
        mock_event.source = event_data["source"]
        mock_event.priority = event_data["priority"]
        mock_event.model = event_data["model"]
        mock_event.sentiment_score = event_data["sentiment_score"]
        mock_event.sentiment_label = event_data["sentiment_label"]
        
        MockSentimentEvent.return_value = mock_event
        
        with patch("api.routes.sentiment.get_db"):
            with patch("api.routes.sentiment.DBTickerSentiment"):
                response = client.post("/sentiment/event", json=event_data)
                assert response.status_code == 200
                data = response.json()
                
                # Verify response structure
                assert data["id"] == 1
                assert data["event_id"] == event_data["event_id"]
                assert data["source"] == event_data["source"]
                assert data["priority"] == event_data["priority"]
                assert data["model"] == event_data["model"]
                assert data["sentiment_score"] == event_data["sentiment_score"]
                assert data["sentiment_label"] == event_data["sentiment_label"]