#!/usr/bin/env python3
"""
Finnhub Data Acquisition CLI

A command-line interface for testing and managing the Finnhub data source.
This CLI allows setting API keys, initializing Iceberg tables, collecting data,
and verifying data storage.
"""

import os
import sys
import json
import asyncio
import argparse
import logging
import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import configparser
import uuid
import pandas as pd
from tqdm import tqdm

# Add parent directory to path for importing config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from config import get_config
except ImportError:
    # Config module not found, will create a fallback implementation
    pass

try:
    from src.finnhub_source import FinnhubDataSource
    from src.iceberg_setup import (
        initialize_iceberg, get_iceberg_catalog, get_table, 
        create_sentiment_records_table, create_market_events_table
    )
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you're running this script from the root of the data-acquisition service")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
CONFIG_DIR = os.path.expanduser("~/.rt-sentiment")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.ini")
DEFAULT_TICKERS = ["AAPL", "MSFT", "AMZN", "GOOGL", "META"]
SP500_FILE = os.path.join(CONFIG_DIR, "sp500.json")


def ensure_config_dir() -> None:
    """Ensure configuration directory exists."""
    os.makedirs(CONFIG_DIR, exist_ok=True)


def get_api_key() -> Optional[str]:
    """Get Finnhub API key from configuration."""
    if not os.path.exists(CONFIG_FILE):
        return None
    
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    
    if "finnhub" in config and "api_key" in config["finnhub"]:
        return config["finnhub"]["api_key"]
    
    return None


def set_api_key(api_key: str) -> None:
    """Set Finnhub API key in configuration."""
    ensure_config_dir()
    
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
    
    if "finnhub" not in config:
        config["finnhub"] = {}
    
    config["finnhub"]["api_key"] = api_key
    
    with open(CONFIG_FILE, "w") as f:
        config.write(f)
    
    logger.info(f"Finnhub API key saved to {CONFIG_FILE}")


def has_config_module() -> bool:
    """Check if the config module exists and can be imported."""
    try:
        from config import get_config
        return True
    except ImportError:
        return False


def create_fallback_config() -> Dict[str, Any]:
    """Create a fallback configuration when the config module is not available."""
    api_key = get_api_key()
    if not api_key:
        logger.error("No API key found. Please set an API key first with: cli.py set-api-key YOUR_KEY")
        sys.exit(1)
    
    # Default SP500 tickers
    sp500_tickers = []
    if os.path.exists(SP500_FILE):
        try:
            with open(SP500_FILE, "r") as f:
                sp500_tickers = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load SP500 tickers: {e}")
            sp500_tickers = DEFAULT_TICKERS
    else:
        sp500_tickers = DEFAULT_TICKERS
    
    # Create fallback config
    return {
        "api_keys": {
            "finnhub": api_key
        },
        "iceberg": {
            "catalog_name": "rt_sentiment",
            "warehouse": os.path.join(CONFIG_DIR, "warehouse")
        },
        "rate_limits": {
            "finnhub": 60  # Finnhub's free tier is 60 calls per minute
        },
        "features": {
            "use_redis_cache": False,
            "use_iceberg_backend": True
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "db": 0
        },
        "data_sources": {
            "sp500_tickers": sp500_tickers
        }
    }


# Monkeypatch get_config if the module is not available
if not has_config_module():
    def get_config():
        return create_fallback_config()
    
    sys.modules["config"] = type("config", (), {"get_config": get_config})


def load_sp500_tickers() -> List[str]:
    """Load S&P 500 tickers from config or use defaults."""
    config = get_config()
    return config["data_sources"]["sp500_tickers"]


def save_sp500_tickers(tickers: List[str]) -> None:
    """Save S&P 500 tickers to a local file."""
    ensure_config_dir()
    
    with open(SP500_FILE, "w") as f:
        json.dump(tickers, f)
    
    logger.info(f"Saved {len(tickers)} S&P 500 tickers to {SP500_FILE}")


class ProgressTracker:
    """Helper class to track and display progress of operations."""
    
    def __init__(self, total: int, desc: str = "Processing"):
        """Initialize progress tracker.
        
        Args:
            total: Total number of items to process
            desc: Description of the operation
        """
        self.total = total
        self.desc = desc
        self.pbar = tqdm(total=total, desc=desc)
        self.success_count = 0
        self.failure_count = 0
        self.start_time = datetime.datetime.now()
    
    def update_success(self) -> None:
        """Update tracker with a successful operation."""
        self.success_count += 1
        self.pbar.update(1)
    
    def update_failure(self) -> None:
        """Update tracker with a failed operation."""
        self.failure_count += 1
        self.pbar.update(1)
    
    def close(self) -> Dict[str, Any]:
        """Close the progress tracker and return stats."""
        self.pbar.close()
        duration = (datetime.datetime.now() - self.start_time).total_seconds()
        
        stats = {
            "total": self.total,
            "success": self.success_count,
            "failure": self.failure_count,
            "duration_seconds": duration
        }
        
        return stats


async def collect_data_for_tickers(
    tickers: List[str], 
    historical_days: int = 7, 
    batch_size: int = 5
) -> Dict[str, Any]:
    """Collect data for a list of tickers with progress display.
    
    Args:
        tickers: List of ticker symbols
        historical_days: Number of historical days to collect
        batch_size: Size of ticker batches to process concurrently
        
    Returns:
        Collection statistics
    """
    # Initialize FinnhubDataSource
    data_source = FinnhubDataSource()
    
    try:
        # Setup progress tracking
        tracker = ProgressTracker(len(tickers), desc="Collecting data")
        
        # Define aggregated results
        results = {
            "success_count": 0,
            "failure_count": 0,
            "total_tickers": len(tickers),
            "total_news": 0,
            "total_sentiment_records": 0,
            "total_earnings": 0,
            "total_market_events": 0
        }
        
        # Process in batches
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            
            # Process batch concurrently
            tasks = [data_source.collect_data_for_ticker(ticker, historical_days) for ticker in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Update progress and results
            for ticker, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to process {ticker}: {result}")
                    tracker.update_failure()
                    results["failure_count"] += 1
                else:
                    success, counts = result
                    if success:
                        tracker.update_success()
                        results["success_count"] += 1
                        results["total_news"] += counts["news_items"]
                        results["total_sentiment_records"] += counts["sentiment_records"]
                        results["total_earnings"] += counts["earnings_items"]
                        results["total_market_events"] += counts["market_events"]
                    else:
                        tracker.update_failure()
                        results["failure_count"] += 1
            
            # Pause between batches
            if i + batch_size < len(tickers):
                await asyncio.sleep(0.5)
        
        # Get final stats and close progress bar
        stats = tracker.close()
        results.update({
            "duration_seconds": stats["duration_seconds"],
            "items_per_second": stats["total"] / stats["duration_seconds"] if stats["duration_seconds"] > 0 else 0
        })
        
        return results
    
    finally:
        # Clean up resources
        await data_source.close()


async def verify_iceberg_data(table_name: str, limit: int = 5) -> bool:
    """Verify data exists in an Iceberg table by displaying sample records.
    
    Args:
        table_name: The name of the Iceberg table to query
        limit: Maximum number of records to display
        
    Returns:
        True if data was found and displayed, False otherwise
    """
    table = get_table(table_name)
    
    if not table:
        logger.error(f"Table '{table_name}' not found")
        return False
    
    try:
        # Query the table
        with table.newScan() as scan:
            rows = list(scan.planFiles().Pandas().iter_rows())
        
        if not rows:
            logger.warning(f"No data found in table '{table_name}'")
            return False
        
        # Display sample records
        print(f"\nSample records from {table_name} table:")
        print("=" * 80)
        
        for i, row in enumerate(rows[:limit]):
            print(f"Record {i+1}:")
            for k, v in row.items():
                if k == "metadata" and isinstance(v, dict):
                    print(f"  {k}:")
                    for mk, mv in v.items():
                        print(f"    {mk}: {mv}")
                else:
                    print(f"  {k}: {v}")
            print("-" * 40)
        
        if len(rows) > limit:
            print(f"... and {len(rows) - limit} more records")
        
        print(f"Total records: {len(rows)}")
        print("=" * 80)
        
        return True
    
    except Exception as e:
        logger.error(f"Error querying table '{table_name}': {e}")
        return False


def command_set_api_key(args) -> None:
    """Handle the set-api-key command."""
    api_key = args.key
    set_api_key(api_key)
    print(f"Finnhub API key has been set.")


def command_init_iceberg(args) -> None:
    """Handle the init-iceberg command."""
    print("Initializing Iceberg catalog and tables...")
    
    success = initialize_iceberg()
    
    if success:
        print("✅ Iceberg catalog and tables successfully initialized")
        
        # Verify tables
        catalog = get_iceberg_catalog()
        namespace = get_config()["iceberg"]["catalog_name"]
        
        print("\nVerifying created tables:")
        for table in ["sentiment_records", "market_events"]:
            full_table_name = f"{namespace}.{table}"
            if catalog.table_exists(full_table_name):
                print(f"✅ Table '{table}' successfully created")
            else:
                print(f"❌ Table '{table}' not found")
    else:
        print("❌ Failed to initialize Iceberg catalog and tables")


async def command_collect_data(args) -> None:
    """Handle the collect-data command."""
    tickers = args.tickers
    
    # Use SP500 list if specified
    if args.sp500:
        tickers = load_sp500_tickers()
    
    # Limit the number of tickers if specified
    if args.limit and args.limit > 0:
        tickers = tickers[:args.limit]
    
    if not tickers:
        print("No tickers specified. Use --tickers or --sp500 option.")
        return
    
    print(f"Collecting data for {len(tickers)} tickers:")
    print(f"  - Historical days: {args.days}")
    print(f"  - Batch size: {args.batch_size}")
    
    results = await collect_data_for_tickers(
        tickers=tickers,
        historical_days=args.days,
        batch_size=args.batch_size
    )
    
    # Display summary
    print("\nCollection Results:")
    print(f"  - Total tickers: {results['total_tickers']}")
    print(f"  - Successful: {results['success_count']}")
    print(f"  - Failed: {results['failure_count']}")
    print(f"  - News items collected: {results['total_news']}")
    print(f"  - Sentiment records: {results['total_sentiment_records']}")
    print(f"  - Earnings items: {results['total_earnings']}")
    print(f"  - Market events: {results['total_market_events']}")
    print(f"  - Duration: {results['duration_seconds']:.2f} seconds")
    print(f"  - Rate: {results['items_per_second']:.2f} tickers/second")


async def command_verify_data(args) -> None:
    """Handle the verify-data command."""
    # Initialize Iceberg if needed
    if args.init:
        success = initialize_iceberg()
        if not success:
            print("❌ Failed to initialize Iceberg. Cannot verify data.")
            return
    
    # Verify sentiment records
    if args.sentiment or not (args.sentiment or args.events):
        await verify_iceberg_data("sentiment_records", args.limit)
    
    # Verify market events
    if args.events or not (args.sentiment or args.events):
        await verify_iceberg_data("market_events", args.limit)


def main() -> None:
    """Main function to handle command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Finnhub Data Acquisition CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Set API key command
    set_key_parser = subparsers.add_parser("set-api-key", help="Set Finnhub API key")
    set_key_parser.add_argument("key", help="Your Finnhub API key")
    
    # Initialize Iceberg command
    init_parser = subparsers.add_parser("init-iceberg", help="Initialize Iceberg tables")
    
    # Collect data command
    collect_parser = subparsers.add_parser("collect-data", help="Collect data for tickers")
    collect_parser.add_argument("--tickers", nargs="+", default=[], help="List of ticker symbols")
    collect_parser.add_argument("--sp500", action="store_true", help="Use S&P 500 tickers")
    collect_parser.add_argument("--limit", type=int, default=0, help="Limit number of tickers to process (0 = no limit)")
    collect_parser.add_argument("--days", type=int, default=7, help="Number of historical days to collect")
    collect_parser.add_argument("--batch-size", type=int, default=5, help="Batch size for concurrent processing")
    
    # Verify data command
    verify_parser = subparsers.add_parser("verify-data", help="Verify data in Iceberg tables")
    verify_parser.add_argument("--init", action="store_true", help="Initialize Iceberg if needed")
    verify_parser.add_argument("--sentiment", action="store_true", help="Verify sentiment records")
    verify_parser.add_argument("--events", action="store_true", help="Verify market events")
    verify_parser.add_argument("--limit", type=int, default=5, help="Maximum number of records to display")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Handle commands
    if args.command == "set-api-key":
        command_set_api_key(args)
    elif args.command == "init-iceberg":
        command_init_iceberg(args)
    elif args.command == "collect-data":
        asyncio.run(command_collect_data(args))
    elif args.command == "verify-data":
        asyncio.run(command_verify_data(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()