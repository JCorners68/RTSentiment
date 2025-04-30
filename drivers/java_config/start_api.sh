#!/bin/bash
source "/home/jonat/WSL_RT_Sentiment/drivers/java_config/setenv.sh"

echo "Starting Sentiment API with enhanced JVM settings..."
cd /home/jonat/WSL_RT_Sentiment

# Set up Python environment
source iceberg_venv/bin/activate

# Start the API with proper JVM settings
PYTHONPATH=/home/jonat/WSL_RT_Sentiment python iceberg_lake/examples/start_sentiment_api.py
