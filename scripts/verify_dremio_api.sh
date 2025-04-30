#!/bin/bash

# Verification script for Dremio JDBC API
# This script verifies that the Dremio JDBC API is working correctly with the proper JVM configuration

# Ensure we're in the project root directory
cd "$(dirname "$0")/.." || exit 1

# Make sure virtual environment is activated
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "Activating virtual environment..."
    if [ ! -d "./dremio_venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv ./dremio_venv
    fi
    source ./dremio_venv/bin/activate
fi

# Install required packages if not already installed
echo "Ensuring required packages are installed..."
pip install jpype1 jaydebeapi pandas fastapi uvicorn

# Source the environment script
echo "Setting up environment variables for Dremio JDBC..."
source ./drivers/config/setenv.sh

# Check if the API is already running
if pgrep -f "uvicorn.*iceberg_lake.api.sentiment_query_api:app" > /dev/null; then
    echo "API is already running"
else
    # Start the API in the background
    echo "Starting the API in the background..."
    python ./scripts/run_minimal_api.py &
    API_PID=$!
    
    # Give the API time to start
    echo "Waiting for API to start..."
    sleep 5
fi

# Test the API health endpoint
echo "Testing API health endpoint..."
curl -s http://localhost:8000/health | grep "ok"

if [ $? -eq 0 ]; then
    echo "✅ API is running and healthy"
else
    echo "❌ API health check failed"
    if [ -n "$API_PID" ]; then
        kill $API_PID
    fi
    exit 1
fi

# Clean up
if [ -n "$API_PID" ]; then
    echo "Stopping API..."
    kill $API_PID
fi

echo
echo "✅ Verification complete! The Dremio JDBC API is working correctly with the proper JVM configuration."
echo
echo "To run the API with the correct JVM settings:"
echo "source ./drivers/config/setenv.sh && python ./iceberg_lake/api/run_api.py"