#!/bin/bash
# Script to build and serve the Jekyll site locally with verbose output
# Shows full output including all SASS warnings and processing details

# Function for logging
log() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1"
}

# Color codes for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log "${GREEN}Setting up local development server for Sentimark website (VERBOSE MODE)${NC}"

# Install dependencies if needed
if [ ! -f "Gemfile.lock" ]; then
  log "${YELLOW}Installing dependencies...${NC}"
  bundle install
fi

# Get WSL IP address for access from Windows
WSL_IP=$(ip addr show eth0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
if [ -z "$WSL_IP" ]; then
  # Try alternative interfaces if eth0 is not found
  WSL_IP=$(hostname -I | awk '{print $1}')
fi

log "${GREEN}Starting Jekyll server with livereload and VERBOSE output...${NC}"
log "${BLUE}Once running, you can access the site at:${NC}"
log "${YELLOW}- From WSL: http://localhost:4000${NC}"
if [ -n "$WSL_IP" ]; then
  log "${YELLOW}- From Windows: http://$WSL_IP:4000${NC}"
fi

log "${BLUE}Full SASS processing and debug information will be displayed${NC}"
log "${YELLOW}Press Ctrl+C to stop the server${NC}"

# Start Jekyll server with livereload enabled and verbose output
bundle exec jekyll serve --livereload --host=0.0.0.0 --trace --verbose