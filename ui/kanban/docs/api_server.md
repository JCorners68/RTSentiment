# CLI Kanban API Server Documentation

## Overview

The CLI Kanban companion server is a lightweight Express.js server that runs alongside the CLI Kanban tool. It provides API endpoints for integration with n8n workflows and external systems, enabling real-time updates and asynchronous processing capabilities.

## Server Architecture

The server follows a modular architecture with the following components:

1. **Express.js Server**: Core HTTP server handling API requests
2. **Route Modules**: Separate modules for different resource types (tasks, epics, evidence)
3. **Authentication Middleware**: Secures webhook endpoints with shared secrets
4. **Configuration System**: Centralized configuration with environment variable support
5. **Python Control Wrapper**: Python interface to start/stop the server from the CLI

## Installation and Setup

The server comes pre-installed with the CLI Kanban tool. It can be started manually or automatically by the CLI when needed.

### Manual Setup

1. Navigate to the server directory:
   ```bash
   cd ui/kanban/server
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the server:
   ```bash
   node index.js
   ```

### Configuration

The server can be configured through environment variables or a `.env` file in the project root. The following configuration options are available:

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `KANBAN_SERVER_PORT` | Port to run the server on | 3000 |
| `KANBAN_SERVER_HOST` | Host to bind the server to | 'localhost' |
| `WEBHOOK_SECRET` | Secret for webhook authentication | 'default-development-secret' |
| `CORS_ORIGINS` | Comma-separated list of allowed CORS origins | 'http://localhost:3000,http://localhost:8080,http://localhost:5678' |
| `LOG_LEVEL` | Server log level | 'info' |
| `LOG_FILE` | Path to log file | './logs/server.log' |
| `N8N_WEBHOOK_URL` | URL for n8n webhooks | 'http://localhost:5678/webhook' |
| `NODE_ENV` | Environment (development, production, test) | 'development' |

## API Endpoints

### Task Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/kanban/tasks` | List all tasks with optional filtering |
| GET | `/api/kanban/task/:id` | Get a specific task by ID |
| POST | `/api/kanban/tasks` | Create a new task |
| PUT | `/api/kanban/task/:id` | Update a task |
| DELETE | `/api/kanban/task/:id` | Delete a task |
| POST | `/api/kanban/task/:id/update` | Special endpoint for n8n callbacks |

#### Query Parameters for Task Listing

- `status`: Filter tasks by status
- `priority`: Filter tasks by priority
- `search`: Search in task title and description

### Epic Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/kanban/epics` | List all epics with optional filtering |
| GET | `/api/kanban/epic/:id` | Get a specific epic by ID |
| POST | `/api/kanban/epics` | Create a new epic |
| PUT | `/api/kanban/epic/:id` | Update an epic |
| DELETE | `/api/kanban/epic/:id` | Delete an epic |
| POST | `/api/kanban/epic/:id/update` | Special endpoint for n8n callbacks |

#### Query Parameters for Epic Listing

- `status`: Filter epics by status
- `search`: Search in epic title and description

### Evidence Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/kanban/evidence` | List all evidence with optional filtering |
| GET | `/api/kanban/evidence/:id` | Get a specific evidence item by ID |
| POST | `/api/kanban/evidence` | Create a new evidence item |
| PUT | `/api/kanban/evidence/:id` | Update an evidence item |
| DELETE | `/api/kanban/evidence/:id` | Delete an evidence item |
| GET | `/api/kanban/evidence/:id/attachments` | List attachments for an evidence item |

#### Query Parameters for Evidence Listing

- `category`: Filter evidence by category
- `relevance`: Filter evidence by minimum relevance score
- `tags`: Filter evidence by tags (comma-separated)
- `search`: Search in evidence title and description

### Server Health Endpoint

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Server health check (not secured) |

## Authentication

All `/api/kanban/*` endpoints are secured with webhook authentication. Clients must include the `x-webhook-secret` header with the correct secret value.

Example authentication:

```javascript
// Node.js example
const axios = require('axios');

axios.get('http://localhost:3000/api/kanban/tasks', {
  headers: {
    'x-webhook-secret': 'your-webhook-secret'
  }
})
.then(response => console.log(response.data))
.catch(error => console.error(error));
```

## Rate Limiting

The server includes basic rate limiting to prevent abuse:

- 100 requests per 15-minute window per IP address
- 429 status code is returned when limit is exceeded

## Python Integration

The CLI Kanban tool includes a Python wrapper to control the server:

```python
from ui.kanban.src.server import start_server, stop_server, get_server_status

# Start the server
start_server()

# Check server status
status = get_server_status()
print(f"Server running: {status['is_running']}")

# Stop the server
stop_server()
```

## Asynchronous Processing Model

The architecture uses an asynchronous processing model:

1. CLI Kanban companion server exposes a local API (localhost:3000)
2. Each CLI command sends a webhook to n8n and returns immediately
3. n8n processes asynchronously and calls back to the local API
4. The CLI Kanban UI refreshes to show updated state

## Error Handling

The server includes robust error handling:

1. All errors are logged to the configured log file
2. Client-facing errors include appropriate HTTP status codes
3. Rate limiting prevents abuse
4. Authentication failures return 401 or 403 status codes
5. Request validation errors return 400 status code with details

## Notifications

The server supports a notification system to inform CLI sessions about changes:

- POST `/api/kanban/notifications` - Send notification to active CLI sessions

## Development and Extending

To add new endpoints:

1. Create a new route file in the `routes` directory
2. Register the route in `index.js`
3. Update documentation

Example of adding a new route:

```javascript
// routes/custom.js
const express = require('express');
const router = express.Router();

router.get('/', (req, res) => {
  res.json({ message: 'Custom endpoint' });
});

module.exports = router;

// In index.js
const customRoutes = require('./routes/custom');
app.use('/api/kanban/custom', customRoutes);
```