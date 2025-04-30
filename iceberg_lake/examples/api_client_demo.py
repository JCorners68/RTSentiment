#!/usr/bin/env python3
"""
Demo script for using the Sentiment Analysis API.

This script demonstrates how to use the API endpoints to access the Dremio-based
sentiment data.
"""
import requests
import json
import sys

def print_separator():
    """Print a separator line."""
    print("-" * 80)

def main():
    """Run the API client demo."""
    base_url = "http://localhost:8000"
    
    print("Sentiment Analysis API Client Demo")
    print_separator()
    
    # Test root endpoint
    print("1. Testing API information endpoint")
    response = requests.get(f"{base_url}/")
    if response.status_code == 200:
        print(f"API Info: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Error accessing API: {response.status_code}")
        return
    print_separator()
    
    # Get top tickers
    print("2. Getting top tickers by volume")
    response = requests.get(f"{base_url}/sentiment/tickers", params={
        "days": 30,
        "limit": 5
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['count']} tickers:")
        
        # Exit if no tickers found
        if data['count'] == 0:
            print("No ticker data available. Exiting.")
            return
        
        # Display ticker data
        for ticker_data in data['data'][:5]:  # Show first 5
            print(f"  {ticker_data['ticker']}: {ticker_data['message_count']} messages, "
                  f"avg sentiment: {ticker_data.get('avg_sentiment', 'N/A')}")
        
        # Use first ticker for further tests
        first_ticker = data['data'][0]['ticker']
    else:
        print(f"Error getting top tickers: {response.status_code}")
        # Use default ticker
        first_ticker = "AAPL"
    print_separator()
    
    # Get sentiment for a specific ticker
    print(f"3. Getting sentiment data for {first_ticker}")
    response = requests.get(f"{base_url}/sentiment/timeseries", params={
        "ticker": first_ticker,
        "interval": "day",
        "days": 30
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['count']} sentiment records")
        
        # Show sample of records
        if data['count'] > 0:
            sample = data['data'][:2]  # Show first 2 records
            for idx, record in enumerate(sample):
                print(f"\nRecord {idx+1}:")
                for key, value in record.items():
                    if key not in ['emotion_intensity_vector', 'aspect_based_sentiment']:
                        print(f"  {key}: {value}")
                
                # Show emotion data if available
                if 'emotion_intensity_vector' in record and record['emotion_intensity_vector']:
                    print("  Emotions:")
                    for emotion, intensity in record['emotion_intensity_vector'].items():
                        print(f"    {emotion}: {intensity}")
    else:
        print(f"Error getting sentiment data: {response.status_code}")
    print_separator()
    
    # Get time series data
    print(f"4. Getting time series data for {first_ticker}")
    response = requests.get(f"{base_url}/sentiment/timeseries", params={
        "ticker": first_ticker,
        "interval": "day",
        "days": 30
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['count']} time series data points")
        
        # Show sample of time series
        if data['count'] > 0:
            print("\nTime series sample:")
            for point in data['data'][:3]:  # Show first 3 data points
                time_bucket = point.get('time_bucket', 'N/A')
                avg_sentiment = point.get('avg_sentiment', 'N/A')
                message_count = point.get('message_count', 'N/A')
                print(f"  {time_bucket}: avg={avg_sentiment}, count={message_count}")
    else:
        print(f"Error getting time series data: {response.status_code}")
    print_separator()
    
    # Get sources breakdown
    print("5. Getting sentiment by source")
    response = requests.get(f"{base_url}/sentiment/sources", params={
        "days": 30
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"Found {data['count']} source systems")
        
        # Show sources
        if data['count'] > 0:
            print("\nSources:")
            for source in data['data']:
                source_name = source.get('source_system', 'Unknown')
                message_count = source.get('message_count', 0)
                avg_sentiment = source.get('avg_sentiment', 'N/A')
                print(f"  {source_name}: {message_count} messages, avg sentiment: {avg_sentiment}")
    else:
        print(f"Error getting sources data: {response.status_code}")
    print_separator()
    
    print("API demo completed successfully!")

if __name__ == "__main__":
    main()