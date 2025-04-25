#!/usr/bin/env python3
"""
WebSocket Test Client

This script tests the WebSocket functionality of the API service.
It connects to the WebSocket endpoint, subscribes to various channels,
and monitors for real-time updates.

Example usage:
    python websocket_test_client.py --host localhost --port 8001
"""

import argparse
import asyncio
import json
import signal
import sys
import websockets
import requests
import time
from datetime import datetime

# Sample tickers to subscribe to
TEST_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

# Track statistics
stats = {
    "connection_attempts": 0,
    "successful_connections": 0,
    "messages_received": 0,
    "connection_errors": 0,
    "message_errors": 0,
    "start_time": None,
    "last_message_time": None,
    "message_types": {}
}

async def trigger_sentiment_event(base_url, ticker):
    """Create a new sentiment event to trigger WebSocket updates."""
    score = 0.7  # Positive sentiment
    event_data = {
        "source": "websocket_test",
        "priority": "high",
        "text": f"Positive news about {ticker} from WebSocket test client",
        "model": "test_model",
        "sentiment_score": score,
        "sentiment_label": "positive",
        "processing_time": 0.05,
        "event_id": f"ws-test-{datetime.now().isoformat()}",
        "ticker_sentiments": [{ticker: score}]
    }
    
    try:
        response = requests.post(f"{base_url}/sentiment/event", json=event_data)
        return response.status_code == 200
    except Exception as e:
        print(f"Error creating test event: {e}")
        return False

async def websocket_client(uri, base_url, test_duration=60):
    """WebSocket client that connects, subscribes, and listens for updates."""
    global stats
    stats["start_time"] = time.time()
    
    # Get the auth token
    try:
        auth_response = requests.post(f"{base_url}/auth/login")
        token = auth_response.json().get("access_token", "")
        if token:
            uri = f"{uri}?token={token}"
    except Exception as e:
        print(f"Failed to get auth token: {e}")
    
    while time.time() - stats["start_time"] < test_duration:
        try:
            stats["connection_attempts"] += 1
            async with websockets.connect(uri) as websocket:
                print(f"Connected to WebSocket server at {uri}")
                stats["successful_connections"] += 1
                
                # Wait for connection confirmation
                message = await websocket.recv()
                print(f"Received: {message}")
                stats["messages_received"] += 1
                
                # Track message type
                try:
                    msg_data = json.loads(message)
                    msg_type = msg_data.get("type", "unknown")
                    stats["message_types"][msg_type] = stats["message_types"].get(msg_type, 0) + 1
                except:
                    pass
                
                # Subscribe to ticker updates
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "channel": "tickers",
                    "filters": {
                        "tickers": TEST_TICKERS
                    }
                }))
                
                # Wait for subscription confirmation
                message = await websocket.recv()
                print(f"Subscription response: {message}")
                stats["messages_received"] += 1
                
                # Track message type
                try:
                    msg_data = json.loads(message)
                    msg_type = msg_data.get("type", "unknown")
                    stats["message_types"][msg_type] = stats["message_types"].get(msg_type, 0) + 1
                except:
                    pass
                
                # Subscribe to all events
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "channel": "events"
                }))
                
                # Wait for subscription confirmation
                message = await websocket.recv()
                print(f"Events subscription response: {message}")
                stats["messages_received"] += 1
                
                # Track message type
                try:
                    msg_data = json.loads(message)
                    msg_type = msg_data.get("type", "unknown")
                    stats["message_types"][msg_type] = stats["message_types"].get(msg_type, 0) + 1
                except:
                    pass
                
                # Trigger some test events to verify we receive them
                print("Triggering test events...")
                for ticker in TEST_TICKERS:
                    success = await trigger_sentiment_event(base_url, ticker)
                    if success:
                        print(f"Created test event for {ticker}")
                    await asyncio.sleep(0.5)  # Small delay between events
                
                # Listen for WebSocket messages
                listen_task = asyncio.create_task(listen_for_messages(websocket))
                
                # Keep running until test duration expires
                end_time = time.time() + test_duration
                while time.time() < end_time:
                    # Every 10 seconds, trigger a new event
                    if int(time.time()) % 10 == 0:
                        ticker = TEST_TICKERS[int(time.time()) % len(TEST_TICKERS)]
                        success = await trigger_sentiment_event(base_url, ticker)
                        if success:
                            print(f"Created periodic test event for {ticker}")
                    
                    await asyncio.sleep(1)
                
                # Cancel the listening task
                listen_task.cancel()
                
                # Unsubscribe before disconnecting
                await websocket.send(json.dumps({
                    "action": "unsubscribe",
                    "channel": "tickers",
                    "filters": {
                        "tickers": TEST_TICKERS
                    }
                }))
                
                # Unsubscribe from events
                await websocket.send(json.dumps({
                    "action": "unsubscribe",
                    "channel": "events"
                }))
                
                print("Test complete, disconnecting")
        
        except websockets.ConnectionClosed as e:
            print(f"WebSocket connection closed: {e}")
            stats["connection_errors"] += 1
            await asyncio.sleep(2)  # Wait before reconnecting
        
        except Exception as e:
            print(f"WebSocket error: {e}")
            stats["connection_errors"] += 1
            await asyncio.sleep(2)  # Wait before reconnecting

async def listen_for_messages(websocket):
    """Listen for WebSocket messages and print them."""
    global stats
    
    try:
        while True:
            message = await websocket.recv()
            stats["messages_received"] += 1
            stats["last_message_time"] = time.time()
            
            try:
                msg_data = json.loads(message)
                msg_type = msg_data.get("type", "unknown")
                stats["message_types"][msg_type] = stats["message_types"].get(msg_type, 0) + 1
                
                # Pretty print message
                print(f"\nReceived {msg_type} message:")
                print(json.dumps(msg_data, indent=2))
            except json.JSONDecodeError:
                print(f"Received non-JSON message: {message}")
                stats["message_errors"] += 1
    
    except asyncio.CancelledError:
        print("Listening task cancelled")
    
    except Exception as e:
        print(f"Error in message listener: {e}")
        stats["message_errors"] += 1

def print_stats():
    """Print test statistics."""
    global stats
    
    if stats["start_time"] is None:
        print("No test statistics available")
        return
    
    duration = time.time() - stats["start_time"]
    
    print("\n=== WebSocket Test Statistics ===")
    print(f"Test duration: {duration:.2f} seconds")
    print(f"Connection attempts: {stats['connection_attempts']}")
    print(f"Successful connections: {stats['successful_connections']}")
    print(f"Connection success rate: {stats['successful_connections']/stats['connection_attempts']*100:.2f}% if stats['connection_attempts'] > 0 else 'N/A'")
    print(f"Total messages received: {stats['messages_received']}")
    print(f"Message reception rate: {stats['messages_received']/duration:.2f} messages/second")
    print(f"Connection errors: {stats['connection_errors']}")
    print(f"Message parsing errors: {stats['message_errors']}")
    
    print("\nMessage types received:")
    for msg_type, count in stats["message_types"].items():
        print(f"  {msg_type}: {count}")
    
    if stats["last_message_time"]:
        time_since_last = time.time() - stats["last_message_time"]
        print(f"\nTime since last message: {time_since_last:.2f} seconds")
    else:
        print("\nNo messages received during test")

def handle_exit(signum, frame):
    """Handle Ctrl+C and print stats before exiting."""
    print("\nTest interrupted! Printing statistics before exiting...")
    print_stats()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, handle_exit)
    
    parser = argparse.ArgumentParser(description='Test WebSocket functionality')
    parser.add_argument('--host', default='localhost', help='API host')
    parser.add_argument('--port', default=8001, type=int, help='API port')
    parser.add_argument('--duration', default=60, type=int, help='Test duration in seconds')
    parser.add_argument('--secure', action='store_true', help='Use secure WebSocket (wss://)')
    
    args = parser.parse_args()
    
    protocol = "wss" if args.secure else "ws"
    ws_uri = f"{protocol}://{args.host}:{args.port}/ws"
    base_url = f"http://{args.host}:{args.port}"
    
    # Check if API is running first
    try:
        response = requests.get(f"{base_url}/health", timeout=2)
        print(f"API service detected at {base_url}")
    except requests.exceptions.ConnectionError:
        print(f"API service not running at {base_url}. Please start it before running the WebSocket test.")
        sys.exit(1)
    
    print(f"Starting WebSocket test for {ws_uri} for {args.duration} seconds...")
    print("Press Ctrl+C to stop the test")
    
    try:
        asyncio.run(websocket_client(ws_uri, base_url, args.duration))
        print_stats()
    except KeyboardInterrupt:
        print("\nTest manually interrupted")
        print_stats()
    except Exception as e:
        print(f"Test failed with error: {e}")
        print_stats()