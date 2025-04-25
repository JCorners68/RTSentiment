#!/bin/bash
# Script to run either the query app or dashboard

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null
then
    echo "Streamlit could not be found. Installing required packages..."
    pip install -r requirements.txt
fi

# Check if we want to run the dashboard or the app
if [ "$1" == "dashboard" ]; then
    echo "Starting dashboard..."
    streamlit run dashboard.py "$@"
else
    echo "Starting interactive query app..."
    streamlit run app.py "$@"
fi