#!/bin/bash
# This script serves the built Flutter web app directly using Busybox httpd for maximum compatibility

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PORT=5555
WSL_IP=$(hostname -I | awk '{print $1}')

echo -e "${YELLOW}Starting minimal HTTP server with BusyBox${NC}"

# Make sure BusyBox is installed
if ! command -v busybox &> /dev/null; then
    echo "BusyBox is not installed. Installing..."
    sudo apt-get update
    sudo apt-get install -y busybox
fi

# First build the Flutter web app
echo -e "${YELLOW}Building Flutter web app...${NC}"
flutter build web

# Create a very basic HTML file to test connectivity
mkdir -p build/web/test
cat > build/web/test/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <title>WSL Test Page</title>
</head>
<body>
  <h1>WSL Connectivity Test</h1>
  <p>If you can see this page, connectivity between Windows and WSL is working!</p>
  <p>Try the <a href="/">Flutter app</a> next.</p>
</body>
</html>
EOF

# Start the HTTP server
echo -e "${GREEN}Starting HTTP server on port ${PORT}${NC}"
echo -e "${GREEN}Test URLs:${NC}"
echo -e "    Simple test page: http://${WSL_IP}:${PORT}/test/"
echo -e "    Flutter app: http://${WSL_IP}:${PORT}/"
echo -e "${YELLOW}Press Ctrl+C to stop${NC}"

cd build/web && python3 -m http.server ${PORT} --bind 0.0.0.0