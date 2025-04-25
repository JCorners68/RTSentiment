#!/bin/bash
set -e

# Define colors for better output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}Real-Time Sentiment Analysis Testing${NC}"
echo ""

function show_help {
    echo "Usage: ./run_tests.sh [OPTION]"
    echo ""
    echo "Options:"
    echo "  -m, --mock       Run mock-based tests only (default)"
    echo "  -i, --integration Run integration tests with docker compose"
    echo "  -a, --api        Run API endpoint tests"
    echo "  -u, --unit       Run unit tests for API"
    echo "  -e, --e2e        Run end-to-end tests"
    echo "  -f, --full       Run all tests including docker-based tests"
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
        -a|--api)
        TEST_TYPE="api"
        shift
        ;;
        -u|--unit)
        TEST_TYPE="unit"
        shift
        ;;
        -e|--e2e)
        TEST_TYPE="e2e"
        shift
        ;;
        -f|--full)
        TEST_TYPE="full"
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
        pip install pytest pytest-asyncio fastapi &&
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

# Run API endpoint tests
function run_api_tests {
    echo -e "${YELLOW}Running API endpoint tests...${NC}"
    echo ""
    
    # Check if the API tests script exists
    if [ -f "tests/run_api_tests.sh" ]; then
        bash tests/run_api_tests.sh
    else
        echo -e "${BLUE}Running direct API tests with pytest...${NC}"
        # Run in a local environment if script not found
        python -m venv venv
        . venv/bin/activate
        pip install -r tests/requirements.txt
        python -m pytest tests/test_sentiment_api.py -v
        deactivate
        rm -rf venv
    fi
}

# Run end-to-end tests
function run_e2e_tests {
    echo -e "${YELLOW}Running end-to-end tests...${NC}"
    echo ""
    
    # Check if the API is running
    if ! curl -s http://localhost:8001/health > /dev/null; then
        echo "API is not running. Starting services..."
        docker compose up -d
        sleep 5  # Give services time to start
    fi
    
    # Run the end-to-end tests
    python -m venv venv
    . venv/bin/activate
    pip install -r tests/requirements.txt
    python tests/end_to_end_test.py --api-host localhost --api-port 8001 --output-file tests/test_results/e2e_latest.json
    deactivate
    rm -rf venv
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
            pip install --no-cache-dir pytest pytest-asyncio fastapi sqlalchemy &&
            pip install -r tests/requirements.txt &&
            python -m pytest tests/test_sentiment_api.py -v &&
            rm -rf venv
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
    api)
    run_api_tests
    ;;
    unit)
    run_existing_tests
    ;;
    e2e)
    run_e2e_tests
    ;;
    full)
    run_mock_tests
    echo ""
    echo -e "${YELLOW}Mock tests completed. Running API tests...${NC}"
    echo ""
    run_api_tests
    echo ""
    echo -e "${YELLOW}API tests completed. Running integration tests...${NC}"
    echo ""
    run_integration_tests
    echo ""
    echo -e "${YELLOW}Integration tests completed. Running end-to-end tests...${NC}"
    echo ""
    run_e2e_tests
    ;;
esac

echo ""
echo -e "${GREEN}Testing completed!${NC}"
echo ""
if [ "$TEST_TYPE" = "mock" ]; then
    echo "Note: Only mock-based tests were run."
    echo "To run other tests, use one of these options:"
    echo "  ./run_tests.sh --api         : Run API endpoint tests"
    echo "  ./run_tests.sh --integration : Run integration tests with Docker Compose"
    echo "  ./run_tests.sh --e2e         : Run end-to-end tests"
    echo "  ./run_tests.sh --full        : Run all tests"
    echo "  docker compose up -d         : Start all services"
    echo "  docker compose exec api pytest : Run tests in the API container"
fi