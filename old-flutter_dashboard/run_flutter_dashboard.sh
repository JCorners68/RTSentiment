#!/bin/bash

# Run the Flutter dashboard locally on WSL

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

DASHBOARD_DIR="tests/flutter_dashboard"
PORT=7071
WSL_IP=$(hostname -I | awk '{print $1}')

echo -e "${YELLOW}Starting Real-Time Sentiment Flutter Dashboard...${NC}"

# Make sure flutter_dashboard directory exists
if [ ! -d "$DASHBOARD_DIR" ]; then
  echo -e "${RED}Error: $DASHBOARD_DIR directory not found!${NC}"
  exit 1
fi

# Change to the dashboard directory
cd "$DASHBOARD_DIR"

# Check if Flutter is installed
if ! command -v flutter &> /dev/null; then
  echo -e "${RED}Error: Flutter is not installed or not in PATH!${NC}"
  exit 1
fi

# Clean Flutter build
echo -e "${YELLOW}Cleaning previous builds...${NC}"
flutter clean

# Get dependencies
echo -e "${YELLOW}Getting Flutter dependencies...${NC}"
flutter pub get

# Build for web
echo -e "${YELLOW}Building Flutter web app...${NC}"
flutter clean
flutter pub get
flutter build web

# Serve the Flutter web app
echo -e "${GREEN}Starting Flutter dashboard on http://$WSL_IP:$PORT${NC}"
echo -e "${GREEN}You can access it in your WSL browser at: http://localhost:$PORT${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"

cd build/web && python3 -m http.server $PORT --bind 0.0.0.0