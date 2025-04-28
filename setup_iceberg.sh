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

# Check for Python virtual environment
VENV_DIR="iceberg_venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    
    # Check if python3-venv is installed
    if ! python3 -m venv --help > /dev/null 2>&1; then
        echo "Installing python3-venv..."
        sudo apt-get update && sudo apt-get install -y python3-venv python3-full
    fi
    
    # Create virtual environment
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r iceberg_lake/requirements.txt

# Start Iceberg services
echo "Starting Iceberg services..."
docker-compose -f docker-compose.iceberg.yml up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Test setup (skipping for initial setup)
echo "Testing Iceberg schema configuration..."
python -m unittest discover -s tests -p "test_iceberg_integration.py" -k "TestIcebergSchema"

# Provide instructions for running full tests later
echo "Note: Full integration tests are skipped during initial setup."
echo "      To run them after services are fully running, use:"
echo "      source $VENV_DIR/bin/activate && python -m unittest tests/test_iceberg_integration.py"

echo "Iceberg lakehouse integration setup complete!"
echo ""
echo "Available services:"
echo "  - MinIO: http://localhost:9000 (console: http://localhost:9001)"
echo "  - Iceberg REST Catalog: http://localhost:8181"
echo "  - Dremio: http://localhost:9047"
echo ""
echo "Next steps:"
echo "  1. Run the example script in the virtual environment:"
echo "     source $VENV_DIR/bin/activate && python iceberg_example.py"
echo ""
echo "  2. Access Dremio at http://localhost:9047"
echo "     Username: dremio"
echo "     Password: dremio123"
echo ""
echo "  3. When you're done, deactivate the virtual environment:"
echo "     deactivate"
echo ""
echo "Your virtual environment is at: $VENV_DIR"