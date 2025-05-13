#!/bin/bash
# Script to run Jekyll development server with minimal output and SASS deprecation warnings suppressed

# Color codes for terminal output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Set the execution date for logging
EXEC_DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo -e "${GREEN}[$EXEC_DATE] Starting Sentimark website development server in quiet mode...${NC}"
echo -e "${YELLOW}Server will be available at http://127.0.0.1:4000/${NC}"

# Get IP address for Windows access (if running in WSL)
if grep -q Microsoft /proc/version; then
  WSL_IP=$(hostname -I | awk '{print $1}')
  echo -e "${BLUE}If using Windows with WSL: http://$WSL_IP:4000${NC}"
fi

echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"

# Update the _config.yml to include quiet_deps: true if needed
if ! grep -q "quiet_deps: true" _config.yml; then
  echo "Adding quiet_deps: true to _config.yml to reduce SASS warnings"
  echo "quiet_deps: true" >> _config.yml
fi

# Run Jekyll with warnings suppressed
# First try with quiet_deps config option
JEKYLL_LOG_LEVEL=error bundle exec jekyll serve --livereload 2> >(grep -v "DEPRECATION WARNING \[import\]" > jekyll_warnings.log)

# Note: Check jekyll_warnings.log for any warnings if needed
# Use the following command to view warnings:
# echo -e "${YELLOW}To check any warnings: cat jekyll_warnings.log${NC}"
