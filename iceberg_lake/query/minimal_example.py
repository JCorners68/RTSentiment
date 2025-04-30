#!/usr/bin/env python3
"""
Minimal example script to verify JVM configuration for Dremio JDBC.
"""

import os
import sys
import logging
import jpype
import jaydebeapi
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Minimal example to verify JVM configuration for Dremio JDBC."""
    # Get JDBC driver path
    jdbc_driver = os.environ.get(
        "DREMIO_JDBC_DRIVER", 
        "/home/jonat/WSL_RT_Sentiment/drivers/dremio-jdbc-driver.jar"
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
    
    logger.info("=== Testing JVM Configuration for Dremio JDBC ===")
    logger.info(f"JDBC Driver: {jdbc_driver}")
    logger.info(f"JVM Arguments: {jvm_args}")
    
    # Initialize JVM if not already running
    if not jpype.isJVMStarted():
        logger.info("Starting JVM with custom arguments...")
        jpype.startJVM(*jvm_args, classpath=[jdbc_driver])
    
    try:
        # Connect to Dremio
        jdbc_url = "jdbc:dremio:direct=localhost:31010"
        username = "dremio"
        password = "dremio123"
        
        logger.info(f"Connecting to Dremio at {jdbc_url}")
        conn = jaydebeapi.connect(
            "com.dremio.jdbc.Driver",
            jdbc_url,
            [username, password],
            jdbc_driver
        )
        
        # Execute a simple query
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchall()
        logger.info(f"Query result: {result}")
        
        # Clean up
        cursor.close()
        conn.close()
        
        logger.info("=== Test completed successfully! ===")
        logger.info("JVM configuration for Dremio JDBC is working correctly.")
        return 0
    except Exception as e:
        logger.error(f"Error: {e}")
        logger.error("JVM configuration test failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())