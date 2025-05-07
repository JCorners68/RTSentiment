#!/usr/bin/env python3
"""
Finnhub POC Script

This script fetches data from Finnhub API and saves it to CSV files.
It demonstrates the core functionality of the Finnhub data source
without the Iceberg dependencies.
"""

import os
import sys
import json
import time
import uuid
import logging
import datetime
import csv
from typing import Dict, List, Any, Optional, Tuple

import finnhub

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FINNHUB_API_KEY, SP500_TICKERS, FINNHUB_RATE_LIMIT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Output directory for CSV files
OUTPUT_DIR = "/home/jonat/real_senti/data/finnhub_poc"


class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__(self, requests_per_minute: int):
        """Initialize rate limiter."""
        self.requests_per_minute = requests_per_minute
        self.interval = 60.0 / requests_per_minute
        self.last_request_time = 0.0
    
    def wait(self) -> None:
        """Wait if necessary to respect the rate limit."""
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if self.last_request_time > 0 and elapsed < self.interval:
            wait_time = self.interval - elapsed
            if wait_time > 0:
                logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
        
        self.last_request_time = time.time()


class FinnhubPOC:
    """Finnhub POC class for fetching and saving data."""
    
    def __init__(self, api_key: str):
        """Initialize with API key."""
        self.api_key = api_key
        self.client = finnhub.Client(api_key=api_key)
        self.rate_limiter = RateLimiter(FINNHUB_RATE_LIMIT)
        
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "news"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "sentiment"), exist_ok=True)
        os.makedirs(os.path.join(OUTPUT_DIR, "earnings"), exist_ok=True)
    
    def get_company_news(self, ticker: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """Get news for a company within a date range."""
        self.rate_limiter.wait()
        try:
            news = self.client.company_news(ticker, _from=from_date, to=to_date)
            logger.info(f"Retrieved {len(news)} news items for {ticker}")
            return news
        except Exception as e:
            logger.error(f"Error fetching news for {ticker}: {e}")
            return []
    
    def get_sentiment_data(self, ticker: str) -> Dict[str, Any]:
        """Get sentiment data for a ticker."""
        self.rate_limiter.wait()
        try:
            sentiment = self.client.news_sentiment(ticker)
            logger.info(f"Retrieved sentiment data for {ticker}")
            return sentiment
        except Exception as e:
            logger.error(f"Error fetching sentiment for {ticker}: {e}")
            return {}
    
    def get_earnings(self, ticker: str) -> List[Dict[str, Any]]:
        """Get earnings data for a ticker."""
        self.rate_limiter.wait()
        try:
            earnings = self.client.company_earnings(ticker)
            logger.info(f"Retrieved {len(earnings)} earnings reports for {ticker}")
            return earnings
        except Exception as e:
            logger.error(f"Error fetching earnings for {ticker}: {e}")
            return []
    
    def save_to_csv(self, data: List[Dict[str, Any]], file_path: str, headers: List[str]) -> None:
        """Save data to a CSV file."""
        try:
            with open(file_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
                for item in data:
                    # Only include fields that are in headers
                    row = {k: item.get(k, '') for k in headers}
                    writer.writerow(row)
            logger.info(f"Saved data to {file_path}")
        except Exception as e:
            logger.error(f"Error saving to {file_path}: {e}")
    
    def process_ticker(self, ticker: str, days: int = 30) -> Tuple[bool, Dict[str, int]]:
        """Process a ticker and save all data to CSV files."""
        try:
            # Calculate date range
            end_date = datetime.datetime.now().date()
            start_date = end_date - datetime.timedelta(days=days)
            from_date = start_date.strftime('%Y-%m-%d')
            to_date = end_date.strftime('%Y-%m-%d')
            
            # Get company news
            news = self.get_company_news(ticker, from_date, to_date)
            news_file = os.path.join(OUTPUT_DIR, "news", f"{ticker}_news.csv")
            news_headers = ['category', 'datetime', 'headline', 'id', 'image', 'related', 'source', 'summary', 'url']
            self.save_to_csv(news, news_file, news_headers)
            
            # Get sentiment data
            sentiment = self.get_sentiment_data(ticker)
            sentiment_file = os.path.join(OUTPUT_DIR, "sentiment", f"{ticker}_sentiment.csv")
            
            # Convert sentiment dict to list for CSV
            sentiment_list = []
            if sentiment and 'buzz' in sentiment:
                sentiment_list.append({
                    'ticker': ticker,
                    'timestamp': datetime.datetime.now().isoformat(),
                    'buzz_articles_in_last_week': sentiment.get('buzz', {}).get('articlesInLastWeek', 0),
                    'buzz_buzz': sentiment.get('buzz', {}).get('buzz', 0),
                    'buzz_weekly_average': sentiment.get('buzz', {}).get('weeklyAverage', 0),
                    'company_news_score': sentiment.get('companyNewsScore', 0),
                    'sector_average_bullish_percent': sentiment.get('sectorAverageBullishPercent', 0),
                    'sector_average_news_score': sentiment.get('sectorAverageNewsScore', 0),
                    'sentiment_bearish_percent': sentiment.get('sentiment', {}).get('bearishPercent', 0),
                    'sentiment_bullish_percent': sentiment.get('sentiment', {}).get('bullishPercent', 0)
                })
            sentiment_headers = [
                'ticker', 'timestamp', 'buzz_articles_in_last_week', 'buzz_buzz', 
                'buzz_weekly_average', 'company_news_score', 'sector_average_bullish_percent',
                'sector_average_news_score', 'sentiment_bearish_percent', 'sentiment_bullish_percent'
            ]
            self.save_to_csv(sentiment_list, sentiment_file, sentiment_headers)
            
            # Get earnings data
            earnings = self.get_earnings(ticker)
            earnings_file = os.path.join(OUTPUT_DIR, "earnings", f"{ticker}_earnings.csv")
            earnings_headers = ['actual', 'estimate', 'period', 'quarter', 'surprise', 'surprisePercent', 'symbol', 'year']
            self.save_to_csv(earnings, earnings_file, earnings_headers)
            
            # Return counts
            counts = {
                'news_items': len(news),
                'sentiment_records': len(sentiment_list),
                'earnings_items': len(earnings)
            }
            
            return True, counts
        
        except Exception as e:
            logger.error(f"Error processing ticker {ticker}: {e}")
            return False, {'news_items': 0, 'sentiment_records': 0, 'earnings_items': 0}


def main():
    """Main function to run the POC."""
    api_key = FINNHUB_API_KEY
    
    if api_key == "your_finnhub_api_key_here":
        logger.error("Please set your Finnhub API key in config.py")
        sys.exit(1)
    
    # Initialize FinnhubPOC
    finnhub_poc = FinnhubPOC(api_key)
    
    # Get tickers to process
    tickers = SP500_TICKERS[:5]  # Limit to 5 tickers for the POC
    
    logger.info(f"Processing {len(tickers)} tickers: {', '.join(tickers)}")
    
    # Process each ticker
    results = {
        'success_count': 0,
        'failure_count': 0,
        'total_news': 0,
        'total_sentiment': 0,
        'total_earnings': 0
    }
    
    start_time = time.time()
    
    for ticker in tickers:
        logger.info(f"Processing {ticker}...")
        success, counts = finnhub_poc.process_ticker(ticker, days=7)
        
        if success:
            results['success_count'] += 1
            results['total_news'] += counts['news_items']
            results['total_sentiment'] += counts['sentiment_records']
            results['total_earnings'] += counts['earnings_items']
        else:
            results['failure_count'] += 1
    
    duration = time.time() - start_time
    
    # Display summary
    logger.info("\nSummary:")
    logger.info(f"Processed {len(tickers)} tickers in {duration:.2f} seconds")
    logger.info(f"Successful: {results['success_count']}")
    logger.info(f"Failed: {results['failure_count']}")
    logger.info(f"Total news items: {results['total_news']}")
    logger.info(f"Total sentiment records: {results['total_sentiment']}")
    logger.info(f"Total earnings reports: {results['total_earnings']}")
    logger.info(f"Data saved to: {OUTPUT_DIR}")
    
    return results


if __name__ == "__main__":
    main()