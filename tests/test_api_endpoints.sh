#!/bin/bash
#
# test_api_endpoints.sh
# 
# This script tests various endpoints of the Senti Hub backend API.
# It sends curl requests to verify the JSON responses from the API running on localhost:8001.
# Use this script to validate that your Flutter app's fromJson methods match the actual API responses.
#
# Usage:
#   1. Make sure the API is running on http://localhost:8001
#   2. Run this script: ./test_api_endpoints.sh
#

# Define colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# The API should be running on port 8001 according to docker-compose.yml
# We'll just test this URL and show a clear error if it's not available
BASE_URL="http://localhost:8001"

# Check if the API is running
echo -e "${BLUE}Checking if API is running at $BASE_URL...${NC}"
API_CHECK=$(curl -s -o /dev/null -w "%{http_code}" $BASE_URL 2>/dev/null || echo "000")

if [ "$API_CHECK" == "200" ] || [ "$API_CHECK" == "404" ]; then
  echo -e "${GREEN}API is reachable at $BASE_URL!${NC}"
else
  echo -e "${RED}Error: API is not running at $BASE_URL (received status $API_CHECK)${NC}"
  echo -e "${YELLOW}Please start your API service with:${NC}"
  echo -e "  docker compose up -d api"
  echo -e "${YELLOW}Then run this script again.${NC}"
  
  # Show container status
  echo -e "\n${BLUE}Current container status:${NC}"
  docker compose ps api
  exit 1
fi

# Print header
echo -e "${GREEN}==============================================${NC}"
echo -e "${GREEN}   Senti Hub API Endpoint Testing Script     ${NC}"
echo -e "${GREEN}==============================================${NC}"
echo -e "This script will test various endpoints of the Senti Hub API.\n"

# Set login details for development environment
USERNAME="demo_user"
PASSWORD="password"
JWT_TOKEN="demo_token"

# =============================
# Test login endpoint
# =============================
echo -e "\n${BLUE}--- Testing POST /auth/login ---${NC}"
echo -e "This will attempt to log in with development credentials."

LOGIN_RESPONSE=$(curl -v -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" 2>&1)

echo -e "\nFull response (including headers):\n$LOGIN_RESPONSE\n"

# Set token automatically for development
echo -e "${YELLOW}Using development token: $JWT_TOKEN${NC}\n"

# Function to test an endpoint and display results
test_endpoint() {
  local endpoint=$1
  local description=$2
  local method=${3:-GET}
  local data=$4
  local headers=$5

  echo -e "\n${BLUE}--- Testing $method $endpoint ($description) ---${NC}"
  
  # Build curl command
  CURL_CMD="curl -v -X $method \"$BASE_URL$endpoint\" -H \"Authorization: Bearer $JWT_TOKEN\""
  
  # Add content type header if needed
  if [ -n "$data" ]; then
    CURL_CMD="$CURL_CMD -H \"Content-Type: application/json\""
  fi
  
  # Add additional headers if provided
  if [ -n "$headers" ]; then
    CURL_CMD="$CURL_CMD $headers"
  fi
  
  # Add data if provided
  if [ -n "$data" ]; then
    CURL_CMD="$CURL_CMD -d '$data'"
  fi
  
  # Execute the command and capture both response and headers
  echo -e "Executing: $CURL_CMD\n"
  RESPONSE=$(eval $CURL_CMD 2>&1)
  
  echo -e "Response (including headers):\n$RESPONSE\n"
  
  # Extract HTTP status code from response
  STATUS_CODE=$(echo "$RESPONSE" | grep -oP 'HTTP/1.1 \K[0-9]+' | head -1)
  
  # Extract JSON body more reliably - look for content between { } or [ ]
  BODY=$(echo "$RESPONSE" | grep -v ">" | grep -v "<" | grep -A 100 -E "(\{|\[)" | grep -v "Connection #0" | grep -v "* " | tr -d '\n')
  
  if [[ "$STATUS_CODE" == "200" && "$BODY" == *"{"* || "$BODY" == *"["* ]]; then
    echo -e "${GREEN}Success! Status: $STATUS_CODE${NC}"
    echo -e "Response body (formatted):"
    echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
  elif [[ "$STATUS_CODE" == "4"* || "$STATUS_CODE" == "5"* ]]; then
    echo -e "${RED}Error: Status $STATUS_CODE${NC}"
    if [[ "$BODY" == *"{"* || "$BODY" == *"["* ]]; then
      echo -e "Error details:"
      echo "$BODY" | jq . 2>/dev/null || echo "$BODY"
    else
      echo -e "No JSON error details available"
    fi
  else
    echo -e "${YELLOW}No valid JSON body detected in the response. Status: $STATUS_CODE${NC}"
  fi
  
  echo -e "${GREEN}Test completed.${NC}"
}

# Test endpoints
test_endpoint "/sentiment/top?limit=2&order=desc" "Top Positive Sentiments"
test_endpoint "/sentiment/top?limit=2&order=asc&maxScore=0" "Top Negative Sentiments"
test_endpoint "/sentiment/query" "Recent Events" "POST" '{"limit": 2}'
test_endpoint "/sentiment/stats" "System Statistics"
test_endpoint "/sentiment/ticker/AAPL" "Ticker Sentiment for AAPL"
test_endpoint "/sentiment/metadata" "API Metadata"
test_endpoint "/sentiment/tickers" "Available Tickers"

# =============================
# Summary
# =============================
echo -e "\n${GREEN}==============================================${NC}"
echo -e "${GREEN}   API Testing Complete                      ${NC}"
echo -e "${GREEN}==============================================${NC}"
echo -e "Use these responses to verify your Flutter app's fromJson methods match the API responses."
echo -e "Check for any discrepancies between expected and actual JSON structures."
echo -e "\nIf you don't see valid JSON in the responses, there might be issues with the API."
echo -e "Look at the complete response output including status codes to diagnose any problems."