#!/usr/bin/env python3
"""
End-to-End Test Script

This script verifies that the entire sentiment analysis system is working
correctly by testing the flow from data ingestion through processing to API access.

Example usage:
    python end_to_end_test.py --api-host localhost --api-port 8001
"""

import argparse
import json
import requests
import time
import asyncio
import websockets
import uuid
from datetime import datetime

class EndToEndTest:
    """End-to-end test for the sentiment analysis system."""
    
    def __init__(self, api_url, websocket_url=None):
        """Initialize with API URL."""
        self.api_url = api_url
        self.websocket_url = websocket_url
        self.test_results = {
            "api_tests": {},
            "websocket_tests": {},
            "end_to_end_tests": {}
        }
    
    def run_all_tests(self):
        """Run all tests and return results."""
        print("Starting end-to-end tests for the sentiment analysis system")
        
        # Run API health tests
        self.test_api_health()
        
        # Run sentiment creation and retrieval tests
        self.test_sentiment_creation()
        
        # Run WebSocket tests if URL provided
        if self.websocket_url:
            asyncio.run(self.test_websockets())
        
        # Run complete end-to-end test with data flow validation
        self.test_full_data_flow()
        
        # Print test summary
        self.print_summary()
        
        return self.test_results
    
    def test_api_health(self):
        """Test API health endpoints."""
        print("\n=== Testing API Health ===")
        
        try:
            # Check API root endpoint
            print("Testing API root endpoint...")
            response = requests.get(self.api_url)
            root_status = response.status_code == 200
            self.test_results["api_tests"]["root_endpoint"] = {
                "status": "PASS" if root_status else "FAIL",
                "details": response.json() if root_status else str(response)
            }
            print(f"  API root endpoint: {'✅ PASS' if root_status else '❌ FAIL'}")
            
            # Check API health endpoint
            print("Testing API health endpoint...")
            response = requests.get(f"{self.api_url}/health")
            health_status = response.status_code == 200
            status_healthy = health_status and response.json().get("status") == "healthy"
            self.test_results["api_tests"]["health_endpoint"] = {
                "status": "PASS" if status_healthy else "FAIL",
                "details": response.json() if health_status else str(response)
            }
            print(f"  API health endpoint: {'✅ PASS' if status_healthy else '❌ FAIL'}")
            
        except Exception as e:
            self.test_results["api_tests"]["connection_error"] = {
                "status": "FAIL",
                "details": str(e)
            }
            print(f"  ❌ FAIL: Could not connect to API: {e}")
    
    def test_sentiment_creation(self):
        """Test sentiment creation and retrieval."""
        print("\n=== Testing Sentiment Creation and Retrieval ===")
        
        # Create a unique test event
        test_id = str(uuid.uuid4())
        test_ticker = "TEST"
        test_score = 0.85
        
        event_data = {
            "source": "e2e_test",
            "priority": "high",
            "text": f"This is an end-to-end test message with ID {test_id}",
            "model": "test_model",
            "sentiment_score": test_score,
            "sentiment_label": "positive",
            "processing_time": 0.05,
            "event_id": f"e2e-test-{test_id}",
            "ticker_sentiments": [{test_ticker: test_score}]
        }
        
        try:
            # Create sentiment event
            print("Creating test sentiment event...")
            response = requests.post(f"{self.api_url}/sentiment/event", json=event_data)
            creation_status = response.status_code == 200
            
            if creation_status:
                created_event = response.json()
                event_id = created_event.get("id")
                self.test_results["api_tests"]["create_sentiment"] = {
                    "status": "PASS",
                    "details": {"event_id": event_id, "ticker": test_ticker}
                }
                print(f"  ✅ PASS: Created sentiment event with ID {event_id}")
                
                # Wait for event processing to complete
                print("Waiting for event processing...")
                time.sleep(2)
                
                # Query for the created event
                print("Querying for event...")
                query_data = {
                    "sources": ["e2e_test"],
                    "limit": 10
                }
                
                response = requests.post(f"{self.api_url}/sentiment/query", json=query_data)
                query_status = response.status_code == 200
                
                if query_status:
                    events = response.json()
                    found_event = None
                    for event in events:
                        if event.get("event_id") == event_data["event_id"]:
                            found_event = event
                            break
                    
                    if found_event:
                        self.test_results["api_tests"]["query_sentiment"] = {
                            "status": "PASS",
                            "details": {"found_event": found_event}
                        }
                        print(f"  ✅ PASS: Found created event in query results")
                    else:
                        self.test_results["api_tests"]["query_sentiment"] = {
                            "status": "FAIL",
                            "details": "Created event not found in query results"
                        }
                        print(f"  ❌ FAIL: Created event not found in query results")
                else:
                    self.test_results["api_tests"]["query_sentiment"] = {
                        "status": "FAIL",
                        "details": str(response.text)
                    }
                    print(f"  ❌ FAIL: Query API call failed: {response.status_code}")
                
                # Get ticker sentiment
                print(f"Getting sentiment for ticker {test_ticker}...")
                response = requests.get(f"{self.api_url}/sentiment/ticker/{test_ticker}")
                ticker_status = response.status_code == 200
                
                if ticker_status:
                    ticker_data = response.json()
                    if ticker_data.get("ticker") == test_ticker:
                        self.test_results["api_tests"]["ticker_sentiment"] = {
                            "status": "PASS",
                            "details": ticker_data
                        }
                        print(f"  ✅ PASS: Retrieved sentiment for ticker {test_ticker}")
                    else:
                        self.test_results["api_tests"]["ticker_sentiment"] = {
                            "status": "FAIL",
                            "details": f"Retrieved incorrect ticker: {ticker_data}"
                        }
                        print(f"  ❌ FAIL: Retrieved incorrect ticker: {ticker_data.get('ticker')}")
                else:
                    self.test_results["api_tests"]["ticker_sentiment"] = {
                        "status": "FAIL",
                        "details": str(response.text)
                    }
                    print(f"  ❌ FAIL: Ticker API call failed: {response.status_code}")
            else:
                self.test_results["api_tests"]["create_sentiment"] = {
                    "status": "FAIL",
                    "details": str(response.text)
                }
                print(f"  ❌ FAIL: Event creation failed: {response.status_code}")
                
        except Exception as e:
            self.test_results["api_tests"]["sentiment_error"] = {
                "status": "FAIL",
                "details": str(e)
            }
            print(f"  ❌ FAIL: Error during sentiment testing: {e}")
    
    async def test_websockets(self):
        """Test WebSocket functionality."""
        print("\n=== Testing WebSocket Connectivity ===")
        
        if not self.websocket_url:
            print("  ⚠️ SKIP: No WebSocket URL provided")
            return
        
        try:
            # Get authentication token
            auth_response = requests.post(f"{self.api_url}/auth/login")
            token = ""
            if auth_response.status_code == 200:
                token = auth_response.json().get("access_token", "")
            
            ws_url = self.websocket_url
            if token:
                ws_url = f"{ws_url}?token={token}"
            
            print(f"Connecting to WebSocket at {ws_url}...")
            
            async with websockets.connect(ws_url) as websocket:
                self.test_results["websocket_tests"]["connection"] = {
                    "status": "PASS",
                    "details": "Successfully connected to WebSocket"
                }
                print(f"  ✅ PASS: Connected to WebSocket server")
                
                # Wait for initial message
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    message_data = json.loads(message)
                    self.test_results["websocket_tests"]["initial_message"] = {
                        "status": "PASS",
                        "details": message_data
                    }
                    print(f"  ✅ PASS: Received initial message from server")
                except asyncio.TimeoutError:
                    self.test_results["websocket_tests"]["initial_message"] = {
                        "status": "FAIL",
                        "details": "Timed out waiting for initial message"
                    }
                    print(f"  ❌ FAIL: Timed out waiting for initial message")
                
                # Test subscription to tickers
                test_ticker = "AAPL"
                
                print(f"Subscribing to ticker {test_ticker}...")
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "channel": "tickers",
                    "filters": {
                        "tickers": [test_ticker]
                    }
                }))
                
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    subscription_success = (
                        response_data.get("type") == "subscription_status" and
                        response_data.get("data", {}).get("status") == "subscribed"
                    )
                    
                    self.test_results["websocket_tests"]["subscription"] = {
                        "status": "PASS" if subscription_success else "FAIL",
                        "details": response_data
                    }
                    
                    if subscription_success:
                        print(f"  ✅ PASS: Successfully subscribed to ticker {test_ticker}")
                    else:
                        print(f"  ❌ FAIL: Failed to subscribe to ticker")
                
                except asyncio.TimeoutError:
                    self.test_results["websocket_tests"]["subscription"] = {
                        "status": "FAIL",
                        "details": "Timed out waiting for subscription response"
                    }
                    print(f"  ❌ FAIL: Timed out waiting for subscription response")
        
        except Exception as e:
            self.test_results["websocket_tests"]["connection_error"] = {
                "status": "FAIL",
                "details": str(e)
            }
            print(f"  ❌ FAIL: WebSocket test error: {e}")
    
    def test_full_data_flow(self):
        """Test the complete data flow from event creation to WebSocket notification."""
        print("\n=== Testing Full End-to-End Data Flow ===")
        
        if not self.websocket_url:
            print("  ⚠️ SKIP: No WebSocket URL provided, skipping full data flow test")
            self.test_results["end_to_end_tests"]["full_flow"] = {
                "status": "SKIP",
                "details": "No WebSocket URL provided"
            }
            return
        
        # This is wrapped in a function so we can use asyncio.run
        async def run_flow_test():
            # Get authentication token
            auth_response = requests.post(f"{self.api_url}/auth/login")
            token = ""
            if auth_response.status_code == 200:
                token = auth_response.json().get("access_token", "")
            
            ws_url = self.websocket_url
            if token:
                ws_url = f"{ws_url}?token={token}"
            
            # Connect to WebSocket
            print("Connecting to WebSocket for real-time updates...")
            
            try:
                async with websockets.connect(ws_url) as websocket:
                    # Skip initial connection message
                    await websocket.recv()
                    
                    # Create unique test data
                    test_id = str(uuid.uuid4())
                    test_ticker = "FLOW"
                    test_score = 0.9
                    
                    # Subscribe to the test ticker
                    print(f"Subscribing to test ticker {test_ticker}...")
                    await websocket.send(json.dumps({
                        "action": "subscribe",
                        "channel": "tickers",
                        "filters": {
                            "tickers": [test_ticker]
                        }
                    }))
                    
                    # Skip subscription confirmation message
                    await websocket.recv()
                    
                    # Also subscribe to events channel
                    print("Subscribing to events channel...")
                    await websocket.send(json.dumps({
                        "action": "subscribe",
                        "channel": "events"
                    }))
                    
                    # Skip subscription confirmation message
                    await websocket.recv()
                    
                    # Create test event
                    print("Creating test sentiment event...")
                    event_data = {
                        "source": "flow_test",
                        "priority": "high",
                        "text": f"This is a full data flow test message with ID {test_id}",
                        "model": "test_model",
                        "sentiment_score": test_score,
                        "sentiment_label": "positive",
                        "processing_time": 0.05,
                        "event_id": f"flow-test-{test_id}",
                        "ticker_sentiments": [{test_ticker: test_score}]
                    }
                    
                    response = requests.post(f"{self.api_url}/sentiment/event", json=event_data)
                    
                    if response.status_code == 200:
                        created_event = response.json()
                        print(f"  ✅ PASS: Created sentiment event with ID {created_event.get('id')}")
                        
                        # Wait for WebSocket updates
                        print("Waiting for WebSocket updates...")
                        
                        event_received = False
                        ticker_update_received = False
                        
                        for _ in range(5):  # Try up to 5 times
                            try:
                                message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                                message_data = json.loads(message)
                                
                                print(f"Received WebSocket message: {json.dumps(message_data, indent=2)}")
                                
                                # Check if this is a new event message matching our event
                                if (message_data.get("type") == "new_event" and 
                                    message_data.get("data", {}).get("eventId") == event_data["event_id"]):
                                    event_received = True
                                    print(f"  ✅ PASS: Received new_event WebSocket message for our event")
                                
                                # Check if this is a ticker update for our ticker
                                elif (message_data.get("type") == "sentiment_update" and 
                                      message_data.get("data", {}).get("ticker") == test_ticker):
                                    ticker_update_received = True
                                    print(f"  ✅ PASS: Received sentiment_update WebSocket message for ticker {test_ticker}")
                                
                                # If we got both types of messages, break early
                                if event_received and ticker_update_received:
                                    break
                                
                            except asyncio.TimeoutError:
                                print(f"  ⚠️ WARNING: Timeout waiting for WebSocket message, retrying...")
                        
                        self.test_results["end_to_end_tests"]["event_notification"] = {
                            "status": "PASS" if event_received else "FAIL",
                            "details": "Received event notification via WebSocket" if event_received else "Did not receive event notification"
                        }
                        
                        self.test_results["end_to_end_tests"]["ticker_update"] = {
                            "status": "PASS" if ticker_update_received else "FAIL",
                            "details": "Received ticker update via WebSocket" if ticker_update_received else "Did not receive ticker update"
                        }
                        
                        if event_received and ticker_update_received:
                            self.test_results["end_to_end_tests"]["full_flow"] = {
                                "status": "PASS",
                                "details": "Complete data flow verified"
                            }
                            print(f"  ✅ PASS: Full data flow test successful")
                        else:
                            failed_parts = []
                            if not event_received:
                                failed_parts.append("event notification")
                            if not ticker_update_received:
                                failed_parts.append("ticker update")
                            
                            self.test_results["end_to_end_tests"]["full_flow"] = {
                                "status": "FAIL",
                                "details": f"Missing {', '.join(failed_parts)}"
                            }
                            print(f"  ❌ FAIL: Full data flow test failed - missing {', '.join(failed_parts)}")
                    else:
                        self.test_results["end_to_end_tests"]["event_creation"] = {
                            "status": "FAIL",
                            "details": str(response.text)
                        }
                        print(f"  ❌ FAIL: Could not create test event: {response.status_code}")
            
            except Exception as e:
                self.test_results["end_to_end_tests"]["websocket_error"] = {
                    "status": "FAIL",
                    "details": str(e)
                }
                print(f"  ❌ FAIL: Error during full data flow test: {e}")
        
        try:
            asyncio.run(run_flow_test())
        except Exception as e:
            self.test_results["end_to_end_tests"]["flow_test_error"] = {
                "status": "FAIL",
                "details": str(e)
            }
            print(f"  ❌ FAIL: Error in flow test: {e}")
    
    def print_summary(self):
        """Print a summary of all test results."""
        print("\n=== Test Summary ===")
        
        # Calculate total tests and passes/fails/skips
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        
        for category in self.test_results.values():
            for test in category.values():
                total_tests += 1
                if test.get("status") == "PASS":
                    passed_tests += 1
                elif test.get("status") == "FAIL":
                    failed_tests += 1
                elif test.get("status") == "SKIP":
                    skipped_tests += 1
        
        pass_rate = passed_tests / total_tests * 100 if total_tests > 0 else 0
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests} ({pass_rate:.1f}%)")
        print(f"Failed: {failed_tests}")
        print(f"Skipped: {skipped_tests}")
        
        # Print detailed results by category
        for category_name, category in self.test_results.items():
            print(f"\n{category_name.replace('_', ' ').title()}:")
            for test_name, test in category.items():
                icon = "✅" if test.get("status") == "PASS" else "❌" if test.get("status") == "FAIL" else "⚠️"
                print(f"  {icon} {test_name.replace('_', ' ').title()}: {test.get('status')}")
        
        # Overall result
        if failed_tests == 0:
            if skipped_tests == 0:
                print("\n✅ ALL TESTS PASSED")
            else:
                print(f"\n✅ ALL TESTS PASSED ({skipped_tests} skipped)")
        else:
            print(f"\n❌ {failed_tests} TESTS FAILED")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run end-to-end tests for the sentiment analysis system')
    parser.add_argument('--api-host', default='localhost', help='API host')
    parser.add_argument('--api-port', default=8001, type=int, help='API port')
    parser.add_argument('--ws-host', default=None, help='WebSocket host (defaults to API host)')
    parser.add_argument('--ws-port', default=None, type=int, help='WebSocket port (defaults to API port)')
    parser.add_argument('--output-file', help='File to write test results to (JSON format)')
    
    args = parser.parse_args()
    
    api_url = f"http://{args.api_host}:{args.api_port}"
    
    ws_host = args.ws_host if args.ws_host else args.api_host
    ws_port = args.ws_port if args.ws_port else args.api_port
    ws_url = f"ws://{ws_host}:{ws_port}/ws"
    
    # Run tests
    tester = EndToEndTest(api_url, ws_url)
    results = tester.run_all_tests()
    
    # Always write results to test_results directory using the new naming convention
    date_str = datetime.now().strftime('%y%m%d')
    
    # Create test_results directory if it doesn't exist
    import os
    test_results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_results")
    os.makedirs(test_results_dir, exist_ok=True)
    
    # Find the next available sequence number
    seq_num = 1
    while True:
        test_filename = f"e2e_results_{date_str}_{seq_num}.json"
        if not os.path.exists(os.path.join(test_results_dir, test_filename)):
            break
        seq_num += 1
    
    test_output_file = os.path.join(test_results_dir, test_filename)
    
    # Save to standard test_results location
    with open(test_output_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "api_url": api_url,
            "websocket_url": ws_url,
            "results": results
        }, f, indent=2)
    print(f"\nTest results written to {test_output_file}")
    
    # Also write to the specified output file if provided
    if args.output_file:
        with open(args.output_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "api_url": api_url,
                "websocket_url": ws_url,
                "results": results
            }, f, indent=2)
        print(f"Test results also written to {args.output_file}")