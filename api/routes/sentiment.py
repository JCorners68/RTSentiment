from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, List, Optional
import json

try:
    # When running in the Docker container
    from services.sentiment_service import SentimentService
    from services.auth_service import get_current_user
    from models.sentiment import TickerSentiment, SentimentResponse
    from models.users import User, UserSubscription
except ImportError:
    # When running directly or with relative imports
    from api.services.sentiment_service import SentimentService
    from api.services.auth_service import get_current_user
    from api.models.sentiment import TickerSentiment, SentimentResponse
    from api.models.users import User, UserSubscription

router = APIRouter()
sentiment_service = SentimentService()

@router.get("/ticker/{ticker}", response_model=TickerSentiment)
async def get_ticker_sentiment(
    ticker: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get sentiment for a specific ticker.
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        TickerSentiment: Sentiment data for the ticker
    """
    # Check subscription for premium features
    if current_user.subscription_tier == UserSubscription.FREE and ticker not in ["AAPL", "MSFT", "GOOGL", "AMZN", "FB"]:
        raise HTTPException(
            status_code=403,
            detail="Free tier is limited to major tech tickers. Upgrade to access all tickers."
        )
    
    # Get sentiment data
    sentiment = await sentiment_service.get_ticker_sentiment(ticker)
    if not sentiment:
        raise HTTPException(
            status_code=404,
            detail=f"No sentiment data found for ticker {ticker}"
        )
    
    return sentiment

@router.get("/tickers", response_model=List[str])
async def get_available_tickers(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available tickers.
    
    Returns:
        List[str]: List of ticker symbols
    """
    tickers = await sentiment_service.get_all_tickers()
    
    # Filter tickers based on subscription tier
    if current_user.subscription_tier == UserSubscription.FREE:
        # Only return major tech tickers for free tier
        free_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "FB"]
        tickers = [ticker for ticker in tickers if ticker in free_tickers]
    
    return tickers

@router.get("/top", response_model=List[TickerSentiment])
async def get_top_sentiment(
    limit: int = Query(10, ge=1, le=50),
    min_score: Optional[float] = Query(None, ge=-1.0, le=1.0),
    max_score: Optional[float] = Query(None, ge=-1.0, le=1.0),
    sort_by: str = Query("score", regex="^(score|weight|count)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user)
):
    """
    Get top tickers by sentiment score.
    
    Args:
        limit (int): Number of tickers to return
        min_score (float): Minimum sentiment score
        max_score (float): Maximum sentiment score
        sort_by (str): Field to sort by
        order (str): Sort order
        
    Returns:
        List[TickerSentiment]: List of ticker sentiment data
    """
    # Limit the number of results based on subscription tier
    if current_user.subscription_tier == UserSubscription.FREE:
        limit = min(limit, 5)
    elif current_user.subscription_tier == UserSubscription.BASIC:
        limit = min(limit, 20)
    
    # Get sentiment data
    sentiment_data = await sentiment_service.get_top_sentiment(
        limit=limit,
        min_score=min_score,
        max_score=max_score,
        sort_by=sort_by,
        order=order
    )
    
    # Filter tickers based on subscription tier
    if current_user.subscription_tier == UserSubscription.FREE:
        # Only return major tech tickers for free tier
        free_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "FB"]
        sentiment_data = [s for s in sentiment_data if s.ticker in free_tickers]
    
    return sentiment_data

@router.post("/analyze", response_model=SentimentResponse)
async def analyze_text_sentiment(
    text: str,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze sentiment of custom text.
    
    Args:
        text (str): Text to analyze
        
    Returns:
        SentimentResponse: Sentiment analysis result
    """
    # Check if user has access to custom analysis
    if current_user.subscription_tier == UserSubscription.FREE:
        raise HTTPException(
            status_code=403,
            detail="Custom sentiment analysis is only available in premium tiers. Please upgrade."
        )
    
    # Analyze sentiment
    result = await sentiment_service.analyze_text_sentiment(text)
    
    return result