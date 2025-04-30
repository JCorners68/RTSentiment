#!/bin/bash
# Environment variables for Dremio JDBC

# Set JAVA_HOME if not already set
if [ -z "$JAVA_HOME" ]; then
    export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))
    echo "Set JAVA_HOME to $JAVA_HOME"
fi

# Add JAVA_HOME/bin to PATH
export PATH=$JAVA_HOME/bin:$PATH

# Set DREMIO_JDBC_DRIVER environment variable
export DREMIO_JDBC_DRIVER="/home/jonat/WSL_RT_Sentiment/drivers/dremio-jdbc-driver.jar"
echo "Set DREMIO_JDBC_DRIVER to $DREMIO_JDBC_DRIVER"

# Set JVM options for JPype
JVM_OPTS=$(cat "/home/jonat/WSL_RT_Sentiment/drivers/config/jvm.opts" | grep -v "^#" | tr '\n' ' ')
export JPYPE_JVM_ARGS="$JVM_OPTS"
echo "Set JPYPE_JVM_ARGS to $JPYPE_JVM_ARGS"

# Set CLASSPATH to include the JDBC driver
if [ -z "$CLASSPATH" ]; then
    export CLASSPATH="/home/jonat/WSL_RT_Sentiment/drivers/dremio-jdbc-driver.jar"
else
    export CLASSPATH="/home/jonat/WSL_RT_Sentiment/drivers/dremio-jdbc-driver.jar:$CLASSPATH"
fi
echo "Added JDBC driver to CLASSPATH"

# Use this command to test if everything is working:
echo "To test connectivity with properly configured JVM:"
echo "source '/home/jonat/WSL_RT_Sentiment/drivers/config/setenv.sh' && python '/home/jonat/WSL_RT_Sentiment/drivers/config/run_with_jpype.py'"
