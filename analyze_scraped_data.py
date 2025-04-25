#!/usr/bin/env python3
"""
Script to analyze scraped data from 2023 and produce monthly summaries.
"""
import os
import json
import glob
from collections import defaultdict
from datetime import datetime

def get_month_year(date_str):
    """Extract month and year from date string."""
    try:
        # Try various date formats that might be in the data
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",  # ISO format with Z
            "%Y-%m-%d %H:%M:%S",    # Standard datetime
            "%Y-%m-%d"              # Just date
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m")
            except ValueError:
                continue
        
        # If we can't parse, use the first 7 chars if it looks like YYYY-MM
        if len(date_str) >= 7 and date_str[4] == '-':
            return date_str[:7]
        
        return "Unknown"
    except:
        return "Unknown"

def analyze_file(file_path):
    """Analyze a single JSON file of scraped data."""
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    source_type = "news" if "news" in os.path.basename(file_path) else "reddit"
    
    # Count by month
    monthly_counts = defaultdict(int)
    for item in data:
        # Get date field based on source
        if source_type == "news":
            date_field = item.get("published_at", "")
        else:  # reddit
            date_field = item.get("created_utc", "")
        
        month_year = get_month_year(date_field)
        monthly_counts[month_year] += 1
    
    return {
        "source": source_type,
        "total_items": len(data),
        "monthly_counts": dict(monthly_counts)
    }

def get_all_data_files():
    """Get all JSON data files in historical output and test results."""
    output_dir = os.path.join(os.getcwd(), "data", "output", "historical")
    test_dir = os.path.join(os.getcwd(), "tests", "test_results")
    
    files = []
    
    # Get files from output directory
    for file_path in glob.glob(os.path.join(output_dir, "*.json")):
        if "news_" in os.path.basename(file_path) or "reddit_" in os.path.basename(file_path):
            files.append(file_path)
    
    # Get files from test results directory
    for file_path in glob.glob(os.path.join(test_dir, "scrape_results_*.json")):
        files.append(file_path)
    
    return files

def analyze_deduplication():
    """Analyze deduplication hash files."""
    news_hash_path = os.path.join(os.getcwd(), "data", "cache", "deduplication", "news_hashes.json")
    reddit_hash_path = os.path.join(os.getcwd(), "data", "cache", "deduplication", "reddit_hashes.json")
    
    try:
        with open(news_hash_path, 'r') as f:
            news_hashes = json.load(f)
            news_hash_count = len(news_hashes)
    except Exception as e:
        print(f"Error reading news hash file: {e}")
        news_hash_count = 0
    
    try:
        with open(reddit_hash_path, 'r') as f:
            reddit_hashes = json.load(f)
            reddit_hash_count = len(reddit_hashes)
    except Exception as e:
        print(f"Error reading reddit hash file: {e}")
        reddit_hash_count = 0
    
    return {
        "news_hash_count": news_hash_count,
        "reddit_hash_count": reddit_hash_count
    }

def analyze_parquet_files():
    """Analyze Parquet files to understand ticker coverage."""
    output_dir = os.path.join(os.getcwd(), "data", "output")
    parquet_files = glob.glob(os.path.join(output_dir, "*.parquet"))
    
    # Extract ticker names from filenames
    tickers = set()
    for file_path in parquet_files:
        ticker = os.path.basename(file_path).replace("_sentiment.parquet", "")
        tickers.add(ticker)
    
    return {
        "total_parquet_files": len(parquet_files),
        "unique_tickers": len(tickers),
        "tickers": sorted(list(tickers))
    }

def main():
    """Main function to analyze scraped data."""
    # Get all data files
    data_files = get_all_data_files()
    
    # Process each file
    results = []
    for file_path in data_files:
        try:
            result = analyze_file(file_path)
            results.append(result)
            print(f"Processed {file_path}: {result['total_items']} items")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    # Combine results by source and month
    news_by_month = defaultdict(int)
    reddit_by_month = defaultdict(int)
    total_news = 0
    total_reddit = 0
    
    for result in results:
        if result["source"] == "news":
            total_news += result["total_items"]
            for month, count in result["monthly_counts"].items():
                news_by_month[month] += count
        else:  # reddit
            total_reddit += result["total_items"]
            for month, count in result["monthly_counts"].items():
                reddit_by_month[month] += count
    
    # Analyze deduplication
    dedup_stats = analyze_deduplication()
    
    # Analyze Parquet files
    parquet_stats = analyze_parquet_files()
    
    # Create summary report
    report = ["# Scraped Data Analysis Report", ""]
    report.append("## Summary")
    report.append(f"- Total News Articles: {total_news}")
    report.append(f"- Total Reddit Posts: {total_reddit}")
    report.append(f"- Total Items: {total_news + total_reddit}")
    report.append("")
    
    # Add deduplication information
    report.append("## Deduplication Analysis")
    report.append(f"- News Hash Entries: {dedup_stats['news_hash_count']}")
    report.append(f"- Reddit Hash Entries: {dedup_stats['reddit_hash_count']}")
    
    if total_news > 0 and dedup_stats['news_hash_count'] > 0:
        dedup_rate_news = ((total_news - dedup_stats['news_hash_count']) / total_news) * 100
        report.append(f"- News Deduplication Rate: {dedup_rate_news:.1f}%")
    
    if total_reddit > 0 and dedup_stats['reddit_hash_count'] > 0:
        dedup_rate_reddit = ((total_reddit - dedup_stats['reddit_hash_count']) / total_reddit) * 100
        report.append(f"- Reddit Deduplication Rate: {dedup_rate_reddit:.1f}%")
    
    report.append("")
    
    # Add Parquet file information
    report.append("## Parquet Storage Analysis")
    report.append(f"- Total Parquet Files: {parquet_stats['total_parquet_files']}")
    report.append(f"- Unique Tickers/Terms: {parquet_stats['unique_tickers']}")
    report.append("")
    
    # Top 20 tickers (to keep the report manageable)
    report.append("### Top 20 Tickers/Terms")
    for ticker in parquet_stats['tickers'][:20]:
        report.append(f"- {ticker}")
    report.append("")
    
    report.append("## Monthly Breakdown")
    report.append("")
    report.append("| Month | News Articles | Reddit Posts | Total |")
    report.append("|-------|--------------|--------------|-------|")
    
    # Get all months and sort them
    all_months = sorted(set(list(news_by_month.keys()) + list(reddit_by_month.keys())))
    
    # Create monthly rows
    for month in all_months:
        news_count = news_by_month[month]
        reddit_count = reddit_by_month[month]
        total = news_count + reddit_count
        report.append(f"| {month} | {news_count} | {reddit_count} | {total} |")
    
    # Add monthly averages
    total_months = len(all_months) or 1  # Avoid division by zero
    report.append("|-------|--------------|--------------|-------|")
    report.append(f"| Average | {total_news / total_months:.1f} | {total_reddit / total_months:.1f} | {(total_news + total_reddit) / total_months:.1f} |")
    
    # Write report to file
    report_path = os.path.join(os.getcwd(), "scraped_data_report.md")
    with open(report_path, 'w') as f:
        f.write("\n".join(report))
    
    print(f"\nReport saved to {report_path}")

if __name__ == "__main__":
    main()