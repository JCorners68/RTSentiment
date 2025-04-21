import pytest
import os
import sys
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Add the parent directory to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from api.main import app

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