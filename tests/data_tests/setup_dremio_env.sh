#!/bin/bash

# Setup Dremio environment for JDBC connections and JVM configuration
echo "Setting up Dremio JDBC environment..."

# Set Java environment variables
export JAVA_HOME=/usr/lib/jvm/default-java
export CLASSPATH=/home/jonat/sentiment_test/drivers/dremio-jdbc-driver.jar
export LD_LIBRARY_PATH=$JAVA_HOME/lib:$LD_LIBRARY_PATH

# Dremio Connection Settings
export DREMIO_ENDPOINT=http://localhost:9047
export DREMIO_USERNAME=dremio
export DREMIO_PASSWORD=dremio123
export DREMIO_JDBC_PORT=31010
export DREMIO_CATALOG=DREMIO

# Iceberg Catalog Settings
export ICEBERG_CATALOG_URI=http://localhost:8181
export ICEBERG_WAREHOUSE_LOCATION=file:///tmp/warehouse/
export ICEBERG_NAMESPACE=sentiment
export ICEBERG_TABLE_NAME=sentiment_data

# Create symbolic link to the JDBC driver in current directory if it doesn't exist
if [ ! -f "/home/jonat/sentiment_test/dremio-jdbc-driver.jar" ]; then
  ln -sf /home/jonat/sentiment_test/drivers/dremio-jdbc-driver.jar /home/jonat/sentiment_test/dremio-jdbc-driver.jar
  echo "Created symbolic link to JDBC driver"
fi

# Set JVM args for Python's JPype with enhanced compatibility settings
export _JAVA_OPTIONS="-Djava.class.path=$CLASSPATH \
  -Djavax.net.ssl.trustStore=$JAVA_HOME/lib/security/cacerts \
  --add-opens=java.base/java.lang=ALL-UNNAMED \
  --add-opens=java.base/java.io=ALL-UNNAMED \
  --add-opens=java.base/java.util=ALL-UNNAMED"

echo "Environment setup complete."
echo "JAVA_HOME: $JAVA_HOME"
echo "CLASSPATH: $CLASSPATH"
echo "Dremio JDBC Driver: $(ls -la /home/jonat/sentiment_test/drivers/dremio-jdbc-driver.jar 2>/dev/null || echo 'Not found')"
echo "Dremio Endpoint: $DREMIO_ENDPOINT"
echo "JVM Options: $_JAVA_OPTIONS"

# Activate Python virtual environment if provided
if [ "$1" == "--activate" ]; then
  source /home/jonat/sentiment_test/dremio_venv/bin/activate
  echo "Activated Python virtual environment: dremio_venv"
fi