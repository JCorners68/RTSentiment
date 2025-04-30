#!/usr/bin/env python3
"""
Script to run the Sentiment Query API with properly configured JVM.
"""
import os
import sys
import jpype
import uvicorn
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Start the API with proper JVM configuration."""
    # Find the JDBC driver
    jdbc_driver = os.environ.get("DREMIO_JDBC_DRIVER", 
                               "/home/jonat/WSL_RT_Sentiment/drivers/dremio-jdbc-driver.jar")
    
    # Prepare JVM arguments
    jvm_args = []
    jvm_opts_file = "/home/jonat/WSL_RT_Sentiment/drivers/config/jvm.opts"
    
    if os.path.exists(jvm_opts_file):
        with open(jvm_opts_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    jvm_args.append(line)
    
    logger.info(f"Using JDBC driver: {jdbc_driver}")
    logger.info(f"Using JVM arguments: {jvm_args}")
    
    # Start JVM if not started
    if not jpype.isJVMStarted():
        logger.info("Starting JVM with custom arguments...")
        jpype.startJVM(jpype.getDefaultJVMPath(), *jvm_args, classpath=[jdbc_driver])
    
    # Start the API
    logger.info("Starting Sentiment Query API on 0.0.0.0:8000")
    uvicorn.run(
        "iceberg_lake.query.sentiment_api:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )

if __name__ == "__main__":
    main()
