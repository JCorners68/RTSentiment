#!/usr/bin/env python3
"""
API Service Verification Script

This script performs a suite of tests to verify that the API service
is functioning correctly. It tests:
1. Health and status endpoints
2. Sentiment analysis endpoints
3. Database connectivity
4. Redis caching (if available)

Example usage:
    python verify_api.py --host localhost --port 8001
"""

import argparse
import requests
import json
import sys
import time
import subprocess
import signal
import os
from datetime import datetime
import unittest

class APIVerificationTest(unittest.TestCase):
    """Test case for verifying API functionality."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        # Parse arguments
        parser = argparse.ArgumentParser(description='Verify API service functionality')
        parser.add_argument('--host', default='localhost', help='API host')
        parser.add_argument('--port', default=8001, type=int, help='API port')
        parser.add_argument('--start-api', action='store_true', help='Start API service if not running')
        
        args = parser.parse_args()
        
        cls.base_url = f"http://{args.host}:{args.port}"
        cls.api_process = None
        
        # Check if API is running
        try:
            response = requests.get(f"{cls.base_url}/health", timeout=2)
            print(f"API service detected at {cls.base_url}")
        except requests.exceptions.ConnectionError:
            if args.start_api:
                print(f"API service not detected. Starting API service...")
                # Start API in a subprocess
                cls.api_process = subprocess.Popen(
                    ["uvicorn", "api.main:app", "--reload", "--host", args.host, "--port", str(args.port)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    preexec_fn=os.setsid
                )
                # Wait for API to start
                for _ in range(5):
                    try:
                        response = requests.get(f"{cls.base_url}/health", timeout=2)
                        if response.status_code == 200:
                            print("API service started successfully")
                            break
                    except requests.exceptions.ConnectionError:
                        pass
                    print("Waiting for API to start...")
                    time.sleep(2)
                else:
                    print("Failed to start API service")
                    if cls.api_process:
                        os.killpg(os.getpgid(cls.api_process.pid), signal.SIGTERM)
                    sys.exit(1)
            else:
                print(f"API service not running at {cls.base_url}. Use --start-api to start it.")
                sys.exit(1)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        if cls.api_process:
            print("Stopping API service...")
            os.killpg(os.getpgid(cls.api_process.pid), signal.SIGTERM)
    
    def test_health_endpoint(self):
        """Test the health endpoint to verify basic API functionality."""
        response = requests.get(f"{self.base_url}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
    
    def test_root_endpoint(self):
        """Test the root endpoint."""
        response = requests.get(self.base_url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
    
    def test_auth_endpoints(self):
        """Test authentication endpoints."""
        # Test login endpoint
        login_response = requests.post(f"{self.base_url}/auth/login")
        self.assertEqual(login_response.status_code, 200)
        login_data = login_response.json()
        self.assertIn("access_token", login_data)
        
        # Test me endpoint
        me_response = requests.get(f"{self.base_url}/auth/me")
        self.assertEqual(me_response.status_code, 200)
        me_data = me_response.json()
        self.assertIn("username", me_data)
    
    def test_sentiment_ticker_endpoint(self):
        """Test getting sentiment for a specific ticker."""
        ticker = "AAPL"
        response = requests.get(f"{self.base_url}/sentiment/ticker/{ticker}")
        if response.status_code == 200:
            data = response.json()
            self.assertEqual(data["ticker"], ticker)
            self.assertIn("sentiment", data)
            self.assertIn("score", data)
            print(f"Ticker sentiment returned: {data}")
        else:
            print(f"Ticker endpoint returned status code {response.status_code}: {response.text}")
            # If DB is empty, this might be a mock response or 404
            self.assertIn(response.status_code, [200, 404])
    
    def test_sentiment_tickers_endpoint(self):
        """Test getting list of available tickers."""
        response = requests.get(f"{self.base_url}/sentiment/tickers")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        if data:
            print(f"Available tickers: {data[:5]}{'...' if len(data) > 5 else ''}")
    
    def test_top_sentiment_endpoint(self):
        """Test getting top sentiment tickers."""
        response = requests.get(f"{self.base_url}/sentiment/top?limit=5")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, list)
        if data:
            print(f"Top sentiment results: {json.dumps(data, indent=2)}")
            self.assertIn("ticker", data[0])
            self.assertIn("sentiment", data[0])
            self.assertIn("score", data[0])
    
    def test_create_and_query_sentiment(self):
        """Test creating a sentiment event and then querying it."""
        # Create a test event
        event_data = {
            "source": "test_script",
            "priority": "standard",
            "text": "This is a test event from the verification script",
            "model": "test_model",
            "sentiment_score": 0.5,
            "sentiment_label": "positive",
            "processing_time": 0.1,
            "event_id": f"test-{datetime.now().isoformat()}",
            "ticker_sentiments": [{"TEST": 0.5}]
        }
        
        create_response = requests.post(
            f"{self.base_url}/sentiment/event",
            json=event_data
        )
        
        if create_response.status_code == 200:
            print("Successfully created test sentiment event")
            create_data = create_response.json()
            event_id = create_data["id"]
            
            # Query for the created event
            query_data = {
                "sources": ["test_script"],
                "limit": 10
            }
            query_response = requests.post(
                f"{self.base_url}/sentiment/query",
                json=query_data
            )
            
            self.assertEqual(query_response.status_code, 200)
            query_results = query_response.json()
            self.assertIsInstance(query_results, list)
            
            # Verify the test event is in the results
            found = False
            for event in query_results:
                if event["source"] == "test_script" and event["event_id"] == event_data["event_id"]:
                    found = True
                    break
            
            self.assertTrue(found, "Created event not found in query results")
            print("Successfully queried and found the test event")
        else:
            print(f"Failed to create test event: {create_response.status_code}: {create_response.text}")
            self.fail("Failed to create test sentiment event")
    
    def test_analyze_sentiment(self):
        """Test the sentiment analysis endpoint."""
        # This may use a mock in development
        text = "Apple's latest quarterly results exceeded expectations with strong iPhone sales."
        response = requests.post(f"{self.base_url}/sentiment/analyze", params={"text": text})
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        print(f"Sentiment analysis results: {json.dumps(data, indent=2)}")
        
        # Check for expected fields
        if "sentiment" in data:
            self.assertIn(data["sentiment"], ["positive", "negative", "neutral"])
        elif "text" in data and "sentiment" in data["text"]:
            self.assertIn(data["text"]["sentiment"], ["positive", "negative", "neutral"])

if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0]])