#!/bin/bash
# Script to deduplicate all available ticker files

# Copy the deduplication script to the Docker container
echo "Copying deduplication script to Docker container..."
docker compose cp /home/jonat/WSL_RT_Sentiment/deduplicate_docker.py api:/app/deduplicate_docker.py

# Create the fixed directory if it doesn't exist
docker compose exec api mkdir -p /app/data/output/fixed

# Get list of available ticker files
echo "Finding available ticker files..."
FILES=$(docker compose exec api find /app/data/output/ -name "*_sentiment.parquet" -not -path "*/fixed/*" | grep -o '[^/]*$' | sed 's/_sentiment.parquet//')

# Check if any files were found
if [ -z "$FILES" ]; then
    echo "No ticker files found."
    exit 1
fi

# Process each file
for TICKER in $FILES; do
    echo "========================================="
    echo "Processing ticker: $TICKER"
    echo "========================================="
    
    # Run the deduplication script
    docker compose exec api python /app/deduplicate_docker.py $TICKER
    
    echo ""
done

echo "All available ticker files processed!"