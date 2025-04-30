#!/usr/bin/env python3
"""
Helper script to run the DremioSentimentQueryService with the right JVM options.
"""
import os
import sys
import jpype
import jaydebeapi
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Test JDBC connection with proper JVM arguments."""
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
    
    # Connect to Dremio
    try:
        logger.info("Testing connection to Dremio...")
        conn = jaydebeapi.connect(
            "com.dremio.jdbc.Driver",
            "jdbc:dremio:direct=localhost:31010",
            ["dremio", "dremio123"],
            jdbc_driver
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchall()
        logger.info(f"Connection successful! Result: {result}")
        
        cursor.close()
        conn.close()
        
        logger.info("Test completed successfully!")
        return 0
    except Exception as e:
        logger.error(f"Error connecting to Dremio: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
