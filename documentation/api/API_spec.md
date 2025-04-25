# API Specification

This document describes the API endpoints available in the Sentiment Analysis System.

## Base URLs

- **REST API**: `http://localhost:8001`
- **WebSocket API**: `ws://localhost:8001`

## Authentication

Most endpoints require authentication. The system uses token-based authentication.

### Getting a Token

```
POST /auth/login
```

**Response:**

```json
{
  "access_token": "demo_token",
  "token_type": "bearer"
}
```

### Using the Token

- For REST API requests, include the token in the Authorization header:
  ```
  Authorization: Bearer demo_token
  ```

- For WebSocket connections, include the token as a query parameter:
  ```
  ws://localhost:8001/ws?token=demo_token
  ```

## REST API Endpoints

### Health Check

```
GET /health
```

Returns the health status of the API service.

**Response:**

```json
{
  "status": "healthy"
}
```

### Sentiment Events

#### Create Sentiment Event

```
POST /sentiment/event
```

Store a new sentiment event in the database.

**Request Body:**

```json
{
  "source": "news",
  "priority": "standard",
  "text": "Apple reports record profits for Q1 2023.",
  "model": "finbert",
  "sentiment_score": 0.85,
  "sentiment_label": "positive",
  "processing_time": 0.125,
  "ticker_sentiments": [
    {
      "AAPL": 0.92
    },
    {
      "MSFT": 0.43
    }
  ]
}
```

**Response:**

```json
{
  "id": 123,
  "event_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "timestamp": "2025-04-23T10:15:30.123Z",
  "source": "news",
  "priority": "standard",
  "model": "finbert",
  "sentiment_score": 0.85,
  "sentiment_label": "positive"
}
```

#### Query Sentiment Events

```
POST /sentiment/query
```

Query sentiment events with various filters.

**Request Body:**

```json
{
  "start_date": "2025-04-01T00:00:00Z",
  "end_date": "2025-04-23T23:59:59Z",
  "sources": ["news", "reddit"],
  "models": ["finbert"],
  "min_score": 0.5,
  "max_score": 1.0,
  "tickers": ["AAPL", "MSFT"],
  "limit": 50,
  "offset": 0
}
```

**Response:**

Array of sentiment events matching the query filters.

#### Get Ticker Sentiment

```
GET /sentiment/ticker/{ticker}
```

Get sentiment for a specific ticker.

**Response:**

```json
{
  "ticker": "AAPL",
  "sentiment": "positive",
  "score": 0.78,
  "weight": 1.5,
  "count": 25,
  "model": "finbert"
}
```

#### Get Available Tickers

```
GET /sentiment/tickers
```

Get list of available tickers.

**Response:**

```json
["AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA"]
```

#### Get Top Sentiment

```
GET /sentiment/top
```

Get top tickers by sentiment score.

**Query Parameters:**

- `limit`: Number of results to return (default: 10)
- `min_score`: Minimum sentiment score
- `max_score`: Maximum sentiment score
- `sort_by`: Field to sort by (score, count)
- `order`: Sort order (asc, desc)

**Response:**

Array of ticker sentiment records.

#### Analyze Text Sentiment

```
POST /sentiment/analyze
```

Analyze sentiment of custom text.

**Request Body:**

```
text=Apple reports record profits for Q1 2023.
```

**Response:**

```json
{
  "sentiment": "positive",
  "score": 0.78,
  "tickers": ["AAPL", "MSFT"],
  "model": "finbert"
}
```

### Statistics

#### Get System Stats

```
GET /sentiment/stats
```

Get system statistics for message processing.

**Response:**

```json
{
  "high_priority": {
    "count": 150,
    "average_processing_time": 0.075,
    "messages_per_minute": 2.5,
    "error_rate": 0.01
  },
  "standard_priority": {
    "count": 1250,
    "average_processing_time": 0.125,
    "messages_per_minute": 12.5,
    "error_rate": 0.02
  },
  "sentiment_results": {
    "count": 1400,
    "average_processing_time": 0.15,
    "messages_per_minute": 15.0,
    "error_rate": 0.015
  }
}
```

#### Get Metadata

```
GET /sentiment/metadata
```

Get metadata for UI filtering.

**Response:**

```json
{
  "sources": ["news", "reddit", "twitter"],
  "models": ["finbert", "fingpt", "llama4_scout"],
  "priorities": ["high", "standard"]
}
```

#### Get Data Flow

```
GET /sentiment/dataflow
```

Get time-series data showing message flow.

**Query Parameters:**

- `points`: Number of data points to return (default: 30, max: 1000)

**Response:**

Array of data points with timestamp, messages_per_second, avg_processing_time, and error_rate.

### Subscriptions

#### Create Subscription

```
POST /subscriptions/create
```

Create a new subscription for tracking specific tickers or sources.

**Request Body:**

```json
{
  "name": "Tech Stocks",
  "tickers": ["AAPL", "MSFT", "GOOGL"],
  "sources": ["news", "reddit"],
  "min_sentiment": -1.0,
  "max_sentiment": 1.0,
  "active": true
}
```

**Response:**

Details of the created subscription.

#### Get Subscriptions

```
GET /subscriptions/list
```

Get the list of subscriptions for the current user.

**Response:**

Array of subscription objects.

## WebSocket API

The WebSocket API provides real-time updates for sentiment events and system statistics.

### Connection

Connect to one of the following WebSocket endpoints:

- `/ws` (primary endpoint)
- `/socket` (alternative endpoint)
- `/websocket` (alternative endpoint)

Include the authentication token as a query parameter:

```
ws://localhost:8001/ws?token=demo_token
```

### Message Format

All messages are JSON objects with a `type` field that indicates the message type.

### Client Actions

#### Ping

Send a ping to check connection status:

```json
{
  "action": "ping"
}
```

Response:

```json
{
  "type": "pong",
  "timestamp": "2025-04-23T10:15:30.123Z"
}
```

#### Subscribe to Channel

Subscribe to a specific channel:

```json
{
  "action": "subscribe",
  "channel": "sentiment_events",
  "filters": {
    "tickers": ["AAPL", "MSFT"]
  }
}
```

Response:

```json
{
  "type": "subscription_confirmed",
  "channel": "sentiment_events",
  "filters": {
    "tickers": ["AAPL", "MSFT"]
  },
  "timestamp": "2025-04-23T10:15:30.123Z"
}
```

Available channels:
- `sentiment_events`: Real-time sentiment events
- `ticker_updates`: Updates to ticker sentiment
- `system_stats`: System statistics
- `data_flow`: Data flow metrics

#### Unsubscribe from Channel

Unsubscribe from a specific channel:

```json
{
  "action": "unsubscribe",
  "channel": "sentiment_events"
}
```

Response:

```json
{
  "type": "unsubscription_confirmed",
  "channel": "sentiment_events",
  "timestamp": "2025-04-23T10:15:30.123Z"
}
```

### Server Messages

#### Connection Established

Sent when the connection is established:

```json
{
  "type": "connection_established",
  "user_id": "demo_user",
  "timestamp": "2025-04-23T10:15:30.123Z",
  "message": "Connected to sentiment analysis WebSocket server"
}
```

#### Sentiment Event

Sent when a new sentiment event is created:

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

#### Ticker Update

Sent when a ticker's sentiment is updated:

```json
{
  "type": "ticker_update",
  "data": {
    "ticker": "AAPL",
    "sentiment": "positive",
    "score": 0.78,
    "weight": 1.5,
    "count": 25,
    "model": "finbert"
  },
  "timestamp": "2025-04-23T10:15:30.123Z"
}
```

#### System Stats

Sent when system statistics are updated:

```json
{
  "type": "system_stats",
  "data": {
    "high_priority": {
      "count": 150,
      "average_processing_time": 0.075,
      "messages_per_minute": 2.5,
      "error_rate": 0.01
    },
    "standard_priority": {
      "count": 1250,
      "average_processing_time": 0.125,
      "messages_per_minute": 12.5,
      "error_rate": 0.02
    },
    "sentiment_results": {
      "count": 1400,
      "average_processing_time": 0.15,
      "messages_per_minute": 15.0,
      "error_rate": 0.015
    }
  },
  "timestamp": "2025-04-23T10:15:30.123Z"
}
```

#### Data Flow

Sent when data flow metrics are updated:

```json
{
  "type": "data_flow",
  "data": {
    "timestamp": "2025-04-23T10:15:30.123Z",
    "messages_per_second": 2.5,
    "avg_processing_time": 0.125,
    "error_rate": 0.015
  },
  "timestamp": "2025-04-23T10:15:30.123Z"
}
```

#### Error

Sent when an error occurs:

```json
{
  "type": "error",
  "error": "Invalid action",
  "received": {
    "action": "unknown_action"
  },
  "timestamp": "2025-04-23T10:15:30.123Z"
}
```
EOL < /dev/null
