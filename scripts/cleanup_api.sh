#!/bin/bash
# Script to clean up API processes

# Find and kill any Python processes running the sentiment API
echo "Finding and killing API processes..."
API_PIDS=$(ps aux | grep "python.*start_mock_api.py" | grep -v grep | awk '{print $2}')

if [[ -n "$API_PIDS" ]]; then
    echo "Found API process(es) with PIDs: $API_PIDS"
    echo "Killing processes..."
    for PID in $API_PIDS; do
        kill $PID
        echo "Killed PID $PID"
    done
else
    echo "No API processes found"
fi

# Find and kill uvicorn processes related to the API
UVICORN_PIDS=$(ps aux | grep "uvicorn.*sentiment_api:app" | grep -v grep | awk '{print $2}')

if [[ -n "$UVICORN_PIDS" ]]; then
    echo "Found uvicorn process(es) with PIDs: $UVICORN_PIDS"
    echo "Killing processes..."
    for PID in $UVICORN_PIDS; do
        kill $PID
        echo "Killed PID $PID"
    done
else
    echo "No uvicorn processes found"
fi

echo "Cleanup complete"