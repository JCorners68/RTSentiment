# RT Sentiment Analysis - API Specification

## API Overview

This document specifies the REST and WebSocket APIs provided by the RT Sentiment Analysis system.

## Base URLs

- SIT Environment: `http://localhost:8001/api`
- UAT Environment: `https://uat-sentiment-api.azure.example.com/api`

## Authentication

All API endpoints require authentication unless specified otherwise. Authentication is performed using JWT tokens.

### Obtaining a Token

```
POST /auth/token
```

**Request:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using a Token

Include the token in the Authorization header:

```
Authorization: Bearer {access_token}
```

## REST API Endpoints

### Sentiment Analysis

#### Get Sentiment Analysis Result

```
GET /sentiment/{id}
```

**Parameters:**
- `id` (path): The unique identifier of the sentiment analysis

**Response:**
```json
{
  "id": "string",
  "text": "string",
  "sentiment_score": 0.0,
  "sentiment_label": "positive|neutral|negative",
  "confidence": 0.0,
  "created_at": "2023-01-01T00:00:00Z"
}
```

#### Submit Text for Analysis

```
POST /sentiment
```

**Request:**
```json
{
  "text": "string",
  "source": "string",
  "reference_id": "string"
}
```

**Response:**
```json
{
  "id": "string",
  "status": "queued|processing|completed|failed"
}
```

### Data Sources

#### List Available Data Sources

```
GET /sources
```

**Response:**
```json
{
  "sources": [
    {
      "id": "string",
      "name": "string",
      "description": "string",
      "status": "active|inactive"
    }
  ]
}
```

#### Get Data Source Details

```
GET /sources/{id}
```

**Parameters:**
- `id` (path): The unique identifier of the data source

**Response:**
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "status": "active|inactive",
  "configuration": {
    "key": "value"
  },
  "created_at": "2023-01-01T00:00:00Z",
  "updated_at": "2023-01-01T00:00:00Z"
}
```

### Reports

#### Get Sentiment Analysis Report

```
GET /reports/{id}
```

**Parameters:**
- `id` (path): The unique identifier of the report

**Response:**
```json
{
  "id": "string",
  "title": "string",
  "description": "string",
  "data": [
    {
      "key": "value"
    }
  ],
  "created_at": "2023-01-01T00:00:00Z"
}
```

## WebSocket API

### Connect to WebSocket

```
WebSocket: /ws
```

**Headers:**
- `Authorization`: Bearer {access_token}

### Real-time Sentiment Updates

**Message Format:**
```json
{
  "type": "sentiment_update",
  "data": {
    "id": "string",
    "text": "string",
    "sentiment_score": 0.0,
    "sentiment_label": "positive|neutral|negative",
    "confidence": 0.0,
    "source": "string",
    "reference_id": "string",
    "created_at": "2023-01-01T00:00:00Z"
  }
}
```

## Error Responses

All API endpoints return standard HTTP status codes. Error responses include a JSON body with error details:

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

## Rate Limiting

API requests are subject to rate limiting. The following headers are included in API responses:

- `X-RateLimit-Limit`: The maximum number of requests allowed in the current period
- `X-RateLimit-Remaining`: The number of remaining requests in the current period
- `X-RateLimit-Reset`: The time at which the current rate limit period resets