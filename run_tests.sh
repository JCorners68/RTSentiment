#!/bin/bash
set -e

# Define colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Real-Time Sentiment Analysis Testing${NC}"
echo ""

function show_help {
    echo "Usage: ./run_tests.sh [OPTION]"
    echo ""
    echo "Options:"
    echo "  -m, --mock       Run mock-based tests only (default)"
    echo "  -i, --integration Run integration tests with docker compose"
    echo "  -u, --unit       Run unit tests for API"
    echo "  -a, --all        Run all tests including docker-based tests"
    echo "  -h, --help       Show this help message"
    echo ""
    exit 0
}

# Default to mock tests
TEST_TYPE="mock"

# Parse arguments
for arg in "$@"
do
    case $arg in
        -m|--mock)
        TEST_TYPE="mock"
        shift
        ;;
        -i|--integration)
        TEST_TYPE="integration"
        shift
        ;;
        -u|--unit)
        TEST_TYPE="unit"
        shift
        ;;
        -a|--all)
        TEST_TYPE="all"
        shift
        ;;
        -h|--help)
        show_help
        shift
        ;;
        *)
        # Unknown option
        echo "Unknown option: $arg"
        show_help
        ;;
    esac
done

# Run mock-based tests
function run_mock_tests {
    echo -e "${YELLOW}Running mock-based tests in a Docker container...${NC}"
    echo ""
    
    # Run all mock-based tests in a single command with a virtual environment
    docker run --rm -v "$(pwd):/app" -w /app python:3.10-slim bash -c "
        python -m venv venv &&
        . venv/bin/activate &&
        pip install --upgrade pip &&
        pip install pytest pytest-asyncio &&
        python -m pytest tests/test_minimal.py tests/test_mock_sentiment_service.py tests/test_integration.py -v &&
        rm -rf venv
    "
}

# Run integration tests
function run_integration_tests {
    echo -e "${YELLOW}Running integration tests with Docker Compose...${NC}"
    echo ""
    
    # Check if docker-compose.test.yml exists
    if [ ! -f "docker-compose.test.yml" ]; then
        echo "Error: docker-compose.test.yml not found"
        exit 1
    fi
    
    # Run the test environment
    docker compose -f docker-compose.test.yml up --build --abort-on-container-exit
}

# Run existing containers tests
function run_existing_tests {
    echo -e "${YELLOW}Running tests on existing containers...${NC}"
    echo ""
    
    if ! docker compose ps api | grep -q "Up"; then
        echo "API container not running, creating isolated test environment..."
        # Start only necessary services
        docker compose up -d postgres redis
        
        # Run tests in an isolated container
        docker run --rm --network wsl_rt_sentiment_default \
            -v "$(pwd):/app" -w /app python:3.10-slim bash -c "
            python -m venv venv && 
            . venv/bin/activate && 
            pip install --no-cache-dir pytest pytest-asyncio && 
            cd api && 
            python -m pytest tests/ -v &&
            rm -rf ../venv
        "
        
        # Cleanup
        docker compose down postgres redis
    else
        # Run tests in the API container
        docker compose exec api pytest
    fi
}

# Run the appropriate tests
case $TEST_TYPE in
    mock)
    run_mock_tests
    ;;
    integration)
    run_integration_tests
    ;;
    unit)
    run_existing_tests
    ;;
    all)
    run_mock_tests
    echo ""
    echo -e "${YELLOW}Mock tests completed. Running integration tests...${NC}"
    echo ""
    run_integration_tests
    ;;
esac

echo ""
echo -e "${GREEN}Testing completed!${NC}"
echo ""
if [ "$TEST_TYPE" = "mock" ]; then
    echo "Note: Only mock-based tests were run."
    echo "To run integration tests, use one of these options:"
    echo "  ./run_tests.sh --integration    : Run integration tests with Docker Compose"
    echo "  docker compose up -d            : Start all services"
    echo "  docker compose exec api pytest  : Run tests in the API container"
fi