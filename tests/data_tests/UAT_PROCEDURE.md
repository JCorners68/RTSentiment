# User Acceptance Testing (UAT) Procedure for RTSentiment Data Tier

This document provides clear, step-by-step instructions for performing User Acceptance Testing on the RTSentiment data tier implementation with Dremio, JDBC, and Iceberg.

## 1. PREREQUISITES

Before starting, ensure you have:

- Linux/WSL environment (Ubuntu recommended)
- Python 3.8+ installed
- Docker and Docker Desktop installed with WSL integration enabled
- Git installed
- 8GB+ RAM available
- Java JDK 11+ installed

## 2. SETUP PROCEDURE

### Step 1: Clone Repository

```bash
# Create a working directory and clone the repository
mkdir -p ~/sentiment_test
cd ~/sentiment_test
git clone -b adv_data_tier https://github.com/JCorners68/RTSentiment.git
```

### Step 2: Set Up Python Environment

```bash
# Create and activate virtual environment
cd ~/sentiment_test
python3 -m venv dremio_venv
source dremio_venv/bin/activate

# Install required packages
pip install -r RTSentiment/requirements.txt
pip install pyiceberg jaydebeapi tabulate JPype1
```

### Step 3: Set Up Dremio JDBC Driver

```bash
# Create drivers directory and copy JDBC driver
mkdir -p ~/sentiment_test/drivers
cp ~/sentiment_test/RTSentiment/drivers/dremio-jdbc-driver.jar ~/sentiment_test/drivers/
ln -sf ~/sentiment_test/drivers/dremio-jdbc-driver.jar ~/sentiment_test/dremio-jdbc-driver.jar
```

### Step 4: Configure Environment Variables

```bash
# Create the environment configuration script
cat > ~/sentiment_test/setup_dremio_env.sh << 'EOL'
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
EOL

# Make the script executable
chmod +x ~/sentiment_test/setup_dremio_env.sh
```

### Step 5: Start Dremio Container

```bash
# Start the Dremio Docker container
cd ~/sentiment_test/RTSentiment
./start_dremio_test_container.sh
```

### Step 6: Create Python Module Fix Script

```bash
# Create a wrapper script to fix Python module imports
cat > ~/sentiment_test/verify_dremio_queries.sh << 'EOL'
#!/bin/bash
# Script to run the Dremio Query Verification with the proper environment setup

echo "===== Dremio Query Verification Setup ====="

# Activate the Python virtual environment
if [ -f "/home/jonat/sentiment_test/dremio_venv/bin/activate" ]; then
    source /home/jonat/sentiment_test/dremio_venv/bin/activate
    echo "✅ Activated Python virtual environment"
else
    echo "⚠️ Virtual environment not found at /home/jonat/sentiment_test/dremio_venv"
    exit 1
fi

# Load Dremio environment variables
if [ -f "/home/jonat/sentiment_test/setup_dremio_env.sh" ]; then
    source /home/jonat/sentiment_test/setup_dremio_env.sh
    echo "✅ Loaded Dremio environment variables"
else
    echo "⚠️ Dremio environment setup script not found"
    exit 1
fi

# Set PYTHONPATH to include the project root
export PYTHONPATH="/home/jonat/sentiment_test/RTSentiment:${PYTHONPATH}"
echo "✅ Set PYTHONPATH to include RTSentiment directory"

# Change to the project directory
cd /home/jonat/sentiment_test/RTSentiment
echo "✅ Changed to RTSentiment directory"

# Parse arguments
TICKER="AAPL"
while [[ $# -gt 0 ]]; do
    case $1 in
        --ticker)
            TICKER="$2"
            shift 2
            ;;
        *)
            # Skip unknown arguments
            shift
            ;;
    esac
done

echo "===== Running verification for ticker: ${TICKER} ====="
echo

# Run the verification script
python -c "
import sys
import os

# Ensure we can import from iceberg_lake
print(f'Current directory: {os.getcwd()}')
print(f'Python path: {sys.path}')

try:
    # Try to import the module
    from iceberg_lake.query.verify_query_service import main
    print('✅ Successfully imported verification module')
    
    # Run the verification
    sys.argv = ['verify_query_service.py', '--ticker', '${TICKER}']
    sys.exit(main())
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo
    echo "===== Verification completed successfully ====="
else
    echo
    echo "===== Verification failed with code: ${EXIT_CODE} ====="
fi

exit $EXIT_CODE
EOL

# Make the script executable
chmod +x ~/sentiment_test/verify_dremio_queries.sh
```

## 3. TESTING PROCEDURE

### Step 1: Verify Dremio Container

```bash
# Check that Dremio container is running
docker ps | grep dremio

# Verify Dremio web interface is accessible
curl http://localhost:9047

# Expected Result: 
# - You should see Dremio container listed in docker ps output
# - curl command should return HTML content (Dremio login page)
```

### Step 2: Verify Dremio REST API Connection

```bash
# Create a REST API test script
cat > ~/sentiment_test/test_dremio_rest.py << 'EOL'
#!/usr/bin/env python3
"""
Test script to verify the Dremio connection using REST API instead of JDBC.
"""
import os
import sys
import requests
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get configuration from environment or use defaults
dremio_endpoint = os.environ.get('DREMIO_ENDPOINT', 'http://localhost:9047')
dremio_username = os.environ.get('DREMIO_USERNAME', 'dremio')
dremio_password = os.environ.get('DREMIO_PASSWORD', 'dremio123')

# Ensure endpoint has proper format
if not dremio_endpoint.startswith('http'):
    dremio_endpoint = f'http://{dremio_endpoint}'

# Strip trailing slash if present
dremio_endpoint = dremio_endpoint.rstrip('/')

# Authentication endpoint
auth_endpoint = f"{dremio_endpoint}/apiv2/login"

logger.info(f"Testing Dremio connection to: {dremio_endpoint}")
logger.info(f"Using credentials: {dremio_username}/******")

try:
    # First check if Dremio is reachable
    try:
        response = requests.get(f"{dremio_endpoint}/", timeout=5)
        logger.info(f"Dremio UI is reachable: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to reach Dremio UI: {str(e)}")
        sys.exit(1)
    
    # Authenticate to get token
    auth_payload = {
        "userName": dremio_username,
        "password": dremio_password
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    response = requests.post(auth_endpoint, 
                            headers=headers, 
                            data=json.dumps(auth_payload))
    
    if response.status_code == 200:
        auth_token = response.json().get('token')
        logger.info(f"✅ Successfully authenticated to Dremio: {response.status_code}")
        
        # Test a simple catalog query
        catalog_endpoint = f"{dremio_endpoint}/api/v3/catalog"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'_dremio{auth_token}'
        }
        
        response = requests.get(catalog_endpoint, headers=headers)
        
        if response.status_code == 200:
            catalog_data = response.json()
            logger.info(f"✅ Successfully retrieved catalog: {response.status_code}")
            
            # Print catalog entries
            for entry in catalog_data.get('data', []):
                logger.info(f"Catalog entry: {entry.get('name')} ({entry.get('type')})")
            
            logger.info("✅ Dremio connection test PASSED")
            sys.exit(0)
        else:
            logger.error(f"Failed to retrieve catalog: {response.status_code}")
            logger.error(f"Response: {response.text}")
            sys.exit(1)
            
    else:
        logger.error(f"Authentication failed: {response.status_code}")
        logger.error(f"Response: {response.text}")
        sys.exit(1)
        
except Exception as e:
    logger.error(f"Connection test failed with error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
EOL

# Make the script executable
chmod +x ~/sentiment_test/test_dremio_rest.py

# Run the REST API test
cd ~/sentiment_test && source ./setup_dremio_env.sh --activate && python test_dremio_rest.py

# Expected Result:
# - Multiple "✅" success messages
# - "✅ Dremio connection test PASSED" as the final message
```

### Step 3: Verify Query Service

```bash
# Run the query verification script
cd ~/sentiment_test && ./verify_dremio_queries.sh --ticker AAPL

# Expected Result:
# - Multiple tests showing "PASS" status
# - Results displayed for different query types
# - Verification completed successfully message
```

## 4. VERIFICATION CHECKLIST

- [ ] Step 1: Repository Cloning
  - [ ] Repository successfully cloned with adv_data_tier branch

- [ ] Step 2: Python Environment Setup
  - [ ] Virtual environment created
  - [ ] All required packages installed without errors

- [ ] Step 3: Dremio JDBC Driver Setup
  - [ ] Driver JAR file correctly copied
  - [ ] Symbolic link created

- [ ] Step 4: Environment Configuration
  - [ ] setup_dremio_env.sh script created
  - [ ] Script runs without errors
  - [ ] Environment variables correctly set

- [ ] Step 5: Dremio Container
  - [ ] Container started successfully
  - [ ] Web interface accessible at http://localhost:9047
  - [ ] Default credentials work (dremio/dremio123)

- [ ] Step 6: Connection Verification
  - [ ] REST API test passes successfully
  - [ ] Catalog entries displayed

- [ ] Step 7: Query Service Verification
  - [ ] Query verification script runs without module errors
  - [ ] All query tests pass
  - [ ] Data displayed for each query type

## 5. COMMON ISSUES AND SOLUTIONS

### Python Import Issues

**Problem**: `ModuleNotFoundError: No module named 'iceberg_lake'`

**Solution**:
- Use the provided `verify_dremio_queries.sh` script which correctly sets PYTHONPATH
- Or manually set PYTHONPATH:
  ```bash
  export PYTHONPATH=~/sentiment_test/RTSentiment:$PYTHONPATH
  ```

### JDBC Connection Issues

**Problem**: Java library errors or "Can't find org.jpype.jar support library"

**Solution**:
- Ensure JDK is properly installed: `java -version`
- Verify CLASSPATH includes the JDBC driver
- Test with REST API first to confirm Dremio connectivity
- Try different JPype versions: `pip install JPype1==1.4.0`

### Docker Integration with WSL

**Problem**: Docker command not found or Docker not starting

**Solution**:
- Ensure Docker Desktop has WSL integration enabled
- Restart Docker Desktop
- In Docker Desktop settings, check "Resources > WSL Integration" 
- Enable integration with your WSL distro

### Dremio Not Accessible

**Problem**: Cannot connect to Dremio UI or API endpoints

**Solution**:
- Check if container is running: `docker ps | grep dremio`
- Check container logs: `docker logs dremio`
- Restart the container: `docker restart dremio`
- Verify ports are not blocked: `curl http://localhost:9047`

## 6. NEXT STEPS

After successful UAT verification:

1. Document any issues or observations in "LESSONS_LEARNED.md"
2. Proceed with data migration from Parquet to Iceberg (if required)
3. Performance testing with larger datasets
4. Deployment planning for production environment

## 7. SUPPORT RESOURCES

If you encounter persistent issues:

1. Check the [CONFIGURATION_DETAILS.md](CONFIGURATION_DETAILS.md) document
2. Review [LESSONS_LEARNED.md](LESSONS_LEARNED.md) for common challenges
3. Visit the Dremio documentation at https://docs.dremio.com/
4. Contact the development team via the project's issue tracker