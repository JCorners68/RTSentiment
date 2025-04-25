from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
import datetime
import uuid
import asyncio
import redis.asyncio as redis
import json

# Import WebSocket publishing functions
from routes.websocket import publish_sentiment_event
from database import SessionLocal, SentimentEvent, TickerSentiment as DBTickerSentiment, query_sentiment_data, get_ticker_sentiment, get_all_tickers, get_top_sentiment

# Import Redis sentiment cache
try:
    from sentiment_service.utils.redis_sentiment_cache import RedisSentimentCache
    redis_sentiment_cache = RedisSentimentCache(
        host="redis",  # Redis service name in docker-compose
        port=6379,
        password=None
    )
    redis_available = True
except ImportError:
    redis_available = False
    print("Redis sentiment cache not available, falling back to direct Parquet/DB queries")

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Pydantic models
class TickerSentiment(BaseModel):
    ticker: str
    sentiment: str
    score: float
    weight: float = 1.0
    count: int = 1
    model: str
    
class HistoricalSentiment(BaseModel):
    ticker: str
    timestamp: datetime.datetime
    sentiment: str
    score: float
    source: Optional[str] = None
    count: int = 1
    model: str
    
class HistoricalSentimentResponse(BaseModel):
    ticker: str
    data: List[HistoricalSentiment]
    start_date: datetime.datetime
    end_date: datetime.datetime
    interval: str

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
    use_cache: bool = True
    
class HistoricalQueryParams(BaseModel):
    ticker: str
    start_date: datetime.datetime
    end_date: datetime.datetime
    source: Optional[str] = None
    interval: Optional[str] = "day"  # day, hour, minute
    use_cache: bool = True

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

# Add a logger for this module
import logging
logger = logging.getLogger(__name__)

# Create a new sentiment event in the database

@router.post("/event", response_model=EventResponse)
async def create_sentiment_event(event: EventRequest, db: Session = Depends(get_db)):
    """Store a new sentiment event in the database and publish to WebSocket clients."""
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
    
    # Convert the event to a dict for WebSocket broadcasting
    event_data = {
        "id": new_event.id,
        "event_id": new_event.event_id,
        "timestamp": new_event.timestamp.isoformat(),
        "source": new_event.source,
        "priority": new_event.priority,
        "text": new_event.text,
        "model": new_event.model,
        "sentiment_score": new_event.sentiment_score,
        "sentiment_label": new_event.sentiment_label,
        "ticker_sentiments": event.ticker_sentiments
    }
    
    # Publish to WebSocket clients asynchronously without waiting
    asyncio.create_task(publish_sentiment_event(event_data))
    
    return new_event

# Query sentiment events from the database
@router.post("/query", response_model=List[EventResponse])
async def query_sentiment_events(query_params: QueryParams = Body(...), db: Session = Depends(get_db)):
    """Query sentiment events with various filters."""
    # Check Redis cache first if enabled and requested
    if redis_available and query_params.use_cache:
        try:
            # Only connect to Redis if needed
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
                
            ticker = query_params.tickers[0] if query_params.tickers else None
            if ticker:
                # Create cache key based on query parameters
                cache_key = f"query:{ticker}:{query_params.start_date}:{query_params.end_date}:{query_params.limit}:{query_params.offset}"
                cached_data = await redis_sentiment_cache.client.get(cache_key)
                
                if cached_data:
                    logger.info(f"Cache hit for query: {cache_key}")
                    return [EventResponse(**item) for item in json.loads(cached_data)]
        except Exception as e:
            print(f"Error accessing Redis cache: {e}")
    
    try:
        # Try to use Parquet FDW first
        ticker = query_params.tickers[0] if query_params.tickers else None
        source = query_params.sources[0] if query_params.sources else None
        
        data = query_sentiment_data(
            db, 
            ticker=ticker,
            start_date=query_params.start_date,
            end_date=query_params.end_date,
            source=source,
            limit=query_params.limit,
            offset=query_params.offset
        )
        
        if data:
            # Convert to EventResponse format
            results = [
                EventResponse(
                    id=i,  # Use index as ID since Parquet doesn't have this concept
                    event_id=item.get('article_id', f"parquet-{i}"),
                    timestamp=datetime.datetime.fromisoformat(item.get('timestamp').replace('Z', '+00:00')) if 'timestamp' in item else datetime.datetime.now(),
                    source=item.get('source', ''),
                    priority='standard',  # Default priority
                    model=item.get('model', ''),
                    sentiment_score=item.get('sentiment', 0.0),
                    sentiment_label='positive' if item.get('sentiment', 0) > 0 else 'negative' if item.get('sentiment', 0) < 0 else 'neutral'
                )
                for i, item in enumerate(data)
            ]
            
            # Cache the results if Redis is available
            if redis_available and query_params.use_cache and ticker:
                try:
                    if not redis_sentiment_cache.is_connected:
                        await redis_sentiment_cache.connect()
                    
                    cache_key = f"query:{ticker}:{query_params.start_date}:{query_params.end_date}:{query_params.limit}:{query_params.offset}"
                    await redis_sentiment_cache.client.setex(
                        cache_key, 
                        3600,  # 1 hour TTL 
                        json.dumps([result.dict() for result in results])
                    )
                except Exception as e:
                    print(f"Error caching query results: {e}")
            
            return results
    except Exception as e:
        # Fall back to traditional database query if Parquet FDW fails
        print(f"Falling back to traditional database query: {e}")
        pass
    
    # Traditional database query as fallback
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
    
    results = query.all()
    
    # Cache results if Redis is available
    if redis_available and query_params.use_cache and ticker and results:
        try:
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
                
            cache_key = f"query:{ticker}:{query_params.start_date}:{query_params.end_date}:{query_params.limit}:{query_params.offset}"
            await redis_sentiment_cache.client.setex(
                cache_key, 
                3600,  # 1 hour TTL 
                json.dumps([result.__dict__ for result in results])
            )
        except Exception as e:
            print(f"Error caching query results: {e}")
    
    return results

@router.get("/ticker/{ticker}", response_model=TickerSentiment)
async def get_ticker_sentiment_endpoint(ticker: str, use_cache: bool = Query(True), db: Session = Depends(get_db)):
    """Get sentiment for a specific ticker."""
    # Check Redis cache first if enabled and requested
    if redis_available and use_cache:
        try:
            # Only connect to Redis if needed
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
                
            cached_sentiment = await redis_sentiment_cache.get_ticker_sentiment(ticker)
            if cached_sentiment:
                print(f"Cache hit for ticker: {ticker}")
                return TickerSentiment(**cached_sentiment)
        except Exception as e:
            print(f"Error accessing Redis cache: {e}")
    
    try:
        # Try to use Parquet FDW first
        sentiment = get_ticker_sentiment(db, ticker)
        if sentiment:
            # Cache the result if Redis is available
            if redis_available and use_cache:
                try:
                    if not redis_sentiment_cache.is_connected:
                        await redis_sentiment_cache.connect()
                    await redis_sentiment_cache.cache_ticker_sentiment(ticker, sentiment.dict())
                except Exception as e:
                    print(f"Error caching ticker sentiment: {e}")
            return sentiment
    except Exception as e:
        # Fall back to service implementation if FDW fails
        print(f"Falling back to service implementation: {e}")
        pass
        
    # Fallback to service implementation
    sentiment = await sentiment_service.get_ticker_sentiment(ticker, db)
    
    # Cache the result if Redis is available
    if redis_available and use_cache:
        try:
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
            await redis_sentiment_cache.cache_ticker_sentiment(ticker, sentiment)
        except Exception as e:
            print(f"Error caching ticker sentiment: {e}")
            
    return sentiment

@router.get("/tickers", response_model=List[str])
async def get_available_tickers(use_cache: bool = Query(True), db: Session = Depends(get_db)):
    """Get list of available tickers."""
    # Check Redis cache first if enabled and requested
    if redis_available and use_cache:
        try:
            # Only connect to Redis if needed
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
                
            cached_tickers = await redis_sentiment_cache.get_available_tickers()
            if cached_tickers:
                print(f"Cache hit for available tickers")
                return list(cached_tickers)
        except Exception as e:
            print(f"Error accessing Redis cache: {e}")
    
    try:
        # Try to use Parquet FDW first
        tickers = get_all_tickers(db)
        if tickers:
            # Cache the result if Redis is available
            if redis_available and use_cache:
                try:
                    if not redis_sentiment_cache.is_connected:
                        await redis_sentiment_cache.connect()
                    for ticker in tickers:
                        await redis_sentiment_cache.client.sadd(redis_sentiment_cache.parquet_tickers_key, ticker)
                except Exception as e:
                    print(f"Error caching tickers: {e}")
            return tickers
    except Exception as e:
        # Fall back to service implementation if FDW fails
        print(f"Falling back to service implementation: {e}")
        pass
        
    # Fallback to service implementation
    tickers = await sentiment_service.get_all_tickers(db)
    
    # Cache the result if Redis is available
    if redis_available and use_cache:
        try:
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
            for ticker in tickers:
                await redis_sentiment_cache.client.sadd(redis_sentiment_cache.parquet_tickers_key, ticker)
        except Exception as e:
            print(f"Error caching tickers: {e}")
            
    return tickers

@router.get("/top", response_model=List[TickerSentiment])
async def get_top_sentiment_endpoint(
    limit: int = Query(10, ge=1, le=50),
    min_score: Optional[float] = Query(None, ge=-1.0, le=1.0),
    max_score: Optional[float] = Query(None, ge=-1.0, le=1.0),
    sort_by: str = Query("score", regex="^(score|count)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    use_cache: bool = Query(True),
    db: Session = Depends(get_db)
):
    """Get top tickers by sentiment score."""
    # Check Redis cache first if enabled and requested
    cache_key = f"top:{limit}:{min_score}:{max_score}:{sort_by}:{order}"
    if redis_available and use_cache:
        try:
            # Only connect to Redis if needed
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
                
            cached_data = await redis_sentiment_cache.client.get(cache_key)
            if cached_data:
                print(f"Cache hit for top tickers")
                return [TickerSentiment(**item) for item in json.loads(cached_data)]
        except Exception as e:
            print(f"Error accessing Redis cache: {e}")
    
    try:
        # Try to use Parquet FDW first
        results = get_top_sentiment(
            db=db,
            limit=limit,
            min_score=min_score,
            max_score=max_score,
            sort_by=sort_by,
            order=order
        )
        if results:
            # Cache the result if Redis is available
            if redis_available and use_cache:
                try:
                    if not redis_sentiment_cache.is_connected:
                        await redis_sentiment_cache.connect()
                    await redis_sentiment_cache.client.setex(
                        cache_key,
                        3600,  # 1 hour TTL
                        json.dumps([result.dict() if hasattr(result, 'dict') else result for result in results])
                    )
                except Exception as e:
                    print(f"Error caching top tickers: {e}")
            return results
    except Exception as e:
        # Fall back to service implementation if FDW fails
        print(f"Falling back to service implementation: {e}")
        pass
        
    # Fallback to service implementation
    results = await sentiment_service.get_top_sentiment(
        db=db,
        limit=limit,
        min_score=min_score,
        max_score=max_score,
        sort_by=sort_by,
        order=order
    )
    
    # Cache the result if Redis is available
    if redis_available and use_cache:
        try:
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
            await redis_sentiment_cache.client.setex(
                cache_key,
                3600,  # 1 hour TTL
                json.dumps([result if isinstance(result, dict) else result.__dict__ for result in results])
            )
        except Exception as e:
            print(f"Error caching top tickers: {e}")
            
    return results

@router.post("/analyze", response_model=SentimentResponse)
async def analyze_text_sentiment(text: str, use_cache: bool = Query(True)):
    """Analyze sentiment of custom text."""
    # Only cache if text is less than 100 characters for efficiency
    should_cache = use_cache and len(text) < 100
    
    if redis_available and should_cache:
        try:
            # Only connect to Redis if needed
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
                
            cache_key = f"analyze_text:{text}"
            cached_data = await redis_sentiment_cache.client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for text analysis")
                return SentimentResponse(**json.loads(cached_data))
        except Exception as e:
            logger.error(f"Error accessing Redis cache: {e}")
    
    result = await sentiment_service.analyze_text_sentiment(text)
    
    # Cache the result if Redis is available and text is cacheable
    if redis_available and should_cache:
        try:
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
            await redis_sentiment_cache.client.setex(
                f"analyze_text:{text}",
                3600,  # 1 hour TTL
                json.dumps(result)
            )
        except Exception as e:
            logger.error(f"Error caching text analysis: {e}")
            
    return result

# Get sources, models, and priorities for UI filtering
@router.get("/metadata")
async def get_metadata(use_cache: bool = Query(True), db: Session = Depends(get_db)):
    """Get metadata for UI filtering."""
    if redis_available and use_cache:
        try:
            # Only connect to Redis if needed
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
                
            cache_key = "metadata"
            cached_data = await redis_sentiment_cache.client.get(cache_key)
            if cached_data:
                logger.info("Cache hit for metadata")
                return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Error accessing Redis cache: {e}")
    
    sources = db.query(SentimentEvent.source).distinct().all()
    models = db.query(SentimentEvent.model).distinct().all()
    priorities = db.query(SentimentEvent.priority).distinct().all()
    
    metadata = {
        "sources": [source[0] for source in sources],
        "models": [model[0] for model in models],
        "priorities": [priority[0] for priority in priorities]
    }
    
    # Cache the result if Redis is available
    if redis_available and use_cache:
        try:
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
            await redis_sentiment_cache.client.setex(
                "metadata",
                3600 * 6,  # 6 hour TTL since this rarely changes
                json.dumps(metadata)
            )
        except Exception as e:
            logger.error(f"Error caching metadata: {e}")
            
    return metadata

# Add new endpoints for historical sentiment data
@router.post("/historical", response_model=HistoricalSentimentResponse)
async def get_historical_sentiment(query_params: HistoricalQueryParams = Body(...), db: Session = Depends(get_db)):
    """Get historical sentiment data for a ticker over a time range."""
    if not query_params.ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")
        
    # Check Redis cache first if enabled and requested
    if redis_available and query_params.use_cache:
        try:
            # Only connect to Redis if needed
            if not redis_sentiment_cache.is_connected:
                await redis_sentiment_cache.connect()
                
            # Create cache key from query parameters
            start_date_str = query_params.start_date.isoformat()
            end_date_str = query_params.end_date.isoformat()
            cache_key = f"historical:{query_params.ticker}:{start_date_str}:{end_date_str}:{query_params.interval}"
            
            # Check if this query is in the cache
            cached_data = await redis_sentiment_cache.client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for historical data: {query_params.ticker}")
                return HistoricalSentimentResponse(**json.loads(cached_data))
                
            # Also check if we've already determined this timerange is not available
            timerange_info = await redis_sentiment_cache.get_parquet_timerange(
                query_params.ticker, start_date_str, end_date_str
            )
            if timerange_info and not timerange_info.get("available", False):
                logger.info(f"Cache hit for unavailable timerange: {query_params.ticker}")
                raise HTTPException(status_code=404, detail=f"No historical data available for {query_params.ticker} in the specified time range")
        except Exception as e:
            logger.error(f"Error accessing Redis cache: {e}")
    
    try:
        # Try to query the data from Parquet via FDW
        from database import query_historical_sentiment_data
        
        historical_data = query_historical_sentiment_data(
            db,
            ticker=query_params.ticker,
            start_date=query_params.start_date,
            end_date=query_params.end_date,
            source=query_params.source,
            interval=query_params.interval
        )
        
        if not historical_data:
            # Cache the fact that this timerange has no data
            if redis_available and query_params.use_cache:
                try:
                    if not redis_sentiment_cache.is_connected:
                        await redis_sentiment_cache.connect()
                    
                    start_date_str = query_params.start_date.isoformat()
                    end_date_str = query_params.end_date.isoformat()
                    
                    await redis_sentiment_cache.cache_parquet_timerange(
                        query_params.ticker,
                        start_date_str,
                        end_date_str,
                        available=False
                    )
                except Exception as e:
                    logger.error(f"Error caching timerange availability: {e}")
                    
            raise HTTPException(status_code=404, detail=f"No historical data available for {query_params.ticker} in the specified time range")
            
        # Format the response
        formatted_data = []
        for item in historical_data:
            sentiment_label = "positive" if item.get('sentiment', 0) > 0 else "negative" if item.get('sentiment', 0) < 0 else "neutral"
            formatted_data.append(
                HistoricalSentiment(
                    ticker=query_params.ticker,
                    timestamp=datetime.datetime.fromisoformat(item.get('timestamp').replace('Z', '+00:00')) if 'timestamp' in item else query_params.start_date,
                    sentiment=sentiment_label,
                    score=item.get('sentiment', 0.0),
                    source=item.get('source', ''),
                    count=item.get('count', 1),
                    model="parquet"
                )
            )
            
        response = HistoricalSentimentResponse(
            ticker=query_params.ticker,
            data=formatted_data,
            start_date=query_params.start_date,
            end_date=query_params.end_date,
            interval=query_params.interval
        )
        
        # Cache the response if Redis is available
        if redis_available and query_params.use_cache:
            try:
                if not redis_sentiment_cache.is_connected:
                    await redis_sentiment_cache.connect()
                
                start_date_str = query_params.start_date.isoformat()
                end_date_str = query_params.end_date.isoformat()
                
                # Cache the full response
                cache_key = f"historical:{query_params.ticker}:{start_date_str}:{end_date_str}:{query_params.interval}"
                await redis_sentiment_cache.client.setex(
                    cache_key,
                    3600 * 24,  # 24 hour TTL for historical data since it rarely changes
                    json.dumps(response.dict())
                )
                
                # Also cache the fact that this timerange has data
                await redis_sentiment_cache.cache_parquet_timerange(
                    query_params.ticker,
                    start_date_str,
                    end_date_str,
                    available=True
                )
            except Exception as e:
                logger.error(f"Error caching historical data: {e}")
                
        return response
        
    except Exception as e:
        logger.error(f"Error querying historical data: {e}")
        raise HTTPException(status_code=500, detail=f"Error querying historical data: {str(e)}")
        
@router.get("/ticker/{ticker}/timerange", response_model=Dict[str, Any])
async def get_ticker_timerange(ticker: str, db: Session = Depends(get_db)):
    """Get the available time range for historical data for a ticker."""
    try:
        # Try to query the time range from Parquet via FDW
        from database import get_ticker_timerange
        
        timerange = get_ticker_timerange(db, ticker)
        if not timerange:
            raise HTTPException(status_code=404, detail=f"No historical data available for {ticker}")
            
        return timerange
    except Exception as e:
        logger.error(f"Error querying ticker timerange: {e}")
        raise HTTPException(status_code=500, detail=f"Error querying ticker timerange: {str(e)}")
        
@router.get("/ticker/{ticker}/sources", response_model=List[str])
async def get_ticker_sources(ticker: str, db: Session = Depends(get_db)):
    """Get the available sources for historical data for a ticker."""
    try:
        # Try to query the sources from Parquet via FDW
        from database import get_ticker_sources
        
        sources = get_ticker_sources(db, ticker)
        if not sources:
            raise HTTPException(status_code=404, detail=f"No sources available for {ticker}")
            
        return sources
    except Exception as e:
        logger.error(f"Error querying ticker sources: {e}")
        raise HTTPException(status_code=500, detail=f"Error querying ticker sources: {str(e)}")