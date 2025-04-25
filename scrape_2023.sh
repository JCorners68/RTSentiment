#!/bin/bash

# Script to scrape news and Reddit data for each month of 2023
# Activate virtual environment
cd /home/jonat/WSL_RT_Sentiment
source venv/bin/activate

# Dates for 2023 by month
MONTHS=(
    "2023-01-01 2023-01-31"
    "2023-02-01 2023-02-28"
    "2023-03-01 2023-03-31"
    "2023-04-01 2023-04-30"
    "2023-05-01 2023-05-31"
    "2023-06-01 2023-06-30"
    "2023-07-01 2023-07-31"
    "2023-08-01 2023-08-31"
    "2023-09-01 2023-09-30"
    "2023-10-01 2023-10-31"
    "2023-11-01 2023-11-30"
    "2023-12-01 2023-12-31"
)

# Scrape both news and Reddit for each month
for month in "${MONTHS[@]}"; do
    read -r start_date end_date <<< "$month"
    
    echo "Scraping news for $start_date to $end_date"
    python3 tests/data_tests/scrape_history.py --start_date "$start_date" --end_date "$end_date" --source news --no-metrics
    
    echo "Scraping Reddit for $start_date to $end_date"
    python3 tests/data_tests/scrape_history.py --start_date "$start_date" --end_date "$end_date" --source reddit --no-metrics
    
    # Give a short pause between runs
    sleep 2
done

echo "All scraping completed."