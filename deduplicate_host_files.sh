#!/bin/bash
# Script to copy all parquet files from host to Docker container and deduplicate them

# Check if a ticker or "all" was provided
if [ $# -eq 0 ]; then
    echo "Error: No ticker provided"
    echo "Usage: ./deduplicate_host_files.sh <ticker_symbol | all>"
    echo "Example: ./deduplicate_host_files.sh vusa"
    echo "         ./deduplicate_host_files.sh all"
    exit 1
fi

TICKER=$1

# Copy the deduplication script to the Docker container
echo "Copying deduplication script to Docker container..."
docker compose cp /home/jonat/WSL_RT_Sentiment/deduplicate_docker.py api:/app/deduplicate_docker.py

# Create the fixed directory in Docker container
docker compose exec api mkdir -p /app/data/output/fixed

# Create the fixed directory on host if it doesn't exist
mkdir -p /home/jonat/WSL_RT_Sentiment/data/output/fixed

if [ "$TICKER" = "all" ]; then
    # Find all ticker files on host
    echo "Finding all ticker files on host..."
    HOST_FILES=$(find /home/jonat/WSL_RT_Sentiment/data/output/ -maxdepth 1 -name "*_sentiment.parquet" | grep -o '[^/]*$' | sed 's/_sentiment.parquet//')
    
    # Check if any files were found
    if [ -z "$HOST_FILES" ]; then
        echo "No ticker files found on host."
        exit 1
    fi
    
    # Process each file
    for TICKER in $HOST_FILES; do
        echo "========================================="
        echo "Processing ticker: $TICKER"
        echo "========================================="
        
        # Copy the file to Docker container
        echo "Copying $TICKER file to Docker container..."
        docker compose cp "/home/jonat/WSL_RT_Sentiment/data/output/${TICKER}_sentiment.parquet" "api:/app/data/output/${TICKER}_sentiment.parquet"
        
        # Run the deduplication script
        echo "Deduplicating $TICKER..."
        docker compose exec api python /app/deduplicate_docker.py $TICKER
        
        # Copy the deduplicated file back to host
        echo "Copying deduplicated $TICKER file back to host..."
        docker compose cp "api:/app/data/output/fixed/${TICKER}_sentiment.parquet" "/home/jonat/WSL_RT_Sentiment/data/output/fixed/${TICKER}_sentiment.parquet"
        
        echo ""
    done
    
    echo "All ticker files processed!"
else
    # Process a single ticker
    echo "========================================="
    echo "Processing ticker: $TICKER"
    echo "========================================="
    
    # Check if file exists on host
    if [ ! -f "/home/jonat/WSL_RT_Sentiment/data/output/${TICKER}_sentiment.parquet" ]; then
        echo "Error: File ${TICKER}_sentiment.parquet does not exist on host."
        exit 1
    fi
    
    # Copy the file to Docker container
    echo "Copying $TICKER file to Docker container..."
    docker compose cp "/home/jonat/WSL_RT_Sentiment/data/output/${TICKER}_sentiment.parquet" "api:/app/data/output/${TICKER}_sentiment.parquet"
    
    # Run the deduplication script
    echo "Deduplicating $TICKER..."
    docker compose exec api python /app/deduplicate_docker.py $TICKER
    
    # Copy the deduplicated file back to host
    echo "Copying deduplicated $TICKER file back to host..."
    docker compose cp "api:/app/data/output/fixed/${TICKER}_sentiment.parquet" "/home/jonat/WSL_RT_Sentiment/data/output/fixed/${TICKER}_sentiment.parquet"
    
    echo "Ticker $TICKER processed successfully!"
fi