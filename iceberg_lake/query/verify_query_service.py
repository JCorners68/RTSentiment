#!/usr/bin/env python3
"""
Verification script for the Dremio Sentiment Query Service.

This script tests the DremioSentimentQueryService against real data in Dremio
to verify Phase 3 of the data tier plan implementation.
"""
import os
import sys
import time
import logging
import argparse
import pandas as pd
from typing import Dict, Any, List, Optional
from tabulate import tabulate

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the query service
try:
    from query.dremio_sentiment_query import DremioSentimentQueryService
except ImportError:
    # Try importing with full path for when running from project root
    from iceberg_lake.query.dremio_sentiment_query import DremioSentimentQueryService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QueryServiceVerifier:
    """Verifier for the DremioSentimentQueryService."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 31010,
        username: str = "dremio",
        password: str = "dremio123",
        driver_path: str = None,
        test_ticker: str = "AAPL"
    ):
        """
        Initialize the QueryServiceVerifier.
        
        Args:
            host: Dremio JDBC host
            port: Dremio JDBC port
            username: Dremio username
            password: Dremio password
            driver_path: Path to JDBC driver JAR file (optional)
            test_ticker: Ticker symbol to use for testing
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.driver_path = driver_path
        self.test_ticker = test_ticker
        
        # Store test results
        self.results = {}
        
        # Initialize query service
        self.query_service = None
        self._init_query_service()
    
    def _init_query_service(self):
        """Initialize the query service."""
        try:
            self.query_service = DremioSentimentQueryService(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                driver_path=self.driver_path
            )
            logger.info("Successfully initialized DremioSentimentQueryService")
            
        except Exception as e:
            logger.error(f"Failed to initialize query service: {str(e)}")
            raise
    
    def _log_dataframe(self, df: pd.DataFrame, limit: int = 5) -> None:
        """
        Log a dataframe in tabular format.
        
        Args:
            df: DataFrame to log
            limit: Maximum number of rows to show
        """
        if df is None or df.empty:
            logger.info("Empty result set")
            return
        
        # Truncate dataframe for display
        display_df = df.head(limit)
        
        # Format as table
        table = tabulate(display_df, headers=display_df.columns, tablefmt='pretty')
        
        # Log result details
        logger.info(f"\nResult shape: {df.shape}\n{table}")
    
    def verify_connection(self) -> bool:
        """
        Verify connection to Dremio.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        logger.info("Verifying connection to Dremio...")
        try:
            # Test connection by checking JDBC driver
            driver_info = self.query_service.verify_driver()
            
            if driver_info:
                logger.info(f"Connection successful - Driver: {driver_info}")
                self.results['connection'] = True
                return True
            else:
                logger.error("Connection failed - Driver verification returned None")
                self.results['connection'] = False
                return False
                
        except Exception as e:
            logger.error(f"Connection verification failed: {str(e)}")
            self.results['connection'] = False
            return False
    
    def verify_base_sentiment_query(self) -> bool:
        """
        Verify basic sentiment query.
        
        Returns:
            bool: True if query is successful, False otherwise
        """
        logger.info(f"Testing basic sentiment query for ticker: {self.test_ticker}...")
        try:
            result = self.query_service.get_sentiment(self.test_ticker)
            
            if result is not None and not result.empty:
                logger.info("Basic sentiment query successful")
                self._log_dataframe(result)
                self.results['base_sentiment'] = True
                return True
            else:
                logger.warning("Basic sentiment query returned empty result")
                self.results['base_sentiment'] = False
                return False
                
        except Exception as e:
            logger.error(f"Basic sentiment query failed: {str(e)}")
            self.results['base_sentiment'] = False
            return False
    
    def verify_timeseries_query(self) -> bool:
        """
        Verify time series query.
        
        Returns:
            bool: True if query is successful, False otherwise
        """
        logger.info(f"Testing time series query for ticker: {self.test_ticker}...")
        try:
            result = self.query_service.get_sentiment_timeseries(self.test_ticker, interval="day")
            
            if result is not None and not result.empty:
                logger.info("Time series query successful")
                self._log_dataframe(result)
                self.results['timeseries'] = True
                return True
            else:
                logger.warning("Time series query returned empty result")
                self.results['timeseries'] = False
                return False
                
        except Exception as e:
            logger.error(f"Time series query failed: {str(e)}")
            self.results['timeseries'] = False
            return False
    
    def verify_emotion_query(self) -> bool:
        """
        Verify emotion analysis query.
        
        Returns:
            bool: True if query is successful, False otherwise
        """
        logger.info(f"Testing emotion analysis query for ticker: {self.test_ticker}...")
        try:
            result = self.query_service.get_sentiment_with_emotions(self.test_ticker)
            
            if result is not None and not result.empty:
                logger.info("Emotion analysis query successful")
                self._log_dataframe(result)
                self.results['emotions'] = True
                return True
            else:
                logger.warning("Emotion analysis query returned empty result")
                self.results['emotions'] = False
                return False
                
        except Exception as e:
            logger.error(f"Emotion analysis query failed: {str(e)}")
            self.results['emotions'] = False
            return False
    
    def verify_entity_query(self) -> bool:
        """
        Verify entity sentiment query.
        
        Returns:
            bool: True if query is successful, False otherwise
        """
        logger.info(f"Testing entity sentiment query for ticker: {self.test_ticker}...")
        try:
            result = self.query_service.get_entity_sentiment_analysis(self.test_ticker)
            
            if result is not None and not result.empty:
                logger.info("Entity sentiment query successful")
                self._log_dataframe(result)
                self.results['entity'] = True
                return True
            else:
                logger.warning("Entity sentiment query returned empty result")
                self.results['entity'] = False
                return False
                
        except Exception as e:
            logger.error(f"Entity sentiment query failed: {str(e)}")
            self.results['entity'] = False
            return False
    
    def verify_aspect_query(self) -> bool:
        """
        Verify aspect-based sentiment query.
        
        Returns:
            bool: True if query is successful, False otherwise
        """
        logger.info(f"Testing aspect-based sentiment query for ticker: {self.test_ticker}...")
        try:
            result = self.query_service.get_aspect_based_sentiment(self.test_ticker)
            
            if result is not None and not result.empty:
                logger.info("Aspect-based sentiment query successful")
                self._log_dataframe(result)
                self.results['aspect'] = True
                return True
            else:
                logger.warning("Aspect-based sentiment query returned empty result")
                self.results['aspect'] = False
                return False
                
        except Exception as e:
            logger.error(f"Aspect-based sentiment query failed: {str(e)}")
            self.results['aspect'] = False
            return False
    
    def verify_all(self) -> bool:
        """
        Run all verification tests.
        
        Returns:
            bool: True if all tests pass, False otherwise
        """
        logger.info("Starting verification of all query service functionality...")
        
        # Track overall success
        all_success = True
        
        # Run tests
        connection_success = self.verify_connection()
        all_success = all_success and connection_success
        
        # Only proceed with data queries if connection is successful
        if connection_success:
            base_success = self.verify_base_sentiment_query()
            all_success = all_success and base_success
            
            timeseries_success = self.verify_timeseries_query()
            all_success = all_success and timeseries_success
            
            emotion_success = self.verify_emotion_query()
            all_success = all_success and emotion_success
            
            entity_success = self.verify_entity_query()
            all_success = all_success and entity_success
            
            aspect_success = self.verify_aspect_query()
            all_success = all_success and aspect_success
        
        # Print summary
        self._print_summary()
        
        return all_success
    
    def _print_summary(self) -> None:
        """Print a summary of verification results."""
        logger.info("\n" + "=" * 50)
        logger.info("VERIFICATION SUMMARY")
        logger.info("=" * 50)
        
        # Create a list of test results
        test_results = []
        for test_name, success in self.results.items():
            status = "PASS" if success else "FAIL"
            test_results.append([test_name, status])
        
        # Calculate overall result
        overall = all(success for success in self.results.values())
        overall_status = "PASS" if overall else "FAIL"
        test_results.append(["overall", overall_status])
        
        # Format as table
        table = tabulate(test_results, headers=["Test", "Status"], tablefmt='pretty')
        logger.info(f"\n{table}")
        logger.info("=" * 50)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Verify Dremio Sentiment Query Service')
    parser.add_argument('--host', default='localhost', help='Dremio JDBC host')
    parser.add_argument('--port', type=int, default=31010, help='Dremio JDBC port')
    parser.add_argument('--username', default='dremio', help='Dremio username')
    parser.add_argument('--password', default='dremio123', help='Dremio password')
    parser.add_argument('--driver-path', help='Path to JDBC driver JAR file')
    parser.add_argument('--ticker', default='AAPL', help='Ticker to use for testing')
    
    args = parser.parse_args()
    
    try:
        # Create verifier
        verifier = QueryServiceVerifier(
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            driver_path=args.driver_path,
            test_ticker=args.ticker
        )
        
        # Run verification
        success = verifier.verify_all()
        
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Verification failed with error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())