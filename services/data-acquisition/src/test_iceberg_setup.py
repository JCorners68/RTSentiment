"""
Test script for the Iceberg setup module.

This script verifies that the Iceberg catalog and tables can be properly initialized.
"""

import logging
import os
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Import the iceberg_setup module
from iceberg_setup import get_iceberg_catalog, initialize_iceberg, get_table

def test_iceberg_setup():
    """Test the Iceberg setup functionality."""
    print("Testing Iceberg setup...")
    
    # Initialize Iceberg
    success = initialize_iceberg()
    assert success, "Failed to initialize Iceberg"
    
    # Get catalog and verify tables exist
    catalog = get_iceberg_catalog()
    config_path = Path(__file__).parent.parent / "config.py"
    sys.path.append(str(config_path.parent))
    from config import ICEBERG_CATALOG_NAME
    
    # Check sentiment_records table
    sentiment_table_name = f"{ICEBERG_CATALOG_NAME}.sentiment_records"
    assert catalog.table_exists(sentiment_table_name), f"Table {sentiment_table_name} does not exist"
    sentiment_table = get_table("sentiment_records")
    assert sentiment_table is not None, "Failed to load sentiment_records table"
    
    # Check market_events table
    events_table_name = f"{ICEBERG_CATALOG_NAME}.market_events"
    assert catalog.table_exists(events_table_name), f"Table {events_table_name} does not exist"
    events_table = get_table("market_events")
    assert events_table is not None, "Failed to load market_events table"
    
    # Print table schemas
    print("\nSentiment Records Schema:")
    print(sentiment_table.schema())
    
    print("\nMarket Events Schema:")
    print(events_table.schema())
    
    # Print partition specs
    print("\nSentiment Records Partition Spec:")
    print(sentiment_table.spec())
    
    print("\nMarket Events Partition Spec:")
    print(events_table.spec())
    
    print("\nAll tests passed successfully!")
    return True

if __name__ == "__main__":
    try:
        test_iceberg_setup()
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)