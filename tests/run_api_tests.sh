#!/bin/bash
#
# Run API tests for the sentiment analysis service
#
# This script runs the unit tests for the sentiment API endpoints
# to validate that all endpoints are working correctly.

# Define colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print header
echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}   Sentiment API Endpoint Testing Script     ${NC}"
echo -e "${GREEN}==============================================${NC}"

# Check if Python and required packages are installed
echo -e "\n${BLUE}Checking Python environment...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    exit 1
fi

# Check for pytest
if ! python3 -c "import pytest" &> /dev/null; then
    echo -e "${YELLOW}Warning: pytest is not installed. Installing...${NC}"
    pip install -r requirements.txt
fi

# Check if the API is running (optional check)
echo -e "\n${BLUE}Checking if API is running for manual tests...${NC}"
API_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001 2>/dev/null || echo "000")

if [ "$API_CHECK" == "200" ] || [ "$API_CHECK" == "404" ]; then
    echo -e "${GREEN}API is reachable at http://localhost:8001!${NC}"
    echo -e "${YELLOW}Note: Unit tests will still run even if the API is not running.${NC}"
else
    echo -e "${YELLOW}Warning: API is not running at http://localhost:8001 (received status $API_CHECK)${NC}"
    echo -e "${YELLOW}Unit tests will still run, but you might want to start the API for manual testing:${NC}"
    echo -e "  docker compose up -d api"
fi

# Run API endpoint unit tests
echo -e "\n${BLUE}Running API endpoint tests...${NC}"
cd "$(dirname "$0")/.." # Go to project root
python -m pytest tests/test_sentiment_api.py -v

# Optional: Run the manual API test script if the API is running
if [ "$API_CHECK" == "200" ] || [ "$API_CHECK" == "404" ]; then
    echo -e "\n${BLUE}Running manual API tests with curl...${NC}"
    bash tests/test_api_endpoints.sh
fi

# Summary
echo -e "\n${GREEN}==============================================${NC}"
echo -e "${GREEN}   API Testing Complete                      ${NC}"
echo -e "${GREEN}==============================================${NC}"
echo -e "API tests completed. Verify that all tests have passed."
echo -e "If any tests failed, check the error messages and fix the issues."
echo -e "You can manually test the API endpoints with:"
echo -e "  bash tests/test_api_endpoints.sh"