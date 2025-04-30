#!/usr/bin/env python3
"""
Test script for the DremioSentimentQueryService implementation.

This script verifies the functionality of the query service by connecting to 
Dremio and executing various queries against real data.
"""
import logging
import os
import sys
import time
from typing import Dict, Any, List, Optional
import json
import pandas as pd
from tabulate import tabulate

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from iceberg_lake.query.dremio_sentiment_query import DremioSentimentQueryService
from iceberg_lake.utils.config import IcebergConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_dataframe_sample(df: pd.DataFrame, title: str, max_rows: int = 5) -> None:
    """
    Print a sample of a DataFrame with a title.
    
    Args:
        df: DataFrame to print
        title: Title to display
        max_rows: Maximum number of rows to display
    """
    print(f"\n{'=' * 80}")
    print(f"= {title}")
    print(f"{'=' * 80}")
    
    if df is None or df.empty:
        print("No data available.")
        return
    
    # Display basic info
    print(f"Shape: {df.shape}")
    print(f"Columns: {', '.join(df.columns)}")
    
    # Display sample
    pd.set_option('display.max_columns', None)
    pd.set_option('display.expand_frame_repr', False)
    pd.set_option('max_colwidth', 30)
    
    try:
        print(tabulate(df.head(max_rows), headers='keys', tablefmt='pretty'))
    except Exception as e:
        print(f"Could not display table: {str(e)}")
        print(df.head(max_rows))
    
    print(f"{'=' * 80}\n")


def run_query_tests(config_file: Optional[str] = None) -> Dict[str, bool]:
    """
    Run tests for the DremioSentimentQueryService.
    
    Args:
        config_file: Path to alternative config file (optional)
        
    Returns:
        Dict[str, bool]: Test results
    """
    print("\nStarting DremioSentimentQueryService tests...")
    test_results = {}
    query_service = None
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = IcebergConfig(config_path=config_file)
        dremio_config = config.get_dremio_config()
        
        # Extract connection details
        dremio_host = dremio_config.get('host', 'localhost')
        dremio_port = dremio_config.get('port', 31010)
        dremio_username = dremio_config.get('username', 'dremio')
        dremio_password = dremio_config.get('password', 'dremio123')
        catalog = dremio_config.get('catalog', 'DREMIO')
        namespace = dremio_config.get('namespace', 'sentiment')
        table_name = dremio_config.get('table_name', 'sentiment_data')
        
        logger.info(f"Connecting to Dremio at {dremio_host}:{dremio_port}")
        
        # Initialize query service
        logger.info("Initializing query service...")
        query_service = DremioSentimentQueryService(
            dremio_host=dremio_host,
            dremio_port=dremio_port,
            dremio_username=dremio_username,
            dremio_password=dremio_password,
            catalog=catalog,
            namespace=namespace,
            table_name=table_name
        )
        
        logger.info("Connected to Dremio successfully.")
        test_results['connection'] = True
        
        # Test 1: Get sentiment with emotions
        logger.info("Test 1: Get sentiment with emotions...")
        try:
            df = query_service.get_sentiment_with_emotions(days=30)
            test_results['get_sentiment_with_emotions'] = not df.empty
            print_dataframe_sample(df, "Sentiment with Emotions Data")
        except Exception as e:
            logger.error(f"Error in get_sentiment_with_emotions: {str(e)}")
            test_results['get_sentiment_with_emotions'] = False
        
        # Test 2: Get top tickers by volume
        logger.info("Test 2: Get top tickers by volume...")
        try:
            df = query_service.get_top_tickers_by_volume(days=30, limit=10)
            test_results['get_top_tickers_by_volume'] = not df.empty
            print_dataframe_sample(df, "Top Tickers by Volume")
            
            # Get the first ticker for further tests
            first_ticker = df['ticker'].iloc[0] if not df.empty else 'AAPL'
            logger.info(f"Using ticker {first_ticker} for further tests")
        except Exception as e:
            logger.error(f"Error in get_top_tickers_by_volume: {str(e)}")
            test_results['get_top_tickers_by_volume'] = False
            first_ticker = 'AAPL'  # Default to AAPL if error
        
        # Test 3: Get sentiment time series
        logger.info("Test 3: Get sentiment time series...")
        try:
            df = query_service.get_sentiment_time_series(ticker=first_ticker, interval='day', days=30)
            test_results['get_sentiment_time_series'] = not df.empty
            print_dataframe_sample(df, f"Sentiment Time Series for {first_ticker}")
        except Exception as e:
            logger.error(f"Error in get_sentiment_time_series: {str(e)}")
            test_results['get_sentiment_time_series'] = False
        
        # Test 4: Get sentiment by source
        logger.info("Test 4: Get sentiment by source...")
        try:
            df = query_service.get_sentiment_by_source(days=30)
            test_results['get_sentiment_by_source'] = not df.empty
            print_dataframe_sample(df, "Sentiment by Source")
        except Exception as e:
            logger.error(f"Error in get_sentiment_by_source: {str(e)}")
            test_results['get_sentiment_by_source'] = False
        
        # Test 5: Get entity sentiment analysis
        logger.info("Test 5: Get entity sentiment analysis...")
        try:
            df = query_service.get_entity_sentiment_analysis(ticker=first_ticker, days=30)
            test_results['get_entity_sentiment_analysis'] = True
            print_dataframe_sample(df, f"Entity Sentiment Analysis for {first_ticker}")
        except Exception as e:
            logger.error(f"Error in get_entity_sentiment_analysis: {str(e)}")
            test_results['get_entity_sentiment_analysis'] = False
        
        # Test 6: Search sentiment data
        logger.info("Test 6: Search sentiment data...")
        try:
            df = query_service.search_sentiment_data(ticker=first_ticker, days=30, limit=10)
            test_results['search_sentiment_data'] = not df.empty
            print_dataframe_sample(df, f"Search Results for {first_ticker}")
        except Exception as e:
            logger.error(f"Error in search_sentiment_data: {str(e)}")
            test_results['search_sentiment_data'] = False
        
        # Test 7: Get correlations
        logger.info("Test 7: Get correlations...")
        try:
            correlations = query_service.get_correlations(ticker=first_ticker, days=30)
            test_results['get_correlations'] = len(correlations) > 0
            print("\n=== Correlations ===")
            for key, value in correlations.items():
                print(f"{key}: {value}")
            print("===================\n")
        except Exception as e:
            logger.error(f"Error in get_correlations: {str(e)}")
            test_results['get_correlations'] = False
        
    except Exception as e:
        logger.error(f"Test setup error: {str(e)}")
        test_results['setup'] = False
    finally:
        # Clean up resources
        if query_service:
            try:
                query_service.close()
                logger.info("Closed query service connection")
            except Exception as e:
                logger.error(f"Error closing connection: {str(e)}")
    
    # Print summary of test results
    print("\n*** TEST RESULTS SUMMARY ***")
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    
    print(f"Total tests: {total_tests}")
    print(f"Passed tests: {passed_tests}")
    print(f"Failed tests: {total_tests - passed_tests}")
    print("\nDetailed results:")
    
    for test_name, passed in test_results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name}: {status}")
    
    return test_results


def run_api_tests(base_url: str = "http://localhost:8000") -> Dict[str, bool]:
    """
    Run tests for the sentiment API endpoints.
    
    Args:
        base_url: Base URL for the API
        
    Returns:
        Dict[str, bool]: Test results
    """
    import requests
    
    print("\nStarting Sentiment API tests...")
    test_results = {}
    
    try:
        # Test 1: Root endpoint
        logger.info("Test 1: Root endpoint...")
        try:
            response = requests.get(f"{base_url}/")
            test_results['root_endpoint'] = response.status_code == 200
            print(f"Root endpoint response: {response.json()}")
        except Exception as e:
            logger.error(f"Error in root endpoint test: {str(e)}")
            test_results['root_endpoint'] = False
        
        # Test 2: Get top tickers
        logger.info("Test 2: Get top tickers...")
        try:
            response = requests.get(f"{base_url}/sentiment/tickers?days=30&limit=10")
            test_results['tickers_endpoint'] = response.status_code == 200
            data = response.json()
            print(f"Got {data['count']} tickers")
            
            # Get the first ticker for further tests
            first_ticker = data['data'][0]['ticker'] if data['count'] > 0 else 'AAPL'
            logger.info(f"Using ticker {first_ticker} for further tests")
        except Exception as e:
            logger.error(f"Error in tickers endpoint test: {str(e)}")
            test_results['tickers_endpoint'] = False
            first_ticker = 'AAPL'  # Default to AAPL if error
        
        # Test 3: Get sentiment
        logger.info("Test 3: Get sentiment...")
        try:
            response = requests.get(f"{base_url}/sentiment?ticker={first_ticker}&days=30")
            test_results['sentiment_endpoint'] = response.status_code == 200
            data = response.json()
            print(f"Got {data['count']} sentiment records for {first_ticker}")
        except Exception as e:
            logger.error(f"Error in sentiment endpoint test: {str(e)}")
            test_results['sentiment_endpoint'] = False
        
        # Test 4: Get timeseries
        logger.info("Test 4: Get timeseries...")
        try:
            response = requests.get(f"{base_url}/sentiment/timeseries?ticker={first_ticker}&interval=day&days=30")
            test_results['timeseries_endpoint'] = response.status_code == 200
            data = response.json()
            print(f"Got {data['count']} timeseries records for {first_ticker}")
        except Exception as e:
            logger.error(f"Error in timeseries endpoint test: {str(e)}")
            test_results['timeseries_endpoint'] = False
        
        # Test 5: Get sources
        logger.info("Test 5: Get sources...")
        try:
            response = requests.get(f"{base_url}/sentiment/sources?days=30")
            test_results['sources_endpoint'] = response.status_code == 200
            data = response.json()
            print(f"Got {data['count']} source records")
        except Exception as e:
            logger.error(f"Error in sources endpoint test: {str(e)}")
            test_results['sources_endpoint'] = False
        
        # Test 6: Search endpoint
        logger.info("Test 6: Search endpoint...")
        try:
            response = requests.get(f"{base_url}/sentiment/search?ticker={first_ticker}&days=30&limit=10")
            test_results['search_endpoint'] = response.status_code == 200
            data = response.json()
            print(f"Got {data['count']} search results for {first_ticker}")
        except Exception as e:
            logger.error(f"Error in search endpoint test: {str(e)}")
            test_results['search_endpoint'] = False
    
    except Exception as e:
        logger.error(f"API test setup error: {str(e)}")
        test_results['api_setup'] = False
    
    # Print summary of test results
    print("\n*** API TEST RESULTS SUMMARY ***")
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    
    print(f"Total tests: {total_tests}")
    print(f"Passed tests: {passed_tests}")
    print(f"Failed tests: {total_tests - passed_tests}")
    print("\nDetailed results:")
    
    for test_name, passed in test_results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"  {test_name}: {status}")
    
    return test_results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the Dremio Sentiment Query Service and API")
    parser.add_argument("--config", help="Path to alternative config file")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Base URL for the API (default: http://localhost:8000)")
    parser.add_argument("--test-api", action="store_true", help="Run API tests")
    parser.add_argument("--test-service", action="store_true", help="Run query service tests")
    args = parser.parse_args()
    
    # If no specific test is selected, run both
    if not args.test_api and not args.test_service:
        args.test_service = True
        args.test_api = True
    
    # Run the tests
    if args.test_service:
        query_results = run_query_tests(config_file=args.config)
    
    if args.test_api:
        api_results = run_api_tests(base_url=args.api_url)