#!/usr/bin/env python3
import asyncio
import websockets
import json
import sys

async def connect_to_websocket(path, host="localhost", port=8001):
    """Connect to a WebSocket endpoint and handle messages."""
    uri = f"ws://{host}:{port}{path}?token=demo_token"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            # Send a ping message
            ping_message = json.dumps({"action": "ping"})
            print(f"Sending: {ping_message}")
            await websocket.send(ping_message)
            
            # Wait for response
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Try to subscribe to a channel
            subscribe_message = json.dumps({
                "action": "subscribe",
                "channel": "sentiment_events"
            })
            print(f"Sending: {subscribe_message}")
            await websocket.send(subscribe_message)
            
            # Wait for subscription confirmation
            response = await websocket.recv()
            print(f"Received: {response}")
            
            # Keep the connection open briefly to see if we get any messages
            print("Listening for messages for 10 seconds...")
            try:
                for _ in range(5):  # Try a few times
                    response = await asyncio.wait_for(websocket.recv(), timeout=2)
                    print(f"Received: {response}")
            except asyncio.TimeoutError:
                print("No more messages received (timeout)")
                
            print("Test complete")
            
    except Exception as e:
        print(f"Error: {e}")
        return False
        
    return True

async def test_multiple_paths(host="0.0.0.0", port=8001):
    """Test multiple WebSocket endpoint paths."""
    paths = [
        "/ws",
        "/socket",
        "/websocket"
    ]
    
    results = {}
    
    for path in paths:
        print(f"\n--- Testing path: {path} ---")
        success = await connect_to_websocket(path, host=host, port=port)
        results[path] = "SUCCESS" if success else "FAILED"
    
    print("\n--- Results Summary ---")
    for path, result in results.items():
        print(f"{path}: {result}")

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "/ws"
    
    # When running inside Docker container, use the container name instead of localhost
    host = "0.0.0.0"  # Use 0.0.0.0 when testing from inside the API container itself
    
    if path == "all":
        asyncio.run(test_multiple_paths(host=host))
    else:
        asyncio.run(connect_to_websocket(path, host=host))