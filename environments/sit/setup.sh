#!/bin/bash

# RT Sentiment Analysis - SIT Environment Setup Script
# This script sets up the System Integration Testing (SIT) environment in WSL.

# Display a message at the start
echo "Setting up RT Sentiment Analysis SIT environment..."

# Create the necessary directories if they don't exist
mkdir -p config
mkdir -p tests
mkdir -p logs

# Ensure the latest version of pip
python -m pip install --upgrade pip

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Navigate to the infrastructure directory to build and start the services
cd ../../infrastructure

# Build the services
echo "Building services..."
docker-compose build

# Start the services
echo "Starting services..."
docker-compose up -d

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 10

# Verify service health
echo "Verifying service health..."
docker-compose ps

# Run tests to verify setup
echo "Running environment verification tests..."
cd ../environments/sit/tests
pytest -xvs

# Display success message
echo "SIT environment setup complete."
echo "Data Acquisition Service is available at: http://localhost:8002"
echo "Use 'docker-compose down' in the infrastructure directory to stop the services."