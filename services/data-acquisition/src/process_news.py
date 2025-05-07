#!/usr/bin/env python3
"""
News Processing Script

This script processes the collected news articles from Finnhub API, 
performs sentiment analysis using FinBERT, and saves the results.
"""

import os
import sys
import json
import csv
import logging
import argparse
import datetime
import pandas as pd
from typing import Dict, Any, List, Optional, Union
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import local modules
from src.sentiment_analyzer import initialize_model, analyze_sentiment, analyze_news_batch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Constants
FINNHUB_DATA_DIR = "/home/jonat/real_senti/data/finnhub_poc"
SENTIMENT_OUTPUT_DIR = "/home/jonat/real_senti/data/sentiment_results"
NEWS_DIR = os.path.join(FINNHUB_DATA_DIR, "news")
SENTIMENT_CSV = os.path.join(SENTIMENT_OUTPUT_DIR, "sentiment_analysis.csv")
SENTIMENT_JSON = os.path.join(SENTIMENT_OUTPUT_DIR, "sentiment_analysis.json")


def load_news_data() -> Dict[str, List[Dict[str, Any]]]:
    """
    Load news data from CSV files.
    
    Returns:
        Dict mapping ticker symbols to lists of news items
    """
    if not os.path.exists(NEWS_DIR):
        logger.error(f"News directory not found: {NEWS_DIR}")
        return {}
    
    news_data = {}
    
    for filename in os.listdir(NEWS_DIR):
        if filename.endswith("_news.csv"):
            ticker = filename.split("_")[0]
            file_path = os.path.join(NEWS_DIR, filename)
            
            try:
                # Read CSV file
                df = pd.read_csv(file_path)
                # Convert to list of dictionaries
                news_items = df.to_dict(orient="records")
                news_data[ticker] = news_items
                logger.info(f"Loaded {len(news_items)} news items for {ticker}")
            except Exception as e:
                logger.error(f"Error loading news data for {ticker}: {e}")
    
    return news_data


def process_news_data(news_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Process news data and perform sentiment analysis.
    
    Args:
        news_data: Dictionary mapping ticker symbols to lists of news items
    
    Returns:
        List of processed news items with sentiment analysis
    """
    # Initialize model
    initialize_model()
    
    all_results = []
    
    # Process each ticker
    for ticker, items in news_data.items():
        logger.info(f"Processing {len(items)} news items for {ticker}")
        
        # Add ticker to each item if not already present
        for item in items:
            if "ticker" not in item:
                item["ticker"] = ticker
        
        # Perform sentiment analysis
        processed_items = analyze_news_batch(items)
        all_results.extend(processed_items)
        
        # Log progress
        logger.info(f"Completed sentiment analysis for {ticker}")
    
    return all_results


def save_sentiment_results(results: List[Dict[str, Any]]) -> None:
    """
    Save sentiment analysis results to CSV and JSON files.
    
    Args:
        results: List of news items with sentiment analysis
    """
    # Create output directory if it doesn't exist
    os.makedirs(SENTIMENT_OUTPUT_DIR, exist_ok=True)
    
    try:
        # Save to CSV
        df = pd.DataFrame(results)
        df.to_csv(SENTIMENT_CSV, index=False)
        logger.info(f"Saved sentiment results to CSV: {SENTIMENT_CSV}")
        
        # Save to JSON
        with open(SENTIMENT_JSON, 'w') as f:
            json.dump(results, f, indent=2)
        logger.info(f"Saved sentiment results to JSON: {SENTIMENT_JSON}")
    except Exception as e:
        logger.error(f"Error saving sentiment results: {e}")


def generate_summary(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate a summary of sentiment analysis results.
    
    Args:
        results: List of news items with sentiment analysis
    
    Returns:
        Dictionary with summary statistics
    """
    df = pd.DataFrame(results)
    
    # Ensure required columns exist
    if "sentiment_score" not in df.columns:
        logger.error("Sentiment score column not found in results")
        return {}
    
    try:
        # Convert sentiment_score to float
        df["sentiment_score"] = df["sentiment_score"].astype(float)
        
        # Calculate ticker-level statistics
        ticker_stats = df.groupby("ticker").agg({
            "sentiment_score": ["mean", "std", "count"],
            "sentiment_label": lambda x: x.value_counts().to_dict()
        })
        
        # Flatten multi-index columns
        ticker_stats.columns = ["_".join(col).strip() for col in ticker_stats.columns.values]
        ticker_stats = ticker_stats.reset_index()
        
        # Convert to dict for JSON serialization
        ticker_summary = ticker_stats.to_dict(orient="records")
        
        # Calculate overall statistics
        overall_sentiment = {
            "mean_score": df["sentiment_score"].mean(),
            "total_articles": len(df),
            "positive_count": (df["sentiment_label"] == "positive").sum(),
            "neutral_count": (df["sentiment_label"] == "neutral").sum(),
            "negative_count": (df["sentiment_label"] == "negative").sum(),
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        summary = {
            "overall": overall_sentiment,
            "by_ticker": ticker_summary
        }
        
        return summary
    
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return {}


def save_summary(summary: Dict[str, Any]) -> None:
    """
    Save sentiment summary to a JSON file.
    
    Args:
        summary: Dictionary with summary statistics
    """
    summary_file = os.path.join(SENTIMENT_OUTPUT_DIR, "sentiment_summary.json")
    
    try:
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        logger.info(f"Saved sentiment summary to: {summary_file}")
    except Exception as e:
        logger.error(f"Error saving summary: {e}")


def main(cli_args=None):
    """
    Main function to process news data and perform sentiment analysis.
    
    Args:
        cli_args: Optional list of command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Process news data and perform sentiment analysis.')
    parser.add_argument('--ticker', help='Process only a specific ticker (e.g., AAPL)')
    parser.add_argument('--summary', action='store_true', 
                        help='Generate and save a summary of sentiment results')
    args = parser.parse_args(cli_args)
    
    logger.info("Starting news processing and sentiment analysis")
    
    # Load news data
    news_data = load_news_data()
    
    if not news_data:
        logger.error("No news data found")
        return
    
    # Filter by ticker if specified
    if args.ticker:
        if args.ticker in news_data:
            news_data = {args.ticker: news_data[args.ticker]}
            logger.info(f"Processing only ticker: {args.ticker}")
        else:
            logger.error(f"Ticker {args.ticker} not found in news data")
            return
    
    # Process news data and perform sentiment analysis
    results = process_news_data(news_data)
    
    # Save results
    save_sentiment_results(results)
    
    # Generate and save summary if requested
    if args.summary:
        summary = generate_summary(results)
        save_summary(summary)
    
    # Print completion message
    logger.info(f"Completed processing {len(results)} news items")
    logger.info(f"Results saved to {SENTIMENT_OUTPUT_DIR}")


if __name__ == "__main__":
    main()