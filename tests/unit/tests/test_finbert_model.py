import pytest
import os
import sys

# Add the parent directory to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sentiment_service.models.finbert import FinBertModel

@pytest.mark.asyncio
async def test_finbert_model_initialization():
    """Test that the FinBERT model can be initialized."""
    model = FinBertModel(use_onnx=False)
    assert model is not None
    assert model.is_loaded is False

@pytest.mark.asyncio
async def test_finbert_sentiment_prediction():
    """
    Test the FinBERT model's sentiment prediction functionality.
    
    This test uses mock data and doesn't actually load the model
    to avoid heavy resource usage during testing.
    """
    model = FinBertModel(use_onnx=False)
    
    # Mock the model loading and prediction
    model.model = "mocked_model"
    model.tokenizer = "mocked_tokenizer"
    model.is_loaded = True
    
    # Mock the predict method
    async def mock_predict(text):
        if "positive" in text.lower():
            return {"positive": 0.8, "negative": 0.1, "neutral": 0.1}
        elif "negative" in text.lower():
            return {"positive": 0.1, "negative": 0.8, "neutral": 0.1}
        else:
            return {"positive": 0.2, "negative": 0.2, "neutral": 0.6}
    
    model._predict = mock_predict
    
    # Test with different texts
    positive_text = "Earnings exceeded expectations, positive outlook."
    negative_text = "Company reported losses, negative growth."
    neutral_text = "The company released its quarterly report."
    
    # Test predictions
    positive_result = await model.analyze(positive_text)
    negative_result = await model.analyze(negative_text)
    neutral_result = await model.analyze(neutral_text)
    
    # Assert results
    assert positive_result["sentiment"] == "positive"
    assert positive_result["score"] > 0.5
    
    assert negative_result["sentiment"] == "negative"
    assert negative_result["score"] < -0.5
    
    assert neutral_result["sentiment"] == "neutral"
    assert -0.5 <= neutral_result["score"] <= 0.5