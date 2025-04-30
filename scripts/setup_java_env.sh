#!/bin/bash
set -e

echo "Setting up Java environment for Dremio JDBC driver..."

# Check Java version
echo "Java version:"
java -version

# Create a directory for Java configuration
JAVA_CONFIG_DIR="/home/jonat/WSL_RT_Sentiment/drivers/java_config"
mkdir -p "${JAVA_CONFIG_DIR}"

# Create a JVM options file for JPype
JVM_OPTIONS_FILE="${JAVA_CONFIG_DIR}/jpype.properties"
cat > "${JVM_OPTIONS_FILE}" << EOL
# JVM options for JPype when using Dremio JDBC
# These options enable Unsafe operations needed by Netty in Dremio JDBC

# Enable Unsafe operations
-XX:+UnlockDiagnosticVMOptions
-XX:+AllowRedefinitionToAddDeleteMethods
-Dio.netty.tryReflectionSetAccessible=true

# Memory settings
-Xms512m
-Xmx1g

# Debugging options (comment out in production)
-Djava.net.preferIPv4Stack=true
-Dlog4j.debug=true
EOL

# Create environment variables script
ENV_SCRIPT="${JAVA_CONFIG_DIR}/setenv.sh"
cat > "${ENV_SCRIPT}" << EOL
#!/bin/bash
# Environment variables for Dremio JDBC

# Java home
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))
export PATH=\${JAVA_HOME}/bin:\${PATH}

# JPype options
export _JPYPE_JVM_ARGS="-Dio.netty.tryReflectionSetAccessible=true -Xmx1g"

# JDBC driver path
export DREMIO_JDBC_DRIVER="/home/jonat/WSL_RT_Sentiment/drivers/dremio-jdbc-driver.jar"

# Java options
export JAVA_OPTS="-Dio.netty.tryReflectionSetAccessible=true -Xmx1g"
EOL

chmod +x "${ENV_SCRIPT}"

# Create a test script
TEST_SCRIPT="${JAVA_CONFIG_DIR}/test_jdbc.py"
cat > "${TEST_SCRIPT}" << EOL
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
EOL

chmod +x "${TEST_SCRIPT}"

# Create script to launch the FastAPI app with the correct JVM settings
API_LAUNCHER="${JAVA_CONFIG_DIR}/start_api.sh"
cat > "${API_LAUNCHER}" << EOL
#!/bin/bash
source "${JAVA_CONFIG_DIR}/setenv.sh"

echo "Starting Sentiment API with enhanced JVM settings..."
cd /home/jonat/WSL_RT_Sentiment

# Set up Python environment
source iceberg_venv/bin/activate

# Start the API with proper JVM settings
PYTHONPATH=/home/jonat/WSL_RT_Sentiment python iceberg_lake/examples/start_sentiment_api.py
EOL

chmod +x "${API_LAUNCHER}"

echo "Java environment setup completed."
echo ""
echo "To apply the settings and test JDBC connectivity:"
echo "  1. Run: source ${JAVA_CONFIG_DIR}/setenv.sh"
echo "  2. Test connection: python ${TEST_SCRIPT}"
echo ""
echo "To start the API with the correct settings:"
echo "  Run: ${API_LAUNCHER}"