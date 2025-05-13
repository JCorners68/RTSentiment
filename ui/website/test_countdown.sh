#!/bin/bash
# Script to test the countdown timer functionality

# Color codes for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Set the execution date for logging
EXEC_DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo -e "${BLUE}[$EXEC_DATE] Testing Kickstarter countdown timer...${NC}"

# Check if countdown.js exists
if [ -f "assets/js/countdown.js" ]; then
  echo -e "${GREEN}✓ countdown.js file exists${NC}"
  
  # Check if the countdown timer code is properly implemented
  if grep -q "document.addEventListener.*DOMContentLoaded" assets/js/countdown.js && \
     grep -q "const countdownDate" assets/js/countdown.js && \
     grep -q "setInterval.*updateCountdown" assets/js/countdown.js; then
    echo -e "${GREEN}✓ countdown.js contains required code structures${NC}"
  else
    echo -e "${RED}✗ countdown.js may be missing important code structures${NC}"
  fi
else
  echo -e "${RED}✗ countdown.js file not found${NC}"
fi

# Check if countdown.css exists
if [ -f "assets/css/countdown.css" ]; then
  echo -e "${GREEN}✓ countdown.css file exists${NC}"
  
  # Check if the CSS contains required styles
  if grep -q "countdown-item" assets/css/countdown.css && \
     grep -q "@keyframes" assets/css/countdown.css; then
    echo -e "${GREEN}✓ countdown.css contains required styles${NC}"
  else
    echo -e "${RED}✗ countdown.css may be missing important styles${NC}"
  fi
else
  echo -e "${RED}✗ countdown.css file not found${NC}"
fi

# Check if kickstarter page has countdown elements
if [ -f "pages/kickstarter/index.html" ]; then
  echo -e "${GREEN}✓ Kickstarter page exists${NC}"
  
  # Check for countdown HTML structure
  if grep -q "countdown-timer" pages/kickstarter/index.html && \
     grep -q "countdown-days" pages/kickstarter/index.html && \
     grep -q "countdown-hours" pages/kickstarter/index.html && \
     grep -q "countdown-minutes" pages/kickstarter/index.html && \
     grep -q "countdown-seconds" pages/kickstarter/index.html; then
    echo -e "${GREEN}✓ Kickstarter page contains countdown elements${NC}"
  else
    echo -e "${RED}✗ Kickstarter page is missing countdown elements${NC}"
  fi
  
  # Check for inline fallback script
  if grep -q "Inline fallback script" pages/kickstarter/index.html; then
    echo -e "${GREEN}✓ Kickstarter page contains fallback script${NC}"
  else
    echo -e "${RED}✗ Kickstarter page is missing fallback script${NC}"
  fi
else
  echo -e "${RED}✗ Kickstarter page not found${NC}"
fi

# Check for test page
if [ -f "test_countdown.html" ]; then
  echo -e "${GREEN}✓ Test page exists${NC}"
  echo -e "${YELLOW}You can open test_countdown.html in a browser to visually verify the timer${NC}"
else
  echo -e "${RED}✗ Test page not found${NC}"
fi

echo -e "${BLUE}[$EXEC_DATE] Test completed${NC}"
echo -e "${YELLOW}To run the website with suppressed warnings: ./serve_quiet.sh${NC}"
echo -e "${YELLOW}Then visit http://127.0.0.1:4000/kickstarter/ to verify the countdown timer${NC}"