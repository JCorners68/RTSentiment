#!/bin/bash

# End-to-end test runner for Real-Time Sentiment Analysis

# Parse command line arguments
SKIP_ENVIRONMENT_CHECK=false
TEST_FILE=""

print_usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --skip-env-check    Skip environment check (use when environment is already running)"
    echo "  --file <path>       Run a specific test file"
    echo "  --help              Display this help message"
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-env-check)
            SKIP_ENVIRONMENT_CHECK=true
            shift
            ;;
        --file)
            TEST_FILE="$2"
            shift 2
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed or not in the PATH"
    exit 1
fi

# Check if Docker Compose is available
if ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose is not available"
    exit 1
fi

# Check if the environment is running
if [ "$SKIP_ENVIRONMENT_CHECK" = false ]; then
    echo "Checking if Docker Compose environment is running..."
    
    if ! docker compose ps | grep -q "Up"; then
        echo "Docker Compose environment is not running."
        echo "Starting the environment..."
        docker compose up -d
        
        # Wait for services to be ready
        echo "Waiting for services to be ready..."
        sleep 15
    else
        echo "Docker Compose environment is already running."
    fi
    
    # Ensure Kafka is running
    if ! docker compose ps kafka | grep -q "Up"; then
        echo "Error: Kafka container is not running"
        echo "Please start the environment with: docker-compose up -d"
        exit 1
    fi
fi

echo "==============================================="
echo "Running end-to-end tests for scrapers"
echo "==============================================="

echo "Installing dependencies in a virtual environment..."
# Create a temporary Python container with the required dependencies
docker run --rm --network host -v "$(pwd):/app" -w /app python:3.10-slim bash -c "
    python -m venv venv &&
    . venv/bin/activate &&
    pip install --upgrade pip &&
    pip install pytest pytest-asyncio pytest-mock aiohttp aiokafka &&
    
    # Run the tests
    if [ -z \"$TEST_FILE\" ]; then
        echo 'Running all end-to-end tests...'
        python -m pytest data_acquisition/tests/test_e2e_scrapers.py -v
    else
        echo 'Running specified test file: $TEST_FILE'
        python -m pytest $TEST_FILE -v
    fi &&
    
    # Remove the virtual environment
    deactivate &&
    rm -rf venv
"

# Check if tests succeeded
TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ End-to-end tests completed successfully!"
else
    echo "❌ End-to-end tests failed!"
fi

# Ask if user wants to shut down the environment
if [ "$SKIP_ENVIRONMENT_CHECK" = false ]; then
    read -p "Do you want to shut down the Docker Compose environment? (y/n): " SHUTDOWN
    if [[ $SHUTDOWN =~ ^[Yy]$ ]]; then
        echo "Shutting down Docker Compose environment..."
        docker compose down
    fi
fi

exit $TEST_RESULT