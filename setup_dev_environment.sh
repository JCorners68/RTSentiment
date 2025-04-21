#!/bin/bash

# Setup script for the Real-Time Sentiment Analysis development environment

echo "Setting up the development environment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    echo "Visit https://docs.docker.com/get-docker/ for installation instructions."
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "Docker Compose is not available. Please install Docker Compose first."
    echo "Visit https://docs.docker.com/compose/install/ for installation instructions."
    exit 1
fi

# Make scripts executable
echo "Making scripts executable..."
chmod +x run_tests.sh
chmod +x run_e2e_tests.sh
chmod +x scripts/*.sh

# Install dependencies in virtual environment using a Docker container
echo "Installing Python dependencies in a Docker container..."
docker run --rm -v "$(pwd):/app" -w /app python:3.10-slim bash -c "
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    echo 'Python dependencies installed!'
"

# Create necessary Docker networks
echo "Creating Docker networks..."
docker network create sentiment-network 2>/dev/null || true

# Pull required Docker images
echo "Pulling required Docker images..."
docker compose pull

echo "====================================================="
echo "Development environment setup complete!"
echo "====================================================="
echo 
echo "To start the environment:"
echo "  docker compose up -d"
echo
echo "To run mock-based tests:"
echo "  ./run_tests.sh --mock"
echo
echo "To run end-to-end tests:"
echo "  ./run_e2e_tests.sh"
echo
echo "To explore the Kafka UI:"
echo "  http://localhost:8080"
echo
echo "To access the API:"
echo "  http://localhost:8001/docs"
echo "====================================================="