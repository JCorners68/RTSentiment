#!/usr/bin/env python3
"""
News Viewer CLI Tool

This script provides a command-line interface to view the news articles collected 
from the Finnhub API and stored in CSV files. It also supports viewing sentiment analysis results.
"""

import os
import sys
import csv
import argparse
import pandas as pd
from datetime import datetime
from tabulate import tabulate


# Configuration
DATA_DIR = "/home/jonat/real_senti/data/finnhub_poc"
NEWS_DIR = os.path.join(DATA_DIR, "news")
SENTIMENT_DIR = "/home/jonat/real_senti/data/sentiment_results"


def list_available_tickers():
    """List all tickers that have news data."""
    if not os.path.exists(NEWS_DIR):
        print(f"News directory not found: {NEWS_DIR}")
        return
    
    tickers = []
    for filename in os.listdir(NEWS_DIR):
        if filename.endswith("_news.csv"):
            ticker = filename.split("_")[0]
            tickers.append(ticker)
    
    return sorted(tickers)


def count_total_news_items():
    """Count the total number of news items across all tickers."""
    if not os.path.exists(NEWS_DIR):
        print(f"News directory not found: {NEWS_DIR}")
        return 0
    
    total_count = 0
    for ticker in list_available_tickers():
        file_path = os.path.join(NEWS_DIR, f"{ticker}_news.csv")
        with open(file_path, 'r') as f:
            reader = csv.reader(f)
            # Subtract 1 for the header row
            rows = sum(1 for row in reader) - 1
            total_count += rows
    
    return total_count


def view_news_for_ticker(ticker, limit=10, full=False):
    """View news for a specific ticker."""
    file_path = os.path.join(NEWS_DIR, f"{ticker}_news.csv")
    
    if not os.path.exists(file_path):
        print(f"No news found for ticker: {ticker}")
        return
    
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        
        # Limit the number of rows to display
        if limit > 0:
            df = df.head(limit)
        
        # Select columns to display
        if full:
            display_cols = df.columns
        else:
            display_cols = ['headline', 'datetime', 'source', 'category']
        
        # Display the news items
        print(f"\nShowing news for {ticker} ({len(df)} items):\n")
        
        # Format the table
        if full:
            print(tabulate(df[display_cols], headers='keys', tablefmt='psql', showindex=False))
        else:
            # For compact view, limit headline length
            df_display = df[display_cols].copy()
            df_display['headline'] = df_display['headline'].str.slice(0, 80) + '...'
            print(tabulate(df_display, headers='keys', tablefmt='psql', showindex=False))
        
    except Exception as e:
        print(f"Error reading news for {ticker}: {e}")


def view_all_news_summary():
    """View a summary of all collected news."""
    tickers = list_available_tickers()
    
    if not tickers:
        print("No news data found.")
        return
    
    summary = []
    total_items = 0
    
    for ticker in tickers:
        file_path = os.path.join(NEWS_DIR, f"{ticker}_news.csv")
        try:
            df = pd.read_csv(file_path)
            news_count = len(df)
            total_items += news_count
            
            # Get some statistics about the data
            oldest_date = df['datetime'].min() if 'datetime' in df.columns else "N/A"
            newest_date = df['datetime'].max() if 'datetime' in df.columns else "N/A"
            
            summary.append({
                'Ticker': ticker,
                'News Count': news_count,
                'Oldest': oldest_date,
                'Newest': newest_date
            })
        except Exception as e:
            summary.append({
                'Ticker': ticker,
                'News Count': "Error",
                'Oldest': "N/A",
                'Newest': "N/A"
            })
    
    # Create a DataFrame for better display
    summary_df = pd.DataFrame(summary)
    print("\nNews Collection Summary:\n")
    print(tabulate(summary_df, headers='keys', tablefmt='psql', showindex=False))
    print(f"\nTotal news items collected: {total_items}")


def view_sentiment_results(ticker=None):
    """View sentiment analysis results."""
    
    # Check if sentiment results directory exists
    if not os.path.exists(SENTIMENT_DIR):
        print(f"Sentiment results directory not found: {SENTIMENT_DIR}")
        return
    
    # Main sentiment results file
    sentiment_file = os.path.join(SENTIMENT_DIR, "sentiment_analysis.csv")
    if not os.path.exists(sentiment_file):
        print(f"Sentiment analysis results file not found: {sentiment_file}")
        return
    
    try:
        # Load sentiment data
        df = pd.read_csv(sentiment_file)
        
        if ticker:
            # Filter by ticker if specified
            df = df[df['ticker'] == ticker]
            if df.empty:
                print(f"No sentiment results found for ticker: {ticker}")
                return
                
            print(f"\nSentiment Analysis Results for {ticker} ({len(df)} articles):\n")
            
            # Display sentiment distribution
            sentiment_counts = df['sentiment_label'].value_counts()
            distribution = []
            for label, count in sentiment_counts.items():
                percentage = (count / len(df)) * 100
                distribution.append({'Sentiment': label, 'Count': count, 'Percentage': f"{percentage:.1f}%"})
            
            print("Sentiment Distribution:")
            print(tabulate(pd.DataFrame(distribution), headers='keys', tablefmt='psql', showindex=False))
            
            # Display average sentiment score
            avg_score = df['sentiment_score'].mean()
            print(f"\nAverage Sentiment Score: {avg_score:.4f}")
            
            # Display some example headlines with their sentiment
            print("\nSample Articles with Sentiment:")
            sample_df = df.sample(min(5, len(df)))
            samples = []
            for _, row in sample_df.iterrows():
                headline = row['headline']
                if len(headline) > 80:
                    headline = headline[:77] + '...'
                samples.append({
                    'Headline': headline,
                    'Sentiment': row['sentiment_label'],
                    'Score': f"{row['sentiment_score']:.2f}"
                })
            print(tabulate(pd.DataFrame(samples), headers='keys', tablefmt='psql', showindex=False))
            
        else:
            # Show overall sentiment summary
            print("\nOverall Sentiment Analysis Results:\n")
            
            # Display overall sentiment distribution
            sentiment_counts = df['sentiment_label'].value_counts()
            distribution = []
            for label, count in sentiment_counts.items():
                percentage = (count / len(df)) * 100
                distribution.append({'Sentiment': label, 'Count': count, 'Percentage': f"{percentage:.1f}%"})
            
            print("Overall Sentiment Distribution:")
            print(tabulate(pd.DataFrame(distribution), headers='keys', tablefmt='psql', showindex=False))
            
            # Display sentiment by ticker
            ticker_sentiment = df.groupby('ticker').agg({
                'sentiment_score': ['mean', 'count'],
                'sentiment_label': lambda x: x.value_counts().idxmax()
            })
            ticker_sentiment.columns = ['Avg_Score', 'Count', 'Dominant_Sentiment']
            ticker_sentiment = ticker_sentiment.reset_index()
            
            ticker_sentiment['Avg_Score'] = ticker_sentiment['Avg_Score'].round(4)
            ticker_data = ticker_sentiment.sort_values('Count', ascending=False)
            
            print("\nSentiment by Ticker:")
            print(tabulate(ticker_data, 
                           headers=['Ticker', 'Avg Score', 'Articles', 'Dominant Sentiment'],
                           tablefmt='psql', showindex=False))
            
    except Exception as e:
        print(f"Error viewing sentiment results: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='View financial news and sentiment analysis results.')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List tickers command
    list_parser = subparsers.add_parser('list', help='List available tickers with news data')
    
    # View news command
    view_parser = subparsers.add_parser('view', help='View news for a specific ticker')
    view_parser.add_argument('ticker', help='Ticker symbol (e.g., AAPL)')
    view_parser.add_argument('--limit', type=int, default=10, 
                             help='Maximum number of news items to display (0 for all)')
    view_parser.add_argument('--full', action='store_true', 
                             help='Show full news details instead of summary')
    
    # Summary command
    summary_parser = subparsers.add_parser('summary', help='Display a summary of all collected news')
    
    # Count command
    count_parser = subparsers.add_parser('count', help='Count total news items')
    
    # Sentiment command
    sentiment_parser = subparsers.add_parser('sentiment', help='View sentiment analysis results')
    sentiment_parser.add_argument('--ticker', help='Ticker symbol to view sentiment for (e.g., AAPL)')
    
    args = parser.parse_args()
    
    if args.command == 'list':
        tickers = list_available_tickers()
        if tickers:
            print("\nAvailable tickers with news data:")
            for ticker in tickers:
                print(f"  - {ticker}")
            print(f"\nTotal tickers: {len(tickers)}")
        else:
            print("No news data found.")
    
    elif args.command == 'view':
        view_news_for_ticker(args.ticker, args.limit, args.full)
    
    elif args.command == 'summary':
        view_all_news_summary()
    
    elif args.command == 'count':
        total = count_total_news_items()
        print(f"Total news items collected: {total}")
    
    elif args.command == 'sentiment':
        view_sentiment_results(args.ticker)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()