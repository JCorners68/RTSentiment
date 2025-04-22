from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import Dict, List, Optional
from pydantic import BaseModel
import datetime
import uuid
from database import get_db, SentimentEvent, TickerSentiment as DBTickerSentiment

# Pydantic models
class TickerSentiment(BaseModel):
    ticker: str
    sentiment: str
    score: float
    weight: float = 1.0
    count: int = 1
    model: str

class SentimentResponse(BaseModel):
    sentiment: str
    score: float
    tickers: List[str]
    model: str

class EventRequest(BaseModel):
    source: str
    priority: str
    text: str
    model: str
    sentiment_score: float
    sentiment_label: str
    processing_time: float
    event_id: Optional[str] = None
    ticker_sentiments: List[Dict[str, float]] = []

class EventResponse(BaseModel):
    id: int
    event_id: str
    timestamp: datetime.datetime
    source: str
    priority: str
    model: str
    sentiment_score: float
    sentiment_label: str

class QueryParams(BaseModel):
    start_date: Optional[datetime.datetime] = None
    end_date: Optional[datetime.datetime] = None
    sources: Optional[List[str]] = None
    priority: Optional[List[str]] = None
    models: Optional[List[str]] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    tickers: Optional[List[str]] = None
    limit: int = 100
    offset: int = 0

# Mock sentiment service
class SentimentService:
    async def analyze_text(self, text, tickers=None):
        if not tickers:
            tickers = ["AAPL", "MSFT"]
        return {
            "sentiment": "positive",
            "score": 0.85,
            "tickers": tickers,
            "model": "finbert"
        }
        
    async def get_ticker_sentiment(self, ticker, db: Session):
        # Real DB query instead of mock data
        result = db.query(
            DBTickerSentiment.ticker,
            func.avg(DBTickerSentiment.sentiment_score).label("score"),
            func.count().label("count")
        ).filter(
            DBTickerSentiment.ticker == ticker
        ).group_by(
            DBTickerSentiment.ticker
        ).first()
        
        if not result:
            return {
                "ticker": ticker,
                "sentiment": "neutral",
                "score": 0.0,
                "weight": 1.0,
                "count": 0,
                "model": "aggregate"
            }
            
        sentiment_label = "positive" if result.score > 0 else "negative" if result.score < 0 else "neutral"
        
        return {
            "ticker": ticker,
            "sentiment": sentiment_label,
            "score": result.score,
            "weight": 1.0,
            "count": result.count,
            "model": "aggregate"
        }
        
    async def get_all_tickers(self, db: Session):
        # Get distinct tickers from database
        results = db.query(DBTickerSentiment.ticker).distinct().all()
        return [result[0] for result in results] or ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]
        
    async def get_top_sentiment(self, db: Session, limit=10, min_score=None, max_score=None, sort_by="score", order="desc"):
        # Build the query
        query = db.query(
            DBTickerSentiment.ticker,
            func.avg(DBTickerSentiment.sentiment_score).label("score"),
            func.count().label("count")
        ).group_by(
            DBTickerSentiment.ticker
        )
        
        # Apply filters
        if min_score is not None:
            query = query.having(func.avg(DBTickerSentiment.sentiment_score) >= min_score)
        if max_score is not None:
            query = query.having(func.avg(DBTickerSentiment.sentiment_score) <= max_score)
            
        # Apply sorting
        if sort_by == "score":
            sort_column = func.avg(DBTickerSentiment.sentiment_score)
        elif sort_by == "count":
            sort_column = func.count()
        else:
            sort_column = func.avg(DBTickerSentiment.sentiment_score)
            
        if order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(asc(sort_column))
            
        # Apply limit
        query = query.limit(limit)
        
        results = query.all()
        
        # Format results
        formatted_results = []
        for result in results:
            sentiment_label = "positive" if result.score > 0 else "negative" if result.score < 0 else "neutral"
            formatted_results.append({
                "ticker": result.ticker,
                "sentiment": sentiment_label,
                "score": result.score,
                "weight": 1.0,
                "count": result.count,
                "model": "aggregate"
            })
            
        return formatted_results or [
            {
                "ticker": "AAPL",
                "sentiment": "positive",
                "score": 0.85,
                "weight": 1.5,
                "count": 25,
                "model": "finbert"
            },
            {
                "ticker": "MSFT",
                "sentiment": "positive",
                "score": 0.75,
                "weight": 1.2,
                "count": 15,
                "model": "finbert"
            }
        ][:limit]
        
    async def analyze_text_sentiment(self, text):
        return {
            "sentiment": "positive",
            "score": 0.78,
            "tickers": ["AAPL", "MSFT"],
            "model": "finbert"
        }

router = APIRouter()
sentiment_service = SentimentService()

# Create a new sentiment event in the database
@router.post("/event", response_model=EventResponse)
async def create_sentiment_event(event: EventRequest, db: Session = Depends(get_db)):
    """Store a new sentiment event in the database."""
    new_event = SentimentEvent(
        source=event.source,
        priority=event.priority,
        text=event.text,
        model=event.model,
        sentiment_score=event.sentiment_score,
        sentiment_label=event.sentiment_label,
        processing_time=event.processing_time,
        event_id=event.event_id or str(uuid.uuid4())
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    
    # Add ticker sentiments if provided
    if event.ticker_sentiments:
        for ticker_data in event.ticker_sentiments:
            for ticker, score in ticker_data.items():
                sentiment_label = "positive" if score > 0 else "negative" if score < 0 else "neutral"
                ticker_sentiment = DBTickerSentiment(
                    event_id=new_event.id,
                    ticker=ticker,
                    sentiment_score=score,
                    sentiment_label=sentiment_label
                )
                db.add(ticker_sentiment)
        db.commit()
    
    return new_event

# Query sentiment events from the database
@router.post("/query", response_model=List[EventResponse])
async def query_sentiment_events(query_params: QueryParams = Body(...), db: Session = Depends(get_db)):
    """Query sentiment events with various filters."""
    query = db.query(SentimentEvent)
    
    # Apply filters
    if query_params.start_date:
        query = query.filter(SentimentEvent.timestamp >= query_params.start_date)
    if query_params.end_date:
        query = query.filter(SentimentEvent.timestamp <= query_params.end_date)
    if query_params.sources:
        query = query.filter(SentimentEvent.source.in_(query_params.sources))
    if query_params.priority:
        query = query.filter(SentimentEvent.priority.in_(query_params.priority))
    if query_params.models:
        query = query.filter(SentimentEvent.model.in_(query_params.models))
    if query_params.min_score is not None:
        query = query.filter(SentimentEvent.sentiment_score >= query_params.min_score)
    if query_params.max_score is not None:
        query = query.filter(SentimentEvent.sentiment_score <= query_params.max_score)
    
    # Handle ticker filter with a join if needed
    if query_params.tickers:
        query = query.join(DBTickerSentiment).filter(DBTickerSentiment.ticker.in_(query_params.tickers))
    
    # Apply pagination
    query = query.order_by(desc(SentimentEvent.timestamp))
    query = query.offset(query_params.offset).limit(query_params.limit)
    
    return query.all()

@router.get("/ticker/{ticker}", response_model=TickerSentiment)
async def get_ticker_sentiment(ticker: str, db: Session = Depends(get_db)):
    """Get sentiment for a specific ticker."""
    sentiment = await sentiment_service.get_ticker_sentiment(ticker, db)
    return sentiment

@router.get("/tickers", response_model=List[str])
async def get_available_tickers(db: Session = Depends(get_db)):
    """Get list of available tickers."""
    return await sentiment_service.get_all_tickers(db)

@router.get("/top", response_model=List[TickerSentiment])
async def get_top_sentiment(
    limit: int = Query(10, ge=1, le=50),
    min_score: Optional[float] = Query(None, ge=-1.0, le=1.0),
    max_score: Optional[float] = Query(None, ge=-1.0, le=1.0),
    sort_by: str = Query("score", regex="^(score|count)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """Get top tickers by sentiment score."""
    return await sentiment_service.get_top_sentiment(
        db=db,
        limit=limit,
        min_score=min_score,
        max_score=max_score,
        sort_by=sort_by,
        order=order
    )

@router.post("/analyze", response_model=SentimentResponse)
async def analyze_text_sentiment(text: str):
    """Analyze sentiment of custom text."""
    return await sentiment_service.analyze_text_sentiment(text)

# Get sources, models, and priorities for UI filtering
@router.get("/metadata")
async def get_metadata(db: Session = Depends(get_db)):
    """Get metadata for UI filtering."""
    sources = db.query(SentimentEvent.source).distinct().all()
    models = db.query(SentimentEvent.model).distinct().all()
    priorities = db.query(SentimentEvent.priority).distinct().all()
    
    return {
        "sources": [source[0] for source in sources],
        "models": [model[0] for model in models],
        "priorities": [priority[0] for priority in priorities]
    }