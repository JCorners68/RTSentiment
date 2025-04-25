# WebSocket Implementation for Real-Time Sentiment Analysis

This document describes the implementation of WebSocket support in the Sentiment Analysis System.

## Overview

The WebSocket implementation enables real-time communication between the backend API and the Flutter client. This allows the client to receive instant updates on sentiment events, ticker updates, system statistics, and data flow metrics.

## API Server Changes

### WebSocket Endpoints

Multiple WebSocket endpoints were implemented to ensure compatibility with the Flutter client:

- `/ws` - Primary WebSocket endpoint
- `/socket` - Alternative endpoint
- `/websocket` - Alternative endpoint

All endpoints provide identical functionality, but the multiple paths give the client flexibility to try different connection options if one fails.

### WebSocket Handler

A helper function `handle_websocket_connection` was implemented to handle all WebSocket connections consistently. This function:

1. Authenticates the user via token
2. Establishes the WebSocket connection
3. Handles incoming messages
4. Manages subscriptions to different channels

### Connection Manager

A `ConnectionManager` class maintains:

- Active WebSocket connections
- User mapping
- Channel subscriptions
- Ticker-specific subscriptions

This allows for efficient broadcasting of messages only to interested clients.

### Event Publishing

The following functions were implemented to broadcast events to WebSocket clients:

- `publish_sentiment_event` - Broadcasts sentiment events
- `publish_ticker_update` - Broadcasts ticker updates
- `publish_system_stats` - Broadcasts system statistics
- `publish_data_flow` - Broadcasts data flow metrics

### Authentication

Authentication for WebSocket connections is handled via a token query parameter. For development and testing purposes, a special `demo_token` is accepted without validation.

## Flutter Client Changes

### WebSocket Service

The `WebSocketService` class in the Flutter client was updated to:

1. Prioritize the supported WebSocket endpoints
2. Handle the WebSocket connection lifecycle
3. Remove fragment identifiers from URLs
4. Support reconnection with exponential backoff
5. Manage subscriptions to different channels

### Endpoint Path Discovery

The client now tries multiple potential paths in order, with a preference for the ones known to work:

```dart
final List<String> _potentialPaths = [
  '/ws',      // Primary endpoint (guaranteed to work)
  '/socket',  // Alternative endpoint (guaranteed to work)
  '/websocket', // Alternative endpoint (guaranteed to work)
  // These are less likely to work, but we'll try them if the primary ones fail
  '/api/ws',
  '/sentiment/ws',
  '/live',
  '/realtime',
  '/socket.io',
];
```

### URL Construction

The URL construction was improved to properly handle potential fragment identifiers:

```dart
// Construct the full WebSocket URL with the token
String wsUrl = '$_baseUrlWithoutPath$path?token=$_authToken';
// Remove any fragment identifiers that might have been present
if (wsUrl.contains('#')) {
  wsUrl = wsUrl.split('#')[0];
}
```

## Message Protocol

### Client to Server

Messages from client to server are JSON objects with an `action` field:

```json
{
  "action": "subscribe",
  "channel": "sentiment_events",
  "filters": {
    "tickers": ["AAPL", "MSFT"]
  }
}
```

Supported actions:
- `ping` - Check connection status
- `subscribe` - Subscribe to a channel
- `unsubscribe` - Unsubscribe from a channel

### Server to Client

Messages from server to client are JSON objects with a `type` field:

```json
{
  "type": "sentiment_event",
  "data": {
    "id": 123,
    "event_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "timestamp": "2025-04-23T10:15:30.123Z",
    "source": "news",
    "priority": "standard",
    "text": "Apple reports record profits for Q1 2023.",
    "model": "finbert",
    "sentiment_score": 0.85,
    "sentiment_label": "positive",
    "ticker_sentiments": [
      {
        "AAPL": 0.92
      },
      {
        "MSFT": 0.43
      }
    ]
  },
  "timestamp": "2025-04-23T10:15:30.123Z"
}
```

Supported message types:
- `connection_established` - Sent when the connection is established
- `pong` - Response to a ping message
- `subscription_confirmed` - Confirms subscription to a channel
- `unsubscription_confirmed` - Confirms unsubscription from a channel
- `sentiment_event` - Contains sentiment event data
- `ticker_update` - Contains ticker sentiment update data
- `system_stats` - Contains system statistics data
- `data_flow` - Contains data flow metrics
- `error` - Contains error information
- `echo` - Echo response for testing

## Testing

A WebSocket test script was created to test the WebSocket endpoints. The script:

1. Connects to the specified WebSocket endpoint
2. Authenticates with a token
3. Sends a ping message
4. Subscribes to a channel
5. Listens for messages
6. Reports success or failure

The test script was used to verify that all implemented WebSocket endpoints were working correctly.

## Documentation

A comprehensive API specification document (`API_spec.md`) was created that includes detailed information about:

- REST API endpoints
- WebSocket connection options
- Message formats
- Authentication mechanisms
- Available channels and subscriptions

This documentation serves as the reference for developers working with the API.

## Next Steps

1. **Enhance Error Handling**: Improve error handling in the WebSocket implementation
2. **Add More Channels**: Implement additional channels for different types of data
3. **Implement Rate Limiting**: Add rate limiting to prevent abuse
4. **Add Heartbeat Mechanism**: Implement a heartbeat mechanism to detect stale connections
5. **Implement WebSocket Health Checks**: Add health checks to monitor WebSocket server status