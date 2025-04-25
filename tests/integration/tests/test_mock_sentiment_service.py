import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

class MockFinBertModel:
    """Mock implementation of the FinBERT model for testing."""
    
    def __init__(self):
        self.is_loaded = True
        
    async def analyze(self, text):
        """Mock analysis that returns sentiment based on text content."""
        if "positive" in text.lower() or "growth" in text.lower() or "exceed" in text.lower():
            sentiment = "positive"
            score = 0.7
        elif "negative" in text.lower() or "below" in text.lower() or "loss" in text.lower():
            sentiment = "negative"
            score = -0.7
        else:
            sentiment = "neutral"
            score = 0.0
            
        return {
            "text": text,
            "sentiment": sentiment,
            "score": score,
            "confidence": 0.85,
            "entities": self._extract_entities(text)
        }
    
    def _extract_entities(self, text):
        """Extract ticker entities from text."""
        entities = []
        
        # Simple entity extraction based on common ticker mentions
        tickers = {
            "AAPL": ["Apple", "iPhone", "iPad", "MacBook"],
            "MSFT": ["Microsoft", "Windows", "Azure", "Teams"],
            "GOOGL": ["Google", "Alphabet", "Android", "Chrome"],
            "AMZN": ["Amazon", "AWS", "Bezos"],
            "TSLA": ["Tesla", "Musk", "EV", "electric vehicle"]
        }
        
        for ticker, keywords in tickers.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    sentiment = "positive" if "positive" in text.lower() else "negative" if "negative" in text.lower() else "neutral"
                    entities.append({
                        "name": keyword,
                        "ticker": ticker,
                        "sentiment": sentiment,
                        "score": 0.7 if sentiment == "positive" else -0.7 if sentiment == "negative" else 0.0
                    })
                    break
                    
        return entities

class MockRedisClient:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self.is_connected = True
        self.cache = {}
        
    async def get(self, key):
        """Get a value from the mock cache."""
        return self.cache.get(key)
        
    async def set(self, key, value, expiration=None):
        """Set a value in the mock cache."""
        self.cache[key] = value
        
    async def close(self):
        """Close the mock connection."""
        self.is_connected = False

class MockSentimentService:
    """Mock sentiment service for testing."""
    
    def __init__(self):
        self.model = MockFinBertModel()
        self.redis = MockRedisClient()
        self.ticker_sentiment = {
            "AAPL": {"ticker": "AAPL", "sentiment": "positive", "score": 0.75, "confidence": 0.85, "source_count": 120, "timestamp": datetime.now().isoformat()},
            "MSFT": {"ticker": "MSFT", "sentiment": "positive", "score": 0.65, "confidence": 0.82, "source_count": 95, "timestamp": datetime.now().isoformat()},
            "GOOGL": {"ticker": "GOOGL", "sentiment": "neutral", "score": 0.15, "confidence": 0.78, "source_count": 105, "timestamp": datetime.now().isoformat()},
            "AMZN": {"ticker": "AMZN", "sentiment": "positive", "score": 0.55, "confidence": 0.75, "source_count": 88, "timestamp": datetime.now().isoformat()},
            "TSLA": {"ticker": "TSLA", "sentiment": "negative", "score": -0.45, "confidence": 0.80, "source_count": 150, "timestamp": datetime.now().isoformat()}
        }
    
    async def get_ticker_sentiment(self, ticker):
        """Get sentiment for a specific ticker."""
        return self.ticker_sentiment.get(ticker)
    
    async def get_all_tickers(self):
        """Get all available tickers."""
        return list(self.ticker_sentiment.keys())
    
    async def get_top_sentiment(self, limit=10, min_score=None, max_score=None, sort_by="score", order="desc"):
        """Get top tickers by sentiment score."""
        results = list(self.ticker_sentiment.values())
        
        # Apply filters
        if min_score is not None:
            results = [r for r in results if r["score"] >= min_score]
        if max_score is not None:
            results = [r for r in results if r["score"] <= max_score]
            
        # Sort results
        reverse = order.lower() == "desc"
        results.sort(key=lambda x: x[sort_by], reverse=reverse)
        
        # Apply limit
        return results[:limit]
    
    async def analyze_text_sentiment(self, text):
        """Analyze sentiment of custom text."""
        return await self.model.analyze(text)

@pytest.mark.asyncio
async def test_get_ticker_sentiment():
    """Test getting sentiment for a specific ticker."""
    service = MockSentimentService()
    
    # Test existing ticker
    apple_sentiment = await service.get_ticker_sentiment("AAPL")
    assert apple_sentiment is not None
    assert apple_sentiment["ticker"] == "AAPL"
    assert apple_sentiment["sentiment"] == "positive"
    assert apple_sentiment["score"] > 0
    
    # Test non-existent ticker
    unknown_sentiment = await service.get_ticker_sentiment("UNKNOWN")
    assert unknown_sentiment is None

@pytest.mark.asyncio
async def test_get_top_sentiment():
    """Test getting top sentiment tickers."""
    service = MockSentimentService()
    
    # Get top 3 tickers, sorted by score in descending order
    top_sentiment = await service.get_top_sentiment(limit=3, sort_by="score", order="desc")
    assert len(top_sentiment) == 3
    
    # Verify sorting (descending)
    for i in range(len(top_sentiment) - 1):
        assert top_sentiment[i]["score"] >= top_sentiment[i + 1]["score"]
    
    # Get top 3 tickers with positive sentiment
    positive_sentiment = await service.get_top_sentiment(limit=3, min_score=0.0)
    assert all(item["score"] >= 0.0 for item in positive_sentiment)
    
    # Get top 3 tickers with negative sentiment
    negative_sentiment = await service.get_top_sentiment(limit=3, max_score=0.0, order="asc")
    assert all(item["score"] <= 0.0 for item in negative_sentiment)

@pytest.mark.asyncio
async def test_analyze_text_sentiment():
    """Test analyzing custom text sentiment."""
    service = MockSentimentService()
    
    # Test positive sentiment
    positive_text = "Apple's latest iPhone sales exceeded expectations, showing strong growth."
    positive_result = await service.analyze_text_sentiment(positive_text)
    assert positive_result["sentiment"] == "positive"
    assert positive_result["score"] > 0
    assert "AAPL" in [entity["ticker"] for entity in positive_result["entities"]]
    
    # Test negative sentiment
    negative_text = "Microsoft's Azure revenue was below expectations, causing a significant loss."
    negative_result = await service.analyze_text_sentiment(negative_text)
    assert negative_result["sentiment"] == "negative"
    assert negative_result["score"] < 0
    assert "MSFT" in [entity["ticker"] for entity in negative_result["entities"]]
    
    # Test neutral sentiment
    neutral_text = "Amazon announced new features for its AWS services today."
    neutral_result = await service.analyze_text_sentiment(neutral_text)
    assert neutral_result["entities"]
    assert "AMZN" in [entity["ticker"] for entity in neutral_result["entities"]]