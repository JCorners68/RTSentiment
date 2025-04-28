#!/usr/bin/env python3
import pandas as pd
import pyarrow.parquet as pq
import matplotlib.pyplot as plt
import os

def analyze_sentiment(parquet_file, output_dir):
    """Analyze sentiment data from a parquet file."""
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read the parquet file
    table = pq.read_table(parquet_file)
    df = table.to_pandas()
    
    print(f'Loaded {len(df)} records from {parquet_file}')
    
    # Basic statistics
    print('\nBasic statistics:')
    print(f'Number of unique tickers: {df["ticker"].nunique()}')
    print(f'Number of unique sources: {df["source"].nunique()}')
    print(f'Date range: {df["timestamp"].min()} to {df["timestamp"].max()}')
    
    # Ticker distribution
    ticker_counts = df['ticker'].value_counts()
    top_tickers = ticker_counts.head(20)
    
    plt.figure(figsize=(12, 6))
    top_tickers.plot(kind='bar')
    plt.title('Top 20 Tickers by Frequency (Deduplicated)')
    plt.xlabel('Ticker')
    plt.ylabel('Count')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/clean_top_tickers.png')
    
    # Source distribution
    source_counts = df['source'].value_counts()
    
    plt.figure(figsize=(10, 5))
    source_counts.plot(kind='bar')
    plt.title('Data Sources (Deduplicated)')
    plt.xlabel('Source')
    plt.ylabel('Count')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/clean_sources.png')
    
    # Sentiment distribution
    plt.figure(figsize=(10, 5))
    df['sentiment'].hist(bins=20)
    plt.title('Sentiment Distribution (Deduplicated)')
    plt.xlabel('Sentiment Score')
    plt.ylabel('Frequency')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/clean_sentiment_distribution.png')
    
    # Top tickers by average sentiment
    ticker_sentiment = df.groupby('ticker')['sentiment'].agg(['mean', 'count'])
    ticker_sentiment = ticker_sentiment[ticker_sentiment['count'] > 4]  # Filter for tickers with >4 records
    ticker_sentiment = ticker_sentiment.sort_values('mean', ascending=False)
    
    plt.figure(figsize=(12, 6))
    ticker_sentiment['mean'].head(20).plot(kind='bar')
    plt.title('Top 20 Tickers by Positive Sentiment (Deduplicated)')
    plt.xlabel('Ticker')
    plt.ylabel('Average Sentiment')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/clean_top_positive_sentiment.png')
    
    plt.figure(figsize=(12, 6))
    ticker_sentiment['mean'].tail(20).iloc[::-1].plot(kind='bar')
    plt.title('Bottom 20 Tickers by Sentiment (Deduplicated)')
    plt.xlabel('Ticker')
    plt.ylabel('Average Sentiment')
    plt.tight_layout()
    plt.savefig(f'{output_dir}/clean_top_negative_sentiment.png')
    
    # Save reports to CSV
    top_tickers.to_csv(f'{output_dir}/clean_top_tickers.csv')
    ticker_sentiment.to_csv(f'{output_dir}/clean_ticker_sentiment.csv')
    
    # Generate summary stats
    print('\nDeduplication summary:')
    print(f'Total deduplicated records: {len(df)}')
    print(f'Total unique tickers: {df["ticker"].nunique()}')
    print(f'Articles with sentiment score = 0: {len(df[df["sentiment"] == 0])} ({len(df[df["sentiment"] == 0])/len(df)*100:.1f}%)')
    print(f'Articles with sentiment score > 0: {len(df[df["sentiment"] > 0])} ({len(df[df["sentiment"] > 0])/len(df)*100:.1f}%)')
    print(f'Articles with sentiment score < 0: {len(df[df["sentiment"] < 0])} ({len(df[df["sentiment"] < 0])/len(df)*100:.1f}%)')
    
    print(f'\nAnalysis complete. Reports saved to {output_dir}')

if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.abspath(__file__))
    parquet_file = os.path.join(base_dir, 'data/output/combined_recalculated/all_clean_sentiment.parquet')
    output_dir = '/tmp/clean_analysis'
    
    analyze_sentiment(parquet_file, output_dir)