import os
import logging
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import text
import datetime
from typing import Generator, Dict, Any, List
from contextlib import contextmanager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection
DB_USER = os.getenv("POSTGRES_USER", "pgadmin")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "localdev")
DB_HOST = os.getenv("POSTGRES_HOST", "postgres")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_NAME = os.getenv("POSTGRES_DB", "sentimentdb")

SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

@contextmanager
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database models - these are kept for backward compatibility
# but we're now using Foreign Data Wrapper for sentiment data
class SentimentEvent(Base):
    __tablename__ = "sentiment_events"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(100), nullable=False)
    priority = Column(String(50), nullable=False)
    text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    model = Column(String(100), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String(50), nullable=True)
    processing_time = Column(Float, nullable=True)  # in seconds
    event_id = Column(String(100), unique=True, index=True)
    ticker_sentiments = relationship("TickerSentiment", back_populates="event")

class TickerSentiment(Base):
    __tablename__ = "ticker_sentiments"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("sentiment_events.id"), nullable=False)
    ticker = Column(String(20), nullable=False)
    sentiment_score = Column(Float, nullable=False)
    sentiment_label = Column(String(50), nullable=False)
    event = relationship("SentimentEvent", back_populates="ticker_sentiments")

# Functions for querying the parquet data through FDW
def query_sentiment_data(db, ticker=None, start_date=None, end_date=None, source=None, limit=100, offset=0) -> List[Dict[str, Any]]:
    """
    Query sentiment data from Parquet files through Foreign Data Wrapper.
    
    Args:
        db: Database session
        ticker: Optional ticker symbol to filter by
        start_date: Optional start date for filtering
        end_date: Optional end date for filtering
        source: Optional source to filter by
        limit: Maximum number of results to return
        offset: Number of results to skip
        
    Returns:
        List of dictionaries containing sentiment data
    """
    try:
        # Start building the query
        query = """
        SELECT 
            timestamp,
            ticker, 
            sentiment, 
            confidence, 
            source,
            model, 
            article_id, 
            article_title
        FROM all_sentiment
        WHERE 1=1
        """
        
        # Prepare parameters
        params = {}
        
        # Add filters
        if ticker:
            query += " AND ticker = :ticker"
            params['ticker'] = ticker
            
        if start_date:
            query += " AND timestamp >= :start_date"
            params['start_date'] = start_date
            
        if end_date:
            query += " AND timestamp <= :end_date"
            params['end_date'] = end_date
            
        if source:
            query += " AND source = :source"
            params['source'] = source
            
        # Add ordering, limit and offset
        query += " ORDER BY timestamp DESC LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        # Execute the query
        result = db.execute(text(query), params)
        
        # Convert to list of dictionaries
        data = [dict(row._mapping) for row in result]
        
        return data
    except Exception as e:
        logger.error(f"Error querying sentiment data: {e}")
        return []

def get_ticker_sentiment(db, ticker) -> Dict[str, Any]:
    """
    Get aggregate sentiment for a specific ticker from Parquet files.
    
    Args:
        db: Database session
        ticker: Ticker symbol
        
    Returns:
        Dictionary with aggregate sentiment data
    """
    try:
        query = """
        SELECT 
            ticker,
            AVG(sentiment) as sentiment_score,
            COUNT(*) as count
        FROM all_sentiment
        WHERE ticker = :ticker
        GROUP BY ticker
        """
        
        # Execute the query
        result = db.execute(text(query), {'ticker': ticker})
        row = result.fetchone()
        
        if not row:
            return {
                'ticker': ticker,
                'sentiment': 'neutral',
                'score': 0.0,
                'weight': 1.0,
                'count': 0,
                'model': 'aggregate'
            }
        
        # Determine sentiment label based on score
        sentiment_label = 'positive' if row.sentiment_score > 0 else 'negative' if row.sentiment_score < 0 else 'neutral'
        
        return {
            'ticker': ticker,
            'sentiment': sentiment_label,
            'score': float(row.sentiment_score),
            'weight': 1.0,
            'count': row.count,
            'model': 'aggregate'
        }
    except Exception as e:
        logger.error(f"Error getting ticker sentiment: {e}")
        return {
            'ticker': ticker,
            'sentiment': 'neutral',
            'score': 0.0,
            'weight': 1.0,
            'count': 0,
            'model': 'aggregate'
        }

def get_all_tickers(db) -> List[str]:
    """
    Get all distinct tickers from Parquet files.
    
    Args:
        db: Database session
        
    Returns:
        List of ticker symbols
    """
    try:
        query = """
        SELECT DISTINCT ticker
        FROM all_sentiment
        ORDER BY ticker
        """
        
        # Execute the query
        result = db.execute(text(query))
        
        # Extract ticker symbols
        tickers = [row[0] for row in result]
        
        return tickers or ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]
    except Exception as e:
        logger.error(f"Error getting all tickers: {e}")
        return ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]

def get_top_sentiment(db, limit=10, min_score=None, max_score=None, sort_by="score", order="desc") -> List[Dict[str, Any]]:
    """
    Get top tickers by sentiment score from Parquet files.
    
    Args:
        db: Database session
        limit: Maximum number of results to return
        min_score: Optional minimum sentiment score
        max_score: Optional maximum sentiment score
        sort_by: Field to sort by (score or count)
        order: Sort order (asc or desc)
        
    Returns:
        List of dictionaries with ticker sentiment data
    """
    try:
        # Start building the query
        query = """
        SELECT 
            ticker,
            AVG(sentiment) as score,
            COUNT(*) as count
        FROM all_sentiment
        GROUP BY ticker
        """
        
        # Prepare parameters
        params = {}
        
        # Add filters
        if min_score is not None:
            query += " HAVING AVG(sentiment) >= :min_score"
            params['min_score'] = min_score
            
        if max_score is not None:
            query += " HAVING" if min_score is None else " AND"
            query += " AVG(sentiment) <= :max_score"
            params['max_score'] = max_score
            
        # Add sorting
        if sort_by == "score":
            query += f" ORDER BY score {order.upper()}"
        elif sort_by == "count":
            query += f" ORDER BY count {order.upper()}"
        else:
            query += f" ORDER BY score {order.upper()}"
            
        # Add limit
        query += " LIMIT :limit"
        params['limit'] = limit
        
        # Execute the query
        result = db.execute(text(query), params)
        
        # Format results
        formatted_results = []
        for row in result:
            sentiment_label = "positive" if row.score > 0 else "negative" if row.score < 0 else "neutral"
            formatted_results.append({
                "ticker": row.ticker,
                "sentiment": sentiment_label,
                "score": float(row.score),
                "weight": 1.0,
                "count": row.count,
                "model": "aggregate"
            })
            
        return formatted_results
    except Exception as e:
        logger.error(f"Error getting top sentiment: {e}")
        return []

# Create tables for backward compatibility
def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Check if FDW extension and tables are available
    with get_db() as db:
        try:
            # Try to query the all_sentiment view to see if it exists
            db.execute(text("SELECT 1 FROM all_sentiment LIMIT 1"))
            logger.info("Parquet FDW is configured and operational")
        except Exception as e:
            logger.warning(f"Parquet FDW not available: {e}")
            logger.warning("Falling back to traditional database tables for sentiment data")