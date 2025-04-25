#\!/bin/bash
echo "Starting Flutter web server with Windows-accessible settings"

# Stop any existing Flutter processes
pkill -f "flutter run" 2>/dev/null

# Get the WSL IP address
WSL_IP=$(hostname -I  < /dev/null |  awk "{print \$1}")
echo "WSL IP: $WSL_IP"

# Run Flutter in web server mode with proper hostname
echo "Starting Flutter web server on http://$WSL_IP:8090"
echo "Access this from Windows at http://$WSL_IP:8090"

flutter run -d web-server --web-hostname=$WSL_IP --web-port=8090

