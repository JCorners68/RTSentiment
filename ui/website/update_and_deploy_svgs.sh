#!/bin/bash

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Copying fixed SVG files to _site directory...${NC}"

# Create _site/assets/images/case-studies if it doesn't exist
mkdir -p _site/assets/images/case-studies

# Copy the fixed SVG files
cp assets/images/case-studies/supply_chain_case.svg _site/assets/images/case-studies/
cp assets/images/case-studies/case_study_overview.svg _site/assets/images/case-studies/
cp assets/images/case-studies/healthcare_case.svg _site/assets/images/case-studies/

echo -e "${GREEN}SVG files copied successfully${NC}"
echo -e "${YELLOW}Starting deployment...${NC}"

# Deploy only the fixed SVG files
ftp_files=(
  "assets/images/case-studies/supply_chain_case.svg"
  "assets/images/case-studies/case_study_overview.svg"
  "assets/images/case-studies/healthcare_case.svg"
)

# Convert array to string with spaces
ftp_files_str="${ftp_files[@]}"

# Deploy the files
./deploy_incremental.sh ${ftp_files_str}

echo -e "${GREEN}Deployment completed!${NC}"