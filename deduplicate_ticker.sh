#!/bin/bash
# Script to deduplicate a specific ticker's sentiment parquet file

# Check if a ticker was provided
if [ $# -eq 0 ]; then
    echo "Error: No ticker provided"
    echo "Usage: ./deduplicate_ticker.sh <ticker_symbol>"
    echo "Example: ./deduplicate_ticker.sh mstr"
    exit 1
fi

TICKER=$1

# Copy the deduplication script to the Docker container
echo "Copying deduplication script to Docker container..."
docker compose cp /home/jonat/WSL_RT_Sentiment/deduplicate_docker.py api:/app/deduplicate_docker.py

# Run the script
echo "Running deduplication for ${TICKER}..."
docker compose exec api python /app/deduplicate_docker.py ${TICKER}

# Check if the deduplication was successful
if [ $? -eq 0 ]; then
    echo "Deduplication completed successfully."
    
    # Copy the deduplicated file back to the host if needed
    # Uncomment the line below if you want to copy the file back
    # docker compose cp api:/app/data/output/fixed/${TICKER}_sentiment.parquet /home/jonat/WSL_RT_Sentiment/data/output/fixed/${TICKER}_sentiment.parquet
else
    echo "Deduplication failed."
fi