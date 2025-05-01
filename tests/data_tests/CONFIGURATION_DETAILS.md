# Dremio Configuration and Setup Details

## Overview

This document provides details on the configuration of the sentiment analysis data tier using Dremio, JDBC, and Iceberg. It includes setup steps, configuration details, and lessons learned during the implementation.

## Environment Details

- **RTSentiment Repository**: Branch `adv_data_tier`
- **Python Environment**: Virtual environment `dremio_venv`
- **Dremio**: Running via Docker container
- **JDBC Driver**: Located at `/home/jonat/sentiment_test/drivers/dremio-jdbc-driver.jar`
- **Java**: OpenJDK 21.0.6

## Setup Steps

### 1. Repository Setup

```bash
git clone -b adv_data_tier https://github.com/JCorners68/RTSentiment.git
```

### 2. Python Virtual Environment

```bash
python3 -m venv dremio_venv
source dremio_venv/bin/activate
pip install -r RTSentiment/requirements.txt
pip install pyiceberg JPype1 jaydebeapi
```

### 3. Dremio JDBC Driver Setup

```bash
mkdir -p ~/sentiment_test/drivers
cp RTSentiment/drivers/dremio-jdbc-driver.jar ~/sentiment_test/drivers/
ln -sf ~/sentiment_test/drivers/dremio-jdbc-driver.jar ~/sentiment_test/dremio-jdbc-driver.jar
```

### 4. Environment Configuration

Created `setup_dremio_env.sh` script with the following content:

```bash
#!/bin/bash

# Setup Dremio environment for JDBC connections and JVM configuration

echo "Setting up Dremio JDBC environment..."

# Set Java environment variables
export JAVA_HOME=/usr/lib/jvm/default-java
export CLASSPATH=/home/jonat/sentiment_test/drivers/dremio-jdbc-driver.jar
export LD_LIBRARY_PATH=$JAVA_HOME/lib:$LD_LIBRARY_PATH

# Source the Dremio configuration
source /home/jonat/sentiment_test/dremio.env

# Set Python env variables from Dremio config
export DREMIO_ENDPOINT
export DREMIO_USERNAME
export DREMIO_PASSWORD
export DREMIO_JDBC_PORT
export DREMIO_CATALOG
export ICEBERG_CATALOG_URI
export ICEBERG_WAREHOUSE_LOCATION
export ICEBERG_NAMESPACE
export ICEBERG_TABLE_NAME

# Create symbolic link to the JDBC driver in current directory if it doesn't exist
if [ ! -f "/home/jonat/sentiment_test/dremio-jdbc-driver.jar" ]; then
  ln -sf /home/jonat/sentiment_test/drivers/dremio-jdbc-driver.jar /home/jonat/sentiment_test/dremio-jdbc-driver.jar
  echo "Created symbolic link to JDBC driver"
fi

# Set JVM args for Python's JPype
export _JAVA_OPTIONS="-Djava.class.path=$CLASSPATH -Djavax.net.ssl.trustStore=$JAVA_HOME/lib/security/cacerts"

echo "Environment setup complete."
echo "JAVA_HOME: $JAVA_HOME"
echo "CLASSPATH: $CLASSPATH"
echo "Dremio JDBC Driver: $(ls -la /home/jonat/sentiment_test/drivers/dremio-jdbc-driver.jar)"
echo "Dremio Endpoint: $DREMIO_ENDPOINT"

# Activate Python virtual environment if provided
if [ "$1" == "--activate" ]; then
  source /home/jonat/sentiment_test/dremio_venv/bin/activate
  echo "Activated Python virtual environment: dremio_venv"
fi
```

### 5. Dremio Configuration

Created `dremio.env` file:

```bash
# Dremio Connection Settings
DREMIO_ENDPOINT=http://localhost:9047
DREMIO_USERNAME=dremio
DREMIO_PASSWORD=dremio123
DREMIO_JDBC_PORT=31010
DREMIO_CATALOG=DREMIO

# Iceberg Catalog Settings
ICEBERG_CATALOG_URI=http://localhost:8181
ICEBERG_WAREHOUSE_LOCATION=file:///tmp/warehouse/
ICEBERG_NAMESPACE=sentiment
ICEBERG_TABLE_NAME=sentiment_data

# JVM Settings for Dremio JDBC
JAVA_HOME=/usr/lib/jvm/default-java
CLASSPATH=/home/jonat/sentiment_test/drivers/dremio-jdbc-driver.jar
```

### 6. Running Dremio Container

The Dremio container is started using the provided script:

```bash
./RTSentiment/start_dremio_test_container.sh
```

This script:
1. Checks if Docker is installed
2. Verifies if Dremio container is already running
3. Starts the container if not running
4. Creates test data for verification

## Connection Verification

We verified the Dremio connection using the REST API approach:

```python
import requests
import json

# Authenticate
auth_payload = {
    "userName": "dremio",
    "password": "dremio123"
}
response = requests.post(
    "http://localhost:9047/apiv2/login",
    headers={"Content-Type": "application/json"},
    data=json.dumps(auth_payload)
)
auth_token = response.json().get('token')

# Test catalog query
headers = {
    'Content-Type': 'application/json',
    'Authorization': f'_dremio{auth_token}'
}
response = requests.get("http://localhost:9047/api/v3/catalog", headers=headers)
catalog_data = response.json()
```

## Access Details

- **Dremio UI**: http://localhost:9047
- **Default Credentials**: dremio/dremio123
- **JDBC URL**: jdbc:dremio:direct=localhost:31010

## Lessons Learned

### 1. Java-Python Integration Challenges

The JDBC connectivity from Python using libraries like JPype and JayDeBeApi can be challenging due to:

- **JVM Initialization Issues**: JPype's JVM initialization is sensitive to the Java version and runtime environment.
- **Support Library Problems**: Errors like "Can't find org.jpype.jar support library" indicate mismatch between JPype and the Java version.
- **Environment Variables**: Ensuring CLASSPATH and JAVA_HOME are correctly set is critical.

**Solution Alternatives**:
- Use REST API for operations when possible
- Consider native Java applications for JDBC operations
- Use PySpark with Dremio connector, which has more robust Java integration

### 2. Docker Integration with WSL

When working with WSL:
- Ensure Docker Desktop has WSL integration enabled
- Check that the Docker daemon is running before attempting container operations
- Use absolute paths in volume mounts to avoid path translation issues

### 3. Dremio Data Source Configuration

For proper functionality:
- Create File System sources pointing to correct paths
- Set appropriate permissions for the Dremio user
- Configure Dremio to work with Iceberg tables through proper catalog settings

### 4. Python Environment Management

- Use isolated virtual environments for each project
- Install exact package versions to avoid compatibility issues
- Use `pip install --only-binary=:all:` for problematic packages with C extensions

## Troubleshooting Guide

### JDBC Connection Issues

If encountering JDBC connection errors:

1. **Verify Dremio Status**:
   ```bash
   curl http://localhost:9047
   ```

2. **Check JDBC Driver**:
   ```bash
   file ~/sentiment_test/drivers/dremio-jdbc-driver.jar
   ```

3. **Test REST API Connection**:
   ```bash
   python test_dremio_rest.py
   ```

4. **Java Version Compatibility**:
   If using Java 11+ with older JPype versions, try downgrading Java to version 8.

### Python Module Import Issues

If encountering `ModuleNotFoundError: No module named 'iceberg_lake'` errors:

1. **Use the Wrapper Script**:
   ```bash
   ./verify_dremio_queries.sh --ticker AAPL
   ```

2. **Set PYTHONPATH Manually**:
   ```bash
   export PYTHONPATH=/home/jonat/sentiment_test/RTSentiment:$PYTHONPATH
   cd /home/jonat/sentiment_test/RTSentiment
   python ./iceberg_lake/query/verify_query_service.py --ticker AAPL
   ```

3. **Check Import Structure**:
   Ensure that the `iceberg_lake` directory has an `__init__.py` file and that the module structure is correct. Sometimes relative imports can be problematic if the directory structure doesn't match the import statements.

4. **Run From Project Root**:
   Always run Python scripts from the project root directory to avoid import path issues.

### Dremio Container Issues

If the Dremio container doesn't start:

1. **Check Docker Service**:
   ```bash
   docker ps -a
   ```

2. **View Container Logs**:
   ```bash
   docker logs dremio
   ```

3. **Restart Container**:
   ```bash
   docker restart dremio
   ```

## Additional Resources

- [Dremio Documentation](https://docs.dremio.com/)
- [Iceberg Documentation](https://iceberg.apache.org/)
- [JPype GitHub Repository](https://github.com/jpype-project/jpype)
- [Dremio REST API Documentation](https://docs.dremio.com/software/rest-api/)