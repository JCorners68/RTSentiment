#!/bin/bash
# Script to start a Dremio test container

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Dremio container is already running
DREMIO_RUNNING=$(docker ps --filter "name=dremio" --format "{{.Names}}" | grep -w "dremio" || echo "")

if [ -n "$DREMIO_RUNNING" ]; then
    echo "Dremio container is already running"
else
    echo "Starting Dremio container..."
    
    # Check if the container exists but is stopped
    DREMIO_EXISTS=$(docker ps -a --filter "name=dremio" --format "{{.Names}}" | grep -w "dremio" || echo "")
    
    if [ -n "$DREMIO_EXISTS" ]; then
        # Start the existing container
        docker start dremio
    else
        # Run a new container
        docker run -d \
            --name dremio \
            -p 9047:9047 -p 31010:31010 \
            -v /tmp/dremio:/var/lib/dremio \
            dremio/dremio-oss
    fi
    
    echo "Waiting for Dremio to start (this may take a minute)..."
    
    # Wait for Dremio to be ready
    for i in {1..30}; do
        if curl -s http://localhost:9047 > /dev/null; then
            echo "Dremio is ready"
            break
        fi
        
        if [ $i -eq 30 ]; then
            echo "Timed out waiting for Dremio to start"
            exit 1
        fi
        
        echo -n "."
        sleep 2
    done
fi

# Show Dremio login info
echo "Dremio is running at http://localhost:9047"
echo "Default credentials: dremio/dremio123"

# Create a test source for verification
echo "Setting up test source in Dremio..."
# This would normally use a REST API call to set up sources, but for simplicity
# we're just displaying instructions
echo "To manually verify Dremio:"
echo "1. Open http://localhost:9047 in your browser"
echo "2. Log in with dremio/dremio123"
echo "3. Create a File System source pointing to /tmp/dremio/test"

# Create a test directory for the source
mkdir -p /tmp/dremio/test

# Create a test file
echo "Creating test data for verification..."
cat > /tmp/dremio/test/sentiment_test.json << 'EOF'
{"message_id": "test-001", "sentiment_score": 0.8, "text_content": "This is a test message for Dremio verification"}
{"message_id": "test-002", "sentiment_score": -0.5, "text_content": "Another test message with negative sentiment"}
{"message_id": "test-003", "sentiment_score": 0.2, "text_content": "A neutral test message"}
EOF

echo "Test data created at /tmp/dremio/test/sentiment_test.json"
echo "You can now run the verification tests"