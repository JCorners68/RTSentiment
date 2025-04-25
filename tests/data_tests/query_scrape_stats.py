#!/usr/bin/env python
"""
Script to query total content scraped by service between date ranges.
"""
import argparse
import datetime
import psycopg2
from typing import Optional, Dict, List, Any
import os

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Query scraped content statistics from Parquet files via FDW',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Query all sources (currently ignores date range due to format variations)
  python tests/data_tests/query_scrape_stats.py 2025-04-01 2025-04-15

  # Query only Reddit data 
  python tests/data_tests/query_scrape_stats.py 2025-04-01 2025-04-15 --source reddit

  # Query only news data
  python tests/data_tests/query_scrape_stats.py 2025-04-01 2025-04-15 --source news
"""
    )
    parser.add_argument('start_date', type=str, help='Start date in YYYY-MM-DD format')
    parser.add_argument('end_date', type=str, help='End date in YYYY-MM-DD format')
    parser.add_argument('--source', type=str, choices=['news', 'reddit', 'all'], 
                        default='all', help='Source to query (news, reddit, or all)')
    
    return parser.parse_args()

def get_db_connection():
    """Connect to PostgreSQL database using environment variables."""
    # Default to localhost if not in Docker environment
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "sentimentdb")
    user = os.getenv("POSTGRES_USER", "pgadmin")
    password = os.getenv("POSTGRES_PASSWORD", "localdev")
    
    # If host is 'postgres' but we're not in Docker environment, use localhost
    if host == "postgres" and not os.path.exists("/.dockerenv"):
        print(f"Not in Docker environment but host is {host}. Falling back to localhost.")
        host = "localhost"
        
    print(f"Attempting to connect to PostgreSQL at {host}:{port}, database: {db_name}")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=db_name,
            user=user,
            password=password
        )
        print("Successfully connected to database")
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("\nPossible solutions:")
        print("1. If running outside Docker, ensure PostgreSQL is installed and running locally")
        print("2. Set environment variables manually:")
        print("   export POSTGRES_HOST=localhost")
        print("   export POSTGRES_PORT=5432")
        print("   export POSTGRES_DB=sentimentdb")
        print("   export POSTGRES_USER=your_username")
        print("   export POSTGRES_PASSWORD=your_password")
        print("3. Use Docker to run the script: docker-compose run --rm api python3 /app/tests/query_scrape_stats.py 2025-04-01 2025-04-15")
        return None

def check_table_exists(conn, table_name):
    """Check if a table exists in the database."""
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name = %s
            );
        """, (table_name,))
        exists = cursor.fetchone()[0]
        cursor.close()
        return exists
    except Exception as e:
        print(f"Error checking if table exists: {e}")
        cursor.close()
        return False

def initialize_database_schema(conn):
    """Initialize the database schema if tables don't exist."""
    print("Attempting to initialize database schema...")
    cursor = conn.cursor()
    try:
        # Create sentiment_events table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sentiment_events (
                id SERIAL PRIMARY KEY,
                source VARCHAR(100) NOT NULL,
                priority VARCHAR(50) NOT NULL,
                text TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model VARCHAR(100),
                sentiment_score FLOAT,
                sentiment_label VARCHAR(50),
                processing_time FLOAT,
                event_id VARCHAR(100) UNIQUE
            );
        """)
        
        # Create ticker_sentiments table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticker_sentiments (
                id SERIAL PRIMARY KEY,
                event_id INTEGER REFERENCES sentiment_events(id),
                ticker VARCHAR(20) NOT NULL,
                sentiment_score FLOAT NOT NULL,
                sentiment_label VARCHAR(50) NOT NULL
            );
        """)
        
        # Add some sample data for testing (only if tables are empty)
        cursor.execute("SELECT COUNT(*) FROM sentiment_events;")
        count = cursor.fetchone()[0]
        
        if count == 0:
            print("Adding sample data for testing...")
            # Insert sample news data
            cursor.execute("""
                INSERT INTO sentiment_events 
                (source, priority, text, timestamp, model, sentiment_score, sentiment_label, processing_time, event_id)
                VALUES 
                ('news_scraper', 'standard', 'Sample news article about AAPL earnings', '2025-04-05 10:00:00', 'finbert', 0.75, 'positive', 0.12, 'sample-news-1'),
                ('news_scraper', 'high', 'Sample news article about TSLA stock crash', '2025-04-10 14:30:00', 'finbert', -0.65, 'negative', 0.11, 'sample-news-2');
            """)
            
            # Insert sample Reddit data
            cursor.execute("""
                INSERT INTO sentiment_events 
                (source, priority, text, timestamp, model, sentiment_score, sentiment_label, processing_time, event_id)
                VALUES 
                ('reddit_scraper', 'standard', 'Sample Reddit post about GME', '2025-04-03 09:15:00', 'finbert', 0.82, 'positive', 0.09, 'sample-reddit-1'),
                ('reddit_scraper', 'standard', 'Sample Reddit post about AMC', '2025-04-12 16:45:00', 'finbert', 0.25, 'neutral', 0.10, 'sample-reddit-2');
            """)
            
            # Insert sample ticker sentiments
            cursor.execute("""
                INSERT INTO ticker_sentiments
                (event_id, ticker, sentiment_score, sentiment_label)
                VALUES
                (1, 'AAPL', 0.75, 'positive'),
                (2, 'TSLA', -0.65, 'negative'),
                (3, 'GME', 0.82, 'positive'),
                (4, 'AMC', 0.25, 'neutral');
            """)
        
        conn.commit()
        print("Database schema initialized successfully.")
        return True
    except Exception as e:
        conn.rollback()
        print(f"Error initializing database schema: {e}")
        return False
    finally:
        cursor.close()

def query_stats(conn, start_date: str, end_date: str, source: Optional[str] = None) -> Dict[str, Any]:
    """
    Query statistics about scraped content between dates using Parquet FDW.
    
    Args:
        conn: Database connection
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        source: Source type to filter by (news, reddit, or None for all)
        
    Returns:
        Dictionary with statistics
    """
    cursor = conn.cursor()
    
    # Check if all_sentiment view exists
    if not check_table_exists(conn, 'all_sentiment'):
        print("Error: 'all_sentiment' view does not exist. Make sure PostgreSQL with parquet_fdw is properly set up.")
        return []
        
    print("Querying data via the all_sentiment view (Parquet FDW)...")
    
    # Build the query based on the source filter
    query = """
    SELECT 
        source,
        COUNT(*) as total_items,
        AVG(sentiment) as avg_sentiment
    FROM 
        all_sentiment
    """
    
    # Initialize parameters and where clause
    params = []
    where_added = False
    
    # Don't filter by date for now, as timestamp formats may vary
    print("Note: Querying all data regardless of date due to potential timestamp format variations")
    
    # Add source filter if specified
    if source and source != 'all':
        if not where_added:
            query += " WHERE"
            where_added = True
        else:
            query += " AND"
            
        if source == 'news':
            query += " source = 'news'"
        elif source == 'reddit':
            query += " source = 'reddit'"
    
    # Group by source
    query += " GROUP BY source ORDER BY source"
    
    try:
        # Execute the query
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Format results
        stats = []
        for row in results:
            try:
                stats.append({
                    'source': row[0],
                    'total_items': row[1],
                    'avg_sentiment': round(float(row[2]), 4) if row[2] is not None else None
                })
            except (IndexError, TypeError) as e:
                print(f"Error processing row {row}: {e}")
                continue
        
        return stats
    except Exception as e:
        print(f"Error executing query: {e}")
        return []
    finally:
        cursor.close()

def main():
    """Main function."""
    args = parse_args()
    
    # Parse dates to ensure proper format
    try:
        start_date = datetime.datetime.strptime(args.start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        end_date = datetime.datetime.strptime(args.end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        
        # Add time component to ensure full day coverage
        start_date += " 00:00:00"
        end_date += " 23:59:59"
    except ValueError:
        print("Error: Dates must be in YYYY-MM-DD format")
        return
    
    # Connect to database
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        # Query statistics
        try:
            stats = query_stats(conn, start_date, end_date, args.source)
        except Exception as e:
            print(f"Error in query_stats: {e}")
            stats = []
        
        # Print results
        if args.source == 'all':
            print(f"\nScraping Statistics (All Records in Parquet Files)")
        else:
            print(f"\nScraping Statistics (Filtered by source={args.source})")
        print("=" * 60)
        
        total_items = 0
        for item in stats:
            total_items += item['total_items']
            print(f"Source: {item['source']}")
            print(f"  Total items: {item['total_items']}")
            print(f"  Average sentiment: {item['avg_sentiment']}")
            print("-" * 30)
        
        print(f"Total items across all sources: {total_items}")
        
    except Exception as e:
        print(f"Error in main function: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()