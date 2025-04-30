#!/usr/bin/env python3
"""
Start the Sentiment API service in mock mode.

This script starts the FastAPI service for the sentiment query API
using the mock implementation rather than the real Dremio connection.
"""
import os
import sys
import logging
import uvicorn

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set environment variable to use mock service
os.environ['USE_MOCK_SERVICE'] = 'true'

def main():
    """Start the API server."""
    logger.info("Starting Sentiment Query API with MOCK implementation")
    logger.info("This will serve sample data and not connect to Dremio")
    
    # Start the API server
    uvicorn.run(
        "iceberg_lake.query.sentiment_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

if __name__ == "__main__":
    main()