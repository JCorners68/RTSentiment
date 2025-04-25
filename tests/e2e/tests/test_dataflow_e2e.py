#!/usr/bin/env python3
"""
End-to-End test for the DataFlow API endpoint.

This script tests the full pipeline:
1. Creates test events
2. Verifies they appear in the dataflow endpoint
3. Tests both the API endpoints and data aggregation
"""

import argparse
import requests
import json
import datetime
import time
import uuid
from typing import List, Dict, Any

def create_test_event(api_url: str, token: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Create a test sentiment event through the API.
    
    Args:
        api_url: Base URL of the API
        token: Authentication token
        verbose: Enable verbose output
        
    Returns:
        Dictionary containing the response from the API
    """
    # Create a unique ID for this test
    event_id = f"dataflow-test-{uuid.uuid4()}"
    
    # Create event data
    event_data = {
        "source": "dataflow_test",
        "priority": "high",
        "text": f"This is a test event for dataflow testing with ID {event_id}",
        "model": "test_model",
        "sentiment_score": 0.85,
        "sentiment_label": "positive",
        "processing_time": 0.05,
        "event_id": event_id,
        "ticker_sentiments": [{"AAPL": 0.85}, {"MSFT": 0.75}]
    }
    
    if verbose:
        print(f"Creating test event with ID: {event_id}")
        
    # Send the request
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    response = requests.post(
        f"{api_url}/sentiment/event", 
        headers=headers,
        json=event_data
    )
    
    if response.status_code != 200:
        print(f"❌ ERROR: Failed to create test event. Status: {response.status_code}")
        print(f"Response: {response.text}")
        return None
    
    try:
        result = response.json()
        if verbose:
            print(f"✅ Created event: {result}")
        return result
    except json.JSONDecodeError:
        print(f"❌ ERROR: Failed to parse response: {response.text}")
        return None

def verify_dataflow(api_url: str, token: str, points: int = 5, verbose: bool = False) -> bool:
    """
    Verify that the dataflow endpoint returns the expected data.
    
    Args:
        api_url: Base URL of the API
        token: Authentication token
        points: Number of points to request
        verbose: Enable verbose output
        
    Returns:
        True if verification succeeded, False otherwise
    """
    if verbose:
        print(f"Checking dataflow with {points} points...")
        
    # Send the request
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{api_url}/sentiment/dataflow?points={points}", 
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ ERROR: Failed to get dataflow. Status: {response.status_code}")
        print(f"Response: {response.text}")
        return False
    
    try:
        data = response.json()
        if not isinstance(data, list):
            print(f"❌ ERROR: Expected a list, got {type(data)}")
            return False
            
        if len(data) != points:
            print(f"⚠️ WARNING: Expected {points} points, got {len(data)}")
            
        if verbose:
            print(f"✅ Received {len(data)} dataflow points")
            
        # Check for non-zero data in the most recent point
        last_point = data[-1]
        if last_point.get("incoming_volume", 0) > 0:
            print(f"✅ Most recent point has incoming_volume: {last_point['incoming_volume']}")
            print(f"✅ Most recent point has timestamp: {last_point['timestamp']}")
            print(f"✅ Most recent point has processed_volume: {last_point['processed_volume']}")
            return True
        else:
            print(f"⚠️ WARNING: Most recent point has zero incoming_volume")
            return False
            
    except json.JSONDecodeError:
        print(f"❌ ERROR: Failed to parse response: {response.text}")
        return False

def run_e2e_test(api_url: str, token: str, num_events: int = 3, verbose: bool = False) -> bool:
    """
    Run the end-to-end test.
    
    Args:
        api_url: Base URL of the API
        token: Authentication token
        num_events: Number of test events to create
        verbose: Enable verbose output
        
    Returns:
        True if the test succeeded, False otherwise
    """
    print("\n=== Starting DataFlow E2E Test ===")
    
    # Step 1: Create test events
    print(f"\nCreating {num_events} test events...")
    events = []
    for i in range(num_events):
        event = create_test_event(api_url, token, verbose)
        if event:
            events.append(event)
        # Small delay to avoid rate limiting
        time.sleep(0.5)
    
    if len(events) != num_events:
        print(f"❌ ERROR: Failed to create all test events. Created {len(events)} of {num_events}")
        return False
        
    print(f"✅ Successfully created {len(events)} test events")
    
    # Step 2: Wait a moment for data to be processed
    print("\nWaiting for data processing...")
    time.sleep(2)
    
    # Step 3: Verify dataflow endpoint
    print("\nVerifying dataflow endpoint...")
    success = verify_dataflow(api_url, token, 5, verbose)
    
    # Summary
    print("\n=== E2E Test Summary ===")
    if success:
        print("✅ E2E test PASSED!")
        print("✅ Created test events successfully")
        print("✅ Verified dataflow endpoint returns expected data")
    else:
        print("❌ E2E test FAILED!")
        print("Check the logs above for details")
        
    return success

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run an E2E test for the DataFlow API')
    parser.add_argument('--url', default='http://localhost:8001', help='Base URL for the API')
    parser.add_argument('--token', default='demo_token', help='Auth token for the API')
    parser.add_argument('--events', type=int, default=3, help='Number of test events to create')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    success = run_e2e_test(args.url, args.token, args.events, args.verbose)
    if not success:
        exit(1)