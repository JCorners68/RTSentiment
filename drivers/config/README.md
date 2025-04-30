# Dremio JDBC Configuration

This directory contains configuration files and utility scripts for working with the Dremio JDBC driver in modern Java environments.

## Files

- `setenv.sh`: Environment setup script for Dremio JDBC compatibility
- `jvm.opts`: JVM options required for Dremio JDBC driver compatibility
- `run_with_jpype.py`: Test script for JDBC connectivity with correct JVM arguments
- `run_query_api.py`: API launcher script with proper JVM initialization

## JVM Configuration for Dremio JDBC

The Dremio JDBC driver requires specific JVM arguments to work properly in modern Java environments (JDK 21+). These arguments are necessary because the driver uses Netty, which needs access to restricted Java modules like `sun.misc.Unsafe` and `java.nio.DirectByteBuffer`.

### Required JVM Arguments

```
--add-opens=java.base/java.nio=ALL-UNNAMED
--add-opens=java.base/sun.nio.ch=ALL-UNNAMED
--add-opens=java.base/sun.security.action=ALL-UNNAMED
--add-opens=java.base/java.util=ALL-UNNAMED
--add-opens=java.base/java.lang=ALL-UNNAMED
--add-opens=java.base/java.lang.reflect=ALL-UNNAMED
-Dio.netty.tryReflectionSetAccessible=true
-Djava.security.egd=file:/dev/./urandom
```

## Usage

### Setting Up the Environment

To set up the environment for using the Dremio JDBC driver:

```bash
source /home/jonat/WSL_RT_Sentiment/drivers/config/setenv.sh
```

This script sets the following environment variables:
- `JAVA_HOME`: Path to the Java installation
- `DREMIO_JDBC_DRIVER`: Path to the Dremio JDBC driver JAR file
- `JPYPE_JVM_ARGS`: JVM arguments required for JDBC driver compatibility
- `CLASSPATH`: Updated to include the JDBC driver

### Testing JDBC Connectivity

To test JDBC connectivity with the correct JVM arguments:

```bash
source /home/jonat/WSL_RT_Sentiment/drivers/config/setenv.sh
python /home/jonat/WSL_RT_Sentiment/drivers/config/run_with_jpype.py
```

### Running the API with Proper JVM Configuration

To run the API with proper JVM initialization:

```bash
source /home/jonat/WSL_RT_Sentiment/drivers/config/setenv.sh
python /home/jonat/WSL_RT_Sentiment/drivers/config/run_query_api.py
```

## Important Notes

1. The JVM must be initialized with the correct arguments **before** attempting to use the JDBC driver
2. Never use `uvicorn` directly to run the API, as it won't initialize the JVM correctly
3. Always use the provided scripts to ensure proper JVM configuration
4. If running in a different environment, make sure to set the environment variables and JVM arguments correctly
5. The JDBC driver path and JVM arguments can be customized by modifying the `setenv.sh` script

## Troubleshooting

If you encounter errors like:
- `sun.misc.Unsafe or java.nio.DirectByteBuffer.<init>(long, int) not available`
- `java.lang.ClassNotFoundException: sun.misc.Unsafe`
- `java.lang.reflect.InaccessibleObjectException: Unable to make member accessible: private java.nio.DirectByteBuffer(long,int)`

Make sure you have:
1. Sourced the `setenv.sh` script
2. Initialized the JVM with the correct arguments before using the JDBC driver
3. Used the provided launcher scripts for running the API

## References

- [Dremio JDBC Driver Documentation](https://docs.dremio.com/software/drivers/dremio-jdbc-driver/)
- [Java Module System](https://openjdk.java.net/projects/jigsaw/quick-start)
- [JPype Documentation](https://jpype.readthedocs.io/en/latest/)