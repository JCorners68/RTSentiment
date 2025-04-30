#!/bin/bash
# Environment variables for Dremio JDBC

# Java home
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
export PATH=${JAVA_HOME}/bin:${PATH}

# JPype options
export _JPYPE_JVM_ARGS="-Dio.netty.tryReflectionSetAccessible=true -Xmx1g"

# JDBC driver path
export DREMIO_JDBC_DRIVER="/home/jonat/WSL_RT_Sentiment/drivers/dremio-jdbc-driver.jar"

# Java options
export JAVA_OPTS="-Dio.netty.tryReflectionSetAccessible=true -Xmx1g"
