#!/usr/bin/env python3
"""
FinBERT Pipeline Verification Script

This script runs the complete FinBERT pipeline from data loading to visualization.
It provides clear output to verify the pipeline is working correctly.
"""

import os
import sys
import json
import time
import logging
import argparse
import subprocess
import pandas as pd
from typing import List, Dict, Any
from pathlib import Path

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
SENTIMENT_SUMMARY = os.path.join(SENTIMENT_OUTPUT_DIR, "sentiment_summary.json")
VISUALIZATIONS_DIR = os.path.join(SENTIMENT_OUTPUT_DIR, "visualizations")

def header(title: str, width: int = 80) -> None:
    """Print a formatted header."""
    print("\n" + "=" * width)
    print(f" {title} ".center(width))
    print("=" * width)

def run_command(cmd: List[str], description: str) -> int:
    """
    Run a command and display its output.
    
    Args:
        cmd: Command to run as list of strings
        description: Description of what the command does
        
    Returns:
        Return code from command
    """
    header(f"RUNNING: {description}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 80)
    
    start_time = time.time()
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )
    
    # Print output in real-time
    output_lines = []
    for line in process.stdout:
        print(line.rstrip())
        output_lines.append(line)
    
    process.wait()
    duration = time.time() - start_time
    
    print("-" * 80)
    print(f"Command completed with return code: {process.returncode}")
    print(f"Duration: {duration:.2f} seconds")
    
    return process.returncode

def count_news_articles() -> Dict[str, int]:
    """
    Count news articles by ticker.
    
    Returns:
        Dictionary mapping tickers to article counts
    """
    header("CHECKING NEWS DATA")
    
    if not os.path.exists(NEWS_DIR):
        print(f"Error: News directory not found: {NEWS_DIR}")
        return {}
    
    counts = {}
    total = 0
    
    print(f"{'Ticker':<10} {'Articles':>10}")
    print("-" * 21)
    
    for filename in os.listdir(NEWS_DIR):
        if filename.endswith("_news.csv"):
            ticker = filename.split("_")[0]
            file_path = os.path.join(NEWS_DIR, filename)
            
            try:
                df = pd.read_csv(file_path)
                count = len(df)
                counts[ticker] = count
                total += count
                print(f"{ticker:<10} {count:>10,}")
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    
    print("-" * 21)
    print(f"{'TOTAL':<10} {total:>10,}")
    
    return counts

def verify_sentiment_results() -> Dict[str, Any]:
    """
    Verify sentiment analysis results.
    
    Returns:
        Dictionary with sentiment statistics
    """
    header("VERIFYING SENTIMENT RESULTS")
    
    if not os.path.exists(SENTIMENT_CSV):
        print(f"Error: Sentiment results not found: {SENTIMENT_CSV}")
        return {}
    
    try:
        df = pd.read_csv(SENTIMENT_CSV)
        
        # Basic statistics
        record_count = len(df)
        ticker_count = df["ticker"].nunique()
        positive_count = (df["sentiment_label"] == "positive").sum()
        negative_count = (df["sentiment_label"] == "negative").sum()
        neutral_count = (df["sentiment_label"] == "neutral").sum()
        
        print(f"Total records: {record_count:,}")
        print(f"Unique tickers: {ticker_count}")
        print()
        print(f"Sentiment distribution:")
        print(f"  Positive: {positive_count:,} ({positive_count/record_count*100:.1f}%)")
        print(f"  Neutral: {neutral_count:,} ({neutral_count/record_count*100:.1f}%)")
        print(f"  Negative: {negative_count:,} ({negative_count/record_count*100:.1f}%)")
        print()
        
        # Sentiment by ticker
        print(f"{'Ticker':<10} {'Count':>8} {'Positive':>10} {'Neutral':>10} {'Negative':>10} {'Avg Score':>10}")
        print("-" * 62)
        
        for ticker, group in df.groupby("ticker"):
            count = len(group)
            pos = (group["sentiment_label"] == "positive").sum()
            neu = (group["sentiment_label"] == "neutral").sum()
            neg = (group["sentiment_label"] == "negative").sum()
            avg = group["sentiment_score"].mean()
            
            print(f"{ticker:<10} {count:>8,} {pos:>10,} {neu:>10,} {neg:>10,} {avg:>10.3f}")
        
        print()
        
        if SENTIMENT_SUMMARY and os.path.exists(SENTIMENT_SUMMARY):
            with open(SENTIMENT_SUMMARY, 'r') as f:
                summary = json.load(f)
                print("Summary statistics available at:")
                print(f"  {SENTIMENT_SUMMARY}")
        
        stats = {
            "record_count": record_count,
            "ticker_count": ticker_count,
            "positive_count": positive_count,
            "neutral_count": neutral_count,
            "negative_count": negative_count
        }
        
        return stats
    
    except Exception as e:
        print(f"Error verifying sentiment results: {e}")
        return {}

def verify_visualizations() -> List[str]:
    """
    Verify visualization outputs.
    
    Returns:
        List of generated visualization paths
    """
    header("VERIFYING VISUALIZATIONS")
    
    if not os.path.exists(VISUALIZATIONS_DIR):
        print(f"Error: Visualizations directory not found: {VISUALIZATIONS_DIR}")
        return []
    
    visualizations = []
    
    print(f"Visualization directory: {VISUALIZATIONS_DIR}")
    print()
    print("Generated visualizations:")
    
    for filename in os.listdir(VISUALIZATIONS_DIR):
        if filename.endswith(".png"):
            path = os.path.join(VISUALIZATIONS_DIR, filename)
            size_kb = os.path.getsize(path) / 1024
            visualizations.append(path)
            print(f"  - {filename} ({size_kb:.1f} KB)")
    
    if not visualizations:
        print("  No visualizations found.")
    
    return visualizations

def main():
    """Main function to run and verify the complete FinBERT pipeline."""
    parser = argparse.ArgumentParser(
        description='Run and verify the complete FinBERT pipeline.')
    
    parser.add_argument('--skip-processing', action='store_true',
                        help='Skip processing step (use existing results)')
    parser.add_argument('--skip-visualization', action='store_true',
                        help='Skip visualization step')
    parser.add_argument('--ticker', type=str,
                        help='Process only a specific ticker (e.g., AAPL)')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print(" FINBERT SENTIMENT ANALYSIS PIPELINE VERIFICATION ".center(80))
    print("=" * 80)
    
    # Create output directories if they don't exist
    os.makedirs(SENTIMENT_OUTPUT_DIR, exist_ok=True)
    os.makedirs(VISUALIZATIONS_DIR, exist_ok=True)
    
    # Verify news data
    news_counts = count_news_articles()
    
    if not news_counts:
        print("Error: No news data available. Cannot proceed.")
        return
    
    # Run sentiment analysis processing
    if not args.skip_processing:
        cmd = ["python", "src/process_news.py", "--summary"]
        if args.ticker:
            cmd.extend(["--ticker", args.ticker])
        run_command(cmd, "Processing News with FinBERT")
    else:
        print("\nSkipping processing step. Using existing results.")
    
    # Verify sentiment results
    sentiment_stats = verify_sentiment_results()
    
    if not sentiment_stats:
        print("Error: No sentiment results available. Cannot proceed with visualization.")
        return
    
    # Run visualization
    if not args.skip_visualization:
        run_command(["python", "src/visualize_sentiment.py", "--all"], 
                    "Generating Visualizations")
    else:
        print("\nSkipping visualization step.")
    
    # Verify visualizations
    visualizations = verify_visualizations()
    
    # Final summary
    header("VERIFICATION SUMMARY")
    
    print(f"News articles processed: {sum(news_counts.values()):,}")
    print(f"Tickers analyzed: {len(news_counts)}")
    
    if sentiment_stats:
        print(f"Sentiment records created: {sentiment_stats['record_count']:,}")
        print(f"Visualizations generated: {len(visualizations)}")
    
    print("\nVerification complete. You can find:")
    print(f"1. News data: {NEWS_DIR}")
    print(f"2. Sentiment results: {SENTIMENT_OUTPUT_DIR}")
    print(f"3. Visualizations: {VISUALIZATIONS_DIR}")
    print()
    print("To view specific sentiment results, run:")
    print(f"  less {SENTIMENT_CSV}")
    print()
    print("To explore additional visualizations, run:")
    print("  python src/visualize_sentiment.py --help")


if __name__ == "__main__":
    main()