#!/usr/bin/env python3
"""
Script to start the Sentiment Query API service.

This script launches the FastAPI service that provides query access to
sentiment data stored in Iceberg tables via Dremio.
"""
import os
import sys
import argparse
import logging
import uvicorn
from pathlib import Path

# Add parent directory to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_api(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """
    Start the FastAPI service for sentiment queries.
    
    Args:
        host: Host address to bind to
        port: Port number to listen on
        reload: Whether to enable auto-reload for development
    """
    logger.info(f"Starting Sentiment Query API on {host}:{port}")
    
    # Import the module containing the FastAPI app
    from iceberg_lake.query.sentiment_api import app
    
    # Start the server
    uvicorn.run(
        "iceberg_lake.query.sentiment_api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the Sentiment Query API service")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port number to listen on (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()
    
    start_api(host=args.host, port=args.port, reload=args.reload)