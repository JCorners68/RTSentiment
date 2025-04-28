# API Documentation

This directory contains comprehensive documentation for the Real-Time Sentiment Analysis system's API endpoints, WebSocket implementation, and integration guides.

## API Documentation Files

- **[API Specification](./API_spec.md)**: Complete API reference with endpoints, parameters, and responses
- **[WebSocket Implementation](./WebSocket_Implementation.md)**: Real-time data streaming protocol and usage
- **[Historical Sentiment API](./historical_sentiment_api.md)**: Access to historical sentiment data
- **[Service Ports](./service_ports.md)**: Port configurations for all system services

## API Overview

The Real-Time Sentiment Analysis system provides several API interfaces:

### REST API Endpoints

The system exposes these primary REST endpoints:

1. **Sentiment Data**
   - `/api/sentiment/current`: Get current sentiment data
   - `/api/sentiment/historical`: Get historical sentiment data
   - `/api/sentiment/ticker/{ticker}`: Get sentiment for specific ticker

2. **Authentication**
   - `/api/auth/login`: Authenticate and receive JWT token
   - `/api/auth/refresh`: Refresh an existing token
   - `/api/auth/validate`: Validate token

3. **Statistics**
   - `/api/stats/system`: Get system performance statistics
   - `/api/stats/data`: Get data collection statistics

4. **Subscriptions**
   - `/api/subscriptions/status`: Get subscription status
   - `/api/subscriptions/manage`: Manage subscription settings

### WebSocket Interface

Real-time updates are provided through WebSockets:

- `ws://host:port/ws/sentiment`: Stream of real-time sentiment updates
- `ws://host:port/ws/stats`: Stream of system statistics updates

## API Implementation

The API is implemented in the `/api/` directory with these key files:

- `/api/main.py`: Main FastAPI application entry point
- `/api/routes/sentiment.py`: Sentiment data endpoints
- `/api/routes/auth.py`: Authentication endpoints
- `/api/routes/stats.py`: Statistics endpoints
- `/api/routes/subscriptions.py`: Subscription management endpoints
- `/api/routes/websocket.py`: WebSocket implementation

## Authentication

The API uses JWT (JSON Web Token) for authentication:

1. Client requests a token via `/api/auth/login`
2. Server validates credentials and returns a JWT
3. Client includes the JWT in subsequent requests
4. Token expiration and refresh mechanisms are implemented

## Data Formats

The API uses these data formats:

- **Requests**: JSON for all REST endpoints
- **Responses**: JSON for all REST responses
- **WebSocket**: JSON messages with standardized event format
- **Errors**: Standard error object with code, message, and details

## Integration Guide

To integrate with the API:

1. **Authentication**: First obtain a JWT token via the login endpoint
2. **REST Queries**: Use REST endpoints for one-time data requests
3. **Real-time Updates**: Connect to WebSocket for continuous updates
4. **Error Handling**: Implement proper handling of error responses
5. **Rate Limiting**: Respect rate limits specified in responses

## Development and Testing

- Use the API documentation to understand available endpoints
- Test endpoints with tools like Postman or curl
- WebSocket connections can be tested with WebSocket client tools
- Check rate limits and token expiration settings during development
