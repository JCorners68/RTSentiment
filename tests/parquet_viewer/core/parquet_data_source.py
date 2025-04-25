"""
Parquet data source module for the Parquet Query Viewer.

This module provides the ParquetDataSource class for connecting to and querying
Parquet files using PyArrow.
"""
import os
import glob
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple, Set, Iterator

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc
from pyarrow.dataset import dataset

from .cache_manager import CacheManager

logger = logging.getLogger(__name__)


class ParquetDataSource:
    """
    A data source for connecting to Parquet files using PyArrow.
    
    This class provides methods for querying Parquet files, filtering data by various
    parameters, and efficiently processing large datasets.
    
    Attributes:
        base_path (str): The base directory path for Parquet files
        cache_manager (CacheManager): The cache manager for query results
        available_files (List[str]): List of available Parquet files
        schema_cache (Dict[str, pa.Schema]): Cache of Parquet file schemas
    """
    
    def __init__(self, base_path: str, cache_enabled: bool = True, cache_ttl: int = 3600):
        """
        Initialize the ParquetDataSource.
        
        Args:
            base_path (str): The base directory path for Parquet files
            cache_enabled (bool): Whether to enable caching of query results
            cache_ttl (int): Time-to-live for cached results in seconds
        
        Raises:
            ValueError: If the base_path does not exist
        """
        if not os.path.exists(base_path):
            raise ValueError(f"Base path does not exist: {base_path}")
        
        self.base_path = base_path
        self.cache_manager = CacheManager(enabled=cache_enabled, ttl=cache_ttl)
        self.available_files = self._discover_files()
        self.schema_cache: Dict[str, pa.Schema] = {}
        
        # Load schemas for all available files
        for file_path in self.available_files:
            try:
                self.schema_cache[file_path] = pq.read_schema(file_path)
            except Exception as e:
                logger.warning(f"Failed to read schema for {file_path}: {e}")
        
        logger.info(f"Initialized ParquetDataSource with {len(self.available_files)} files")
        
    def _discover_files(self) -> List[str]:
        """
        Discover available Parquet files in the base directory.
        
        Returns:
            List[str]: List of absolute paths to Parquet files
        """
        parquet_files = []
        
        # Search for .parquet files in the base directory and subdirectories
        for path in glob.glob(os.path.join(self.base_path, "**", "*.parquet"), recursive=True):
            if os.path.isfile(path):
                parquet_files.append(os.path.abspath(path))
        
        logger.debug(f"Discovered {len(parquet_files)} Parquet files")
        return parquet_files
    
    def refresh_files(self) -> None:
        """
        Refresh the list of available Parquet files.
        
        This method updates the available_files attribute by rediscovering
        Parquet files in the base directory.
        """
        logger.debug("Refreshing Parquet file list")
        self.available_files = self._discover_files()
        
        # Update schema cache with any new files
        for file_path in self.available_files:
            if file_path not in self.schema_cache:
                try:
                    self.schema_cache[file_path] = pq.read_schema(file_path)
                except Exception as e:
                    logger.warning(f"Failed to read schema for {file_path}: {e}")
    
    def get_available_tickers(self) -> Set[str]:
        """
        Get a set of all available ticker symbols from Parquet files.
        
        Returns:
            Set[str]: Set of unique ticker symbols
        """
        # Use cache if available
        cache_key = "available_tickers"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        tickers = set()
        
        # Extract tickers from file names
        for file_path in self.available_files:
            filename = os.path.basename(file_path)
            if "_sentiment.parquet" in filename:
                ticker = filename.split("_sentiment.parquet")[0].upper()
                tickers.add(ticker)
        
        # Cache result
        self.cache_manager.set(cache_key, tickers)
        
        return tickers
    
    def get_schema(self, file_path: str) -> Optional[pa.Schema]:
        """
        Get the schema for a specific Parquet file.
        
        Args:
            file_path (str): Path to the Parquet file
            
        Returns:
            Optional[pa.Schema]: The PyArrow schema or None if not found
        """
        if file_path in self.schema_cache:
            return self.schema_cache[file_path]
        
        try:
            schema = pq.read_schema(file_path)
            self.schema_cache[file_path] = schema
            return schema
        except Exception as e:
            logger.error(f"Failed to read schema for {file_path}: {e}")
            return None
    
    def get_ticker_file(self, ticker: str) -> Optional[str]:
        """
        Get the Parquet file path for a specific ticker.
        
        Args:
            ticker (str): The ticker symbol
            
        Returns:
            Optional[str]: The file path or None if not found
        """
        ticker = ticker.lower()
        ticker_file = f"{ticker}_sentiment.parquet"
        
        for file_path in self.available_files:
            if os.path.basename(file_path) == ticker_file:
                return file_path
        
        return None
    
    def query_ticker(
        self,
        ticker: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sources: Optional[List[str]] = None,
        sentiment_range: Optional[Tuple[float, float]] = None,
        limit: Optional[int] = None,
        sort_by: Optional[str] = None,
        ascending: bool = True
    ) -> pd.DataFrame:
        """
        Query sentiment data for a specific ticker.
        
        Args:
            ticker (str): The ticker symbol
            start_date (Optional[datetime]): Start date for filtering
            end_date (Optional[datetime]): End date for filtering
            sources (Optional[List[str]]): List of sources to include
            sentiment_range (Optional[Tuple[float, float]]): Range of sentiment values
            limit (Optional[int]): Maximum number of rows to return
            sort_by (Optional[str]): Column to sort by
            ascending (bool): Sort in ascending order if True
            
        Returns:
            pd.DataFrame: DataFrame containing query results
            
        Raises:
            ValueError: If the ticker file cannot be found
        """
        # Generate cache key
        cache_key = f"ticker_{ticker}_{start_date}_{end_date}_{sources}_{sentiment_range}_{limit}_{sort_by}_{ascending}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Find the Parquet file for the ticker
        file_path = self.get_ticker_file(ticker)
        if not file_path:
            raise ValueError(f"No data file found for ticker: {ticker}")
        
        # Build filter expressions
        filters = []
        
        # Date filters
        if start_date:
            start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
            filters.append(("timestamp", ">=", start_date_str))
        
        if end_date:
            end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")
            filters.append(("timestamp", "<=", end_date_str))
        
        # Source filter
        if sources:
            filters.append(("source", "in", sources))
        
        # Sentiment range filter
        if sentiment_range:
            filters.append(("sentiment", ">=", sentiment_range[0]))
            filters.append(("sentiment", "<=", sentiment_range[1]))
        
        # Read data with filters
        try:
            # Create a PyArrow dataset for better filtering performance
            ds = dataset(file_path, format="parquet")
            
            # Apply filters
            scanner = ds.scanner()
            for col, op, val in filters:
                if op == ">=":
                    scanner = scanner.filter(pc.field(col) >= val)
                elif op == "<=":
                    scanner = scanner.filter(pc.field(col) <= val)
                elif op == "==":
                    scanner = scanner.filter(pc.field(col) == val)
                elif op == "!=":
                    scanner = scanner.filter(pc.field(col) != val)
                elif op == "in":
                    # Handle 'in' operator for lists
                    in_filter = pc.is_in(pc.field(col), pa.array(val))
                    scanner = scanner.filter(in_filter)
            
            # Execute the query and convert to pandas
            table = scanner.to_table()
            df = table.to_pandas()
            
            # Apply sorting
            if sort_by and sort_by in df.columns:
                df = df.sort_values(by=sort_by, ascending=ascending)
            
            # Apply limit
            if limit:
                df = df.head(limit)
            
            # Cache result
            self.cache_manager.set(cache_key, df)
            
            return df
        except Exception as e:
            logger.error(f"Error querying ticker {ticker}: {e}")
            raise
    
    def query_multi_ticker(
        self,
        tickers: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sources: Optional[List[str]] = None,
        sentiment_range: Optional[Tuple[float, float]] = None,
        limit: Optional[int] = None,
        sort_by: Optional[str] = None,
        ascending: bool = True
    ) -> pd.DataFrame:
        """
        Query sentiment data for multiple tickers.
        
        Args:
            tickers (List[str]): List of ticker symbols
            start_date (Optional[datetime]): Start date for filtering
            end_date (Optional[datetime]): End date for filtering
            sources (Optional[List[str]]): List of sources to include
            sentiment_range (Optional[Tuple[float, float]]): Range of sentiment values
            limit (Optional[int]): Maximum number of rows to return
            sort_by (Optional[str]): Column to sort by
            ascending (bool): Sort in ascending order if True
            
        Returns:
            pd.DataFrame: DataFrame containing query results
        """
        # Generate cache key
        cache_key = f"multi_ticker_{tickers}_{start_date}_{end_date}_{sources}_{sentiment_range}_{limit}_{sort_by}_{ascending}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        all_results = []
        
        # Query each ticker separately
        for ticker in tickers:
            try:
                df = self.query_ticker(
                    ticker=ticker,
                    start_date=start_date,
                    end_date=end_date,
                    sources=sources,
                    sentiment_range=sentiment_range,
                    limit=None,  # Don't limit individual queries
                    sort_by=sort_by,
                    ascending=ascending
                )
                all_results.append(df)
            except ValueError:
                # Skip tickers with no data file
                logger.warning(f"No data file found for ticker: {ticker}")
                continue
            except Exception as e:
                logger.error(f"Error querying ticker {ticker}: {e}")
                continue
        
        if not all_results:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=["timestamp", "ticker", "sentiment", "confidence", 
                                         "source", "model", "article_id", "article_title"])
        
        # Combine results
        combined_df = pd.concat(all_results, ignore_index=True)
        
        # Apply sorting on combined results
        if sort_by and sort_by in combined_df.columns:
            combined_df = combined_df.sort_values(by=sort_by, ascending=ascending)
        
        # Apply limit on combined results
        if limit:
            combined_df = combined_df.head(limit)
        
        # Cache result
        self.cache_manager.set(cache_key, combined_df)
        
        return combined_df
    
    def query_by_source(
        self,
        source: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = None,
        sort_by: Optional[str] = None,
        ascending: bool = True
    ) -> pd.DataFrame:
        """
        Query sentiment data by source.
        
        Args:
            source (str): The source to filter by
            start_date (Optional[datetime]): Start date for filtering
            end_date (Optional[datetime]): End date for filtering
            limit (Optional[int]): Maximum number of rows to return
            sort_by (Optional[str]): Column to sort by
            ascending (bool): Sort in ascending order if True
            
        Returns:
            pd.DataFrame: DataFrame containing query results
        """
        # Generate cache key
        cache_key = f"source_{source}_{start_date}_{end_date}_{limit}_{sort_by}_{ascending}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        all_results = []
        
        # Query all files and filter by source
        for file_path in self.available_files:
            try:
                # Create a PyArrow dataset
                ds = dataset(file_path, format="parquet")
                
                # Build filters
                filters = [pc.field("source") == source]
                
                # Add date filters
                if start_date:
                    start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
                    filters.append(pc.field("timestamp") >= start_date_str)
                
                if end_date:
                    end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")
                    filters.append(pc.field("timestamp") <= end_date_str)
                
                # Apply filters
                scanner = ds.scanner()
                for filter_expr in filters:
                    scanner = scanner.filter(filter_expr)
                
                # Execute the query and convert to pandas
                table = scanner.to_table()
                if table.num_rows > 0:
                    df = table.to_pandas()
                    all_results.append(df)
            except Exception as e:
                logger.error(f"Error querying file {file_path} for source {source}: {e}")
                continue
        
        if not all_results:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=["timestamp", "ticker", "sentiment", "confidence", 
                                         "source", "model", "article_id", "article_title"])
        
        # Combine results
        combined_df = pd.concat(all_results, ignore_index=True)
        
        # Apply sorting
        if sort_by and sort_by in combined_df.columns:
            combined_df = combined_df.sort_values(by=sort_by, ascending=ascending)
        
        # Apply limit
        if limit:
            combined_df = combined_df.head(limit)
        
        # Cache result
        self.cache_manager.set(cache_key, combined_df)
        
        return combined_df
    
    def query_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        tickers: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        sentiment_range: Optional[Tuple[float, float]] = None,
        limit: Optional[int] = None,
        sort_by: Optional[str] = None,
        ascending: bool = True
    ) -> pd.DataFrame:
        """
        Query sentiment data for a specific date range.
        
        Args:
            start_date (datetime): Start date for filtering
            end_date (datetime): End date for filtering
            tickers (Optional[List[str]]): List of ticker symbols to include
            sources (Optional[List[str]]): List of sources to include
            sentiment_range (Optional[Tuple[float, float]]): Range of sentiment values
            limit (Optional[int]): Maximum number of rows to return
            sort_by (Optional[str]): Column to sort by
            ascending (bool): Sort in ascending order if True
            
        Returns:
            pd.DataFrame: DataFrame containing query results
        """
        # Generate cache key
        cache_key = f"date_range_{start_date}_{end_date}_{tickers}_{sources}_{sentiment_range}_{limit}_{sort_by}_{ascending}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Convert dates to strings for filtering
        start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S")
        end_date_str = end_date.strftime("%Y-%m-%dT%H:%M:%S")
        
        all_results = []
        
        # Determine which files to query
        files_to_query = self.available_files
        if tickers:
            # Filter files by ticker
            ticker_files = []
            for ticker in tickers:
                file_path = self.get_ticker_file(ticker)
                if file_path:
                    ticker_files.append(file_path)
            files_to_query = ticker_files
        
        # Query each file
        for file_path in files_to_query:
            try:
                # Create a PyArrow dataset
                ds = dataset(file_path, format="parquet")
                
                # Build filters
                filters = [
                    pc.field("timestamp") >= start_date_str,
                    pc.field("timestamp") <= end_date_str
                ]
                
                # Add source filter
                if sources:
                    source_filter = pc.is_in(pc.field("source"), pa.array(sources))
                    filters.append(source_filter)
                
                # Add sentiment range filter
                if sentiment_range:
                    filters.append(pc.field("sentiment") >= sentiment_range[0])
                    filters.append(pc.field("sentiment") <= sentiment_range[1])
                
                # Apply filters
                scanner = ds.scanner()
                for filter_expr in filters:
                    scanner = scanner.filter(filter_expr)
                
                # Execute the query and convert to pandas
                table = scanner.to_table()
                if table.num_rows > 0:
                    df = table.to_pandas()
                    all_results.append(df)
            except Exception as e:
                logger.error(f"Error querying file {file_path} for date range: {e}")
                continue
        
        if not all_results:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=["timestamp", "ticker", "sentiment", "confidence", 
                                         "source", "model", "article_id", "article_title"])
        
        # Combine results
        combined_df = pd.concat(all_results, ignore_index=True)
        
        # Apply sorting
        if sort_by and sort_by in combined_df.columns:
            combined_df = combined_df.sort_values(by=sort_by, ascending=ascending)
        
        # Apply limit
        if limit:
            combined_df = combined_df.head(limit)
        
        # Cache result
        self.cache_manager.set(cache_key, combined_df)
        
        return combined_df
    
    def aggregate_sentiment_by_ticker(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tickers: Optional[List[str]] = None,
        sources: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Aggregate sentiment data by ticker.
        
        Args:
            start_date (Optional[datetime]): Start date for filtering
            end_date (Optional[datetime]): End date for filtering
            tickers (Optional[List[str]]): List of ticker symbols to include
            sources (Optional[List[str]]): List of sources to include
            
        Returns:
            pd.DataFrame: DataFrame with aggregated sentiment by ticker
        """
        # Generate cache key
        cache_key = f"agg_by_ticker_{start_date}_{end_date}_{tickers}_{sources}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Get data for the specified parameters
        if tickers:
            df = self.query_multi_ticker(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                sources=sources
            )
        else:
            df = self.query_date_range(
                start_date=start_date or datetime(1900, 1, 1),
                end_date=end_date or datetime(2100, 1, 1),
                sources=sources
            )
        
        # Group by ticker and calculate aggregates
        if df.empty:
            return pd.DataFrame(columns=["ticker", "count", "avg_sentiment", "min_sentiment", 
                                         "max_sentiment", "std_sentiment"])
        
        agg_df = df.groupby("ticker").agg(
            count=pd.NamedAgg(column="sentiment", aggfunc="count"),
            avg_sentiment=pd.NamedAgg(column="sentiment", aggfunc="mean"),
            min_sentiment=pd.NamedAgg(column="sentiment", aggfunc="min"),
            max_sentiment=pd.NamedAgg(column="sentiment", aggfunc="max"),
            std_sentiment=pd.NamedAgg(column="sentiment", aggfunc="std")
        ).reset_index()
        
        # Fill NaN values in std_sentiment (occurs when count=1)
        agg_df["std_sentiment"] = agg_df["std_sentiment"].fillna(0)
        
        # Sort by count in descending order
        agg_df = agg_df.sort_values(by="count", ascending=False)
        
        # Cache result
        self.cache_manager.set(cache_key, agg_df)
        
        return agg_df
    
    def aggregate_sentiment_by_source(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        tickers: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Aggregate sentiment data by source.
        
        Args:
            start_date (Optional[datetime]): Start date for filtering
            end_date (Optional[datetime]): End date for filtering
            tickers (Optional[List[str]]): List of ticker symbols to include
            
        Returns:
            pd.DataFrame: DataFrame with aggregated sentiment by source
        """
        # Generate cache key
        cache_key = f"agg_by_source_{start_date}_{end_date}_{tickers}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Get data for the specified parameters
        if tickers:
            df = self.query_multi_ticker(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date
            )
        else:
            df = self.query_date_range(
                start_date=start_date or datetime(1900, 1, 1),
                end_date=end_date or datetime(2100, 1, 1)
            )
        
        # Group by source and calculate aggregates
        if df.empty:
            return pd.DataFrame(columns=["source", "count", "avg_sentiment", "min_sentiment", 
                                         "max_sentiment", "std_sentiment"])
        
        agg_df = df.groupby("source").agg(
            count=pd.NamedAgg(column="sentiment", aggfunc="count"),
            avg_sentiment=pd.NamedAgg(column="sentiment", aggfunc="mean"),
            min_sentiment=pd.NamedAgg(column="sentiment", aggfunc="min"),
            max_sentiment=pd.NamedAgg(column="sentiment", aggfunc="max"),
            std_sentiment=pd.NamedAgg(column="sentiment", aggfunc="std")
        ).reset_index()
        
        # Fill NaN values in std_sentiment (occurs when count=1)
        agg_df["std_sentiment"] = agg_df["std_sentiment"].fillna(0)
        
        # Sort by count in descending order
        agg_df = agg_df.sort_values(by="count", ascending=False)
        
        # Cache result
        self.cache_manager.set(cache_key, agg_df)
        
        return agg_df
    
    def aggregate_sentiment_by_date(
        self,
        start_date: datetime,
        end_date: datetime,
        tickers: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        freq: str = "D"
    ) -> pd.DataFrame:
        """
        Aggregate sentiment data by date.
        
        Args:
            start_date (datetime): Start date for filtering
            end_date (datetime): End date for filtering
            tickers (Optional[List[str]]): List of ticker symbols to include
            sources (Optional[List[str]]): List of sources to include
            freq (str): Frequency for resampling ('D' for daily, 'W' for weekly, etc.)
            
        Returns:
            pd.DataFrame: DataFrame with aggregated sentiment by date
        """
        # Generate cache key
        cache_key = f"agg_by_date_{start_date}_{end_date}_{tickers}_{sources}_{freq}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Get data for the specified parameters
        if tickers:
            df = self.query_multi_ticker(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                sources=sources
            )
        else:
            df = self.query_date_range(
                start_date=start_date,
                end_date=end_date,
                sources=sources
            )
        
        # Process timestamp column
        if df.empty:
            return pd.DataFrame(columns=["date", "count", "avg_sentiment", "min_sentiment", 
                                         "max_sentiment", "std_sentiment"])
        
        # Convert timestamp to datetime if it's not already
        if df["timestamp"].dtype == object:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        
        # Set timestamp as index for resampling
        df = df.set_index("timestamp")
        
        # Resample by the specified frequency and calculate aggregates
        agg_df = df.resample(freq).agg(
            count=pd.NamedAgg(column="sentiment", aggfunc="count"),
            avg_sentiment=pd.NamedAgg(column="sentiment", aggfunc="mean"),
            min_sentiment=pd.NamedAgg(column="sentiment", aggfunc="min"),
            max_sentiment=pd.NamedAgg(column="sentiment", aggfunc="max"),
            std_sentiment=pd.NamedAgg(column="sentiment", aggfunc="std")
        ).reset_index()
        
        # Rename timestamp column to date
        agg_df = agg_df.rename(columns={"timestamp": "date"})
        
        # Fill NaN values in std_sentiment (occurs when count=1)
        agg_df["std_sentiment"] = agg_df["std_sentiment"].fillna(0)
        
        # Cache result
        self.cache_manager.set(cache_key, agg_df)
        
        return agg_df
    
    def get_sentiment_histogram(
        self,
        ticker: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        sources: Optional[List[str]] = None,
        bins: int = 10
    ) -> Dict[str, Any]:
        """
        Get histogram data for sentiment values.
        
        Args:
            ticker (Optional[str]): Ticker symbol to filter by
            start_date (Optional[datetime]): Start date for filtering
            end_date (Optional[datetime]): End date for filtering
            sources (Optional[List[str]]): List of sources to include
            bins (int): Number of bins for the histogram
            
        Returns:
            Dict[str, Any]: Dictionary with histogram data
        """
        # Generate cache key
        cache_key = f"histogram_{ticker}_{start_date}_{end_date}_{sources}_{bins}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Get data for the specified parameters
        if ticker:
            df = self.query_ticker(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                sources=sources
            )
        else:
            df = self.query_date_range(
                start_date=start_date or datetime(1900, 1, 1),
                end_date=end_date or datetime(2100, 1, 1),
                sources=sources
            )
        
        # Calculate histogram
        if df.empty:
            return {"bins": [], "counts": [], "total": 0}
        
        hist, bin_edges = np.histogram(df["sentiment"], bins=bins)
        
        # Prepare result
        result = {
            "bins": [float(x) for x in bin_edges[:-1]],  # Convert to Python float
            "counts": [int(x) for x in hist],  # Convert to Python int
            "total": int(df.shape[0])
        }
        
        # Cache result
        self.cache_manager.set(cache_key, result)
        
        return result
    
    def execute_raw_query(
        self,
        query_func,
        file_paths: Optional[List[str]] = None
    ) -> Union[pd.DataFrame, Dict[str, Any]]:
        """
        Execute a raw query function on the specified Parquet files.
        
        This method allows for custom query logic to be applied to the Parquet files.
        
        Args:
            query_func: A function that takes a PyArrow Table as input and returns
                        a processed result
            file_paths (Optional[List[str]]): Paths to the Parquet files to query.
                                              If None, all available files are used.
            
        Returns:
            Union[pd.DataFrame, Dict[str, Any]]: The result of the query function
            
        Note:
            This method bypasses caching for raw queries.
        """
        if file_paths is None:
            file_paths = self.available_files
        
        all_results = []
        
        for file_path in file_paths:
            try:
                # Read the file
                table = pq.read_table(file_path)
                
                # Apply the query function
                result = query_func(table)
                
                # Process the result based on its type
                if isinstance(result, pa.Table):
                    all_results.append(result.to_pandas())
                elif isinstance(result, pd.DataFrame):
                    all_results.append(result)
                else:
                    # If the result is not a table or DataFrame, return it directly
                    return result
            except Exception as e:
                logger.error(f"Error executing raw query on {file_path}: {e}")
                continue
        
        if not all_results:
            # Return empty DataFrame if no results
            return pd.DataFrame()
        
        # Combine results if they are DataFrames
        return pd.concat(all_results, ignore_index=True)
    
    def get_file_stats(self) -> List[Dict[str, Any]]:
        """
        Get statistics for all available Parquet files.
        
        Returns:
            List[Dict[str, Any]]: List of dictionaries with file statistics
        """
        # Generate cache key
        cache_key = "file_stats"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        stats = []
        
        for file_path in self.available_files:
            try:
                # Get file information
                file_size = os.path.getsize(file_path)
                last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                # Read metadata
                metadata = pq.read_metadata(file_path)
                
                # Extract ticker from filename
                filename = os.path.basename(file_path)
                ticker = filename.split("_sentiment.parquet")[0].upper()
                
                # Create stats entry
                stats_entry = {
                    "file_path": file_path,
                    "ticker": ticker,
                    "size_bytes": file_size,
                    "size_human": self._format_file_size(file_size),
                    "last_modified": last_modified,
                    "num_rows": metadata.num_rows,
                    "num_row_groups": metadata.num_row_groups,
                    "schema": [field.name for field in self.schema_cache.get(file_path, [])]
                }
                
                stats.append(stats_entry)
            except Exception as e:
                logger.error(f"Error getting stats for {file_path}: {e}")
                continue
        
        # Cache result
        self.cache_manager.set(cache_key, stats)
        
        return stats
    
    def _format_file_size(self, size_bytes: int) -> str:
        """
        Format file size in a human-readable format.
        
        Args:
            size_bytes (int): File size in bytes
            
        Returns:
            str: Formatted file size string
        """
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024 or unit == 'TB':
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024