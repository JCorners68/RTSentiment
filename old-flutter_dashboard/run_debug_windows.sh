#!/bin/bash
# Script to run the Flutter app in debug mode with Windows Chrome browser

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

LOGFILE="flutter_debug.log"
echo -e "${YELLOW}Starting Flutter Dashboard DEBUG mode for Windows Chrome${NC}"
echo -e "${YELLOW}Detailed logs will be saved to ${LOGFILE}${NC}"

# Clear existing log
echo "=== DEBUG SESSION STARTED $(date) ===" > $LOGFILE

# Ensure the Flutter web support is enabled
flutter config --enable-web 2>&1 | tee -a $LOGFILE

# Check Flutter doctor for any issues
echo -e "${BLUE}Checking Flutter installation...${NC}"
flutter doctor -v 2>&1 | tee -a $LOGFILE

# Get dependencies
echo -e "${YELLOW}Getting dependencies...${NC}"
flutter pub get 2>&1 | tee -a $LOGFILE

# Check the window_config.js file
if [[ -f "web/window_config.js" ]]; then
  echo -e "${BLUE}web/window_config.js contents:${NC}" | tee -a $LOGFILE
  cat web/window_config.js | tee -a $LOGFILE
fi

# Try running with the debug entry point
echo -e "${GREEN}Running with DIAGNOSTIC configuration...${NC}"
echo -e "${RED}Log data will be saved to ${LOGFILE}${NC}"
echo -e "${GREEN}Access the app at http://localhost:9090 in your Windows Chrome browser${NC}"

# Updated to remove the invalid --web-renderer option
flutter run -d web-server \
  --web-hostname=0.0.0.0 \
  --web-port=9090 \
  --observatory-port=9091 \
  --enable-dart-profiling \
  --dart-define=FLUTTER_WEB_DEBUG=true \
  --verbose \
  lib/main_debug.dart 2>&1 | tee -a $LOGFILE

echo "=== DEBUG SESSION ENDED $(date) ===" >> $LOGFILE
echo -e "${YELLOW}Debug session completed. Logs saved to ${LOGFILE}${NC}"
echo -e "${YELLOW}If the app didn't load properly, check ${LOGFILE} for errors${NC}"