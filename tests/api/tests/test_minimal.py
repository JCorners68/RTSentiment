import pytest
import json

def test_sentiment_score_calculation():
    """Test a simple sentiment score calculation function."""
    
    def calculate_sentiment_score(positive: float, negative: float, neutral: float):
        """
        Calculate a normalized sentiment score between -1 and 1.
        
        Args:
            positive: Positive sentiment probability (0-1)
            negative: Negative sentiment probability (0-1)
            neutral: Neutral sentiment probability (0-1)
            
        Returns:
            float: Normalized sentiment score between -1 and 1
        """
        # Ensure probabilities sum to 1
        total = positive + negative + neutral
        positive = positive / total
        negative = negative / total
        neutral = neutral / total
        
        # Calculate score between -1 and 1
        score = positive - negative
        
        # Apply neutral dampening (high neutral reduces the absolute score)
        dampening = 1 - (neutral * 0.5)
        return score * dampening
    
    # Test cases
    test_cases = [
        # positive, negative, neutral, expected score
        (0.8, 0.1, 0.1, 0.665),  # Strong positive
        (0.1, 0.8, 0.1, -0.665),  # Strong negative
        (0.3, 0.3, 0.4, 0.0),     # Balanced with high neutral
        (0.5, 0.5, 0.0, 0.0),     # Perfectly balanced
        (0.4, 0.3, 0.3, 0.085),   # Slightly positive
        (0.0, 0.0, 1.0, 0.0),     # Completely neutral
    ]
    
    for positive, negative, neutral, expected in test_cases:
        score = calculate_sentiment_score(positive, negative, neutral)
        assert abs(score - expected) < 0.001, f"Calculation error for ({positive}, {negative}, {neutral})"

def test_sentiment_data_structure():
    """Test the structure of sentiment data JSON."""
    
    # Example sentiment result
    sentiment_data = {
        "ticker": "AAPL",
        "sentiment": "positive",
        "score": 0.75,
        "confidence": 0.85,
        "source_count": 120,
        "timestamp": "2024-04-21T12:00:00"
    }
    
    # Convert to JSON and back
    json_str = json.dumps(sentiment_data)
    parsed_data = json.loads(json_str)
    
    # Verify structure is preserved
    assert parsed_data["ticker"] == "AAPL"
    assert parsed_data["sentiment"] == "positive"
    assert parsed_data["score"] == 0.75
    assert parsed_data["source_count"] == 120