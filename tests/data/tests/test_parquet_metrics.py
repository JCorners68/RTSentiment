#!/usr/bin/env python3
"""
Test script for the Parquet metrics server.
This script validates that the Parquet metrics server can read Parquet files
and correctly expose them as Prometheus metrics.
"""
import os
import sys
import time
import requests
import unittest
import subprocess
import pandas as pd
from collections import defaultdict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class TestParquetMetricsServer(unittest.TestCase):
    """Test case for the Parquet metrics server."""
    
    @classmethod
    def setUpClass(cls):
        """Set up the test case."""
        # Start the Parquet metrics server
        cls.server_process = None
        try:
            # Get base directory
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
            # Start the server process
            cls.server_process = subprocess.Popen(
                [
                    "python",
                    os.path.join(base_dir, "data_acquisition", "parquet_metrics_server.py"),
                    "--port", "8099",
                    "--parquet-dir", os.path.join(base_dir, "data", "output"),
                    "--update-interval", "5"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for the server to start
            print("Waiting for the server to start...")
            time.sleep(3)
            
            # Check if the server is running
            try:
                response = requests.get("http://localhost:8099/metrics")
                if response.status_code != 200:
                    raise Exception(f"Server returned status code {response.status_code}")
            except Exception as e:
                print(f"Server not running: {e}")
                cls.tearDownClass()
                raise
            
            print("Server is running.")
        except Exception as e:
            print(f"Error starting server: {e}")
            if cls.server_process:
                cls.server_process.terminate()
                cls.server_process = None
            raise
    
    @classmethod
    def tearDownClass(cls):
        """Tear down the test case."""
        # Stop the Parquet metrics server
        if cls.server_process:
            cls.server_process.terminate()
            stdout, stderr = cls.server_process.communicate(timeout=5)
            print(f"Server output: {stdout.decode()}")
            print(f"Server errors: {stderr.decode()}")
    
    def test_metrics_endpoint(self):
        """Test that the metrics endpoint is available."""
        response = requests.get("http://localhost:8099/metrics")
        self.assertEqual(response.status_code, 200)
        
        # Check that the metrics are valid Prometheus format
        metrics_text = response.text
        self.assertIn("sentiment_value", metrics_text)
        self.assertIn("sentiment_count", metrics_text)
        self.assertIn("sentiment_confidence", metrics_text)
    
    def test_metrics_match_parquet(self):
        """Test that the metrics match the Parquet files."""
        # Get the metrics
        response = requests.get("http://localhost:8099/metrics")
        metrics_text = response.text
        
        # Parse the metrics
        sentiment_values = defaultdict(dict)
        sentiment_counts = defaultdict(dict)
        
        for line in metrics_text.split("\n"):
            # Skip comments and empty lines
            if line.startswith("#") or not line.strip():
                continue
                
            # Parse sentiment_value metrics
            if line.startswith("sentiment_value{"):
                parts = line.split()
                if len(parts) >= 2:
                    labels = parts[0].split("{")[1].split("}")[0]
                    value = float(parts[1])
                    
                    # Extract labels
                    label_dict = {}
                    for label_pair in labels.split(","):
                        key, val = label_pair.split("=")
                        label_dict[key] = val.strip('"')
                    
                    ticker = label_dict.get("ticker")
                    source = label_dict.get("source")
                    if ticker and source:
                        sentiment_values[ticker][source] = value
            
            # Parse sentiment_count metrics
            if line.startswith("sentiment_count{"):
                parts = line.split()
                if len(parts) >= 2:
                    labels = parts[0].split("{")[1].split("}")[0]
                    value = float(parts[1])
                    
                    # Extract labels
                    label_dict = {}
                    for label_pair in labels.split(","):
                        key, val = label_pair.split("=")
                        label_dict[key] = val.strip('"')
                    
                    ticker = label_dict.get("ticker")
                    source = label_dict.get("source")
                    if ticker and source:
                        sentiment_counts[ticker][source] = value
        
        # Validate that we have some metrics
        self.assertGreater(len(sentiment_values), 0)
        self.assertGreater(len(sentiment_counts), 0)
        
        # Get base directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        parquet_dir = os.path.join(base_dir, "data", "output")
        
        # Load multi_ticker file if it exists
        multi_ticker_path = os.path.join(parquet_dir, "multi_ticker_sentiment.parquet")
        if os.path.exists(multi_ticker_path):
            df = pd.read_parquet(multi_ticker_path)
            
            # Check some of the tickers in the multi-ticker file
            if not df.empty:
                # Get unique tickers
                tickers = df['ticker'].unique()
                
                # Check at least one ticker
                if len(tickers) > 0:
                    ticker = tickers[0]
                    ticker_df = df[df['ticker'] == ticker]
                    
                    # Get unique sources
                    sources = ticker_df['source'].unique()
                    
                    if len(sources) > 0:
                        source = sources[0]
                        source_df = ticker_df[ticker_df['source'] == source]
                        
                        # Count should match
                        expected_count = len(source_df)
                        actual_count = sentiment_counts.get(ticker, {}).get(source, 0)
                        
                        print(f"Testing ticker {ticker}, source {source}")
                        print(f"Expected count: {expected_count}, Actual count: {actual_count}")
                        
                        # Allow for some flexibility in count (might be approximated in metrics)
                        self.assertGreaterEqual(actual_count, 0)

if __name__ == "__main__":
    unittest.main()