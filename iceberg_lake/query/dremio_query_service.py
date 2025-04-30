"""
Dremio Sentiment Query Service.

This module provides a service for querying sentiment data from Dremio.
The service uses JDBC to connect to Dremio and query the data.
"""

import os
import logging
import jpype
import jaydebeapi
import pandas as pd
from typing import List, Dict, Any, Optional, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DremioSentimentQueryService:
    """Service for querying sentiment data from Dremio."""
    
    def __init__(
        self, 
        jdbc_driver_path: Optional[str] = None,
        dremio_host: str = "localhost",
        dremio_port: int = 31010,
        dremio_username: str = "dremio",
        dremio_password: str = "dremio123",
        jvm_args: Optional[List[str]] = None
    ):
        """
        Initialize the DremioSentimentQueryService.
        
        Args:
            jdbc_driver_path: Path to the Dremio JDBC driver jar file.
                If None, use the DREMIO_JDBC_DRIVER environment variable.
            dremio_host: Hostname of the Dremio server.
            dremio_port: Port of the Dremio server.
            dremio_username: Username to connect to Dremio.
            dremio_password: Password to connect to Dremio.
            jvm_args: Additional JVM arguments to pass to the JVM. If None,
                use the JPYPE_JVM_ARGS environment variable.
        """
        self.jdbc_driver_path = jdbc_driver_path or os.environ.get(
            "DREMIO_JDBC_DRIVER",
            "/home/jonat/WSL_RT_Sentiment/drivers/dremio-jdbc-driver.jar"
        )
        self.dremio_host = dremio_host
        self.dremio_port = dremio_port
        self.dremio_username = dremio_username
        self.dremio_password = dremio_password
        
        # Get JVM args from environment or use defaults
        self.jvm_args = jvm_args
        if not self.jvm_args:
            jpype_jvm_args = os.environ.get("JPYPE_JVM_ARGS", "")
            if jpype_jvm_args:
                self.jvm_args = jpype_jvm_args.split()
            else:
                # Default JVM args for Dremio JDBC compatibility
                self.jvm_args = [
                    "--add-opens=java.base/java.nio=ALL-UNNAMED",
                    "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED",
                    "--add-opens=java.base/sun.security.action=ALL-UNNAMED",
                    "--add-opens=java.base/java.util=ALL-UNNAMED",
                    "--add-opens=java.base/java.lang=ALL-UNNAMED",
                    "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
                    "-Dio.netty.tryReflectionSetAccessible=true",
                    "-Djava.security.egd=file:/dev/./urandom"
                ]
        
        # Initialize the JVM if not already running
        self._initialize_jvm()
        
        # JDBC connection details
        self.jdbc_url = f"jdbc:dremio:direct={dremio_host}:{dremio_port}"
        self.connection = None
        
    def _initialize_jvm(self):
        """Initialize the JVM with the correct arguments if not already running."""
        if not jpype.isJVMStarted():
            logger.info(f"Using JDBC driver: {self.jdbc_driver_path}")
            logger.info(f"Using JVM arguments: {self.jvm_args}")
            
            # Add JDBC driver to classpath
            classpath = os.environ.get("CLASSPATH", "")
            if self.jdbc_driver_path not in classpath:
                if classpath:
                    classpath = f"{classpath}:{self.jdbc_driver_path}"
                else:
                    classpath = self.jdbc_driver_path
                os.environ["CLASSPATH"] = classpath
            
            logger.info("Starting JVM with custom arguments...")
            jpype.startJVM(*self.jvm_args, classpath=classpath)
    
    def connect(self):
        """Connect to Dremio using JDBC."""
        if self.connection is not None:
            logger.info("Already connected to Dremio")
            return
        
        try:
            logger.info(f"Connecting to Dremio at {self.jdbc_url}")
            self.connection = jaydebeapi.connect(
                "com.dremio.jdbc.Driver",
                self.jdbc_url,
                [self.dremio_username, self.dremio_password],
                self.jdbc_driver_path
            )
            logger.info("Connected to Dremio")
        except Exception as e:
            logger.error(f"Failed to connect to Dremio: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from Dremio."""
        if self.connection is not None:
            try:
                self.connection.close()
                logger.info("Disconnected from Dremio")
            except Exception as e:
                logger.error(f"Error disconnecting from Dremio: {e}")
            finally:
                self.connection = None
    
    def query(self, query: str) -> pd.DataFrame:
        """
        Execute a SQL query against Dremio and return the results as a pandas DataFrame.
        
        Args:
            query: SQL query to execute
            
        Returns:
            DataFrame containing the query results
        """
        if self.connection is None:
            self.connect()
            
        try:
            logger.info(f"Executing query: {query}")
            df = pd.read_sql(query, self.connection)
            logger.info(f"Query returned {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise
    
    def get_ticker_sentiment(self, ticker: str, days: int = 30) -> pd.DataFrame:
        """
        Get sentiment data for a specific ticker for the last N days.
        
        Args:
            ticker: Stock ticker symbol
            days: Number of days of data to return
            
        Returns:
            DataFrame containing sentiment data for the ticker
        """
        query = f"""
        SELECT 
            ticker,
            timestamp,
            sentiment_score,
            source,
            message_id,
            url
        FROM 
            iceberg_catalog.sentiment.ticker_sentiment
        WHERE 
            ticker = '{ticker.upper()}'
            AND timestamp >= CURRENT_DATE - INTERVAL '{days}' DAY
        ORDER BY 
            timestamp DESC
        """
        return self.query(query)
    
    def get_average_sentiment(self, tickers: List[str], days: int = 7) -> pd.DataFrame:
        """
        Get average sentiment scores for a list of tickers over the specified time period.
        
        Args:
            tickers: List of ticker symbols
            days: Number of days to include in the average
            
        Returns:
            DataFrame with average sentiment scores for each ticker
        """
        ticker_list = "', '".join([t.upper() for t in tickers])
        query = f"""
        SELECT 
            ticker,
            AVG(sentiment_score) as avg_sentiment,
            COUNT(*) as message_count
        FROM 
            iceberg_catalog.sentiment.ticker_sentiment
        WHERE 
            ticker IN ('{ticker_list}')
            AND timestamp >= CURRENT_DATE - INTERVAL '{days}' DAY
        GROUP BY 
            ticker
        ORDER BY 
            avg_sentiment DESC
        """
        return self.query(query)
    
    def get_sentiment_trend(self, ticker: str, days: int = 30) -> pd.DataFrame:
        """
        Get daily sentiment trend for a ticker over time.
        
        Args:
            ticker: Ticker symbol
            days: Number of days to include
            
        Returns:
            DataFrame with daily average sentiment scores
        """
        query = f"""
        SELECT 
            ticker,
            DATE_TRUNC('DAY', timestamp) as date,
            AVG(sentiment_score) as avg_sentiment,
            COUNT(*) as message_count
        FROM 
            iceberg_catalog.sentiment.ticker_sentiment
        WHERE 
            ticker = '{ticker.upper()}'
            AND timestamp >= CURRENT_DATE - INTERVAL '{days}' DAY
        GROUP BY 
            ticker, DATE_TRUNC('DAY', timestamp)
        ORDER BY 
            date
        """
        return self.query(query)
    
    def get_top_positive_tickers(self, limit: int = 10, days: int = 7) -> pd.DataFrame:
        """
        Get the top N tickers with the most positive sentiment.
        
        Args:
            limit: Number of tickers to return
            days: Number of days to include
            
        Returns:
            DataFrame with top positive sentiment tickers
        """
        query = f"""
        SELECT 
            ticker,
            AVG(sentiment_score) as avg_sentiment,
            COUNT(*) as message_count
        FROM 
            iceberg_catalog.sentiment.ticker_sentiment
        WHERE 
            timestamp >= CURRENT_DATE - INTERVAL '{days}' DAY
        GROUP BY 
            ticker
        HAVING 
            COUNT(*) >= 10
        ORDER BY 
            avg_sentiment DESC
        LIMIT {limit}
        """
        return self.query(query)
    
    def get_top_negative_tickers(self, limit: int = 10, days: int = 7) -> pd.DataFrame:
        """
        Get the top N tickers with the most negative sentiment.
        
        Args:
            limit: Number of tickers to return
            days: Number of days to include
            
        Returns:
            DataFrame with top negative sentiment tickers
        """
        query = f"""
        SELECT 
            ticker,
            AVG(sentiment_score) as avg_sentiment,
            COUNT(*) as message_count
        FROM 
            iceberg_catalog.sentiment.ticker_sentiment
        WHERE 
            timestamp >= CURRENT_DATE - INTERVAL '{days}' DAY
        GROUP BY 
            ticker
        HAVING 
            COUNT(*) >= 10
        ORDER BY 
            avg_sentiment ASC
        LIMIT {limit}
        """
        return self.query(query)
    
    def get_sentiment_by_source(self, ticker: str, days: int = 30) -> pd.DataFrame:
        """
        Get sentiment breakdown by source for a specific ticker.
        
        Args:
            ticker: Ticker symbol
            days: Number of days to include
            
        Returns:
            DataFrame with sentiment by source
        """
        query = f"""
        SELECT 
            ticker,
            source,
            AVG(sentiment_score) as avg_sentiment,
            COUNT(*) as message_count
        FROM 
            iceberg_catalog.sentiment.ticker_sentiment
        WHERE 
            ticker = '{ticker.upper()}'
            AND timestamp >= CURRENT_DATE - INTERVAL '{days}' DAY
        GROUP BY 
            ticker, source
        ORDER BY 
            avg_sentiment DESC
        """
        return self.query(query)
    
    def __enter__(self):
        """Context manager enter method."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit method."""
        self.disconnect()