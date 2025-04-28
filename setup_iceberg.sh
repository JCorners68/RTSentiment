#!/bin/bash
# Setup script for the Iceberg lakehouse integration

set -e

# Check if docker and docker-compose are installed
if ! command -v docker &> /dev/null; then
    echo "Error: docker is not installed"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Error: docker-compose is not installed"
    exit 1
fi

# Create required directories
mkdir -p data/iceberg_warehouse
mkdir -p iceberg_lake/dremio/data

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt
pip install pyiceberg==1.4.0 boto3>=1.28.0 requests>=2.31.0

# Start Iceberg services
echo "Starting Iceberg services..."
docker-compose -f docker-compose.iceberg.yml up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Test setup
echo "Testing Iceberg integration..."
python -m unittest tests/test_iceberg_integration.py

echo "Iceberg lakehouse integration setup complete!"
echo ""
echo "Available services:"
echo "  - MinIO: http://localhost:9000 (console: http://localhost:9001)"
echo "  - Iceberg REST Catalog: http://localhost:8181"
echo "  - Dremio: http://localhost:9047"
echo ""
echo "Next steps:"
echo "  1. Run the integration tests to verify functionality"
echo "  2. Configure connection details in your environment"
echo "  3. Start using the Iceberg lakehouse for sentiment data!"