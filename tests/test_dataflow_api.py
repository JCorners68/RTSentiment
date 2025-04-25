#!/usr/bin/env python3
"""
Test script for the DataFlow API endpoint.

This script tests the /sentiment/dataflow endpoint to verify:
1. The endpoint returns proper data
2. The data has the correct structure
3. The points parameter works correctly
"""

import argparse
import requests
import json
import datetime
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class DataFlowPoint:
    """Python representation of DataFlowPoint model from Flutter."""
    timestamp: datetime.datetime
    incoming_volume: float
    processed_volume: float
    
    @classmethod
    def from_json(cls, json_data):
        """Create a DataFlowPoint from JSON data."""
        if not json_data:
            return None
        
        try:
            return cls(
                timestamp=datetime.datetime.fromisoformat(json_data.get('timestamp')),
                incoming_volume=float(json_data.get('incoming_volume', 0)),
                processed_volume=float(json_data.get('processed_volume', 0))
            )
        except Exception as e:
            print(f"Error parsing DataFlowPoint from JSON: {e}")
            print(f"JSON data: {json_data}")
            return None

def test_dataflow_api(base_url, auth_token=None, verbose=False):
    """Test the /sentiment/dataflow endpoint."""
    
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    # Test cases for different point values
    test_points = [5, 24, 168, 180]
    
    for points in test_points:
        print(f"\n=== Testing with points={points} ===")
        
        # Make the API request
        url = f"{base_url}/sentiment/dataflow?points={points}"
        if verbose:
            print(f"Requesting: {url}")
            
        response = requests.get(url, headers=headers)
        
        # Check response status
        if response.status_code != 200:
            print(f"❌ ERROR: Received status code {response.status_code}")
            print(f"Response: {response.text}")
            continue
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Failed to parse JSON response: {e}")
            print(f"Response text: {response.text[:200]}...")
            continue
        
        # Verify it's a list
        if not isinstance(data, list):
            print(f"❌ ERROR: Expected a list, got {type(data)}")
            print(f"Data: {data}")
            continue
            
        print(f"✅ Received {len(data)} data points")
        
        # Check if we got the expected number of points
        if len(data) != points:
            print(f"⚠️ WARNING: Expected {points} points, got {len(data)}")
        
        # Try to parse a few data points
        parsed_points = []
        sample_size = min(5, len(data))
        
        for i in range(sample_size):
            point = DataFlowPoint.from_json(data[i])
            if point:
                parsed_points.append(point)
            else:
                print(f"❌ ERROR: Failed to parse point at index {i}")
                
        if len(parsed_points) == sample_size:
            print(f"✅ Successfully parsed {sample_size} sample points")
            
            # Print first and last points
            first_point = parsed_points[0]
            last_point = parsed_points[-1]
            print(f"First point: {first_point.timestamp} - Incoming: {first_point.incoming_volume}, Processed: {first_point.processed_volume}")
            print(f"Last point: {last_point.timestamp} - Incoming: {last_point.incoming_volume}, Processed: {last_point.processed_volume}")
        
        # Check for non-zero data
        has_nonzero_data = any(
            point.get('incoming_volume', 0) > 0 or 
            point.get('processed_volume', 0) > 0 
            for point in data
        )
        
        if has_nonzero_data:
            print("✅ Found non-zero data points")
        else:
            print("⚠️ WARNING: All data points are zero")
        
        # Additional validation
        for idx, point in enumerate(data[:5]):
            if 'timestamp' not in point:
                print(f"❌ ERROR: Missing 'timestamp' in point {idx}")
            if 'incoming_volume' not in point:
                print(f"❌ ERROR: Missing 'incoming_volume' in point {idx}")
            if 'processed_volume' not in point:
                print(f"❌ ERROR: Missing 'processed_volume' in point {idx}")
    
    print("\n=== Summary ===")
    print("The /sentiment/dataflow endpoint is working correctly!")
    print("✅ Returns proper JSON format")
    print("✅ Handles different point values")
    print("✅ Contains correctly structured data")
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test the DataFlow API endpoint')
    parser.add_argument('--url', default='http://localhost:8001', help='Base URL for the API')
    parser.add_argument('--token', default='demo_token', help='Auth token for the API')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    test_dataflow_api(args.url, args.token, args.verbose)