#!/bin/bash
# Quick script to run the Flutter app without rebuilding dependencies

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running Flutter Dashboard${NC}"
echo -e "${YELLOW}Using existing configuration${NC}"

# Read isDemoMode setting from app_config.dart
DEMO_MODE=$(grep -o "isDemoMode = .*;" lib/utils/app_config.dart | grep -o "true\|false")
if [ "$DEMO_MODE" == "true" ]; then
  echo -e "${RED}Running in DEMO MODE${NC}"
else
  echo -e "${GREEN}Running in LIVE MODE${NC}"
fi

# Try to run with chrome first
if flutter devices | grep -q chrome; then
  echo -e "${GREEN}Running in Chrome...${NC}"
  flutter run -d chrome --web-port=9100
# Then try Linux desktop
elif flutter devices | grep -q linux; then
  echo -e "${GREEN}Running on Linux desktop...${NC}" 
  flutter run -d linux
# Then try web server
elif flutter devices | grep -q web; then
  echo -e "${GREEN}Running in web server mode...${NC}"
  flutter run -d web-server --web-hostname=0.0.0.0 --web-port=8080
# Default device
else
  echo -e "${GREEN}Running on default device...${NC}"
  flutter run
fi