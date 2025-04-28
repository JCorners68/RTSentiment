# Verbosity Control System for RT Sentiment

This document outlines an enhanced verbosity control system that integrates with the existing observability architecture to provide fine-grained visibility into system components.

## Overview

The Verbosity Control System allows operators to dynamically adjust logging levels and debug information across all system components without service restarts. This provides:

1. **Component-Level Verbosity**: Adjust logging detail per component
2. **Runtime Configuration**: Change verbosity without service restarts
3. **Port-Based Monitoring**: Access metrics and logs through dedicated ports
4. **Centralized Control**: Unified interface for verbosity management
5. **Integration with Existing Observability**: Enhanced visibility in Grafana

## Architecture Integration

The Verbosity Control System extends the current observability architecture:

```
┌───────────────────────────────────────────────────────────────┐
│                     RT Sentiment System                        │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│  │             │   │             │   │             │          │
│  │    Data     │   │  Sentiment  │   │     API     │  ...     │
│  │ Acquisition │   │   Service   │   │   Service   │          │
│  │             │   │             │   │             │          │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘          │
│         │                 │                 │                 │
│   ┌─────▼─────┐     ┌─────▼─────┐     ┌─────▼─────┐           │
│   │ Verbosity │     │ Verbosity │     │ Verbosity │           │
│   │ Endpoint  │     │ Endpoint  │     │ Endpoint  │           │
│   │ Port:9100 │     │ Port:9000 │     │ Port:9001 │           │
│   └─────┬─────┘     └─────┬─────┘     └─────┬─────┘           │
└─────────┼─────────────────┼─────────────────┼─────────────────┘
          │                 │                 │
┌─────────▼─────────────────▼─────────────────▼─────────────────┐
│                   Observability System                         │
│                                                                │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     │
│   │             │     │             │     │             │     │
│   │  Prometheus │────►│   Grafana   │     │ VerbosityUI │     │
│   │             │     │             │     │             │     │
│   └─────────────┘     └──────┬──────┘     └──────┬──────┘     │
│                              │                   │            │
│                      ┌───────▼───────────────────▼────────┐   │
│                      │                                     │   │
│                      │        Unified Dashboard            │   │
│                      │                                     │   │
│                      └─────────────────────────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Component Design

### 1. Verbosity Controller

Each service will implement a verbosity controller with these endpoints:

- **GET /verbosity** - Return current verbosity settings
- **PUT /verbosity** - Update verbosity settings
- **GET /logs** - Stream logs at the current verbosity level
- **GET /metrics** - Prometheus metrics endpoint (existing)
- **GET /health** - Service health check (existing)

### 2. Service-Specific Ports

Each component exposes metrics and verbosity controls on dedicated ports:

| Service             | Application | Metrics/Verbosity | Health Check |
|---------------------|-------------|-------------------|--------------|
| Data Acquisition    | 8100        | 9100              | 8500         |
| Sentiment Service   | 8000        | 9000              | 8501         |
| API Service         | 8001        | 9001              | 8502         |
| Iceberg/Dremio      | 9047        | 9047              | 8503         |
| Redis Cache         | 6379        | 9379              | 8504         |

### 3. Verbosity Configuration

The system supports five verbosity levels:

1. **ERROR** - Only error conditions are logged
2. **WARN** - Warnings and errors
3. **INFO** - General operational information (default)
4. **DEBUG** - Detailed information for debugging
5. **TRACE** - Fine-grained tracing of execution

## Implementation

### 1. Logger Implementation

```python
# logger.py - To be used in all components
import logging
import os
import json
import threading
from datetime import datetime
from typing import Dict, Any

class VerbosityLogger:
    """Logger with dynamic verbosity control."""

    # Map log level names to Python logging levels
    LEVEL_MAP = {
        "ERROR": logging.ERROR,
        "WARN": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "TRACE": logging.DEBUG,  # Python logging doesn't have TRACE
    }

    def __init__(self, component_name: str, default_level: str = "INFO"):
        """Initialize the verbosity logger.
        
        Args:
            component_name: Name of the component for logging context
            default_level: Default verbosity level
        """
        self.component_name = component_name
        self.default_level = default_level
        self.current_level = os.environ.get(
            f"{component_name.upper()}_VERBOSITY", 
            os.environ.get("VERBOSITY", default_level)
        )
        self.logger = self._create_logger()
        self.recent_logs = []
        self.log_lock = threading.Lock()
        self.max_recent_logs = 1000  # Store recent logs for retrieval

    def _create_logger(self):
        """Create the underlying logger with proper configuration."""
        logger = logging.getLogger(self.component_name)
        level = self.LEVEL_MAP.get(self.current_level, logging.INFO)
        logger.setLevel(level)
        
        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # Create handler that captures logs for access through API
        class MemoryHandler(logging.Handler):
            def __init__(self, parent):
                super().__init__()
                self.parent = parent
                
            def emit(self, record):
                log_entry = {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": record.levelname,
                    "component": self.parent.component_name,
                    "message": record.getMessage(),
                    "logger": record.name,
                    "path": record.pathname,
                    "lineno": record.lineno,
                    "thread": record.threadName,
                }
                
                # Add extra fields from record
                for key, value in record.__dict__.items():
                    if key not in ["args", "asctime", "created", "exc_info", 
                                   "filename", "funcName", "id", "levelname", 
                                   "levelno", "lineno", "module", "msecs", 
                                   "message", "msg", "name", "pathname", 
                                   "process", "processName", "relativeCreated", 
                                   "stack_info", "thread", "threadName"]:
                        log_entry[key] = value
                
                # Add exception info if present
                if record.exc_info:
                    log_entry["exception"] = {
                        "type": record.exc_info[0].__name__,
                        "message": str(record.exc_info[1]),
                        "traceback": self.formatter.formatException(record.exc_info),
                    }
                
                with self.parent.log_lock:
                    self.parent.recent_logs.append(log_entry)
                    # Trim logs if needed
                    if len(self.parent.recent_logs) > self.parent.max_recent_logs:
                        self.parent.recent_logs = self.parent.recent_logs[-self.parent.max_recent_logs:]
        
        # Console handler for terminal output
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Memory handler for API access
        memory_handler = MemoryHandler(self)
        memory_handler.setFormatter(formatter)
        logger.addHandler(memory_handler)
        
        return logger

    def set_verbosity(self, level: str) -> bool:
        """Set the verbosity level dynamically.
        
        Args:
            level: New verbosity level (ERROR, WARN, INFO, DEBUG, TRACE)
            
        Returns:
            bool: True if successful, False otherwise
        """
        if level in self.LEVEL_MAP:
            self.current_level = level
            # Update the logger level
            self.logger.setLevel(self.LEVEL_MAP[level])
            # Also update environment variable for child processes
            os.environ[f"{self.component_name.upper()}_VERBOSITY"] = level
            self.info(f"Verbosity level changed to {level}")
            return True
        return False

    def get_verbosity(self) -> str:
        """Get current verbosity level.
        
        Returns:
            str: Current verbosity level
        """
        return self.current_level

    def get_recent_logs(self, count: int = 100, level: str = None) -> list:
        """Get recent logs, optionally filtered by level.
        
        Args:
            count: Maximum number of logs to return
            level: Filter by log level
            
        Returns:
            list: Recent log entries
        """
        with self.log_lock:
            if level:
                filtered = [log for log in self.recent_logs if log["level"] == level]
                return filtered[-count:]
            else:
                return self.recent_logs[-count:]

    # Standard logging methods
    def error(self, msg, *args, **kwargs):
        """Log an error message."""
        self.logger.error(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """Log a warning message."""
        self.logger.warning(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """Log an info message."""
        self.logger.info(msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        """Log a debug message."""
        self.logger.debug(msg, *args, **kwargs)

    def trace(self, msg, *args, **kwargs):
        """Log a trace message (very detailed)."""
        if self.current_level == "TRACE":
            self.logger.debug(f"[TRACE] {msg}", *args, **kwargs)
```

### 2. FastAPI Verbosity Controller

```python
# verbosity_controller.py - Used in each service

from fastapi import APIRouter, FastAPI, Response, Query
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List, Optional
import asyncio
import json
import time

class VerbosityController:
    """Controller for verbosity settings and log access."""
    
    def __init__(self, app: FastAPI, logger: 'VerbosityLogger'):
        """Initialize the verbosity controller.
        
        Args:
            app: FastAPI application
            logger: VerbosityLogger instance
        """
        self.app = app
        self.logger = logger
        self.router = APIRouter(tags=["verbosity"])
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up the API routes."""
        
        @self.router.get("/verbosity")
        async def get_verbosity() -> Dict[str, Any]:
            """Get current verbosity settings."""
            return {
                "component": self.logger.component_name,
                "level": self.logger.get_verbosity(),
                "available_levels": list(self.logger.LEVEL_MAP.keys())
            }
        
        @self.router.put("/verbosity")
        async def set_verbosity(level: str) -> Dict[str, Any]:
            """Set verbosity level.
            
            Args:
                level: New verbosity level
            """
            success = self.logger.set_verbosity(level.upper())
            return {
                "component": self.logger.component_name,
                "level": self.logger.get_verbosity(),
                "updated": success,
                "message": "Verbosity updated successfully" if success else "Invalid verbosity level"
            }
        
        @self.router.get("/logs")
        async def get_logs(
            count: int = Query(100, gt=0, lt=10000),
            level: Optional[str] = None,
            format: str = Query("json", regex="^(json|text)$")
        ):
            """Get recent logs with optional filtering.
            
            Args:
                count: Maximum number of logs to return
                level: Filter by log level
                format: Output format (json or text)
            """
            logs = self.logger.get_recent_logs(count, level)
            
            if format == "text":
                # Return plain text logs
                text_logs = []
                for log in logs:
                    msg = f"{log['timestamp']} [{log['level']}] {log['component']}: {log['message']}"
                    if 'exception' in log:
                        msg += f"\n{log['exception']['type']}: {log['exception']['message']}\n{log['exception']['traceback']}"
                    text_logs.append(msg)
                
                return Response(
                    content="\n".join(text_logs),
                    media_type="text/plain"
                )
            else:
                # Return JSON logs
                return {"logs": logs, "count": len(logs)}
        
        @self.router.get("/logs/stream")
        async def stream_logs(level: Optional[str] = None):
            """Stream logs in real-time.
            
            Args:
                level: Filter by log level
            """
            # This implements server-sent events (SSE)
            async def event_generator():
                last_log_count = len(self.logger.recent_logs)
                
                while True:
                    current_count = len(self.logger.recent_logs)
                    
                    if current_count > last_log_count:
                        # New logs have been added
                        new_logs = self.logger.recent_logs[last_log_count:current_count]
                        last_log_count = current_count
                        
                        # Filter by level if specified
                        if level:
                            new_logs = [log for log in new_logs if log["level"] == level]
                        
                        # Send each log as an event
                        for log in new_logs:
                            yield f"data: {json.dumps(log)}\n\n"
                    
                    await asyncio.sleep(0.5)
            
            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream"
            )
        
        # Add the router to the app
        self.app.include_router(self.router)
```

### 3. Docker Compose Configuration

Update the docker-compose.yml file to add verbosity configuration:

```yaml
# Verbosity-enabled services section in docker-compose.yml
services:
  data-acquisition:
    image: rtsentiment/data-acquisition:latest
    ports:
      - "8100:8100"  # Application
      - "9100:9100"  # Metrics/Verbosity
      - "8500:8500"  # Health
    environment:
      - VERBOSITY=INFO                   # System-wide default
      - DATA_ACQUISITION_VERBOSITY=INFO  # Component-specific
      - METRICS_PORT=9100
      - HEALTH_PORT=8500
      
  sentiment-service:
    image: rtsentiment/sentiment-service:latest
    ports:
      - "8000:8000"  # Application
      - "9000:9000"  # Metrics/Verbosity
      - "8501:8501"  # Health
    environment:
      - VERBOSITY=INFO
      - SENTIMENT_SERVICE_VERBOSITY=INFO
      - METRICS_PORT=9000
      - HEALTH_PORT=8501
      
  api:
    image: rtsentiment/api:latest
    ports:
      - "8001:8001"  # Application
      - "9001:9001"  # Metrics/Verbosity
      - "8502:8502"  # Health
    environment:
      - VERBOSITY=INFO
      - API_VERBOSITY=INFO
      - METRICS_PORT=9001
      - HEALTH_PORT=8502
```

## Usage Examples

### 1. Component Integration

In each service component:

```python
# main.py for any service component
from fastapi import FastAPI
from logger import VerbosityLogger
from verbosity_controller import VerbosityController

# Create the FastAPI application
app = FastAPI(title="Service Name")

# Initialize the verbosity logger
logger = VerbosityLogger("component_name")

# Set up verbosity controller
controller = VerbosityController(app, logger)

# Example usage in application code
@app.get("/sample")
async def sample_endpoint():
    # Different verbosity levels
    logger.error("Critical error occurred")
    logger.warning("Warning condition detected")
    logger.info("Normal operational information")
    logger.debug("Detailed debugging information")
    logger.trace("Fine-grained tracing information")
    
    return {"status": "ok"}
```

### 2. Accessing Verbosity Controls

#### Command-Line Examples

```bash
# Get current verbosity for data acquisition service
curl http://localhost:9100/verbosity

# Set verbosity to DEBUG for sentiment service
curl -X PUT http://localhost:9000/verbosity?level=DEBUG

# Get recent logs from API service
curl http://localhost:9001/logs?count=50&level=ERROR

# Stream logs in real-time from data acquisition
curl http://localhost:9100/logs/stream
```

#### Grafana Integration

Create a dashboard with dynamic verbosity controls:

1. Add a dashboard variable for verbosity levels:
   - Name: `verbosity_level`
   - Type: `Custom`
   - Values: `ERROR,WARN,INFO,DEBUG,TRACE`

2. Add a dashboard variable for component selection:
   - Name: `component`
   - Type: `Custom`
   - Values: `data-acquisition,sentiment-service,api`

3. Add a panel with an HTTP request to change verbosity:
   ```
   PUT http://${component}:${component_port}/verbosity?level=${verbosity_level}
   ```

4. Add a logs panel that pulls from the logs endpoint:
   ```
   GET http://${component}:${component_port}/logs?count=100
   ```

## Benefits

1. **Real-time Visibility**: See exactly what's happening in each component
2. **Targeted Debugging**: Increase verbosity only for problematic components
3. **Resource Efficiency**: Control logging overhead in production
4. **Operational Flexibility**: Change logging behavior without restarts
5. **Improved Troubleshooting**: Easily correlate logs with metrics

## Conclusion

This verbosity control system enhances the existing observability architecture by providing fine-grained control over logging and debug information. By exposing component-specific ports and standardized endpoints, operators can easily adjust verbosity levels and access detailed logs as needed, without disrupting production operations.