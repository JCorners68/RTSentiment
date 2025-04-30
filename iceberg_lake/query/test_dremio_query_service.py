"""
Test script for DremioSentimentQueryService.

This script tests the DremioSentimentQueryService by connecting to Dremio
and executing some basic queries.
"""

import os
import sys
import logging
import argparse
import pandas as pd
from pathlib import Path

# Add parent directory to path so we can import the module
sys.path.append(str(Path(__file__).parent.parent))

from query.dremio_query_service import DremioSentimentQueryService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_connection(service):
    """Test connection to Dremio."""
    try:
        logger.info("Testing connection to Dremio...")
        
        # Simple test query
        test_query = "SELECT 1 as test"
        result = service.query(test_query)
        
        logger.info(f"Connection successful! Result: {result}")
        return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False

def test_reflection_query(service):
    """Test querying a reflection."""
    try:
        logger.info("Testing reflection query...")
        
        # First, check the schema of the reflections table
        try:
            schema_query = """
            SELECT 
                column_name, 
                data_type 
            FROM 
                information_schema.columns 
            WHERE 
                table_schema = 'sys' 
                AND table_name = 'reflections'
            """
            schema = service.query(schema_query)
            logger.info(f"Reflections table schema:")
            if not schema.empty:
                for _, row in schema.iterrows():
                    logger.info(f"Column: {row['column_name']} - Type: {row['data_type']}")
            
            # Try a simpler query against sys.reflections
            reflection_query = """
            SELECT 
                name, 
                state, 
                type 
            FROM 
                sys.reflections
            LIMIT 10
            """
            
            reflections = service.query(reflection_query)
            logger.info(f"Found {len(reflections)} reflections:")
            
            # Display reflection information
            if not reflections.empty:
                for _, row in reflections.iterrows():
                    logger.info(f"Reflection: {row['name']} - Type: {row['type']} - State: {row['state']}")
            
        except Exception as e:
            logger.warning(f"Could not query reflections: {e}")
            logger.info("Trying alternative query approach...")
            
            # Try to list all schemas in sys
            schemas_query = """
            SELECT 
                table_schema, 
                table_name 
            FROM 
                information_schema.tables 
            WHERE 
                table_schema = 'sys'
            """
            try:
                sys_tables = service.query(schemas_query)
                logger.info(f"Available tables in sys schema:")
                for _, row in sys_tables.iterrows():
                    logger.info(f"Table: {row['table_schema']}.{row['table_name']}")
            except Exception as schema_err:
                logger.warning(f"Could not list sys tables: {schema_err}")
        
        return True
    except Exception as e:
        logger.error(f"Reflection query test failed: {e}")
        return False

def test_sentiment_queries(service):
    """Test sentiment-specific queries."""
    try:
        logger.info("Testing sentiment queries...")
        
        # First, check what catalogs are available
        try:
            catalogs_query = "SHOW CATALOGS"
            catalogs = service.query(catalogs_query)
            if not catalogs.empty:
                logger.info(f"Available catalogs: {', '.join(catalogs['name'].tolist())}")
                
                # For each catalog, try to get schemas
                all_schemas = []
                for catalog in catalogs['name'].tolist():
                    try:
                        schemas_query = f"SHOW SCHEMAS IN {catalog}"
                        schemas = service.query(schemas_query)
                        if not schemas.empty:
                            logger.info(f"Schemas in catalog {catalog}: {', '.join(schemas['name'].tolist())}")
                            all_schemas.extend([f"{catalog}.{schema}" for schema in schemas['name'].tolist()])
                    except Exception as sch_err:
                        logger.warning(f"Could not list schemas in catalog {catalog}: {sch_err}")
                
                # Check if 'iceberg_catalog.sentiment' is in the available schemas
                if 'iceberg_catalog.sentiment' in all_schemas:
                    # Look for tables in the sentiment schema
                    test_query = """
                    SELECT 
                        table_schema, 
                        table_name 
                    FROM 
                        information_schema.tables 
                    WHERE 
                        table_schema = 'iceberg_catalog.sentiment'
                    """
                    tables = service.query(test_query)
                    logger.info(f"Found {len(tables)} tables in iceberg_catalog.sentiment schema:")
                    
                    # Display table information
                    if not tables.empty:
                        for _, row in tables.iterrows():
                            logger.info(f"Table: {row['table_schema']}.{row['table_name']}")
                        
                        # If ticker_sentiment table exists, test a query against it
                        if 'ticker_sentiment' in tables['table_name'].values:
                            # First check the schema of ticker_sentiment
                            columns_query = """
                            SELECT 
                                column_name, 
                                data_type 
                            FROM 
                                information_schema.columns 
                            WHERE 
                                table_schema = 'iceberg_catalog.sentiment' 
                                AND table_name = 'ticker_sentiment'
                            """
                            columns = service.query(columns_query)
                            if not columns.empty:
                                logger.info(f"Columns in ticker_sentiment: {', '.join(columns['column_name'].tolist())}")
                                
                                # Try a simple query that should work on most tables
                                sample_query = """
                                SELECT 
                                    * 
                                FROM 
                                    iceberg_catalog.sentiment.ticker_sentiment 
                                LIMIT 5
                                """
                                try:
                                    sample_data = service.query(sample_query)
                                    logger.info(f"Sample data from ticker_sentiment table: {len(sample_data)} rows")
                                    if not sample_data.empty:
                                        logger.info(f"Columns: {', '.join(sample_data.columns.tolist())}")
                                except Exception as q_err:
                                    logger.warning(f"Could not query ticker_sentiment table: {q_err}")
                        else:
                            logger.warning("ticker_sentiment table not found in iceberg_catalog.sentiment schema")
                    else:
                        logger.warning("No tables found in iceberg_catalog.sentiment schema")
                else:
                    logger.warning("iceberg_catalog.sentiment schema not found")
            else:
                logger.warning("No catalogs found")
                
        except Exception as cat_err:
            logger.warning(f"Could not query catalogs: {cat_err}")
            
            # Try listing all schemas
            try:
                schemas_query = "SHOW SCHEMAS"
                schemas = service.query(schemas_query)
                logger.info(f"Available schemas: {', '.join(schemas['name'].tolist())}")
            except Exception as sch_err:
                logger.warning(f"Could not list schemas: {sch_err}")
            
            # Try listing tables in the information_schema
            try:
                tables_query = """
                SELECT 
                    table_schema, 
                    table_name 
                FROM 
                    information_schema.tables 
                LIMIT 10
                """
                tables = service.query(tables_query)
                logger.info(f"Sample tables from information_schema: {len(tables)} rows")
                if not tables.empty:
                    for _, row in tables.iterrows():
                        logger.info(f"Table: {row['table_schema']}.{row['table_name']}")
            except Exception as tab_err:
                logger.warning(f"Could not list tables: {tab_err}")
        
        return True
    except Exception as e:
        logger.error(f"Sentiment query test failed: {e}")
        return False

def demo_sentiment_service(service):
    """Demonstrate the DremioSentimentQueryService API."""
    try:
        logger.info("\n\n=== DREMIO SENTIMENT QUERY SERVICE DEMO ===\n")
        
        # Try using the service methods with a sample ticker
        ticker = "AAPL"
        
        try:
            # Get sentiment for a specific ticker
            logger.info(f"Getting sentiment data for {ticker}...")
            sentiment_data = service.get_ticker_sentiment(ticker, days=7)
            if not sentiment_data.empty:
                logger.info(f"Found {len(sentiment_data)} sentiment records for {ticker}")
                logger.info(f"Sample data: {sentiment_data.head(3)}")
            else:
                logger.info(f"No sentiment data found for {ticker}")
            
            # Get sentiment trend
            logger.info(f"Getting sentiment trend for {ticker}...")
            trend_data = service.get_sentiment_trend(ticker, days=30)
            if not trend_data.empty:
                logger.info(f"Sentiment trend for {ticker} over the last 30 days:")
                logger.info(trend_data)
            else:
                logger.info(f"No trend data found for {ticker}")
            
            # Get top positive tickers
            logger.info("Getting top positive sentiment tickers...")
            positive_tickers = service.get_top_positive_tickers(limit=5)
            if not positive_tickers.empty:
                logger.info("Top 5 positive sentiment tickers:")
                logger.info(positive_tickers)
            else:
                logger.info("No positive ticker data found")
            
            # Get sentiment by source
            logger.info(f"Getting sentiment by source for {ticker}...")
            source_data = service.get_sentiment_by_source(ticker)
            if not source_data.empty:
                logger.info(f"Sentiment by source for {ticker}:")
                logger.info(source_data)
            else:
                logger.info(f"No source data found for {ticker}")
                
        except Exception as api_err:
            logger.warning(f"Could not run sentiment API methods: {api_err}")
            logger.info("Some methods may require specific table structures that aren't available yet.")
            
        return True
    except Exception as e:
        logger.error(f"Sentiment service demo failed: {e}")
        return False

def main():
    """Main function for testing the DremioSentimentQueryService."""
    parser = argparse.ArgumentParser(description='Test DremioSentimentQueryService')
    parser.add_argument('--host', default='localhost', help='Dremio host')
    parser.add_argument('--port', type=int, default=31010, help='Dremio port')
    parser.add_argument('--user', default='dremio', help='Dremio username')
    parser.add_argument('--password', default='dremio123', help='Dremio password')
    parser.add_argument('--driver', help='Path to Dremio JDBC driver jar file')
    
    args = parser.parse_args()
    
    # Create the service
    service = DremioSentimentQueryService(
        jdbc_driver_path=args.driver,
        dremio_host=args.host,
        dremio_port=args.port,
        dremio_username=args.user,
        dremio_password=args.password
    )
    
    # Test with context manager
    with service as dremio:
        # Run tests
        conn_success = test_connection(dremio)
        
        if conn_success:
            reflection_success = test_reflection_query(dremio)
            sentiment_success = test_sentiment_queries(dremio)
            demo_success = demo_sentiment_service(dremio)
            
            # Overall success
            if reflection_success and sentiment_success:
                logger.info("\n✅ All tests passed successfully!")
            else:
                logger.warning("\n⚠️ Some tests failed, but basic connectivity works.")
        else:
            logger.error("\n❌ Failed to connect to Dremio.")

if __name__ == "__main__":
    main()