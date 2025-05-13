#!/bin/bash

# Script to check for utility files that may have been mistakenly deployed
# This script should be run after site build to verify exclusion rules are working

set -e

BUILD_DIR="_site"
EXCLUDE_FILE=".deployment_exclude"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Checking for utility files that may have been deployed...${NC}"

if [ ! -d "../../$BUILD_DIR" ]; then
  echo -e "${RED}Error: Build directory '$BUILD_DIR' not found!${NC}"
  echo -e "${YELLOW}Please run 'bundle exec jekyll build' first.${NC}"
  exit 1
fi

if [ ! -f "$SCRIPT_DIR/$EXCLUDE_FILE" ]; then
  echo -e "${RED}Error: Exclusion file '$EXCLUDE_FILE' not found!${NC}"
  exit 1
fi

# Count total files in the build directory for stats
TOTAL_FILES=$(find "../../$BUILD_DIR" -type f | wc -l)
echo -e "${BLUE}Total files in build: $TOTAL_FILES${NC}"

# Initialize counters
EXCLUDED_FILES=0
UTILITY_FILES_FOUND=0

# Check each pattern in the exclude file
while IFS= read -r line || [[ -n "$line" ]]; do
  # Skip comments and empty lines
  if [[ "$line" =~ ^#.*$ ]] || [[ -z "$line" ]]; then
    continue
  fi
  
  # Find files matching the pattern
  MATCHING_FILES=$(find "../../$BUILD_DIR" -name "$line" -type f 2>/dev/null || echo "")
  
  if [ -n "$MATCHING_FILES" ]; then
    COUNT=$(echo "$MATCHING_FILES" | wc -l)
    UTILITY_FILES_FOUND=$((UTILITY_FILES_FOUND + COUNT))
    
    echo -e "${YELLOW}Found $COUNT files matching '$line':${NC}"
    echo "$MATCHING_FILES" | sed "s|../../$BUILD_DIR/||g" | sed 's/^/  /'
    
    # Display a warning for each file
    echo -e "${RED}WARNING: These utility files should not be deployed!${NC}"
  else
    echo -e "${GREEN}✓ No '$line' files found in build directory.${NC}"
    EXCLUDED_FILES=$((EXCLUDED_FILES + 1))
  fi
done < "$SCRIPT_DIR/$EXCLUDE_FILE"

# Summary
echo -e "\n${BLUE}=== Summary ===${NC}"
if [ $UTILITY_FILES_FOUND -eq 0 ]; then
  echo -e "${GREEN}✓ No utility files found in the build directory.${NC}"
  echo -e "${GREEN}✓ All $EXCLUDED_FILES exclusion patterns are being properly applied.${NC}"
else
  echo -e "${RED}× Found $UTILITY_FILES_FOUND utility files that should not be deployed!${NC}"
  echo -e "${YELLOW}Please ensure the deployment scripts are correctly filtering these files.${NC}"
  echo -e "${YELLOW}Specifically check the .deployment_exclude file and deploy scripts.${NC}"
fi

# Check for specific utilities in image directories
echo -e "\n${BLUE}=== Checking Image Directories ===${NC}"
IMAGE_DIRS=(
  "images"
  "images/case-studies"
  "images/icons"
)

for DIR in "${IMAGE_DIRS[@]}"; do
  UTILS_IN_DIR=$(find "../../$BUILD_DIR/assets/$DIR" -name "*.py" -o -name "*.sh" -o -name "*_requirements.json" 2>/dev/null || echo "")
  
  if [ -n "$UTILS_IN_DIR" ]; then
    COUNT=$(echo "$UTILS_IN_DIR" | wc -l)
    echo -e "${RED}Found $COUNT utility files in assets/$DIR:${NC}"
    echo "$UTILS_IN_DIR" | sed "s|../../$BUILD_DIR/||g" | sed 's/^/  /'
  else
    echo -e "${GREEN}✓ No utility files found in assets/$DIR${NC}"
  fi
done

if [ $UTILITY_FILES_FOUND -gt 0 ]; then
  exit 1
else
  echo -e "\n${GREEN}All checks passed! Your build directory is clean of utility files.${NC}"
  exit 0
fi