# Data Cleaning and Deduplication Report

## Overview

This document outlines the process of cleaning and deduplicating financial sentiment data stored in parquet files. The goal was to identify and remove duplicate entries while preserving unique records to ensure data quality and accuracy for downstream analysis.

## Problem

The original parquet files in `/data/output/*.parquet` contained duplicate entries with:
- Same article titles
- Multiple instances of identical data with different article IDs
- No clear distinction between real and simulated data

## Solution

### 1. Data Organization

- Separated real data into `/data/output/real/` directory
- Created a deduplication script (`deduplicate_parquet.py`) to systematically remove duplicates

### 2. Deduplication Process

The deduplication process uses the following approach:
- Identifies duplicate records based on `timestamp` and `article_title` fields
- Keeps the first occurrence of each unique record
- Saves deduplicated data to the `/data/output/real/` directory
- Preserves directory structure to maintain compatibility with existing code

### 3. Data Consolidation

After deduplication, created a unified dataset:
- Combined all deduplicated parquet files into a single file: `/data/output/combined_recalculated/all_clean_sentiment.parquet`
- This file contains 1,248 unique records across 441 different tickers
- All data comes from a single source (RedditScraper)
- Date range: 2025-03-01 to 2025-04-26

### 4. Analysis and Reporting

Created analysis scripts to provide insights on the cleaned data:
- `analyze_sentiment.py`: Generates statistical analysis and visualizations
- `create_report.py`: Creates an HTML report with embedded visualizations

## Results

The deduplication process successfully removed all duplicate records. The final dataset contains:
- 1,248 unique sentiment records
- 441 unique ticker symbols
- Single data source (RedditScraper)
- Data spanning from 2025-03-01 to 2025-04-26
- All sentiment scores are 0, indicating potential issues with sentiment calculation

## Reports and Outputs

- **HTML Report**: `/data/analysis/sentiment_report.html` - A comprehensive dashboard with visualizations
- **CSV Reports**:
  - `/data/analysis/ticker_sentiment.csv` - Average sentiment by ticker symbol
  - `/data/analysis/top_tickers.csv` - Most frequent ticker symbols
- **Visualizations**: 
  - Sentiment distribution
  - Top tickers by frequency
  - Top positive/negative sentiment tickers

## Tools Used

1. **deduplicate_parquet.py** - Main deduplication script
2. **combine_parquet.py** - Combines deduplicated files
3. **analyze_sentiment.py** - Statistical analysis and visualizations
4. **create_report.py** - HTML report generation

## Technologies

- Python (pandas, pyarrow)
- Docker for execution environment
- Matplotlib for visualization
- HTML/CSS for reporting

## Usage

To rerun the deduplication process:

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate
pip install pandas pyarrow matplotlib

# Run deduplication
python deduplicate_parquet.py

# Combine files
python combine_parquet.py

# Generate analysis
python analyze_clean_sentiment.py

# Create HTML report
python create_report.py
```

## Next Steps

The fact that all sentiment scores are 0 indicates a potential issue with sentiment calculation. Recommended actions:

1. Investigate the sentiment analysis implementation in the data pipeline
2. Recalculate sentiment scores using a working sentiment model
3. Update the combined dataset with proper sentiment values
4. Re-run the analysis to get meaningful insights from sentiment distribution