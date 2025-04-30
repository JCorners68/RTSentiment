#!/bin/bash
set -e

echo "Setting up proper JVM configuration for Dremio JDBC compatibility"

# Create the drivers directory if it doesn't exist
DRIVERS_DIR="/home/jonat/WSL_RT_Sentiment/drivers"
mkdir -p "$DRIVERS_DIR"

# Download the Dremio JDBC driver if it doesn't exist
DREMIO_JDBC_JAR="$DRIVERS_DIR/dremio-jdbc-driver.jar"
if [ ! -f "$DREMIO_JDBC_JAR" ]; then
    echo "Downloading Dremio JDBC driver..."
    curl -L -o "$DREMIO_JDBC_JAR" "https://download.dremio.com/jdbc-driver/dremio-jdbc-driver-LATEST.jar"
    echo "Downloaded JDBC driver to $DREMIO_JDBC_JAR"
else
    echo "JDBC driver already exists at $DREMIO_JDBC_JAR"
fi

# Create a file with the JVM configuration settings
CONFIG_DIR="$DRIVERS_DIR/config"
mkdir -p "$CONFIG_DIR"

JVM_OPTS_FILE="$CONFIG_DIR/jvm.opts"
cat > "$JVM_OPTS_FILE" << EOL
# JVM options for Dremio JDBC compatibility
--add-opens=java.base/java.nio=ALL-UNNAMED
--add-opens=java.base/sun.nio.ch=ALL-UNNAMED
--add-opens=java.base/sun.security.action=ALL-UNNAMED
--add-opens=java.base/java.util=ALL-UNNAMED
--add-opens=java.base/java.lang=ALL-UNNAMED
--add-opens=java.base/java.lang.reflect=ALL-UNNAMED
-Dio.netty.tryReflectionSetAccessible=true
-Djava.security.egd=file:/dev/./urandom
EOL

echo "Created JVM options file at $JVM_OPTS_FILE"

# Create a script to run JPype with the correct JVM arguments
cat > "$CONFIG_DIR/run_with_jpype.py" << EOL
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
EOL

chmod +x "$CONFIG_DIR/run_with_jpype.py"
echo "Created test script at $CONFIG_DIR/run_with_jpype.py"

# Create environment variables script
ENV_SCRIPT="$CONFIG_DIR/setenv.sh"
cat > "$ENV_SCRIPT" << EOL
#!/bin/bash
# Environment variables for Dremio JDBC

# Set JAVA_HOME if not already set
if [ -z "\$JAVA_HOME" ]; then
    export JAVA_HOME=\$(dirname \$(dirname \$(readlink -f \$(which java))))
    echo "Set JAVA_HOME to \$JAVA_HOME"
fi

# Add JAVA_HOME/bin to PATH
export PATH=\$JAVA_HOME/bin:\$PATH

# Set DREMIO_JDBC_DRIVER environment variable
export DREMIO_JDBC_DRIVER="$DREMIO_JDBC_JAR"
echo "Set DREMIO_JDBC_DRIVER to \$DREMIO_JDBC_DRIVER"

# Set JVM options for JPype
JVM_OPTS=\$(cat "$JVM_OPTS_FILE" | grep -v "^#" | tr '\n' ' ')
export JPYPE_JVM_ARGS="\$JVM_OPTS"
echo "Set JPYPE_JVM_ARGS to \$JPYPE_JVM_ARGS"

# Set CLASSPATH to include the JDBC driver
if [ -z "\$CLASSPATH" ]; then
    export CLASSPATH="$DREMIO_JDBC_JAR"
else
    export CLASSPATH="$DREMIO_JDBC_JAR:\$CLASSPATH"
fi
echo "Added JDBC driver to CLASSPATH"

# Use this command to test if everything is working:
echo "To test connectivity with properly configured JVM:"
echo "source '$ENV_SCRIPT' && python '$CONFIG_DIR/run_with_jpype.py'"
EOL

chmod +x "$ENV_SCRIPT"
echo "Created environment script at $ENV_SCRIPT"

# Create a script to launch the API with the correct JVM settings
API_LAUNCHER="$CONFIG_DIR/run_query_api.py"
cat > "$API_LAUNCHER" << EOL
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
EOL

chmod +x "$API_LAUNCHER"
echo "Created API launcher script at $API_LAUNCHER"

echo ""
echo "====================================================================="
echo "JVM has been configured for Dremio JDBC compatibility"
echo "To use the configuration, run:"
echo "source '$ENV_SCRIPT'"
echo ""
echo "Then test the JDBC connectivity with:"
echo "python '$CONFIG_DIR/run_with_jpype.py'"
echo ""
echo "To run the API with the correct JVM settings:"
echo "python '$API_LAUNCHER'"
echo "====================================================================="