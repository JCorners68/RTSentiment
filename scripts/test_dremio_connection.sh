#!/bin/bash

# Test script for Dremio connection
# This script sets up the environment and runs the Dremio query service test

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

# Run the test script
echo "Running Dremio connection test..."
python ./iceberg_lake/query/test_dremio_query_service.py "$@"

# Display success message
echo
echo "Test complete! If successful, you can run the API with:"
echo "source ./drivers/config/setenv.sh && python ./iceberg_lake/api/run_api.py"