#!/bin/bash
# Script to run minimal debug version of the Flutter app

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

LOGFILE="flutter_minimal_debug.log"
PORT=8181
DEBUG_INDEX="web_minimal/debug_index.html"

echo -e "${YELLOW}Starting Minimal Debug Flutter Dashboard${NC}"
echo -e "${YELLOW}Logs will be saved to ${LOGFILE}${NC}"

# Clear existing log
> $LOGFILE

echo "=== MINIMAL DEBUG SESSION STARTED $(date) ===" | tee -a $LOGFILE

# Check if debug index exists
if [ ! -f "$DEBUG_INDEX" ]; then
  echo -e "${RED}Error: Debug index file not found at $DEBUG_INDEX${NC}" | tee -a $LOGFILE
  exit 1
fi

# Get dependencies
echo -e "${YELLOW}Getting dependencies...${NC}" | tee -a $LOGFILE
flutter pub get 2>&1 | tee -a $LOGFILE

# Check Flutter web support
echo -e "${BLUE}Checking Flutter web support...${NC}" | tee -a $LOGFILE
flutter config --enable-web 2>&1 | tee -a $LOGFILE

# Display IP address for Windows access
WSL_IP=$(hostname -I | awk '{print $1}')
echo -e "${GREEN}WSL IP Address: ${WSL_IP}${NC}" | tee -a $LOGFILE

# Available devices
echo -e "${BLUE}Available devices:${NC}" | tee -a $LOGFILE
flutter devices 2>&1 | tee -a $LOGFILE

# Build for web first
echo -e "${YELLOW}Building Flutter for web...${NC}" | tee -a $LOGFILE
flutter build web --dart-define=FLUTTER_WEB_DEBUG=true 2>&1 | tee -a $LOGFILE

# Copy the debug index to the build directory
echo -e "${YELLOW}Setting up debug environment...${NC}" | tee -a $LOGFILE
mkdir -p build/web
cp $DEBUG_INDEX build/web/index.html
echo "Debug index copied to build/web/index.html" | tee -a $LOGFILE

# Check firewall status
echo -e "${BLUE}Checking firewall status...${NC}" | tee -a $LOGFILE
sudo -n iptables -L INPUT -v 2>/dev/null | grep -E "$PORT|all" | tee -a $LOGFILE || echo "Could not check firewall rules (sudo permission required)" | tee -a $LOGFILE

# Start a simple HTTP server for the minimal app with specific binding to expose to Windows
echo -e "${GREEN}Starting minimal debug server on port $PORT...${NC}" | tee -a $LOGFILE
echo -e "${GREEN}Access from Windows at: http://${WSL_IP}:${PORT}${NC}" | tee -a $LOGFILE
echo -e "${YELLOW}Note: If you can't connect from Windows, try these troubleshooting steps:${NC}"
echo -e "${YELLOW}1. Make sure Windows firewall allows connections to WSL${NC}"
echo -e "${YELLOW}2. Try accessing from WSL browser with: http://localhost:${PORT}${NC}"
echo -e "${YELLOW}3. Check if WSL IP is accessible from Windows with: ping ${WSL_IP}${NC}"

cd build/web && python3 -m http.server $PORT --bind 0.0.0.0 2>&1 | tee -a ../../$LOGFILE