#!/bin/bash
# Script to run the Flutter app in web mode

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Preparing Flutter Dashboard for Web${NC}"

# Get dependencies
echo -e "${YELLOW}Getting dependencies...${NC}"
flutter pub get

# Run build runner to generate JSON serialization code
echo -e "${YELLOW}Running build_runner...${NC}"
flutter pub run build_runner build --delete-conflicting-outputs

# Run in Chrome if available, otherwise fallback to web-server mode
if flutter devices | grep -q Chrome; then
  echo -e "${GREEN}Running in Chrome...${NC}"
  flutter run -d chrome
else
  echo -e "${YELLOW}Chrome not available, running in web-server mode...${NC}"
  flutter run -d web-server --web-hostname=0.0.0.0 --web-port=8080
  echo -e "${GREEN}Web server running at http://localhost:8080${NC}"
fi