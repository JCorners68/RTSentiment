#!/bin/bash

# Run the Streamlit dashboard locally

echo "Starting Real-Time Sentiment Analysis Dashboard..."

# Make sure streamlit_dashboard directory exists
if [ ! -d "streamlit_dashboard" ]; then
  echo "Error: streamlit_dashboard directory not found!"
  exit 1
fi

# Check if running in Docker or locally
if [ "$1" == "--docker" ]; then
  echo "Starting dashboard in Docker container..."
  
  # Check if Docker Compose environment is running
  if ! docker compose ps | grep -q "Up"; then
    echo "Starting Docker Compose environment..."
    docker compose up -d
  fi
  
  # Build and start the dashboard container
  docker compose up -d dashboard
  
  echo "Dashboard started! Access at http://localhost:8501"
  
else
  # Run locally with Python
  echo "Starting dashboard locally..."
  
  # Check if virtual environment exists, create if not
  if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
  fi
  
  # Activate virtual environment and install requirements
  source venv/bin/activate
  echo "Installing requirements..."
  pip install -r streamlit_dashboard/requirements.txt
  
  # Run the dashboard
  echo "Starting Streamlit server..."
  cd streamlit_dashboard
  streamlit run app.py
fi