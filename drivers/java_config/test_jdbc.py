#!/usr/bin/env python3
"""
Test script for Dremio JDBC connection.
"""
import os
import sys
import jpype
import jaydebeapi
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_jdbc_connection():
    """Test connecting to Dremio via JDBC."""
    # Find JDBC driver
    driver_path = os.environ.get("DREMIO_JDBC_DRIVER", "/home/jonat/WSL_RT_Sentiment/drivers/dremio-jdbc-driver.jar")
    
    # JDBC connection parameters
    host = "localhost"
    port = 31010
    username = "dremio"
    password = "dremio123"
    
    url = f"jdbc:dremio:direct={host}:{port}"
    
    logger.info(f"Testing JDBC connection to {url}")
    logger.info(f"Using JDBC driver: {driver_path}")
    
    # Set JVM parameters
    if not jpype.isJVMStarted():
        args = ["-Dio.netty.tryReflectionSetAccessible=true", "-Xmx1g"]
        logger.info(f"Starting JVM with args: {args}")
        jpype.startJVM(jpype.getDefaultJVMPath(), *args, classpath=[driver_path])
    
    try:
        # Try to connect
        connection = jaydebeapi.connect(
            "com.dremio.jdbc.Driver",
            url,
            [username, password],
            driver_path
        )
        
        logger.info("Successfully connected to Dremio!")
        
        # Test query execution
        cursor = connection.cursor()
        cursor.execute("SELECT 1 AS test")
        result = cursor.fetchall()
        logger.info(f"Query result: {result}")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to connect to Dremio: {e}")
        return False

if __name__ == "__main__":
    success = test_jdbc_connection()
    sys.exit(0 if success else 1)
