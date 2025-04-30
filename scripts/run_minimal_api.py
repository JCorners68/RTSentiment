#!/usr/bin/env python3
"""
Run a minimal API to verify JVM configuration.
"""

import os
import sys
import logging
import jpype
import uvicorn
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Run the minimal API."""
    # Get JDBC driver path
    jdbc_driver = os.environ.get(
        "DREMIO_JDBC_DRIVER", 
        str(Path(__file__).parent.parent / "drivers" / "dremio-jdbc-driver.jar")
    )
    
    # Check if environment variables are set
    jpype_jvm_args = os.environ.get("JPYPE_JVM_ARGS", "")
    if not jpype_jvm_args:
        # Default JVM args for Dremio JDBC compatibility
        jvm_args = [
            "--add-opens=java.base/java.nio=ALL-UNNAMED",
            "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED",
            "--add-opens=java.base/sun.security.action=ALL-UNNAMED",
            "--add-opens=java.base/java.util=ALL-UNNAMED",
            "--add-opens=java.base/java.lang=ALL-UNNAMED",
            "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
            "-Dio.netty.tryReflectionSetAccessible=true",
            "-Djava.security.egd=file:/dev/./urandom"
        ]
    else:
        jvm_args = jpype_jvm_args.split()
    
    logger.info(f"JDBC Driver: {jdbc_driver}")
    logger.info(f"JVM Arguments: {jvm_args}")
    
    # Initialize JVM if not already running
    if not jpype.isJVMStarted():
        logger.info("Starting JVM with custom arguments...")
        jpype.startJVM(*jvm_args, classpath=[jdbc_driver])
    
    # Define API module path
    api_file = Path(__file__).parent.parent / "iceberg_lake" / "api" / "sentiment_query_api.py"
    
    if not api_file.exists():
        logger.error(f"API file not found: {api_file}")
        return 1
    
    # Set necessary environment variable for the API
    os.environ["DREMIO_JDBC_DRIVER"] = jdbc_driver
    
    # Use uvicorn CLI-style arguments to run the API
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    logger.info("Starting API...")
    uvicorn.run(
        "iceberg_lake.api.sentiment_query_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
    
    return 0

if __name__ == "__main__":
    sys.exit(main())