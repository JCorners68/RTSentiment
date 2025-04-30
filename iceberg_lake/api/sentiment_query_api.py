"""
Sentiment Query API for testing JVM configuration.

A minimal API to verify the JVM configuration for Dremio JDBC.
"""

import os
import logging
from fastapi import FastAPI, HTTPException, Query
import jpype
import jaydebeapi
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Initialize FastAPI app
app = FastAPI(
    title="Sentiment Query API",
    description="API for querying sentiment data from Dremio",
    version="1.0.0",
)

# Global connection variable
dremio_connection = None

def get_jdbc_connection():
    """Get JDBC connection to Dremio."""
    global dremio_connection
    
    if dremio_connection is not None:
        return dremio_connection
    
    # Get JDBC driver path
    jdbc_driver = os.environ.get(
        "DREMIO_JDBC_DRIVER", 
        "/home/jonat/WSL_RT_Sentiment/drivers/dremio-jdbc-driver.jar"
    )
    
    # Check if JVM is already started
    if not jpype.isJVMStarted():
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
        
        logger.info(f"Starting JVM with custom arguments: {jvm_args}")
        jpype.startJVM(*jvm_args, classpath=[jdbc_driver])
    
    # Connect to Dremio
    jdbc_url = "jdbc:dremio:direct=localhost:31010"
    username = "dremio"
    password = "dremio123"
    
    logger.info(f"Connecting to Dremio at {jdbc_url}")
    dremio_connection = jaydebeapi.connect(
        "com.dremio.jdbc.Driver",
        jdbc_url,
        [username, password],
        jdbc_driver
    )
    
    return dremio_connection

@app.get("/health")
def health_check():
    """Health check endpoint."""
    try:
        # Get connection
        conn = get_jdbc_connection()
        
        # Execute test query
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchall()
        cursor.close()
        
        if result:
            return {"status": "ok", "service": "sentiment-query-api", "jdbc_connection": "ok"}
        else:
            return {"status": "error", "service": "sentiment-query-api", "jdbc_connection": "error"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
def test_connection():
    """Test connection to Dremio."""
    try:
        # Get connection
        conn = get_jdbc_connection()
        
        # Execute test query
        cursor = conn.cursor()
        cursor.execute("SELECT 1 as test")
        result = cursor.fetchall()
        cursor.close()
        
        return {"result": result}
    except Exception as e:
        logger.error(f"Test connection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Startup event handler."""
    logger.info("Starting Sentiment Query API")
    
    # Ensure JVM args are set in environment
    if "JPYPE_JVM_ARGS" not in os.environ:
        os.environ["JPYPE_JVM_ARGS"] = " ".join([
            "--add-opens=java.base/java.nio=ALL-UNNAMED",
            "--add-opens=java.base/sun.nio.ch=ALL-UNNAMED",
            "--add-opens=java.base/sun.security.action=ALL-UNNAMED",
            "--add-opens=java.base/java.util=ALL-UNNAMED",
            "--add-opens=java.base/java.lang=ALL-UNNAMED",
            "--add-opens=java.base/java.lang.reflect=ALL-UNNAMED",
            "-Dio.netty.tryReflectionSetAccessible=true",
            "-Djava.security.egd=file:/dev/./urandom"
        ])

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown event handler."""
    global dremio_connection
    
    logger.info("Shutting down Sentiment Query API")
    
    # Close JDBC connection
    if dremio_connection is not None:
        try:
            dremio_connection.close()
        except Exception as e:
            logger.error(f"Error closing JDBC connection: {e}")
        finally:
            dremio_connection = None