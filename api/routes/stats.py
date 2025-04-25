"""
Stats API routes for the sentiment analysis system.
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, select, desc, asc, text
from typing import List, Dict, Optional
from pydantic import BaseModel
import logging
import datetime
import asyncio

# Import WebSocket functions
from routes.websocket import publish_system_stats, publish_data_flow
from database import SessionLocal, SentimentEvent, TickerSentiment

# Setup logging
logger = logging.getLogger(__name__)

# Pydantic models for request/response validation
class MessageCategoryStats(BaseModel):
    count: int = 0
    average_processing_time: float = 0.0
    messages_per_minute: float = 0.0
    error_rate: float = 0.0

class MessageStatsResponse(BaseModel):
    high_priority: MessageCategoryStats
    standard_priority: MessageCategoryStats
    sentiment_results: MessageCategoryStats
    
class DataFlowPoint(BaseModel):
    """Data model for a time-series data point showing message volume flow."""
    timestamp: datetime.datetime
    messages_per_second: float = 0.0
    avg_processing_time: float = 0.0
    error_rate: float = 0.0
    
    # Backwards compatibility for the existing implementation
    incoming_volume: Optional[float] = None
    processed_volume: Optional[float] = None

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create router
router = APIRouter()

@router.get("/stats", response_model=MessageStatsResponse)
async def get_sentiment_stats(db: Session = Depends(get_db)):
    """
    Get system statistics for message processing.
    
    Returns statistics for high priority events, standard priority events,
    and sentiment analysis results.
    """
    try:
        # Query for high priority events
        high_count = db.query(func.count(SentimentEvent.id)).filter(
            SentimentEvent.priority == "high"
        ).scalar() or 0
        
        high_avg_time = db.query(func.avg(SentimentEvent.processing_time)).filter(
            SentimentEvent.priority == "high",
            SentimentEvent.processing_time.isnot(None)
        ).scalar() or 0.0
        
        # Query for standard priority events
        std_count = db.query(func.count(SentimentEvent.id)).filter(
            SentimentEvent.priority == "standard"
        ).scalar() or 0
        
        std_avg_time = db.query(func.avg(SentimentEvent.processing_time)).filter(
            SentimentEvent.priority == "standard",
            SentimentEvent.processing_time.isnot(None)
        ).scalar() or 0.0
        
        # Query for sentiment results (all events with sentiment score)
        sent_count = db.query(func.count(SentimentEvent.id)).filter(
            SentimentEvent.sentiment_score.isnot(None)
        ).scalar() or 0
        
        sent_avg_time = db.query(func.avg(SentimentEvent.processing_time)).filter(
            SentimentEvent.sentiment_score.isnot(None),
            SentimentEvent.processing_time.isnot(None)
        ).scalar() or 0.0
        
        # Messages per minute - simplified mock values for now
        # In a real application, you would calculate this from time-series data
        high_msgs_per_min = float(high_count) / 60.0 if high_count > 0 else 0.0
        std_msgs_per_min = float(std_count) / 60.0 if std_count > 0 else 0.0
        sent_msgs_per_min = float(sent_count) / 60.0 if sent_count > 0 else 0.0
        
        # Create the stats response
        response = MessageStatsResponse(
            high_priority=MessageCategoryStats(
                count=high_count,
                average_processing_time=float(high_avg_time) if high_avg_time else 0.0,
                messages_per_minute=high_msgs_per_min,
                error_rate=0.0  # Placeholder
            ),
            standard_priority=MessageCategoryStats(
                count=std_count,
                average_processing_time=float(std_avg_time) if std_avg_time else 0.0,
                messages_per_minute=std_msgs_per_min,
                error_rate=0.0  # Placeholder
            ),
            sentiment_results=MessageCategoryStats(
                count=sent_count,
                average_processing_time=float(sent_avg_time) if sent_avg_time else 0.0,
                messages_per_minute=sent_msgs_per_min,
                error_rate=0.0  # Placeholder
            )
        )
        
        # Convert to dict for broadcasting
        stats_data = {
            "high_priority": {
                "count": high_count,
                "average_processing_time": float(high_avg_time) if high_avg_time else 0.0,
                "messages_per_minute": high_msgs_per_min,
                "error_rate": 0.0
            },
            "standard_priority": {
                "count": std_count,
                "average_processing_time": float(std_avg_time) if std_avg_time else 0.0,
                "messages_per_minute": std_msgs_per_min,
                "error_rate": 0.0
            },
            "sentiment_results": {
                "count": sent_count,
                "average_processing_time": float(sent_avg_time) if sent_avg_time else 0.0,
                "messages_per_minute": sent_msgs_per_min,
                "error_rate": 0.0
            },
            "timestamp": datetime.datetime.utcnow().isoformat()
        }
        
        # Publish to WebSocket clients asynchronously
        asyncio.create_task(publish_system_stats(stats_data))
        
        return response
        
    except Exception as e:
        logger.error(f"Error in get_sentiment_stats: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching system statistics")

@router.get("/metadata", response_model=Dict[str, List[str]])
def get_metadata(db: Session = Depends(get_db)):
    """
    Get metadata for UI filtering.
    
    Returns lists of available sources, models, and priorities
    from the sentiment_events table.
    """
    try:
        # Query for distinct sources
        sources_result = db.query(SentimentEvent.source).distinct().all()
        sources = [row[0] for row in sources_result if row[0]]
        
        # Query for distinct models
        models_result = db.query(SentimentEvent.model).distinct().all()
        models = [row[0] for row in models_result if row[0]]
        
        # Query for distinct priorities
        priorities_result = db.query(SentimentEvent.priority).distinct().all()
        priorities = [row[0] for row in priorities_result if row[0]]
    
        # Return metadata
        return {
            "sources": sources or ["news", "reddit", "twitter"],  # Fallback defaults
            "models": models or ["finbert", "fingpt", "llama4_scout"],
            "priorities": priorities or ["high", "standard"]
        }
        
    except Exception as e:
        logger.error(f"Error in get_metadata: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching metadata")
        
@router.get("/dataflow", response_model=List[DataFlowPoint])
async def get_data_flow(
    points: int = Query(30, gt=0, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get time-series data showing incoming vs. processed message volume.
    
    Returns a list of data points with timestamp, incoming_volume, and 
    processed_volume for the specified number of most recent time periods.
    
    Args:
        points: Number of data points to return (default: 30, max: 1000)
        
    Returns:
        List of DataFlowPoint objects ordered by timestamp (ascending)
    """
    try:
        # Get the current time for calculations
        now = datetime.datetime.utcnow()
        
        # Calculate the time interval based on the number of points
        # For points <= 24, use hourly data
        # For points > 24, use daily data
        if points <= 24:
            # Hourly data
            interval_minutes = 60
            format_str = "%Y-%m-%d %H:00:00"
            date_trunc = "hour"
        elif points <= 168:  # 7 days * 24 hours = 168 hours (weekly view)
            # Every 4 hours
            interval_minutes = 240
            format_str = "%Y-%m-%d %H:00:00"
            date_trunc = "hour"
        else:
            # Daily data
            interval_minutes = 1440  # 24 hours * 60 minutes
            format_str = "%Y-%m-%d 00:00:00"
            date_trunc = "day"
        
        # Start time for query
        start_time = now - datetime.timedelta(minutes=interval_minutes * points)
        
        # Query for incoming messages (all events within the time range)
        incoming_data = db.query(
            func.date_trunc(date_trunc, SentimentEvent.timestamp).label('time_bucket'),
            func.count().label('count')
        ).filter(
            SentimentEvent.timestamp >= start_time
        ).group_by(
            func.date_trunc(date_trunc, SentimentEvent.timestamp)
        ).order_by(
            func.date_trunc(date_trunc, SentimentEvent.timestamp)
        ).all()
        
        # Query for processed messages (events with sentiment scores)
        processed_data = db.query(
            func.date_trunc(date_trunc, SentimentEvent.timestamp).label('time_bucket'),
            func.count().label('count')
        ).filter(
            SentimentEvent.timestamp >= start_time,
            SentimentEvent.sentiment_score.isnot(None)
        ).group_by(
            func.date_trunc(date_trunc, SentimentEvent.timestamp)
        ).order_by(
            func.date_trunc(date_trunc, SentimentEvent.timestamp)
        ).all()
        
        # Convert query results to dictionaries
        incoming_dict = {str(row.time_bucket): row.count for row in incoming_data}
        processed_dict = {str(row.time_bucket): row.count for row in processed_data}
        
        # Generate the full time range
        all_buckets = []
        for i in range(points):
            if points <= 24:
                # Hourly buckets
                bucket_time = now - datetime.timedelta(hours=points-i-1)
                bucket_key = bucket_time.strftime(format_str)
            elif points <= 168:
                # 4-hour buckets
                bucket_time = now - datetime.timedelta(hours=(points-i-1) * 4)
                bucket_key = bucket_time.strftime(format_str)
            else:
                # Daily buckets
                bucket_time = now - datetime.timedelta(days=points-i-1)
                bucket_key = bucket_time.strftime(format_str)
            
            # Parse the bucket time string back to datetime for consistent output
            bucket_datetime = datetime.datetime.strptime(bucket_key, format_str)
            
            # Calculate new metrics
            incoming_volume = float(incoming_dict.get(bucket_key, 0))
            processed_volume = float(processed_dict.get(bucket_key, 0))
            
            # Convert volumes to messages_per_second
            # This depends on the interval (hourly, 4-hourly, or daily)
            interval_seconds = 3600  # Default to hourly (3600 seconds)
            if points > 168:
                interval_seconds = 86400  # Daily (24 hours * 60 min * 60 sec)
            elif points > 24:
                interval_seconds = 14400  # 4-hourly (4 hours * 60 min * 60 sec)
                
            messages_per_second = incoming_volume / interval_seconds if interval_seconds > 0 else 0
            
            # Calculate average processing time (mock data - in a real implementation, 
            # you would retrieve this from appropriate metrics)
            avg_processing_time = 0.05
            
            # Calculate error rate (mock data - in a real implementation, 
            # you would retrieve this from appropriate metrics)
            error_rate = 0.01 if incoming_volume > 0 else 0.0
            
            # Create DataFlowPoint for this bucket
            data_point = DataFlowPoint(
                timestamp=bucket_datetime,
                messages_per_second=messages_per_second,
                avg_processing_time=avg_processing_time,
                error_rate=error_rate,
                # Keep old fields for backwards compatibility
                incoming_volume=incoming_volume,
                processed_volume=processed_volume
            )
            all_buckets.append(data_point)
            
            # Create a dict version for WebSocket
            ws_data_point = {
                "timestamp": bucket_datetime.isoformat(),
                "messages_per_second": messages_per_second,
                "avg_processing_time": avg_processing_time,
                "error_rate": error_rate,
                # Include old fields for backwards compatibility
                "incoming_volume": incoming_volume,
                "processed_volume": processed_volume
            }
            
            # Publish the latest point to WebSocket clients
            if i == points - 1:  # Only publish the latest point
                asyncio.create_task(publish_data_flow(ws_data_point))
        
        return all_buckets
        
    except Exception as e:
        logger.error(f"Error in get_data_flow: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while fetching data flow information")