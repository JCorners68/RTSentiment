#\!/bin/bash
echo "Starting WSL to Windows port forwarding service"
# Find the WSL IP address
WSL_IP=$(hostname -I  < /dev/null |  awk "{print \$1}")
echo "WSL IP: $WSL_IP"

# Forward ports
echo "Setting up port forwarding from WSL to Windows..."
WINDOWS_IP=172.25.16.1  # Common Windows host IP from WSL

# Stop any running socat processes
pkill socat 2>/dev/null

# Start port forwarding
echo "Forwarding port 8090 for Flutter web app"
socat TCP-LISTEN:8090,fork,reuseaddr TCP:$WINDOWS_IP:8090 &
SOCAT_PID=$\!

echo "Port forwarding active. Press Ctrl+C to stop."
trap "kill $SOCAT_PID; echo \"Port forwarding stopped.\"" EXIT

# Keep script running until interrupted
wait $SOCAT_PID

