"""
Sentiment Analyzer Module

This module provides financial sentiment analysis functionality using FinBERT.
"""

import logging
import os
import sys
import torch
import warnings
from typing import Dict, Any, List, Optional, Union, Tuple
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
MODEL_NAME = "ProsusAI/finbert"
MODEL_CACHE_DIR = "/home/jonat/real_senti/data/models/finbert"
SENTIMENT_LABELS = ["negative", "neutral", "positive"]

# Environment variables
USE_CUDA = os.environ.get("USE_CUDA", "auto").lower()  # "auto", "yes", "no"
CUDA_DEVICE = os.environ.get("CUDA_DEVICE", "0")  # Default to first GPU

# Global variables
tokenizer = None
model = None
sentiment_pipeline = None


def check_cuda_compatibility() -> Tuple[bool, str]:
    """
    Check if CUDA is available and compatible with the installed PyTorch.
    
    Returns:
        Tuple[bool, str]: (is_compatible, reason)
            - is_compatible: True if CUDA is available and compatible
            - reason: Description of compatibility status
    """
    if not torch.cuda.is_available():
        return False, "CUDA is not available on this system"
    
    try:
        # Check CUDA device
        cuda_device = torch.cuda.current_device()
        device_name = torch.cuda.get_device_name(cuda_device)
        capability = torch.cuda.get_device_capability(cuda_device)
        cuda_version = torch.version.cuda
        
        # Convert capability to sm_XX format
        sm_capability = f"sm_{capability[0]}{capability[1]}"
        
        # Simplified compatibility check - this might need adjustments for different PyTorch versions
        if capability[0] > 9:  # SM 10.x and above likely not supported by current PyTorch
            return False, f"GPU {device_name} with capability {sm_capability} is newer than what PyTorch supports (built for sm_50 to sm_90)"
        
        # Test a simple CUDA operation
        try:
            x = torch.tensor([1.0, 2.0, 3.0, 4.0], device='cuda')
            y = x * 2
            del x, y
            return True, f"CUDA is compatible: {device_name} ({sm_capability}), CUDA version {cuda_version}"
        except Exception as e:
            return False, f"CUDA operation failed: {str(e)}"
            
    except Exception as e:
        return False, f"Error checking CUDA compatibility: {str(e)}"


def initialize_model() -> bool:
    """
    Initialize the FinBERT model for sentiment analysis.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    global tokenizer, model, sentiment_pipeline
    
    try:
        logger.info(f"Initializing FinBERT model from {MODEL_NAME}")
        
        # Ensure cache directory exists
        os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
        
        # Determine device to use
        device = "cpu"
        device_idx = -1  # -1 means CPU for pipeline
        
        # Check if we should try to use CUDA
        if USE_CUDA in ("auto", "yes", "true", "1"):
            cuda_compatible, reason = check_cuda_compatibility()
            
            if cuda_compatible and USE_CUDA != "auto":
                # User explicitly wants CUDA, so use it
                device = "cuda"
                device_idx = int(CUDA_DEVICE)
                logger.info(f"Using GPU (CUDA device {device_idx}): {torch.cuda.get_device_name(device_idx)}")
            elif cuda_compatible:
                # Auto mode and compatible
                device = "cuda"
                device_idx = int(CUDA_DEVICE)
                logger.info(f"Automatically selected GPU: {torch.cuda.get_device_name(device_idx)}")
            else:
                # Not compatible, fall back to CPU
                if USE_CUDA != "auto":
                    logger.warning(f"Cannot use CUDA (explicitly requested): {reason}")
                else:
                    logger.info(f"Using CPU for model inference: {reason}")
        else:
            logger.info("Using CPU for model inference (CUDA disabled)")
        
        # Load tokenizer and model
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, cache_dir=MODEL_CACHE_DIR)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, cache_dir=MODEL_CACHE_DIR)
        
        # Move model to appropriate device
        model.to(device)
        
        # Create the sentiment analysis pipeline
        sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model=model,
            tokenizer=tokenizer,
            device=device_idx
        )
        
        logger.info(f"FinBERT model initialized successfully on {device}")
        return True
    
    except Exception as e:
        logger.error(f"Error initializing FinBERT model: {e}")
        return False


def analyze_sentiment(text: str) -> Tuple[str, float, float]:
    """
    Analyze the sentiment of a given text.
    
    Args:
        text: The text to analyze
        
    Returns:
        Tuple of (sentiment_label, sentiment_score, confidence)
        - sentiment_label: "positive", "negative", or "neutral"
        - sentiment_score: A value between -1.0 and 1.0 where -1.0 is negative, 
                          0.0 is neutral, and 1.0 is positive
        - confidence: A value between 0.0 and 1.0 indicating confidence in the prediction
    """
    global sentiment_pipeline
    
    # Initialize model if not already done
    if sentiment_pipeline is None:
        if not initialize_model():
            logger.error("Failed to initialize sentiment model")
            return ("neutral", 0.0, 0.0)
    
    try:
        # Ensure text is not None and is a string
        if not text or not isinstance(text, str):
            logger.warning("Invalid text provided for sentiment analysis")
            return ("neutral", 0.0, 0.0)
        
        # Truncate text if too long to avoid excessive processing time
        if len(text) > 1024:
            logger.debug(f"Truncating text from {len(text)} to 1024 characters")
            text = text[:1024]
        
        # Get sentiment prediction
        result = sentiment_pipeline(text)[0]
        
        # Extract label and score
        label = result["label"].lower()
        confidence = float(result["score"])
        
        # Calculate sentiment score (-1 to 1 scale)
        sentiment_score = 0.0
        if label == "positive":
            sentiment_score = confidence
        elif label == "negative":
            sentiment_score = -confidence
        
        logger.debug(f"Sentiment: {label}, Score: {sentiment_score:.4f}, Confidence: {confidence:.4f}")
        return (label, sentiment_score, confidence)
    
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return ("neutral", 0.0, 0.0)


def analyze_news_batch(news_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyze sentiment for a batch of news items.
    
    Args:
        news_items: List of news item dictionaries
        
    Returns:
        List of news items with added sentiment information
    """
    # Initialize model first
    if sentiment_pipeline is None:
        initialize_model()
    
    results = []
    
    for item in news_items:
        try:
            # Use headline for sentiment analysis, fallback to summary
            text = item.get("headline", "")
            if not text:
                text = item.get("summary", "")
            
            if not text:
                logger.warning(f"No text found for sentiment analysis in item {item.get('id')}")
                # Add neutral sentiment if no text is available
                item["sentiment_label"] = "neutral"
                item["sentiment_score"] = 0.0
                item["sentiment_confidence"] = 0.0
                results.append(item)
                continue
            
            # Analyze sentiment
            label, score, confidence = analyze_sentiment(text)
            
            # Add sentiment to item
            item["sentiment_label"] = label
            item["sentiment_score"] = score
            item["sentiment_confidence"] = confidence
            
            results.append(item)
            
        except Exception as e:
            logger.error(f"Error processing news item {item.get('id')}: {e}")
            item["sentiment_label"] = "neutral"
            item["sentiment_score"] = 0.0
            item["sentiment_confidence"] = 0.0
            results.append(item)
    
    return results


if __name__ == "__main__":
    # Test the sentiment analyzer with a sample text
    initialize_model()
    sample_text = "The company reported strong earnings, exceeding analysts' expectations."
    label, score, confidence = analyze_sentiment(sample_text)
    print(f"Text: '{sample_text}'")
    print(f"Sentiment: {label}, Score: {score:.4f}, Confidence: {confidence:.4f}")