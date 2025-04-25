#!/bin/bash
# Script to fix the code issues and run the Flutter app

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Fixing Flutter Dashboard Code Issues${NC}"

# Clean build first
echo -e "${YELLOW}Cleaning previous build artifacts...${NC}"
flutter clean

# Get dependencies with updated chart library
echo -e "${YELLOW}Getting dependencies...${NC}"
flutter pub get

# Run build runner to generate JSON serialization code
echo -e "${YELLOW}Running build_runner...${NC}"
dart run build_runner build --delete-conflicting-outputs

echo -e "${GREEN}Fixed code issues!${NC}"
echo -e "${YELLOW}Now trying to run the app...${NC}"
echo -e "flutter run -d linux"

# Try to run the app
flutter run -d linux