#!/bin/bash
# Script to run the Flutter app in Windows Chrome browser

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

LOGFILE="flutter_web_debug.log"
echo -e "${YELLOW}Preparing Flutter Dashboard for Windows Chrome${NC}"
echo -e "${YELLOW}Log will be saved to ${LOGFILE}${NC}"

# Clear existing log
> $LOGFILE

# Get WSL IP address for Windows access
WSL_IP=$(hostname -I | awk '{print $1}')
echo -e "${GREEN}WSL IP Address: ${WSL_IP}${NC}" | tee -a $LOGFILE

# Log system info
echo "=== SYSTEM INFO ===" | tee -a $LOGFILE
echo "Date: $(date)" | tee -a $LOGFILE
echo "WSL: $(uname -a)" | tee -a $LOGFILE
echo "Flutter: $(flutter --version | head -n 1)" | tee -a $LOGFILE
echo "WSL IP: ${WSL_IP}" | tee -a $LOGFILE
echo "=====================" | tee -a $LOGFILE

# Check Flutter web support
echo -e "${YELLOW}Checking Flutter web support...${NC}"
flutter config --enable-web 2>&1 | tee -a $LOGFILE

# Clean and get dependencies (force rebuild)
echo -e "${YELLOW}Cleaning for fresh build...${NC}"
flutter clean 2>&1 | tee -a $LOGFILE

echo -e "${YELLOW}Getting dependencies...${NC}"
flutter pub get 2>&1 | tee -a $LOGFILE

# Run build runner to generate JSON serialization code
echo -e "${YELLOW}Running build_runner...${NC}"
flutter pub run build_runner build --delete-conflicting-outputs 2>&1 | tee -a $LOGFILE

# Network connectivity check
echo -e "${BLUE}Checking network connectivity...${NC}" | tee -a $LOGFILE
echo "Internal connection test:" | tee -a $LOGFILE
nc -zv localhost 8080 2>&1 | tee -a $LOGFILE || echo "Port 8080 not used internally yet" | tee -a $LOGFILE

# Check Flutter version for proper web-renderer syntax
FLUTTER_VERSION=$(flutter --version | head -n 1 | sed 's/Flutter //' | awk '{print $1}')
MAJOR_VERSION=$(echo $FLUTTER_VERSION | cut -d. -f1)
MINOR_VERSION=$(echo $FLUTTER_VERSION | cut -d. -f2)

# Choose the correct syntax based on Flutter version
# For Flutter >=3.3.0, use --web-renderer=html
# For older versions, use --web-renderer html
if [ $MAJOR_VERSION -gt 3 ] || ([ $MAJOR_VERSION -eq 3 ] && [ $MINOR_VERSION -ge 3 ]); then
  WEB_RENDERER_FLAG="--web-renderer=html"
else
  WEB_RENDERER_FLAG="--web-renderer html"
fi

echo -e "${YELLOW}Using web renderer flag: ${WEB_RENDERER_FLAG}${NC}" | tee -a $LOGFILE

# Try running app with WSL IP
echo -e "${YELLOW}Running with Windows Chrome configuration...${NC}"
echo -e "${GREEN}Access the app from Windows at: http://${WSL_IP}:8080${NC}"
echo -e "${BLUE}If page is blank, open Chrome developer tools (F12) to see console errors${NC}"
echo -e "${RED}Press Ctrl+C to stop the app${NC}"

echo "=== STARTING FLUTTER WEB SERVER ===" | tee -a $LOGFILE
# Run with verbose logging and redirect to both terminal and log file
flutter run -d web-server \
  --web-hostname=0.0.0.0 \
  --web-port=8080 \
  $WEB_RENDERER_FLAG \
  --verbose 2>&1 | tee -a $LOGFILE

# Add note about log file
echo -e "${YELLOW}Complete log saved to ${LOGFILE}${NC}"