# Dremio Sentiment Query Layer

This directory contains the implementation of Phase 3 of the data tier plan: the query layer for sentiment analysis data stored in Iceberg tables and accessed via Dremio.

## Components

### 1. Dremio Sentiment Query Service

The `dremio_sentiment_query.py` file contains the `DremioSentimentQueryService` class, which provides methods for executing various sentiment analysis queries against Dremio.

Key features:
- JDBC-based connection to Dremio
- Support for complex sentiment analysis queries
- Efficient result caching
- Comprehensive error handling
- Connection pooling for better performance

### 2. REST API Service

The `sentiment_api.py` file implements a FastAPI-based REST API service that exposes the query functionality as HTTP endpoints.

Key features:
- RESTful API design
- Parameter validation
- JSON response formatting
- Error handling and status codes
- Swagger/OpenAPI documentation

### 3. Dremio Reflection Manager

The `setup_dremio_reflections.py` script provides a utility for creating and managing Dremio reflections, which are essential for optimizing query performance.

Key features:
- Dremio REST API integration
- Creation of various reflection types for sentiment data
- Comprehensive error handling and logging
- Command-line interface for flexible configuration

### 4. Query Service Verification

The `verify_query_service.py` script provides a comprehensive verification tool for testing the query service functionality against real data.

Key features:
- Tests for all major query types
- Detailed result logging and validation
- Command-line interface for configuration
- Clear success/failure reporting

## Usage

### Setting Up Dremio Reflections

To set up Dremio reflections for optimized query performance:

```bash
python setup_dremio_reflections.py --host localhost --port 9047 --username dremio --password dremio123
```

Options:
- `--host`: Dremio host (default: localhost)
- `--port`: Dremio REST API port (default: 9047)
- `--username`: Dremio username (default: dremio)
- `--password`: Dremio password (default: dremio123)
- `--catalog`: Dremio catalog (default: DREMIO)
- `--namespace`: Dremio namespace (default: sentiment)
- `--table-name`: Dremio table name (default: sentiment_data)

### Verifying Query Service

To verify the query service functionality:

```bash
python verify_query_service.py --host localhost --port 31010 --username dremio --password dremio123 --ticker AAPL
```

Options:
- `--host`: Dremio JDBC host (default: localhost)
- `--port`: Dremio JDBC port (default: 31010)
- `--username`: Dremio username (default: dremio)
- `--password`: Dremio password (default: dremio123)
- `--driver-path`: Path to JDBC driver JAR file (optional)
- `--ticker`: Ticker symbol to use for testing (default: AAPL)

### Running the API Service

To start the REST API service with proper JVM configuration:

```bash
# Set up the JVM configuration
source /home/jonat/WSL_RT_Sentiment/drivers/config/setenv.sh

# Run the API with proper JVM initialization
python /home/jonat/WSL_RT_Sentiment/iceberg_lake/api/run_api.py
```

Alternatively, you can use the launcher script:

```bash
python /home/jonat/WSL_RT_Sentiment/drivers/config/run_query_api.py
```

The API will be available at `http://localhost:8000` with Swagger documentation at `http://localhost:8000/docs`.

> **IMPORTANT**: When using `uvicorn` directly, the JVM must be initialized before importing the API module. Use the provided launcher scripts to ensure correct JVM initialization.

## Requirements

- Python 3.8+
- JDK 8+
- Dremio JDBC driver
- Dremio instance with access to Iceberg tables
- Virtual environment with required packages:
  - jpype1
  - pandas
  - fastapi
  - uvicorn
  - tabulate
  - requests

## Troubleshooting

### JDBC Connection Issues

If you encounter JDBC connection issues:
1. Verify that the JDBC driver is properly installed
2. Ensure Dremio is running and accessible
3. Check credentials and connection details
4. Verify that the JVM is properly configured

#### JVM Configuration for Modern Java (JDK 21+)

For newer Java versions (JDK 21+), you must configure the JVM with special arguments to allow the Dremio JDBC driver to access restricted modules:

```bash
# Set up the JVM configuration
source /home/jonat/WSL_RT_Sentiment/drivers/config/setenv.sh

# Test the connection
python /home/jonat/WSL_RT_Sentiment/iceberg_lake/query/test_dremio_query_service.py
```

Required JVM arguments:
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

These arguments are required to allow the Dremio JDBC driver to access restricted Java modules, which is needed for Netty to work properly with `sun.misc.Unsafe` and `java.nio.DirectByteBuffer`.

### Reflection Setup Issues

If reflection setup fails:
1. Check Dremio REST API credentials and endpoint
2. Verify that the table exists in Dremio
3. Check for proper permissions in Dremio
4. Inspect logs for detailed error information

### Empty Query Results

If queries return empty results:
1. Verify that data exists in the target table
2. Check that the ticker symbol is correct
3. Ensure that the time range includes data
4. Check for any filtering conditions that might exclude all data

## Performance Optimization

For optimal performance:
1. Ensure appropriate reflections are created for common query patterns
2. Use connection pooling for multiple concurrent queries
3. Implement result caching for frequent queries
4. Monitor and tune JVM memory allocation
5. Optimize query execution plans in Dremio

## Next Steps

Future enhancements could include:
1. Implementing more advanced caching strategies
2. Adding security measures like authentication and encryption
3. Integrating with dashboarding tools
4. Implementing performance monitoring and alerting
5. Adding support for more complex analytical queries