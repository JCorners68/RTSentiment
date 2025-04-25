"""
Parquet reader service for efficiently reading and querying sentiment data from Parquet files.
"""
import logging
import os
import time
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple, Any, Union

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
import pyarrow.dataset as ds

logger = logging.getLogger(__name__)

class ParquetReader:
    """
    A service for efficiently reading and querying sentiment data from Parquet files.
    
    This class provides optimized methods for accessing sentiment data stored in Parquet
    format, with support for filtering by ticker, date range, and other criteria.
    """
    
    def __init__(self, data_dir: str = None, cache_size: int = 128):
        """
        Initialize the ParquetReader.
        
        Args:
            data_dir (str): Directory containing Parquet files. If None, defaults to
                           'data/output' relative to current working directory.
            cache_size (int): Size of the LRU cache for query results.
        """
        # Set default data directory if not provided
        if data_dir is None:
            self.data_dir = os.path.join(os.getcwd(), "data", "output")
        else:
            self.data_dir = data_dir
        
        # Verify data directory exists
        if not os.path.exists(self.data_dir):
            logger.warning(f"Data directory {self.data_dir} does not exist. Creating it.")
            os.makedirs(self.data_dir, exist_ok=True)
        
        # Cache size for LRU cache
        self.cache_size = cache_size
        
        # Metrics for monitoring
        self.metrics = {
            "total_reads": 0,
            "cache_hits": 0,
            "read_errors": 0,
            "last_refresh": time.time()
        }
        
        # Column mapping for schema flexibility
        self.column_mapping = {
            # Core columns
            "timestamp": ["timestamp", "time", "date"],
            "ticker": ["ticker", "symbol", "stock"],
            "sentiment": ["sentiment", "sentiment_score", "score"],
            "confidence": ["confidence", "confidence_score", "certainty"],
            "source": ["source", "data_source", "scraper"],
            "model": ["model", "model_name", "sentiment_model"],
            "article_id": ["article_id", "id", "event_id", "uuid"],
            "article_title": ["article_title", "title", "headline"],
            
            # Extended columns
            "text_snippet": ["text_snippet", "content", "text", "snippet"],
            "source_url": ["source_url", "url", "link"],
            "source_credibility": ["source_credibility", "credibility", "reliability"],
            "event_weight": ["event_weight", "weight", "importance"],
            "priority": ["priority", "urgency"],
            "subscription_tier": ["subscription_tier", "tier", "user_tier"]
        }
        
        logger.info(f"ParquetReader initialized with data directory: {self.data_dir}")
    
    def _normalize_column_name(self, table: pa.Table, desired_name: str) -> str:
        """
        Find the actual column name in the table that matches one of the possible
        column names for the desired semantic field.
        
        Args:
            table (pa.Table): PyArrow table
            desired_name (str): Semantic name to find in the table
            
        Returns:
            str: Actual column name in the table, or desired_name if not found
        """
        possible_names = self.column_mapping.get(desired_name, [desired_name])
        schema_fields = table.schema.names
        
        for name in possible_names:
            if name in schema_fields:
                return name
        
        # Return original name if none found (will likely cause an error later)
        return desired_name
    
    def _list_parquet_files(self, ticker: str = None) -> List[str]:
        """
        List Parquet files in the data directory.
        
        Args:
            ticker (str, optional): Filter files by ticker. If provided, returns only the
                                   file for that ticker. If None, returns all files.
                                   
        Returns:
            List[str]: List of Parquet file paths
        """
        if ticker:
            # Look for specific ticker file
            ticker = ticker.lower()
            file_path = os.path.join(self.data_dir, f"{ticker}_sentiment.parquet")
            return [file_path] if os.path.exists(file_path) else []
        else:
            # Get all parquet files
            files = []
            for file in os.listdir(self.data_dir):
                if file.endswith("_sentiment.parquet"):
                    files.append(os.path.join(self.data_dir, file))
            return files
    
    def _get_all_tickers(self) -> Set[str]:
        """
        Get all available ticker symbols from file names.
        
        Returns:
            Set[str]: Set of ticker symbols
        """
        files = self._list_parquet_files()
        tickers = set()
        
        for file in files:
            base_name = os.path.basename(file)
            if base_name == "multi_ticker_sentiment.parquet":
                continue
                
            ticker = base_name.split("_sentiment.parquet")[0].upper()
            tickers.add(ticker)
            
        return tickers
    
    @lru_cache(maxsize=32)
    def get_file_schema(self, file_path: str) -> pa.Schema:
        """
        Get the schema of a Parquet file.
        
        Args:
            file_path (str): Path to Parquet file
            
        Returns:
            pa.Schema: PyArrow schema
        """
        try:
            # Get schema without reading data
            return pq.read_schema(file_path)
        except Exception as e:
            logger.error(f"Error reading schema from {file_path}: {str(e)}")
            self.metrics["read_errors"] += 1
            return None
    
    @lru_cache(maxsize=128)
    def read_ticker_data(self, ticker: str) -> pd.DataFrame:
        """
        Read sentiment data for a specific ticker.
        
        Args:
            ticker (str): Ticker symbol
            
        Returns:
            pd.DataFrame: DataFrame containing sentiment data
        """
        self.metrics["total_reads"] += 1
        
        try:
            file_path = os.path.join(self.data_dir, f"{ticker.lower()}_sentiment.parquet")
            
            if not os.path.exists(file_path):
                logger.warning(f"No data file found for ticker {ticker}")
                return pd.DataFrame()
                
            # Read Parquet file to pandas DataFrame
            df = pd.read_parquet(file_path)
            
            # Sort by timestamp (descending)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp', ascending=False)
            
            return df
        except Exception as e:
            logger.error(f"Error reading data for ticker {ticker}: {str(e)}")
            self.metrics["read_errors"] += 1
            return pd.DataFrame()
    
    def query(self, 
              tickers: Optional[List[str]] = None, 
              start_date: Optional[str] = None,
              end_date: Optional[str] = None,
              sources: Optional[List[str]] = None,
              min_sentiment: Optional[float] = None,
              max_sentiment: Optional[float] = None,
              min_confidence: Optional[float] = None,
              limit: int = 1000,
              models: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Query sentiment data with filtering.
        
        Args:
            tickers: List of ticker symbols to include
            start_date: Start date for filtering (ISO format)
            end_date: End date for filtering (ISO format)
            sources: List of data sources to include
            min_sentiment: Minimum sentiment score
            max_sentiment: Maximum sentiment score
            min_confidence: Minimum confidence score
            limit: Maximum number of results
            models: List of model names to include
            
        Returns:
            pd.DataFrame: DataFrame containing query results
        """
        # Generate cache key for lru_cache
        cache_key = f"{tickers}_{start_date}_{end_date}_{sources}_{min_sentiment}_{max_sentiment}_{min_confidence}_{limit}_{models}"
        
        # Check if we have this query cached
        result = self._cached_query(cache_key)
        if result is not None:
            self.metrics["cache_hits"] += 1
            return result
        
        # Determine which files to read
        if tickers:
            # Read specific ticker files
            file_paths = []
            for ticker in tickers:
                file_paths.extend(self._list_parquet_files(ticker))
            
            # Always include multi-ticker file
            multi_file = os.path.join(self.data_dir, "multi_ticker_sentiment.parquet")
            if os.path.exists(multi_file):
                file_paths.append(multi_file)
        else:
            # Read all files
            file_paths = self._list_parquet_files()
        
        # Create dataset for efficient filtering
        try:
            # Create filters using PyArrow's predicate pushdown
            filters = []
            
            if start_date:
                filters.append(('timestamp', '>=', start_date))
            
            if end_date:
                filters.append(('timestamp', '<=', end_date))
            
            if min_sentiment is not None:
                filters.append(('sentiment', '>=', min_sentiment))
            
            if max_sentiment is not None:
                filters.append(('sentiment', '<=', max_sentiment))
            
            if min_confidence is not None:
                filters.append(('confidence', '>=', min_confidence))
            
            # Create dataset with filters
            dataset = ds.dataset(file_paths, format='parquet')
            
            # Apply filters that PyArrow can push down
            if filters:
                scanner = dataset.scanner(filter=ds.field('timestamp') != '')  # Start with a dummy filter
                for column, op, value in filters:
                    try:
                        field = ds.field(column)
                        if op == '>=':
                            scanner = scanner.filter(field >= value)
                        elif op == '<=':
                            scanner = scanner.filter(field <= value)
                        elif op == '==':
                            scanner = scanner.filter(field == value)
                    except Exception as e:
                        logger.warning(f"Filter error for {column} {op} {value}: {str(e)}")
            else:
                scanner = dataset.scanner()
            
            # Read into a table
            table = scanner.to_table()
            
            # Convert to pandas for post-filtering
            df = table.to_pandas()
            
            # Apply filters that couldn't be pushed down
            if sources:
                df = df[df['source'].isin(sources)]
            
            if models:
                df = df[df['model'].isin(models)]
            
            if tickers and 'ticker' in df.columns:
                df = df[df['ticker'].isin([t.upper() for t in tickers])]
            
            # Sort by timestamp (descending)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.sort_values('timestamp', ascending=False)
            
            # Apply limit
            df = df.head(limit)
            
            # Cache and return
            self._cached_query.cache_clear()  # Clear old entries
            self._cache_query(cache_key, df)
            
            return df
        except Exception as e:
            logger.error(f"Error querying sentiment data: {str(e)}")
            self.metrics["read_errors"] += 1
            return pd.DataFrame()
    
    @lru_cache(maxsize=128)
    def _cached_query(self, cache_key: str) -> Optional[pd.DataFrame]:
        """
        Cached query function wrapped with lru_cache.
        
        Args:
            cache_key (str): Cache key
            
        Returns:
            Optional[pd.DataFrame]: Cached DataFrame or None
        """
        # This function is a placeholder for the lru_cache decorator
        # It will never be called directly, but rather through the lru_cache mechanism
        return None
    
    def _cache_query(self, cache_key: str, df: pd.DataFrame) -> None:
        """
        Cache a query result.
        
        Args:
            cache_key (str): Cache key
            df (pd.DataFrame): DataFrame to cache
        """
        # Store in the lru_cache by calling the cached function
        # This is a workaround to make the cache both accessible and persistent
        self._cached_query.__wrapped__.__dict__[cache_key] = df
    
    def get_all_tickers(self) -> List[str]:
        """
        Get all available ticker symbols.
        
        Returns:
            List[str]: List of ticker symbols
        """
        return sorted(list(self._get_all_tickers()))
    
    def get_latest_events(self, limit: int = 100) -> pd.DataFrame:
        """
        Get the most recent sentiment events across all tickers.
        
        Args:
            limit (int): Maximum number of events to return
            
        Returns:
            pd.DataFrame: DataFrame containing the latest events
        """
        # Get all sentiment data for the last 24 hours
        end_date = datetime.now().isoformat()
        start_date = (datetime.now() - timedelta(days=1)).isoformat()
        
        df = self.query(start_date=start_date, end_date=end_date, limit=limit)
        
        # Sort by timestamp (descending)
        if not df.empty and 'timestamp' in df.columns:
            df = df.sort_values('timestamp', ascending=False)
            
        return df.head(limit)
    
    def get_average_sentiment(self, ticker: str, days: int = 7) -> float:
        """
        Get the average sentiment for a ticker over a period.
        
        Args:
            ticker (str): Ticker symbol
            days (int): Number of days to average
            
        Returns:
            float: Average sentiment score
        """
        # Set date range
        end_date = datetime.now().isoformat()
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Query data
        df = self.query(
            tickers=[ticker],
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate weighted average based on confidence
        if not df.empty and 'sentiment' in df.columns and 'confidence' in df.columns:
            # Replace NaN with default values
            df['sentiment'] = df['sentiment'].fillna(0)
            df['confidence'] = df['confidence'].fillna(0.5)
            
            # Calculate weighted average
            if 'event_weight' in df.columns:
                # Use event_weight if available
                weights = df['confidence'] * df['event_weight']
            else:
                weights = df['confidence']
                
            # Handle edge case of zero weights
            if weights.sum() == 0:
                return 0
                
            # Calculate weighted average
            weighted_avg = (df['sentiment'] * weights).sum() / weights.sum()
            return float(weighted_avg)
        
        return 0.0
    
    def get_sentiment_distribution(self, ticker: str, days: int = 30) -> Dict[str, int]:
        """
        Get the distribution of sentiment scores for a ticker.
        
        Args:
            ticker (str): Ticker symbol
            days (int): Number of days to include
            
        Returns:
            Dict[str, int]: Distribution of sentiment categories
        """
        # Set date range
        end_date = datetime.now().isoformat()
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Query data
        df = self.query(
            tickers=[ticker],
            start_date=start_date,
            end_date=end_date
        )
        
        # Count sentiment categories
        distribution = {
            "positive": 0,
            "neutral": 0,
            "negative": 0
        }
        
        if not df.empty and 'sentiment' in df.columns:
            # Categorize sentiment scores
            for score in df['sentiment']:
                if score > 0.3:
                    distribution["positive"] += 1
                elif score < -0.3:
                    distribution["negative"] += 1
                else:
                    distribution["neutral"] += 1
        
        return distribution
    
    def get_sentiment_by_source(self, ticker: str, days: int = 7) -> Dict[str, float]:
        """
        Get average sentiment scores by source.
        
        Args:
            ticker (str): Ticker symbol
            days (int): Number of days to include
            
        Returns:
            Dict[str, float]: Average sentiment by source
        """
        # Set date range
        end_date = datetime.now().isoformat()
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Query data
        df = self.query(
            tickers=[ticker],
            start_date=start_date,
            end_date=end_date
        )
        
        # Calculate average by source
        result = {}
        
        if not df.empty and 'sentiment' in df.columns and 'source' in df.columns:
            # Group by source and calculate average
            grouped = df.groupby('source')['sentiment'].mean()
            
            # Convert to dictionary
            for source, avg in grouped.items():
                result[source] = float(avg)
        
        return result
    
    def get_sentiment_trend(self, ticker: str, days: int = 30, interval: str = 'D') -> pd.DataFrame:
        """
        Get sentiment trend over time.
        
        Args:
            ticker (str): Ticker symbol
            days (int): Number of days to include
            interval (str): Resampling interval (D=daily, H=hourly, etc.)
            
        Returns:
            pd.DataFrame: DataFrame with sentiment trend
        """
        # Set date range
        end_date = datetime.now().isoformat()
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Query data
        df = self.query(
            tickers=[ticker],
            start_date=start_date,
            end_date=end_date
        )
        
        # Create trend data
        if not df.empty and 'timestamp' in df.columns and 'sentiment' in df.columns:
            # Ensure timestamp is datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Set timestamp as index
            df = df.set_index('timestamp')
            
            # Resample by interval and calculate average
            resampled = df['sentiment'].resample(interval).mean()
            
            # Fill NaN values with forward fill, then backward fill
            resampled = resampled.fillna(method='ffill').fillna(method='bfill')
            
            # Reset index to get timestamp as column
            trend_df = resampled.reset_index()
            trend_df.columns = ['timestamp', 'sentiment']
            
            return trend_df
        
        # Return empty DataFrame with correct columns
        return pd.DataFrame(columns=['timestamp', 'sentiment'])
    
    def clear_cache(self):
        """Clear all cached data."""
        self.read_ticker_data.cache_clear()
        self._cached_query.cache_clear()
        self.get_file_schema.cache_clear()
        logger.info("Cache cleared")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get metrics for monitoring.
        
        Returns:
            Dict[str, Any]: Dictionary of metrics
        """
        # Update last refresh time
        self.metrics["last_refresh"] = time.time()
        
        # Calculate cache hit ratio
        total = max(1, self.metrics["total_reads"])  # Avoid division by zero
        self.metrics["cache_hit_ratio"] = self.metrics["cache_hits"] / total
        
        return self.metrics