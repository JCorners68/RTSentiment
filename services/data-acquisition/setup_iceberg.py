#!/usr/bin/env python3
"""
Iceberg Setup Script

This script initializes the Iceberg catalog and tables for the Finnhub POC.
"""

import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Ensure the warehouse directory exists
WAREHOUSE_PATH = "/home/jonat/real_senti/data/iceberg/warehouse"
os.makedirs(WAREHOUSE_PATH, exist_ok=True)
logger.info(f"Warehouse directory created at: {WAREHOUSE_PATH}")

# Add project directory to path
sys.path.append("/home/jonat/real_senti/services/data-acquisition")

# Import the iceberg_setup module
try:
    from src.iceberg_setup import initialize_iceberg, get_iceberg_catalog
    from config import get_config
    
    # Initialize Iceberg
    logger.info("Initializing Iceberg catalog and tables...")
    success = initialize_iceberg()
    
    if success:
        logger.info("Iceberg initialization successful!")
        
        # Verify tables were created
        catalog = get_iceberg_catalog()
        namespace = get_config()["iceberg"]["catalog_name"]
        
        for table in ["sentiment_records", "market_events"]:
            full_table_name = f"{namespace}.{table}"
            if catalog.table_exists(full_table_name):
                logger.info(f"✅ Table '{full_table_name}' successfully created")
            else:
                logger.error(f"❌ Table '{full_table_name}' not found")
    else:
        logger.error("Failed to initialize Iceberg")
        sys.exit(1)
    
except Exception as e:
    logger.error(f"Error during Iceberg setup: {e}")
    sys.exit(1)

logger.info("Iceberg setup completed successfully")