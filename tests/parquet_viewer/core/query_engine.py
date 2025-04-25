"""
Query engine module for the Parquet Query Viewer.

This module provides the QueryEngine class for processing and executing
queries on Parquet data.
"""
import re
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Tuple, Set, Iterator

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.compute as pc
import numpy as np

from .parquet_data_source import ParquetDataSource
from .cache_manager import CacheManager
from .utils import DataFormatter, ExportManager

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    A query engine for processing and executing queries on Parquet data.
    
    This class provides methods for translating user queries into PyArrow operations,
    handling aggregations and transformations, and returning results in standardized formats.
    
    Attributes:
        data_source (ParquetDataSource): The Parquet data source
        cache_manager (CacheManager): The cache manager for query results
        formatter (DataFormatter): The data formatter for results
        export_manager (ExportManager): The export manager for results
    """
    
    def __init__(
        self,
        data_source: ParquetDataSource,
        cache_enabled: bool = True,
        cache_ttl: int = 3600
    ):
        """
        Initialize the QueryEngine.
        
        Args:
            data_source (ParquetDataSource): The Parquet data source
            cache_enabled (bool): Whether to enable caching of query results
            cache_ttl (int): Time-to-live for cached results in seconds
        """
        self.data_source = data_source
        self.cache_manager = CacheManager(enabled=cache_enabled, ttl=cache_ttl)
        self.formatter = DataFormatter()
        self.export_manager = ExportManager()
        
        logger.info("Initialized QueryEngine")
    
    def parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse a date string into a datetime object.
        
        Args:
            date_str (str): The date string to parse
            
        Returns:
            Optional[datetime]: The parsed datetime object, or None if parsing fails
            
        Note:
            This method supports various date formats, including:
            - ISO format (2025-04-23, 2025-04-23T12:34:56)
            - Relative dates (today, yesterday, 1d, 1w, 1m, 1y)
        """
        # Check for None or empty string
        if not date_str:
            return None
        
        try:
            # Handle ISO format
            if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
                # If time is not included, default to midnight
                if 'T' not in date_str and ' ' not in date_str:
                    date_str += 'T00:00:00'
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            
            # Handle relative dates
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if date_str.lower() == 'today':
                return today
            
            if date_str.lower() == 'yesterday':
                return today - timedelta(days=1)
            
            # Handle 1d, 1w, 1m, 1y format
            if re.match(r'^\d+[dwmy]$', date_str.lower()):
                value = int(date_str[:-1])
                unit = date_str[-1].lower()
                
                if unit == 'd':
                    return today - timedelta(days=value)
                elif unit == 'w':
                    return today - timedelta(weeks=value)
                elif unit == 'm':
                    # Approximate month as 30 days
                    return today - timedelta(days=value * 30)
                elif unit == 'y':
                    # Approximate year as 365 days
                    return today - timedelta(days=value * 365)
            
            # If all else fails, try generic parsing
            return pd.to_datetime(date_str).to_pydatetime()
        except Exception as e:
            logger.error(f"Error parsing date '{date_str}': {e}")
            return None
    
    def parse_filter_expression(self, filter_expr: str) -> List[Tuple[str, str, Any]]:
        """
        Parse a filter expression into a list of filter tuples.
        
        Args:
            filter_expr (str): The filter expression to parse
            
        Returns:
            List[Tuple[str, str, Any]]: List of (column, operator, value) tuples
            
        Examples:
            "sentiment > 0.5" -> [("sentiment", ">", 0.5)]
            "source = 'Twitter' AND sentiment > 0.5" -> [("source", "=", "Twitter"), ("sentiment", ">", 0.5)]
        """
        if not filter_expr:
            return []
        
        # Split by AND/OR, preserving quoted strings
        def split_preserving_quotes(s, delimiters):
            pattern = '|'.join(map(re.escape, delimiters))
            tokens = []
            current = ''
            in_quotes = False
            
            for char in s:
                if char in ['"', "'"]:
                    in_quotes = not in_quotes
                    current += char
                elif not in_quotes and re.match(pattern, char, re.IGNORECASE):
                    if current.strip():
                        tokens.append(current.strip())
                    tokens.append(char.upper())  # Normalize to uppercase
                    current = ''
                else:
                    current += char
            
            if current.strip():
                tokens.append(current.strip())
            
            return tokens
        
        tokens = split_preserving_quotes(filter_expr, [' AND ', ' OR ', '(', ')'])
        
        # Process the tokens
        filters = []
        i = 0
        while i < len(tokens):
            if tokens[i] in ['AND', 'OR', '(', ')']:
                # Skip logical operators for now (simple implementation)
                i += 1
                continue
            
            # Parse individual condition
            condition_match = re.match(r'(\w+)\s*([=><~!]+)\s*(.+)', tokens[i])
            if condition_match:
                col, op, val = condition_match.groups()
                
                # Clean and parse value
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    # String value
                    val = val[1:-1]  # Remove quotes
                else:
                    # Try to convert to appropriate type
                    try:
                        if '.' in val:
                            val = float(val)
                        else:
                            val = int(val)
                    except ValueError:
                        # Handle special values
                        if val.lower() == 'null':
                            val = None
                        elif val.lower() == 'true':
                            val = True
                        elif val.lower() == 'false':
                            val = False
                        # Otherwise, keep as string
                
                filters.append((col, op, val))
            
            i += 1
        
        return filters
    
    def execute_query(
        self,
        query_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a query based on the specified query type and parameters.
        
        Args:
            query_type (str): The type of query to execute
            parameters (Dict[str, Any]): The query parameters
            
        Returns:
            Dict[str, Any]: Dictionary with query results
            
        Raises:
            ValueError: If an invalid query type is specified
            
        Note:
            Supported query types:
            - "ticker": Query data for a specific ticker
            - "multi_ticker": Query data for multiple tickers
            - "date_range": Query data for a date range
            - "aggregate_by_ticker": Aggregate data by ticker
            - "aggregate_by_source": Aggregate data by source
            - "aggregate_by_date": Aggregate data by date
            - "sentiment_histogram": Get histogram of sentiment values
            - "stats": Get statistics about available data
        """
        # Generate cache key
        cache_key = f"query_{query_type}_{hash(str(parameters))}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Process dates if present in parameters
        date_params = ['start_date', 'end_date']
        for param in date_params:
            if param in parameters and isinstance(parameters[param], str):
                parameters[param] = self.parse_date(parameters[param])
        
        # Process filter expression if present
        if 'filter' in parameters and isinstance(parameters['filter'], str):
            parameters['filters'] = self.parse_filter_expression(parameters['filter'])
        
        # Execute the appropriate query based on query_type
        result: Any = None
        
        if query_type == "ticker":
            # Get the ticker parameter
            ticker = parameters.get('ticker')
            if not ticker:
                raise ValueError("Ticker parameter is required")
            
            # Execute the ticker query
            df = self.data_source.query_ticker(
                ticker=ticker,
                start_date=parameters.get('start_date'),
                end_date=parameters.get('end_date'),
                sources=parameters.get('sources'),
                sentiment_range=parameters.get('sentiment_range'),
                limit=parameters.get('limit'),
                sort_by=parameters.get('sort_by'),
                ascending=parameters.get('ascending', True)
            )
            
            result = self.formatter.format_dataframe(df)
        
        elif query_type == "multi_ticker":
            # Get the tickers parameter
            tickers = parameters.get('tickers', [])
            if not tickers:
                raise ValueError("Tickers parameter is required")
            
            # Execute the multi-ticker query
            df = self.data_source.query_multi_ticker(
                tickers=tickers,
                start_date=parameters.get('start_date'),
                end_date=parameters.get('end_date'),
                sources=parameters.get('sources'),
                sentiment_range=parameters.get('sentiment_range'),
                limit=parameters.get('limit'),
                sort_by=parameters.get('sort_by'),
                ascending=parameters.get('ascending', True)
            )
            
            result = self.formatter.format_dataframe(df)
        
        elif query_type == "date_range":
            # Get the date range parameters
            start_date = parameters.get('start_date')
            end_date = parameters.get('end_date')
            
            if not start_date or not end_date:
                raise ValueError("Start date and end date parameters are required")
            
            # Execute the date range query
            df = self.data_source.query_date_range(
                start_date=start_date,
                end_date=end_date,
                tickers=parameters.get('tickers'),
                sources=parameters.get('sources'),
                sentiment_range=parameters.get('sentiment_range'),
                limit=parameters.get('limit'),
                sort_by=parameters.get('sort_by'),
                ascending=parameters.get('ascending', True)
            )
            
            result = self.formatter.format_dataframe(df)
        
        elif query_type == "aggregate_by_ticker":
            # Execute the aggregate by ticker query
            df = self.data_source.aggregate_sentiment_by_ticker(
                start_date=parameters.get('start_date'),
                end_date=parameters.get('end_date'),
                tickers=parameters.get('tickers'),
                sources=parameters.get('sources')
            )
            
            result = self.formatter.format_dataframe(df)
        
        elif query_type == "aggregate_by_source":
            # Execute the aggregate by source query
            df = self.data_source.aggregate_sentiment_by_source(
                start_date=parameters.get('start_date'),
                end_date=parameters.get('end_date'),
                tickers=parameters.get('tickers')
            )
            
            result = self.formatter.format_dataframe(df)
        
        elif query_type == "aggregate_by_date":
            # Get the date range parameters
            start_date = parameters.get('start_date')
            end_date = parameters.get('end_date')
            
            if not start_date or not end_date:
                raise ValueError("Start date and end date parameters are required")
            
            # Execute the aggregate by date query
            df = self.data_source.aggregate_sentiment_by_date(
                start_date=start_date,
                end_date=end_date,
                tickers=parameters.get('tickers'),
                sources=parameters.get('sources'),
                freq=parameters.get('freq', 'D')
            )
            
            result = self.formatter.format_dataframe(df)
        
        elif query_type == "sentiment_histogram":
            # Execute the sentiment histogram query
            histogram_data = self.data_source.get_sentiment_histogram(
                ticker=parameters.get('ticker'),
                start_date=parameters.get('start_date'),
                end_date=parameters.get('end_date'),
                sources=parameters.get('sources'),
                bins=parameters.get('bins', 10)
            )
            
            result = histogram_data
        
        elif query_type == "stats":
            # Get statistics about available data
            stats = self.data_source.get_file_stats()
            
            result = {
                "file_stats": stats,
                "total_files": len(stats),
                "total_rows": sum(s.get("num_rows", 0) for s in stats),
                "total_size_bytes": sum(s.get("size_bytes", 0) for s in stats),
                "total_size_human": self._format_file_size(sum(s.get("size_bytes", 0) for s in stats)),
                "tickers": sorted(list(set(s.get("ticker", "") for s in stats))),
                "cache_stats": self.cache_manager.get_stats()
            }
        
        else:
            raise ValueError(f"Invalid query type: {query_type}")
        
        # Format and cache the result
        if isinstance(result, Dict):
            formatted_result = result  # Already formatted
        else:
            formatted_result = {"data": result}
        
        # Add metadata to the result
        formatted_result["metadata"] = {
            "query_type": query_type,
            "parameters": {k: str(v) if isinstance(v, (datetime, pd.Timestamp)) else v 
                           for k, v in parameters.items()},
            "timestamp": datetime.now().isoformat(),
            "row_count": len(result["data"]) if isinstance(result, Dict) and "data" in result else 0
        }
        
        # Cache the result
        self.cache_manager.set(cache_key, formatted_result)
        
        return formatted_result
    
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
    
    def export_results(
        self,
        result: Dict[str, Any],
        format: str,
        file_path: Optional[str] = None
    ) -> Union[str, bytes]:
        """
        Export query results to the specified format.
        
        Args:
            result (Dict[str, Any]): Query result to export
            format (str): Export format (e.g., 'csv', 'json', 'excel')
            file_path (Optional[str]): Path to save the exported file
            
        Returns:
            Union[str, bytes]: The exported data as string or bytes
            
        Raises:
            ValueError: If the result format is invalid or unsupported
        """
        if "data" not in result:
            raise ValueError("Invalid result format: missing 'data' key")
        
        data = result["data"]
        
        if isinstance(data, list) and all(isinstance(item, Dict) for item in data):
            # Convert list of dictionaries to DataFrame
            df = pd.DataFrame(data)
        elif isinstance(data, Dict) and "columns" in data and "data" in data:
            # Convert columnar data to DataFrame
            df = pd.DataFrame(data["data"], columns=data["columns"])
        else:
            raise ValueError("Unsupported data format for export")
        
        return self.export_manager.export(df, format, file_path)
    
    def execute_sql_query(self, sql_query: str) -> Dict[str, Any]:
        """
        Execute a SQL-like query on the Parquet data.
        
        Args:
            sql_query (str): SQL-like query string
            
        Returns:
            Dict[str, Any]: Dictionary with query results
            
        Raises:
            ValueError: If the SQL query is invalid
            
        Note:
            This method supports a simplified SQL syntax:
            - SELECT columns FROM table [WHERE conditions] [ORDER BY column [ASC|DESC]] [LIMIT n]
        """
        # Generate cache key
        cache_key = f"sql_query_{hash(sql_query)}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Parse the SQL query
        select_match = re.search(
            r'SELECT\s+(.*?)\s+FROM\s+(\w+)(?:\s+WHERE\s+(.*?))?(?:\s+ORDER\s+BY\s+(.*?)(?:\s+(ASC|DESC))?)?(?:\s+LIMIT\s+(\d+))?$',
            sql_query,
            re.IGNORECASE
        )
        
        if not select_match:
            raise ValueError("Invalid SQL query format")
        
        columns_str, table_name, where_clause, order_by, order_direction, limit_str = select_match.groups()
        
        # Extract ticker from table name
        ticker_match = re.match(r'([A-Za-z0-9]+)_sentiment', table_name)
        if not ticker_match:
            ticker = table_name.upper()
        else:
            ticker = ticker_match.group(1).upper()
        
        # Process columns
        if columns_str.strip() == '*':
            columns = None  # All columns
        else:
            columns = [col.strip() for col in columns_str.split(',')]
        
        # Process limit
        limit = int(limit_str) if limit_str else None
        
        # Process order by
        sort_by = order_by.strip() if order_by else None
        ascending = True if not order_direction or order_direction.upper() == 'ASC' else False
        
        # Process where clause
        filters = []
        if where_clause:
            filters = self.parse_filter_expression(where_clause)
        
        # Convert filters to sentiment range if applicable
        sentiment_range = None
        sources = None
        start_date = None
        end_date = None
        
        for col, op, val in filters:
            if col == 'sentiment':
                if not sentiment_range:
                    sentiment_range = [-float('inf'), float('inf')]
                
                if op == '>':
                    sentiment_range[0] = max(sentiment_range[0], val)
                elif op == '>=':
                    sentiment_range[0] = max(sentiment_range[0], val)
                elif op == '<':
                    sentiment_range[1] = min(sentiment_range[1], val)
                elif op == '<=':
                    sentiment_range[1] = min(sentiment_range[1], val)
            elif col == 'source' and op == '=':
                if not sources:
                    sources = []
                sources.append(val)
            elif col == 'timestamp':
                date_val = self.parse_date(val)
                if not date_val:
                    continue
                
                if op == '>=' or op == '>':
                    start_date = date_val
                elif op == '<=' or op == '<':
                    end_date = date_val
        
        # Execute the query
        try:
            df = self.data_source.query_ticker(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date,
                sources=sources,
                sentiment_range=sentiment_range if sentiment_range else None,
                limit=limit,
                sort_by=sort_by,
                ascending=ascending
            )
            
            # Filter columns if specified
            if columns:
                df = df[columns]
            
            result = self.formatter.format_dataframe(df)
            
            # Add metadata
            result["metadata"] = {
                "query_type": "sql",
                "sql_query": sql_query,
                "timestamp": datetime.now().isoformat(),
                "row_count": len(df)
            }
            
            # Cache the result
            self.cache_manager.set(cache_key, result)
            
            return result
        except Exception as e:
            logger.error(f"Error executing SQL query: {e}")
            raise ValueError(f"Error executing SQL query: {e}")
    
    def build_query(
        self,
        query_builder: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build and execute a query from a query builder specification.
        
        Args:
            query_builder (Dict[str, Any]): Query builder specification
            
        Returns:
            Dict[str, Any]: Dictionary with query results
            
        Raises:
            ValueError: If the query builder specification is invalid
            
        Example query_builder:
        {
            "query_type": "ticker",
            "ticker": "AAPL",
            "start_date": "2025-04-01",
            "end_date": "2025-04-23",
            "sources": ["Twitter", "Reddit"],
            "limit": 100,
            "sort": {
                "column": "sentiment",
                "direction": "desc"
            }
        }
        """
        # Generate cache key
        cache_key = f"builder_query_{hash(str(query_builder))}"
        cached_result = self.cache_manager.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Extract query type
        query_type = query_builder.get("query_type")
        if not query_type:
            raise ValueError("Query type is required")
        
        # Build parameters based on query type
        parameters = {}
        
        # Common parameters
        if "start_date" in query_builder:
            parameters["start_date"] = self.parse_date(query_builder["start_date"])
        
        if "end_date" in query_builder:
            parameters["end_date"] = self.parse_date(query_builder["end_date"])
        
        if "sources" in query_builder:
            parameters["sources"] = query_builder["sources"]
        
        if "limit" in query_builder:
            parameters["limit"] = int(query_builder["limit"])
        
        if "sort" in query_builder and isinstance(query_builder["sort"], Dict):
            parameters["sort_by"] = query_builder["sort"].get("column")
            parameters["ascending"] = query_builder["sort"].get("direction", "asc").lower() == "asc"
        
        # Query-specific parameters
        if query_type == "ticker":
            if "ticker" not in query_builder:
                raise ValueError("Ticker parameter is required")
            parameters["ticker"] = query_builder["ticker"]
        
        elif query_type == "multi_ticker":
            if "tickers" not in query_builder:
                raise ValueError("Tickers parameter is required")
            parameters["tickers"] = query_builder["tickers"]
        
        elif query_type == "sentiment_histogram":
            if "ticker" in query_builder:
                parameters["ticker"] = query_builder["ticker"]
            
            if "bins" in query_builder:
                parameters["bins"] = int(query_builder["bins"])
        
        elif query_type == "aggregate_by_date":
            if "freq" in query_builder:
                parameters["freq"] = query_builder["freq"]
        
        # Execute the query
        result = self.execute_query(query_type, parameters)
        
        # Cache the result
        self.cache_manager.set(cache_key, result)
        
        return result