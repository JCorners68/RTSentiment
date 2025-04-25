#!/bin/bash
set -e

# Simple test script that runs one test file directly
# This is a lightweight alternative to the full docker-based testing

echo "Running minimal test directly..."

# Install pytest if needed
pip install pytest pytest-asyncio || pip3 install pytest pytest-asyncio || echo "Failed to install pytest, proceeding anyway"

# Run the test
python -m pytest tests/test_minimal.py -v || python3 -m pytest tests/test_minimal.py -v