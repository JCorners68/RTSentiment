#!/bin/bash
# Script to install Flutter and set up the Flutter dashboard

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up Flutter for RT Sentiment Dashboard${NC}"

# Check if Flutter is installed
if ! command -v flutter &> /dev/null; then
    echo -e "${YELLOW}Flutter not found. Please install Flutter following these steps:${NC}"
    echo ""
    echo "1. Download Flutter SDK from https://docs.flutter.dev/get-started/install/linux"
    echo "   wget https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.19.3-stable.tar.xz"
    echo ""
    echo "2. Extract it to a location of your choice (e.g., ~/development):"
    echo "   mkdir -p ~/development"
    echo "   tar xf flutter_linux_3.19.3-stable.tar.xz -C ~/development"
    echo ""
    echo "3. Add Flutter to your PATH by adding this line to your ~/.bashrc:"
    echo "   export PATH=\"\$PATH:\$HOME/development/flutter/bin\""
    echo ""
    echo "4. Apply the changes:"
    echo "   source ~/.bashrc"
    echo ""
    echo "5. Run flutter doctor to verify the installation:"
    echo "   flutter doctor"
    echo ""
    echo "Once Flutter is installed, run this script again."
    exit 1
fi

# Flutter is installed, continue with setup
echo -e "${GREEN}Flutter found. Continuing with dashboard setup...${NC}"

# Navigate to flutter_dashboard directory
cd "$(dirname "$0")/flutter_dashboard" || {
    echo "Could not navigate to flutter_dashboard directory."
    exit 1
}

# Install dependencies
echo -e "${YELLOW}Installing Flutter dependencies...${NC}"
flutter pub get

# Generate JSON serialization code
echo -e "${YELLOW}Generating JSON serialization code...${NC}"
flutter pub run build_runner build --delete-conflicting-outputs

echo -e "${GREEN}Setup complete! You can now run the Flutter dashboard with:${NC}"
echo "cd $(dirname "$0")/flutter_dashboard && flutter run -d chrome"
echo ""
echo -e "${YELLOW}Make sure your backend API is running at http://localhost:8001${NC}"
echo "If you need to use a different API URL, edit the baseUrl in lib/api/api_client.dart"