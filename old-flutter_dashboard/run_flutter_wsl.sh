#!/bin/bash
# Script to run the Flutter dashboard on WSL

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Running Flutter Dashboard on WSL${NC}"

# Check if Flutter is installed
if ! command -v flutter &> /dev/null; then
    echo -e "${YELLOW}Flutter not found. Please install Flutter first.${NC}"
    echo "See Documentation/FLUTTER_SETUP.md for installation instructions."
    exit 1
fi

# Navigate to flutter_dashboard directory
cd "$(dirname "$0")" || {
    echo "Could not navigate to flutter_dashboard directory."
    exit 1
}

# Check for dependencies
echo -e "${YELLOW}Checking for Flutter dependencies...${NC}"
flutter pub get

# Check if we have Linux desktop enabled
echo -e "${YELLOW}Checking if Linux desktop support is enabled...${NC}"
if ! flutter config --list | grep -q "enable-linux-desktop: true"; then
    echo -e "${YELLOW}Enabling Linux desktop support...${NC}"
    flutter config --enable-linux-desktop
fi

# Check if GTK dependencies are installed
if ! dpkg -l | grep -q libgtk-3-dev; then
    echo -e "${YELLOW}Linux desktop dependencies may be missing.${NC}"
    echo "Consider running: sudo apt install -y clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev"
    
    # Ask if user wants to proceed anyway
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check available devices
echo -e "${YELLOW}Checking available devices...${NC}"
DEVICES=$(flutter devices)
echo "$DEVICES"

# Run the app on Linux by default
echo -e "${GREEN}Running Flutter dashboard on Linux desktop...${NC}"
flutter run -d linux

# If that fails, try running with default device
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}Failed to run on Linux desktop. Trying default device...${NC}"
    flutter run
fi