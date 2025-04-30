"""
Sentiment Query API service for the sentiment analysis system.

This module provides a REST API service that exposes the DremioSentimentQueryService
functionality to clients, implementing the API component of Phase 3.
"""
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import numpy as np

from iceberg_lake.query.dremio_sentiment_query import DremioSentimentQueryService
from iceberg_lake.query.mock_query_service import MockSentimentQueryService
from iceberg_lake.utils.config import IcebergConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Sentiment Analysis API",
    description="API for querying sentiment analysis data",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global query service instance
query_service = None


def get_query_service(use_mock: bool = True):
    """
    Get or create the sentiment query service instance.
    
    Args:
        use_mock: If True, use the MockSentimentQueryService if real service fails
        
    Returns:
        DremioSentimentQueryService or MockSentimentQueryService: The query service instance
    """
    global query_service
    
    if query_service is None:
        # Load configuration
        config = IcebergConfig()
        dremio_config = config.get_dremio_config()
        
        # Extract connection details
        dremio_host = dremio_config.get('host', 'localhost')
        dremio_port = dremio_config.get('jdbc_port', 31010)
        dremio_username = dremio_config.get('username', 'dremio')
        dremio_password = dremio_config.get('password', 'dremio123')
        catalog = dremio_config.get('catalog', 'DREMIO')
        namespace = config.get_catalog_config().get('namespace', 'sentiment')
        table_name = config.get_catalog_config().get('table_name', 'sentiment_data')
        
        # Check for MOCK_SERVICE environment variable
        if os.environ.get('USE_MOCK_SERVICE', '').lower() == 'true' or use_mock:
            logger.info(f"Using MockSentimentQueryService (configured via environment or parameter)")
            query_service = MockSentimentQueryService(
                catalog=catalog,
                namespace=namespace,
                table_name=table_name
            )
            return query_service
            
        try:
            # Find JDBC driver
            jar_paths = [
                # Check for environment variable
                [os.environ.get('DREMIO_JDBC_DRIVER')] if os.environ.get('DREMIO_JDBC_DRIVER') else [],
                # Check current directory
                [os.path.abspath(f) for f in os.listdir('.') if f.endswith('.jar') and 'dremio' in f.lower()],
                # Check drivers directory if it exists
                [os.path.abspath(os.path.join('drivers', f)) for f in os.listdir('drivers') if os.path.exists('drivers') and f.endswith('.jar') and 'dremio' in f.lower()],
            ]
            jar_files = [item for sublist in jar_paths for item in sublist if item]
            jar_path = jar_files[0] if jar_files else None
            
            if jar_path:
                logger.info(f"Found JDBC driver: {jar_path}")
            else:
                logger.warning("No JDBC driver found, DremioSentimentQueryService may fail")
            
            # Create query service
            query_service = DremioSentimentQueryService(
                dremio_host=dremio_host,
                dremio_port=dremio_port,
                dremio_username=dremio_username,
                dremio_password=dremio_password,
                catalog=catalog,
                namespace=namespace,
                table_name=table_name,
                jar_path=jar_path
            )
            
            logger.info(f"Created DremioSentimentQueryService for {catalog}.{namespace}.{table_name}")
            
        except Exception as e:
            logger.error(f"Failed to create DremioSentimentQueryService: {str(e)}")
            
            if use_mock:
                logger.info("Falling back to MockSentimentQueryService")
                query_service = MockSentimentQueryService(
                    catalog=catalog,
                    namespace=namespace,
                    table_name=table_name
                )
            else:
                raise
    
    return query_service


# Helper function to convert pandas DataFrames to JSON
def dataframe_to_dict(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Convert a pandas DataFrame to a JSON-serializable dictionary.
    
    Args:
        df: Pandas DataFrame to convert
        
    Returns:
        Dict[str, Any]: JSON-serializable dictionary
    """
    if df.empty:
        return {"data": [], "count": 0}
    
    # Replace NaN values with None
    df = df.replace({np.nan: None})
    
    # Convert to dict
    records = df.to_dict(orient='records')
    
    return {
        "data": records,
        "count": len(records)
    }


# API Routes

@app.get("/")
async def root():
    """Root endpoint, returns API info."""
    return {
        "name": "Sentiment Analysis API",
        "version": "1.0.0",
        "description": "API for querying sentiment analysis data"
    }


@app.get("/sentiment")
async def get_sentiment(
    ticker: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    service: DremioSentimentQueryService = Depends(get_query_service)
):
    """
    Get sentiment data with emotion analysis.
    
    Args:
        ticker: Stock ticker symbol (optional)
        days: Number of days to look back (default: 30)
        
    Returns:
        JSONResponse: Sentiment data with emotion analysis
    """
    try:
        df = service.get_sentiment_with_emotions(ticker=ticker, days=days)
        return JSONResponse(content=dataframe_to_dict(df))
    except Exception as e:
        logger.error(f"Error in get_sentiment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment/entities")
async def get_entity_sentiment(
    ticker: Optional[str] = None,
    entity_type: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    service: DremioSentimentQueryService = Depends(get_query_service)
):
    """
    Get sentiment analysis broken down by entity.
    
    Args:
        ticker: Stock ticker symbol (optional)
        entity_type: Entity type to filter by (e.g., 'PERSON', 'ORGANIZATION')
        days: Number of days to look back (default: 30)
        
    Returns:
        JSONResponse: Entity sentiment analysis
    """
    try:
        df = service.get_entity_sentiment_analysis(ticker=ticker, entity_type=entity_type, days=days)
        return JSONResponse(content=dataframe_to_dict(df))
    except Exception as e:
        logger.error(f"Error in get_entity_sentiment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment/aspects")
async def get_aspect_sentiment(
    ticker: str,
    days: int = Query(30, ge=1, le=365),
    service: DremioSentimentQueryService = Depends(get_query_service)
):
    """
    Get aspect-based sentiment analysis for a specific ticker.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to look back (default: 30)
        
    Returns:
        JSONResponse: Aspect-based sentiment analysis
    """
    try:
        df = service.get_aspect_based_sentiment(ticker=ticker, days=days)
        return JSONResponse(content=dataframe_to_dict(df))
    except Exception as e:
        logger.error(f"Error in get_aspect_sentiment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment/toxic")
async def get_toxic_content(
    min_toxicity: float = Query(0.5, ge=0.0, le=1.0),
    days: int = Query(30, ge=1, le=365),
    service: DremioSentimentQueryService = Depends(get_query_service)
):
    """
    Get potentially toxic content for moderation.
    
    Args:
        min_toxicity: Minimum toxicity score (0.0 to 1.0)
        days: Number of days to look back (default: 30)
        
    Returns:
        JSONResponse: Toxic content analysis
    """
    try:
        df = service.get_toxicity_analysis(min_toxicity=min_toxicity, days=days)
        return JSONResponse(content=dataframe_to_dict(df))
    except Exception as e:
        logger.error(f"Error in get_toxic_content: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment/intents")
async def get_intents(
    ticker: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    service: DremioSentimentQueryService = Depends(get_query_service)
):
    """
    Get distribution of user intents.
    
    Args:
        ticker: Stock ticker symbol (optional)
        days: Number of days to look back (default: 30)
        
    Returns:
        JSONResponse: User intent distribution
    """
    try:
        df = service.get_intent_distribution(ticker=ticker, days=days)
        return JSONResponse(content=dataframe_to_dict(df))
    except Exception as e:
        logger.error(f"Error in get_intents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment/timeseries")
async def get_timeseries(
    ticker: str,
    interval: str = Query("day", regex="^(hour|day|week|month)$"),
    days: int = Query(30, ge=1, le=365),
    service: DremioSentimentQueryService = Depends(get_query_service)
):
    """
    Get sentiment time series data with advanced metrics.
    
    Args:
        ticker: Stock ticker symbol
        interval: Time interval ('hour', 'day', 'week', 'month')
        days: Number of days to look back (default: 30)
        
    Returns:
        JSONResponse: Sentiment time series data
    """
    try:
        df = service.get_sentiment_time_series(ticker=ticker, interval=interval, days=days)
        return JSONResponse(content=dataframe_to_dict(df))
    except Exception as e:
        logger.error(f"Error in get_timeseries: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment/tickers")
async def get_top_tickers(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    service: DremioSentimentQueryService = Depends(get_query_service)
):
    """
    Get top tickers by message volume.
    
    Args:
        days: Number of days to look back (default: 30)
        limit: Number of top tickers to return
        
    Returns:
        JSONResponse: Top tickers by volume
    """
    try:
        df = service.get_top_tickers_by_volume(days=days, limit=limit)
        return JSONResponse(content=dataframe_to_dict(df))
    except Exception as e:
        logger.error(f"Error in get_top_tickers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment/emotions")
async def get_emotions(
    ticker: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    service: DremioSentimentQueryService = Depends(get_query_service)
):
    """
    Get top emotions for a ticker or across all tickers.
    
    Args:
        ticker: Stock ticker symbol (optional)
        days: Number of days to look back (default: 30)
        limit: Number of top emotions to return
        
    Returns:
        JSONResponse: Top emotions
    """
    try:
        df = service.get_top_emotions(ticker=ticker, days=days, limit=limit)
        return JSONResponse(content=dataframe_to_dict(df))
    except Exception as e:
        logger.error(f"Error in get_emotions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment/sources")
async def get_sources(
    ticker: Optional[str] = None,
    days: int = Query(30, ge=1, le=365),
    service: DremioSentimentQueryService = Depends(get_query_service)
):
    """
    Get sentiment analysis broken down by source system.
    
    Args:
        ticker: Stock ticker symbol (optional)
        days: Number of days to look back (default: 30)
        
    Returns:
        JSONResponse: Sentiment by source
    """
    try:
        df = service.get_sentiment_by_source(ticker=ticker, days=days)
        return JSONResponse(content=dataframe_to_dict(df))
    except Exception as e:
        logger.error(f"Error in get_sources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment/search")
async def search_sentiment(
    keyword: Optional[str] = None,
    ticker: Optional[str] = None,
    source_system: Optional[str] = None,
    min_sentiment: Optional[float] = None,
    max_sentiment: Optional[float] = None,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, ge=1, le=1000),
    service: DremioSentimentQueryService = Depends(get_query_service)
):
    """
    Search sentiment data with various filters.
    
    Args:
        keyword: Keyword to search in text_content (optional)
        ticker: Stock ticker symbol (optional)
        source_system: Source system identifier (optional)
        min_sentiment: Minimum sentiment score (optional)
        max_sentiment: Maximum sentiment score (optional)
        days: Number of days to look back (default: 30)
        limit: Maximum number of results to return
        
    Returns:
        JSONResponse: Search results
    """
    try:
        df = service.search_sentiment_data(
            keyword=keyword,
            ticker=ticker,
            source_system=source_system,
            min_sentiment=min_sentiment,
            max_sentiment=max_sentiment,
            days=days,
            limit=limit
        )
        return JSONResponse(content=dataframe_to_dict(df))
    except Exception as e:
        logger.error(f"Error in search_sentiment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sentiment/correlations")
async def get_correlations(
    ticker: str,
    days: int = Query(30, ge=1, le=365),
    service: DremioSentimentQueryService = Depends(get_query_service)
):
    """
    Calculate correlations between different metrics for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to look back (default: 30)
        
    Returns:
        JSONResponse: Correlation coefficients
    """
    try:
        correlations = service.get_correlations(ticker=ticker, days=days)
        return JSONResponse(content={"correlations": correlations})
    except Exception as e:
        logger.error(f"Error in get_correlations: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))