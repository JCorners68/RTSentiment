"""
Utility functions for calculating event weight.
"""
import logging
from typing import Dict, Any, List, Set, Optional

logger = logging.getLogger(__name__)

# Keywords that increase the weight of an event
HIGH_IMPACT_KEYWORDS = {
    "merger", "acquisition", "earnings", "beat expectations", "miss expectations",
    "scandal", "lawsuit", "sec investigation", "ceo", "resignation", "bankruptcy",
    "unexpected", "surprise", "breaking", "exclusive", "urgent", "alert",
    "crash", "surge", "plunge", "soar", "tumble", "layoffs", "restructuring"
}

# Ticker symbols of high-interest companies
HIGH_INTEREST_TICKERS = {
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "JPM", "V", "WMT",
    "JNJ", "PG", "XOM", "BAC", "DIS", "NFLX", "INTC", "VZ", "KO", "PEP"
}

def calculate_weight(event: Dict[str, Any]) -> float:
    """
    Calculate the weight of an event based on various factors.
    
    Args:
        event: Event data dictionary
        
    Returns:
        Weight score between 0.0 and 1.0
    """
    weight = 0.5  # Default middle weight
    
    # Adjust based on source
    source_type = event.get("source_type", "")
    if source_type == "subscription":
        weight += 0.1  # Subscription services generally more reliable
    
    source_name = event.get("source_name", "").lower()
    if "bloomberg" in source_name or "reuters" in source_name:
        weight += 0.1  # Premium news sources
    
    # Check for high-impact keywords in title and content
    keyword_count = 0
    title = event.get("title", "").lower()
    content = event.get("content", "").lower()
    
    for keyword in HIGH_IMPACT_KEYWORDS:
        if keyword in title:
            keyword_count += 2  # Keywords in title are more important
        elif keyword in content:
            keyword_count += 1
    
    # Adjust weight based on keyword count
    if keyword_count > 5:
        weight += 0.2
    elif keyword_count > 2:
        weight += 0.1
    elif keyword_count > 0:
        weight += 0.05
    
    # Check for high-interest tickers
    tickers = event.get("tickers", [])
    high_interest_count = len(set(tickers) & HIGH_INTEREST_TICKERS)
    
    if high_interest_count > 3:
        weight += 0.15
    elif high_interest_count > 0:
        weight += 0.05 * high_interest_count
    
    # Social media engagement
    engagement = event.get("engagement", {})
    likes = engagement.get("likes", 0)
    comments = engagement.get("comments", 0)
    shares = engagement.get("shares", 0)
    
    engagement_score = (likes + comments * 2 + shares * 3) / 100.0
    weight += min(0.2, engagement_score)  # Cap at 0.2
    
    # Ensure weight is between 0.0 and 1.0
    weight = max(0.0, min(1.0, weight))
    
    return weight