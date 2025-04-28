#!/bin/bash
# Setup script for the Iceberg lakehouse integration

# Enable error handling
set -e

echo "======================================================================"
echo "  ICEBERG LAKEHOUSE INTEGRATION SETUP"
echo "======================================================================"

# Create required directories
echo -e "\n1. Creating directories..."
mkdir -p data/iceberg_warehouse
mkdir -p iceberg_lake/dremio/data
echo "   ✓ Directories created"

# Create virtual environment
VENV_DIR="iceberg_venv"
echo -e "\n2. Setting up Python environment..."
if [ ! -d "$VENV_DIR" ]; then
    echo "   Creating virtual environment at $VENV_DIR"
    # Try to create virtual environment with python3 -m venv
    if command -v python3 &> /dev/null; then
        python3 -m venv "$VENV_DIR" || {
            echo "   ⚠️  Could not create venv with python3 -m venv"
            echo "   Trying with virtualenv..."
            # If venv fails, try virtualenv as a fallback
            if command -v virtualenv &> /dev/null; then
                virtualenv "$VENV_DIR"
            else
                echo "   ⚠️  Neither python3 -m venv nor virtualenv is available"
                echo "   Please install one of them and try again"
                exit 1
            fi
        }
    else
        echo "   ⚠️  python3 command not found"
        exit 1
    fi
else
    echo "   ✓ Virtual environment already exists at $VENV_DIR"
fi

# Activate virtual environment
echo "   Activating virtual environment..."
source "$VENV_DIR/bin/activate" || {
    echo "   ⚠️  Failed to activate virtual environment"
    exit 1
}

# Install minimal dependencies
echo -e "\n3. Installing minimal dependencies..."
pip install --upgrade pip || echo "   ⚠️  Failed to upgrade pip, continuing anyway"
pip install pyiceberg==0.9.0 boto3 requests || {
    echo "   ⚠️  Failed to install dependencies"
    exit 1
}
echo "   ✓ Dependencies installed"

# Test basic functionality
echo -e "\n4. Testing basic functionality..."
python test_iceberg_setup.py

# Provide usage instructions
echo -e "\n5. Next steps:"
echo "   a. Start Docker services: docker-compose -f docker-compose.iceberg.yml up -d"
echo "   b. Run example: source $VENV_DIR/bin/activate && python iceberg_example.py"
echo "   c. Access Dremio: http://localhost:9047 (dremio/dremio123)"
echo ""
echo "   Your virtual environment is at: $VENV_DIR"