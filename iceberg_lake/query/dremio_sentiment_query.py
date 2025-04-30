"""
DremioSentimentQueryService for the sentiment analysis system.

This module provides a query service for retrieving and analyzing sentiment data
stored in Iceberg tables via Dremio's JDBC interface, implementing Phase 3 of the data tier plan.
"""
import json
import logging
import time
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union

import jaydebeapi
import pandas as pd

from iceberg_lake.schema.iceberg_schema import create_sentiment_schema


class DremioSentimentQueryService:
    """
    Service for querying sentiment analysis data from Iceberg tables via Dremio JDBC.
    
    This class implements the Phase 3 approach from the data tier plan, providing
    SQL-based access to sentiment data with advanced query capabilities.
    """
    
    def __init__(
        self,
        dremio_host: str,
        dremio_port: int,
        dremio_username: str,
        dremio_password: str,
        catalog: str = "DREMIO",
        namespace: str = "sentiment",
        table_name: str = "sentiment_data",
        max_retries: int = 3,
        retry_delay: int = 1000,  # milliseconds
        jar_path: Optional[str] = None,
        driver_class: str = "com.dremio.jdbc.Driver",
        cache_expires: int = 300  # 5 minutes
    ):
        """
        Initialize Dremio sentiment query service.
        
        Args:
            dremio_host: Dremio server hostname
            dremio_port: Dremio JDBC port (usually 31010)
            dremio_username: Dremio username
            dremio_password: Dremio password
            catalog: Dremio catalog name
            namespace: Schema/namespace for the table
            table_name: Table name for sentiment data
            max_retries: Maximum number of query retries
            retry_delay: Delay between retries (ms)
            jar_path: Path to Dremio JDBC driver JAR file (optional)
            driver_class: JDBC driver class name
            cache_expires: Cache expiration time in seconds
        """
        self.logger = logging.getLogger(__name__)
        
        # Connection parameters
        self.dremio_host = dremio_host
        self.dremio_port = dremio_port
        self.dremio_username = dremio_username
        self.dremio_password = dremio_password
        self.catalog = catalog
        self.namespace = namespace
        self.table_name = table_name
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.jar_path = jar_path
        self.driver_class = driver_class
        self.cache_expires = cache_expires
        
        # Construct the JDBC URL for Dremio
        self.jdbc_url = f"jdbc:dremio:direct={dremio_host}:{dremio_port}"
        
        # Construct the full table identifier
        self.table_identifier = f'"{catalog}"."{namespace}"."{table_name}"'
        
        # Initialize connection pool
        self.connection = None
        
        # Initialize cache
        self.query_cache = {}
        self.cache_timestamps = {}
        
        # Verify JDBC driver availability first
        self._verify_jdbc_driver()
        
        # Verify the table exists
        self._verify_table_exists()
    
    def _verify_jdbc_driver(self) -> None:
        """
        Verify that the Dremio JDBC driver is available.
        
        Raises:
            RuntimeError: If the driver is not found
        """
        import jpype
        
        # Check if jar_path is provided
        if self.jar_path and os.path.exists(self.jar_path):
            self.logger.info(f"Using provided JDBC driver: {self.jar_path}")
            return
            
        # Check multiple locations for the driver
        jar_paths = [
            # Check current directory
            [os.path.abspath(f) for f in os.listdir('.') if f.endswith('.jar') and 'dremio' in f.lower()],
            # Check drivers directory if it exists
            [os.path.abspath(os.path.join('drivers', f)) for f in os.listdir('drivers') if os.path.exists('drivers') and f.endswith('.jar') and 'dremio' in f.lower()],
            # Check standard lib directories
            [os.path.join('/usr/lib/dremio', f) for f in os.listdir('/usr/lib/dremio') if os.path.exists('/usr/lib/dremio') and f.endswith('.jar') and 'dremio' in f.lower()],
            [os.path.join('/usr/local/lib/dremio', f) for f in os.listdir('/usr/local/lib/dremio') if os.path.exists('/usr/local/lib/dremio') and f.endswith('.jar') and 'dremio' in f.lower()]
        ]
        
        # Flatten the list and take the first JAR found
        jar_files = [item for sublist in jar_paths for item in sublist]
        
        if jar_files:
            self.jar_path = jar_files[0]
            self.logger.info(f"Found Dremio JDBC driver: {self.jar_path}")
            return
            
        # Try to load the driver class directly from classpath
        try:
            if not jpype.isJVMStarted():
                jpype.startJVM()
            driver_class = jpype.JClass(self.driver_class)
            self.logger.info(f"Found Dremio JDBC driver class in classpath: {self.driver_class}")
            return
        except Exception as e:
            self.logger.warning(f"Could not load driver class from classpath: {str(e)}")
        
        raise RuntimeError(
            "Dremio JDBC driver not found. Please run scripts/setup_dremio_jdbc.sh to download and set up the driver, "
            "or provide the jar_path parameter with the path to the driver JAR file."
        )
    
    def _get_connection(self) -> jaydebeapi.Connection:
        """
        Get a JDBC connection to Dremio.
        
        Returns:
            Connection: JDBC connection object
        """
        if self.connection is None:
            try:
                self.logger.info(f"Connecting to Dremio JDBC: {self.jdbc_url}")
                
                connection_properties = {
                    "user": self.dremio_username,
                    "password": self.dremio_password
                }
                
                if self.jar_path:
                    # Connect using the provided JAR file
                    self.connection = jaydebeapi.connect(
                        self.driver_class,
                        self.jdbc_url,
                        [self.dremio_username, self.dremio_password],
                        self.jar_path
                    )
                else:
                    # Connect using the driver on the classpath
                    self.connection = jaydebeapi.connect(
                        self.driver_class,
                        self.jdbc_url,
                        [self.dremio_username, self.dremio_password]
                    )
                
                self.connection.jconn.setAutoCommit(True)  # Auto-commit for queries
                self.logger.info("Connected to Dremio JDBC successfully")
            
            except Exception as e:
                self.logger.error(f"Failed to connect to Dremio JDBC: {str(e)}")
                raise
        
        return self.connection
    
    def _verify_table_exists(self) -> bool:
        """
        Verify the target Iceberg table exists in Dremio.
        
        Returns:
            bool: True if the table exists, False otherwise
        """
        connection = self._get_connection()
        cursor = connection.cursor()
        
        try:
            # Check if table exists
            self.logger.info(f"Checking if table exists: {self.table_identifier}")
            
            # Use Dremio's INFORMATION_SCHEMA to check for table existence
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_CATALOG = '{self.catalog}'
                AND TABLE_SCHEMA = '{self.namespace}'
                AND TABLE_NAME = '{self.table_name}'
            """)
            
            count = cursor.fetchone()[0]
            
            if count == 0:
                self.logger.warning(f"Table does not exist: {self.table_identifier}")
                return False
            else:
                self.logger.info(f"Table exists: {self.table_identifier}")
                return True
        
        except Exception as e:
            self.logger.error(f"Error checking table existence: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def _execute_query(self, query: str, params: List[Any] = None) -> List[Tuple]:
        """
        Execute a SQL query against Dremio.
        
        Args:
            query: SQL query to execute
            params: Query parameters (optional)
            
        Returns:
            List[Tuple]: Query results
        """
        # Check cache first
        cache_key = f"{query}_{str(params)}"
        current_time = time.time()
        
        if cache_key in self.query_cache:
            cache_time = self.cache_timestamps.get(cache_key, 0)
            if current_time - cache_time < self.cache_expires:
                self.logger.debug(f"Cache hit for query: {query}")
                return self.query_cache[cache_key]
        
        # Not in cache or expired, execute query
        connection = self._get_connection()
        cursor = connection.cursor()
        
        try:
            self.logger.debug(f"Executing query: {query}")
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            results = cursor.fetchall()
            
            # Get column names
            column_names = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Cache the results
            self.query_cache[cache_key] = (results, column_names)
            self.cache_timestamps[cache_key] = current_time
            
            return results, column_names
            
        except Exception as e:
            self.logger.error(f"Error executing query: {str(e)}")
            raise
        finally:
            cursor.close()
    
    def _query_to_dataframe(self, query: str, params: List[Any] = None) -> pd.DataFrame:
        """
        Execute a SQL query and return results as a pandas DataFrame.
        
        Args:
            query: SQL query to execute
            params: Query parameters (optional)
            
        Returns:
            pd.DataFrame: Query results as DataFrame
        """
        results, column_names = self._execute_query(query, params)
        
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=column_names)
        
        # Convert JSON strings to Python objects
        for col in df.columns:
            if col in ['emotion_intensity_vector', 'aspect_based_sentiment', 'aspect_target_identification', 'entity_recognition']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: json.loads(x) if isinstance(x, str) and x else {})
        
        return df
    
    def get_sentiment_with_emotions(self, ticker: str = None, days: int = 30) -> pd.DataFrame:
        """
        Get sentiment data including emotion analysis for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol (optional)
            days: Number of days to look back (default: 30)
            
        Returns:
            pd.DataFrame: Sentiment data with emotion analysis
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build query
        query = f"""
        SELECT
            message_id,
            event_timestamp,
            text_content,
            sentiment_score,
            sentiment_magnitude,
            primary_emotion,
            emotion_intensity_vector,
            ticker,
            source_system
        FROM {self.table_identifier}
        WHERE event_timestamp BETWEEN ? AND ?
        """
        
        params = [start_date, end_date]
        
        # Add ticker filter if provided
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        
        query += " ORDER BY event_timestamp DESC"
        
        # Execute query
        return self._query_to_dataframe(query, params)
    
    def get_entity_sentiment_analysis(self, ticker: str = None, entity_type: str = None, days: int = 30) -> pd.DataFrame:
        """
        Get sentiment analysis broken down by entity.
        
        Args:
            ticker: Stock ticker symbol (optional)
            entity_type: Entity type to filter by (e.g., 'PERSON', 'ORGANIZATION')
            days: Number of days to look back (default: 30)
            
        Returns:
            pd.DataFrame: Entity sentiment analysis
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build query
        query = f"""
        SELECT
            message_id,
            event_timestamp,
            text_content,
            sentiment_score,
            entity_recognition,
            ticker,
            source_system
        FROM {self.table_identifier}
        WHERE event_timestamp BETWEEN ? AND ?
        AND entity_recognition IS NOT NULL
        """
        
        params = [start_date, end_date]
        
        # Add ticker filter if provided
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        
        query += " ORDER BY event_timestamp DESC"
        
        # Execute query
        df = self._query_to_dataframe(query, params)
        
        # Filter by entity type if provided
        if entity_type and not df.empty:
            # Create a new dataframe with filtered entities
            filtered_rows = []
            for _, row in df.iterrows():
                entities = row['entity_recognition']
                if not entities:
                    continue
                    
                matched_entities = [e for e in entities if e.get('type') == entity_type]
                if matched_entities:
                    for entity in matched_entities:
                        new_row = row.copy()
                        new_row['entity_text'] = entity.get('text')
                        new_row['entity_type'] = entity.get('type')
                        filtered_rows.append(new_row)
            
            if filtered_rows:
                return pd.DataFrame(filtered_rows)
            return pd.DataFrame()
        
        return df
    
    def get_aspect_based_sentiment(self, ticker: str, days: int = 30) -> pd.DataFrame:
        """
        Get aspect-based sentiment analysis for a specific ticker.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back (default: 30)
            
        Returns:
            pd.DataFrame: Aspect-based sentiment analysis
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build query
        query = f"""
        SELECT
            message_id,
            event_timestamp,
            text_content,
            sentiment_score,
            aspect_based_sentiment,
            aspect_target_identification,
            ticker,
            source_system
        FROM {self.table_identifier}
        WHERE event_timestamp BETWEEN ? AND ?
        AND ticker = ?
        AND aspect_based_sentiment IS NOT NULL
        ORDER BY event_timestamp DESC
        """
        
        params = [start_date, end_date, ticker]
        
        # Execute query
        df = self._query_to_dataframe(query, params)
        
        # Explode aspect-based sentiment into separate rows
        if not df.empty:
            aspect_rows = []
            for _, row in df.iterrows():
                aspects = row['aspect_based_sentiment']
                if not aspects:
                    continue
                    
                for aspect, score in aspects.items():
                    new_row = row.copy()
                    new_row['aspect'] = aspect
                    new_row['aspect_score'] = score
                    aspect_rows.append(new_row)
            
            if aspect_rows:
                return pd.DataFrame(aspect_rows)
        
        return df
    
    def get_toxicity_analysis(self, min_toxicity: float = 0.5, days: int = 30) -> pd.DataFrame:
        """
        Get potentially toxic content for moderation.
        
        Args:
            min_toxicity: Minimum toxicity score (0.0 to 1.0)
            days: Number of days to look back (default: 30)
            
        Returns:
            pd.DataFrame: Toxic content analysis
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build query
        query = f"""
        SELECT
            message_id,
            event_timestamp,
            text_content,
            toxicity_score,
            ticker,
            source_system
        FROM {self.table_identifier}
        WHERE event_timestamp BETWEEN ? AND ?
        AND toxicity_score >= ?
        ORDER BY toxicity_score DESC, event_timestamp DESC
        """
        
        params = [start_date, end_date, min_toxicity]
        
        # Execute query
        return self._query_to_dataframe(query, params)
    
    def get_intent_distribution(self, ticker: str = None, days: int = 30) -> pd.DataFrame:
        """
        Get distribution of user intents.
        
        Args:
            ticker: Stock ticker symbol (optional)
            days: Number of days to look back (default: 30)
            
        Returns:
            pd.DataFrame: User intent distribution
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build query
        query = f"""
        SELECT
            user_intent,
            COUNT(*) as count,
            AVG(sentiment_score) as avg_sentiment
        FROM {self.table_identifier}
        WHERE event_timestamp BETWEEN ? AND ?
        """
        
        params = [start_date, end_date]
        
        # Add ticker filter if provided
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        
        query += " GROUP BY user_intent ORDER BY count DESC"
        
        # Execute query
        return self._query_to_dataframe(query, params)
    
    def get_sentiment_time_series(self, ticker: str, interval: str = 'day', days: int = 30) -> pd.DataFrame:
        """
        Get sentiment time series data with advanced metrics.
        
        Args:
            ticker: Stock ticker symbol
            interval: Time interval ('hour', 'day', 'week', 'month')
            days: Number of days to look back (default: 30)
            
        Returns:
            pd.DataFrame: Sentiment time series data
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Define time bucket function based on interval
        if interval == 'hour':
            time_bucket = "DATE_TRUNC('HOUR', event_timestamp)"
        elif interval == 'day':
            time_bucket = "DATE_TRUNC('DAY', event_timestamp)"
        elif interval == 'week':
            time_bucket = "DATE_TRUNC('WEEK', event_timestamp)"
        elif interval == 'month':
            time_bucket = "DATE_TRUNC('MONTH', event_timestamp)"
        else:
            raise ValueError(f"Invalid interval: {interval}. Must be one of: hour, day, week, month")
        
        # Build query
        query = f"""
        SELECT
            {time_bucket} as time_bucket,
            COUNT(*) as message_count,
            AVG(sentiment_score) as avg_sentiment,
            MIN(sentiment_score) as min_sentiment,
            MAX(sentiment_score) as max_sentiment,
            STDDEV(sentiment_score) as std_sentiment,
            AVG(sentiment_magnitude) as avg_magnitude,
            AVG(subjectivity_score) as avg_subjectivity,
            SUM(CASE WHEN sentiment_score > 0 THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN sentiment_score < 0 THEN 1 ELSE 0 END) as negative_count,
            SUM(CASE WHEN sentiment_score = 0 THEN 1 ELSE 0 END) as neutral_count
        FROM {self.table_identifier}
        WHERE event_timestamp BETWEEN ? AND ?
        AND ticker = ?
        GROUP BY time_bucket
        ORDER BY time_bucket ASC
        """
        
        params = [start_date, end_date, ticker]
        
        # Execute query
        df = self._query_to_dataframe(query, params)
        
        # Calculate additional metrics
        if not df.empty:
            df['sentiment_ratio'] = df['positive_count'] / df['negative_count'].replace(0, 1)  # Avoid division by zero
            df['sentiment_volatility'] = df['std_sentiment']
        
        return df
    
    def get_top_tickers_by_volume(self, days: int = 30, limit: int = 20) -> pd.DataFrame:
        """
        Get top tickers by message volume.
        
        Args:
            days: Number of days to look back (default: 30)
            limit: Number of top tickers to return
            
        Returns:
            pd.DataFrame: Top tickers by volume
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build query
        query = f"""
        SELECT
            ticker,
            COUNT(*) as message_count,
            AVG(sentiment_score) as avg_sentiment,
            AVG(sentiment_magnitude) as avg_magnitude,
            COUNT(DISTINCT source_system) as source_count
        FROM {self.table_identifier}
        WHERE event_timestamp BETWEEN ? AND ?
        AND ticker IS NOT NULL
        GROUP BY ticker
        ORDER BY message_count DESC
        LIMIT {limit}
        """
        
        params = [start_date, end_date]
        
        # Execute query
        return self._query_to_dataframe(query, params)
    
    def get_top_emotions(self, ticker: str = None, days: int = 30, limit: int = 10) -> pd.DataFrame:
        """
        Get top emotions for a ticker or across all tickers.
        
        Args:
            ticker: Stock ticker symbol (optional)
            days: Number of days to look back (default: 30)
            limit: Number of top emotions to return
            
        Returns:
            pd.DataFrame: Top emotions
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build query
        query = f"""
        SELECT
            primary_emotion,
            COUNT(*) as count,
            AVG(sentiment_score) as avg_sentiment,
            AVG(sentiment_magnitude) as avg_magnitude
        FROM {self.table_identifier}
        WHERE event_timestamp BETWEEN ? AND ?
        """
        
        params = [start_date, end_date]
        
        # Add ticker filter if provided
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        
        query += f" GROUP BY primary_emotion ORDER BY count DESC LIMIT {limit}"
        
        # Execute query
        return self._query_to_dataframe(query, params)
    
    def get_sentiment_by_source(self, ticker: str = None, days: int = 30) -> pd.DataFrame:
        """
        Get sentiment analysis broken down by source system.
        
        Args:
            ticker: Stock ticker symbol (optional)
            days: Number of days to look back (default: 30)
            
        Returns:
            pd.DataFrame: Sentiment by source
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build query
        query = f"""
        SELECT
            source_system,
            COUNT(*) as message_count,
            AVG(sentiment_score) as avg_sentiment,
            AVG(sentiment_magnitude) as avg_magnitude,
            AVG(subjectivity_score) as avg_subjectivity,
            AVG(toxicity_score) as avg_toxicity,
            SUM(CASE WHEN sentiment_score > 0 THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN sentiment_score < 0 THEN 1 ELSE 0 END) as negative_count,
            SUM(CASE WHEN sentiment_score = 0 THEN 1 ELSE 0 END) as neutral_count
        FROM {self.table_identifier}
        WHERE event_timestamp BETWEEN ? AND ?
        """
        
        params = [start_date, end_date]
        
        # Add ticker filter if provided
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        
        query += " GROUP BY source_system ORDER BY message_count DESC"
        
        # Execute query
        return self._query_to_dataframe(query, params)
    
    def search_sentiment_data(
        self, 
        keyword: str = None,
        ticker: str = None, 
        source_system: str = None,
        min_sentiment: float = None,
        max_sentiment: float = None,
        days: int = 30,
        limit: int = 100
    ) -> pd.DataFrame:
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
            pd.DataFrame: Search results
        """
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Build query
        query = f"""
        SELECT
            message_id,
            event_timestamp,
            text_content,
            sentiment_score,
            sentiment_magnitude,
            primary_emotion,
            ticker,
            source_system
        FROM {self.table_identifier}
        WHERE event_timestamp BETWEEN ? AND ?
        """
        
        params = [start_date, end_date]
        
        # Add filters
        if keyword:
            query += " AND text_content LIKE ?"
            params.append(f"%{keyword}%")
        
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        
        if source_system:
            query += " AND source_system = ?"
            params.append(source_system)
        
        if min_sentiment is not None:
            query += " AND sentiment_score >= ?"
            params.append(min_sentiment)
        
        if max_sentiment is not None:
            query += " AND sentiment_score <= ?"
            params.append(max_sentiment)
        
        query += f" ORDER BY event_timestamp DESC LIMIT {limit}"
        
        # Execute query
        return self._query_to_dataframe(query, params)
    
    def get_correlations(self, ticker: str, days: int = 30) -> Dict[str, float]:
        """
        Calculate correlations between different metrics for a ticker.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back (default: 30)
            
        Returns:
            Dict[str, float]: Correlation coefficients
        """
        # Get time series data
        df = self.get_sentiment_time_series(ticker, interval='day', days=days)
        
        if df.empty or len(df) < 5:  # Need enough data points for correlation
            return {}
        
        # Calculate correlations
        correlations = {}
        
        # Sentiment vs. volume
        correlations['sentiment_volume'] = df['avg_sentiment'].corr(df['message_count'])
        
        # Sentiment vs. volatility
        correlations['sentiment_volatility'] = df['avg_sentiment'].corr(df['std_sentiment'])
        
        # Sentiment vs. magnitude
        correlations['sentiment_magnitude'] = df['avg_sentiment'].corr(df['avg_magnitude'])
        
        # Positive vs. negative count
        correlations['positive_negative'] = df['positive_count'].corr(df['negative_count'])
        
        return correlations
    
    def close(self) -> None:
        """Close the JDBC connection."""
        if self.connection:
            try:
                self.connection.close()
                self.connection = None
                self.logger.info("Closed JDBC connection")
            except Exception as e:
                self.logger.error(f"Error closing JDBC connection: {str(e)}")