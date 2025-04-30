"""
API launcher script with JVM initialization.

This script initializes the JVM with the correct settings before starting the API.
"""

import os
import sys
import logging
import jpype
import uvicorn
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_jvm():
    """Initialize JVM with the correct settings if not already running."""
    if not jpype.isJVMStarted():
        # Get JDBC driver path from environment or use default
        jdbc_driver_path = os.environ.get(
            "DREMIO_JDBC_DRIVER",
            str(Path(__file__).parent.parent.parent / "drivers" / "dremio-jdbc-driver.jar")
        )
        
        # Get JVM args from environment or use defaults
        jpype_jvm_args = os.environ.get("JPYPE_JVM_ARGS", "")
        if jpype_jvm_args:
            jvm_args = jpype_jvm_args.split()
        else:
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
        
        logger.info(f"Using JDBC driver: {jdbc_driver_path}")
        logger.info(f"Using JVM arguments: {jvm_args}")
        
        # Add JDBC driver to classpath
        classpath = os.environ.get("CLASSPATH", "")
        if jdbc_driver_path not in classpath:
            if classpath:
                classpath = f"{classpath}:{jdbc_driver_path}"
            else:
                classpath = jdbc_driver_path
            os.environ["CLASSPATH"] = classpath
        
        # Start JVM with the correct settings
        logger.info("Initializing JVM with custom arguments...")
        jpype.startJVM(*jvm_args, classpath=classpath)
        logger.info("JVM initialized successfully")

def main():
    """Start the API with the correct JVM settings."""
    # Initialize JVM before importing the API module
    initialize_jvm()
    
    # Now import the API module
    api_module = "iceberg_lake.api.sentiment_query_api:app"
    
    # Use direct import to avoid module path issues
    from iceberg_lake.api.sentiment_query_api import app
    
    # Run the API
    logger.info("Starting API...")
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False  # Disable reload to avoid JVM initialization issues
    )

if __name__ == "__main__":
    main()