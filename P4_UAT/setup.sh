#!/bin/bash
# UAT Setup Script for Phase 4 Testing

set -e  # Exit on any error

echo "========================================="
echo "Setting up Phase 4 UAT Environment"
echo "========================================="

# Check prerequisites
echo "Checking prerequisites..."
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required but not installed. Aborting."; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting."; exit 1; }
command -v java >/dev/null 2>&1 || { echo "Java is required but not installed. Aborting."; exit 1; }

# Create and activate virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Install project package
echo "Installing project package..."
pip install -e ..

# Set up JDBC driver
echo "Setting up JDBC driver..."
../scripts/setup_dremio_jdbc.sh

# Copy config file
echo "Setting up configuration..."
cp ../tests/data_tests/azure_migration/config_local.json ./config.json

echo "Creating directories for test results..."
mkdir -p test_results

echo "========================================="
echo "UAT Environment Setup Complete!"
echo "========================================="
echo ""
echo "To activate the environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To start testing, run:"
echo "  python ../tests/data_tests/azure_migration/run_all_tests.py --local --config ./config.json"
echo ""
echo "See LOCAL_UAT_INSTRUCTIONS.md for detailed testing instructions."