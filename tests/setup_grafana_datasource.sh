#!/bin/bash
# Script to set up Grafana data source directly via API

# Wait for Grafana to be ready
echo "Waiting for Grafana to be ready..."
until $(curl --output /dev/null --silent --head --fail http://localhost:3000/api/health); do
    printf '.'
    sleep 1
done

echo ""
echo "Grafana is ready!"

# Try to authenticate with the default admin/admin credentials
echo "Authenticating with Grafana..."
CSRF_TOKEN=$(curl -s -c /tmp/grafana_cookies.txt http://localhost:3000/login | grep -oE '"xsrf":"[^"]+"' | cut -d'"' -f4)

if [ -z "$CSRF_TOKEN" ]; then
    echo "Failed to get CSRF token. Using direct API call instead."
    
    # Try to log in and get a session cookie
    curl -s -c /tmp/grafana_cookies.txt -d '{"user":"admin","password":"admin"}' -H "Content-Type: application/json" http://localhost:3000/login > /dev/null
else
    echo "Got CSRF token: $CSRF_TOKEN"
    
    # Log in with the CSRF token
    curl -s -c /tmp/grafana_cookies.txt -d "user=admin&password=admin&xsrf=$CSRF_TOKEN" -H "Content-Type: application/x-www-form-urlencoded" http://localhost:3000/login > /dev/null
fi

# Create Prometheus data source
echo "Creating Prometheus data source..."
RESPONSE=$(curl -s -b /tmp/grafana_cookies.txt -H "Content-Type: application/json" -X POST http://localhost:3000/api/datasources -d '{
  "name": "Prometheus",
  "type": "prometheus",
  "url": "http://prometheus:9090",
  "access": "proxy",
  "isDefault": true,
  "uid": "prometheus",
  "jsonData": {
    "timeInterval": "5s",
    "queryTimeout": "60s",
    "httpMethod": "POST"
  }
}')

echo $RESPONSE | grep -q "Datasource added" && echo "✅ Data source created successfully" || echo "❌ Failed to create data source: $RESPONSE"

# Clean up
rm -f /tmp/grafana_cookies.txt