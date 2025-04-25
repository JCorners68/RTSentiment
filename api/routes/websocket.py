"""
WebSocket router for real-time data streaming.
This module provides a WebSocket connection endpoint that allows clients
to subscribe to real-time sentiment updates and other events.
"""
import asyncio
import json
import logging
from typing import Dict, List, Set, Optional, Any
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from routes.auth import oauth2_scheme

# Simple mock user authentication for development
class User:
    def __init__(self, id, username):
        self.id = id
        self.username = username

def get_current_user_from_token(token: str, db=None):
    """
    Mock user authentication for development.
    In a real application, this would validate the token and retrieve the user from the database.
    """
    if token == "demo_token":
        return User(id="demo_user_id", username="demo_user")
    return None

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        # All active connections
        self.active_connections: List[WebSocket] = []
        # Maps connection to user ID
        self.connection_user_map: Dict[WebSocket, str] = {}
        # Maps connection to subscribed channels
        self.connection_channels: Dict[WebSocket, Dict[str, Dict[str, Any]]] = {}
        # Maps tickers to connections subscribed to them
        self.ticker_subscriptions: Dict[str, Set[WebSocket]] = {}
        # Statistics
        self.connection_count = 0
        self.message_count = 0

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept connection and store it"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_user_map[websocket] = user_id
        self.connection_channels[websocket] = {}
        self.connection_count += 1
        logger.info(f"WebSocket connection accepted for user {user_id}. Total connections: {len(self.active_connections)}")
        
        # Send welcome message with connection ID
        await self.send_personal_message(
            {
                "type": "connection_established",
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to sentiment analysis WebSocket server"
            },
            websocket
        )

    def disconnect(self, websocket: WebSocket):
        """Remove connection and clean up subscriptions"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
            # Clean up user mapping
            if websocket in self.connection_user_map:
                user_id = self.connection_user_map.pop(websocket)
                logger.info(f"WebSocket connection closed for user {user_id}. Remaining connections: {len(self.active_connections)}")
            
            # Clean up channel subscriptions
            if websocket in self.connection_channels:
                channels = self.connection_channels.pop(websocket)
                
                # If subscribed to tickers, remove from ticker subscriptions
                if "tickers" in channels:
                    tickers = channels["tickers"].get("tickers", [])
                    for ticker in tickers:
                        if ticker in self.ticker_subscriptions and websocket in self.ticker_subscriptions[ticker]:
                            self.ticker_subscriptions[ticker].remove(websocket)
                            # Clean up empty sets
                            if not self.ticker_subscriptions[ticker]:
                                del self.ticker_subscriptions[ticker]

    async def subscribe(self, websocket: WebSocket, channel: str, filters: Optional[Dict[str, Any]] = None):
        """Subscribe a connection to a channel with optional filters"""
        if websocket not in self.active_connections:
            logger.warning(f"Subscription request from non-active connection")
            return False
        
        # Store subscription details
        self.connection_channels[websocket][channel] = filters or {}
        logger.info(f"Connection subscribed to {channel} with filters: {filters}")
        
        # Handle ticker-specific subscriptions
        if channel == "tickers" and filters and "tickers" in filters:
            tickers = filters["tickers"]
            if isinstance(tickers, list):
                for ticker in tickers:
                    if ticker not in self.ticker_subscriptions:
                        self.ticker_subscriptions[ticker] = set()
                    self.ticker_subscriptions[ticker].add(websocket)
                logger.info(f"Added ticker subscriptions: {tickers}")
        
        # Send confirmation
        await self.send_personal_message(
            {
                "type": "subscription_confirmed",
                "channel": channel,
                "filters": filters,
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )
        return True

    async def unsubscribe(self, websocket: WebSocket, channel: str, filters: Optional[Dict[str, Any]] = None):
        """Unsubscribe a connection from a channel"""
        if websocket not in self.active_connections:
            logger.warning(f"Unsubscribe request from non-active connection")
            return False
        
        # Handle ticker-specific unsubscriptions
        if channel == "tickers" and filters and "tickers" in filters:
            tickers = filters["tickers"]
            if isinstance(tickers, list):
                for ticker in tickers:
                    if ticker in self.ticker_subscriptions and websocket in self.ticker_subscriptions[ticker]:
                        self.ticker_subscriptions[ticker].remove(websocket)
                        # Clean up empty sets
                        if not self.ticker_subscriptions[ticker]:
                            del self.ticker_subscriptions[ticker]
                logger.info(f"Removed ticker subscriptions: {tickers}")
        
        # Remove channel subscription
        if channel in self.connection_channels.get(websocket, {}):
            del self.connection_channels[websocket][channel]
            logger.info(f"Connection unsubscribed from {channel}")
        
        # Send confirmation
        await self.send_personal_message(
            {
                "type": "unsubscription_confirmed",
                "channel": channel,
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )
        return True

    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send a message to a specific client"""
        if websocket in self.active_connections:
            try:
                await websocket.send_json(message)
                self.message_count += 1
            except Exception as e:
                logger.error(f"Error sending message to client: {e}")

    async def broadcast(self, message: Dict[str, Any]):
        """Send a message to all connected clients"""
        disconnect_list = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                self.message_count += 1
            except Exception as e:
                logger.error(f"Error broadcasting message to client: {e}")
                disconnect_list.append(connection)
        
        # Clean up any failed connections
        for connection in disconnect_list:
            self.disconnect(connection)

    async def broadcast_ticker_update(self, ticker: str, ticker_data: Dict[str, Any]):
        """Send a ticker update to all subscribed clients"""
        if ticker not in self.ticker_subscriptions:
            return
        
        message = {
            "type": "ticker_update",
            "data": ticker_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        disconnect_list = []
        for connection in self.ticker_subscriptions[ticker]:
            try:
                await connection.send_json(message)
                self.message_count += 1
            except Exception as e:
                logger.error(f"Error sending ticker update to client: {e}")
                disconnect_list.append(connection)
        
        # Clean up any failed connections
        for connection in disconnect_list:
            self.disconnect(connection)

    async def broadcast_sentiment_event(self, event_data: Dict[str, Any]):
        """Broadcast a sentiment event to relevant clients"""
        # Prepare the message
        message = {
            "type": "sentiment_event",
            "data": event_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to clients subscribed to the events channel
        event_subscribers = set()
        disconnect_list = []
        
        # Find all clients subscribed to events channel
        for connection, channels in self.connection_channels.items():
            if "events" in channels:
                event_subscribers.add(connection)
        
        # Send message to all event subscribers
        for connection in event_subscribers:
            try:
                await connection.send_json(message)
                self.message_count += 1
            except Exception as e:
                logger.error(f"Error sending sentiment event to client: {e}")
                disconnect_list.append(connection)
        
        # Also send to ticker-specific subscribers if applicable
        if "ticker_sentiments" in event_data:
            for ticker_data in event_data["ticker_sentiments"]:
                for ticker in ticker_data.keys():
                    if ticker in self.ticker_subscriptions:
                        for connection in self.ticker_subscriptions[ticker]:
                            if connection not in event_subscribers:  # Avoid sending twice
                                try:
                                    await connection.send_json(message)
                                    self.message_count += 1
                                except Exception as e:
                                    logger.error(f"Error sending ticker-specific sentiment event: {e}")
                                    disconnect_list.append(connection)
        
        # Clean up any failed connections
        for connection in disconnect_list:
            self.disconnect(connection)

    async def broadcast_system_stats(self, stats_data: Dict[str, Any]):
        """Broadcast system stats to all clients"""
        message = {
            "type": "system_stats",
            "data": stats_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast(message)

    async def broadcast_data_flow(self, data_point: Dict[str, Any]):
        """Broadcast data flow point to all clients"""
        message = {
            "type": "data_flow",
            "data": data_point,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        await self.broadcast(message)

    def get_stats(self):
        """Get connection statistics"""
        return {
            "active_connections": len(self.active_connections),
            "total_connections": self.connection_count,
            "messages_sent": self.message_count,
            "ticker_subscriptions": {ticker: len(conns) for ticker, conns in self.ticker_subscriptions.items()},
            "timestamp": datetime.utcnow().isoformat()
        }


# Create a connection manager instance
manager = ConnectionManager()

# Helper function for handling WebSocket connections
async def handle_websocket_connection(websocket: WebSocket, token: Optional[str], db: Session):
    """Process a WebSocket connection with authentication and message handling"""
    # Special handling for development/demo token
    if token == "demo_token":
        # For development purposes, accept demo_token without validation
        logger.info("Accepting demo token for development purposes")
        user_id = "demo_user"
    else:
        # Standard authentication for production use
        # Authenticate the connection
        if token is None:
            await websocket.close(code=1008, reason="Missing authentication token")
            return
        
        try:
            # Validate the token and get the user
            current_user = get_current_user_from_token(token, db)
            if current_user is None:
                await websocket.close(code=1008, reason="Invalid authentication token")
                return
            
            user_id = str(current_user.id)
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            await websocket.close(code=1008, reason="Authentication error")
            return
    
    # Accept the connection
    await manager.connect(websocket, user_id)
    
    try:
        # Handle messages until disconnection
        while True:
            # Wait for messages from the client
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    channel = message.get("channel")
                    filters = message.get("filters")
                    if channel:
                        await manager.subscribe(websocket, channel, filters)
                
                elif action == "unsubscribe":
                    channel = message.get("channel")
                    filters = message.get("filters")
                    if channel:
                        await manager.unsubscribe(websocket, channel, filters)
                
                elif action == "ping":
                    # Respond to heartbeat requests
                    await manager.send_personal_message(
                        {"type": "pong", "timestamp": datetime.utcnow().isoformat()},
                        websocket
                    )
                
                else:
                    # Unknown action
                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "error": "Unknown action",
                            "received": message,
                            "timestamp": datetime.utcnow().isoformat()
                        },
                        websocket
                    )
            
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "error": "Invalid JSON",
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    websocket
                )
                
    except WebSocketDisconnect:
        # Client disconnected
        manager.disconnect(websocket)
    
    except Exception as e:
        # Handle other errors
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Define WebSocket endpoints for all paths the Flutter client might try
@router.websocket("/ws")
async def websocket_endpoint_primary(
    websocket: WebSocket, 
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Primary WebSocket endpoint at /ws
    """
    await handle_websocket_connection(websocket, token, db)

@router.websocket("/api/ws")
async def websocket_endpoint_api(
    websocket: WebSocket, 
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Alternative WebSocket endpoint at /api/ws
    """
    await handle_websocket_connection(websocket, token, db)
    
@router.websocket("/sentiment/ws")
async def websocket_endpoint_sentiment(
    websocket: WebSocket, 
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Alternative WebSocket endpoint at /sentiment/ws
    """
    await handle_websocket_connection(websocket, token, db)
    
@router.websocket("/socket")
async def websocket_endpoint_socket(
    websocket: WebSocket, 
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Alternative WebSocket endpoint at /socket
    """
    await handle_websocket_connection(websocket, token, db)
    
@router.websocket("/websocket")
async def websocket_endpoint_websocket(
    websocket: WebSocket, 
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Alternative WebSocket endpoint at /websocket
    """
    await handle_websocket_connection(websocket, token, db)
    
@router.websocket("/live")
async def websocket_endpoint_live(
    websocket: WebSocket, 
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Alternative WebSocket endpoint at /live
    """
    await handle_websocket_connection(websocket, token, db)
    
@router.websocket("/realtime")
async def websocket_endpoint_realtime(
    websocket: WebSocket, 
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Alternative WebSocket endpoint at /realtime
    """
    await handle_websocket_connection(websocket, token, db)

# We can't use paths without a leading slash in FastAPI,
# so we'll handle the path handling in the Flutter client instead.

# Root WebSocket endpoint for clients that might try the root path
@router.websocket("/")
async def websocket_endpoint_root(
    websocket: WebSocket, 
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Root WebSocket endpoint
    """
    await handle_websocket_connection(websocket, token, db)


# ------- Event publishing API for internal use -------

async def publish_ticker_update(ticker: str, ticker_data: Dict[str, Any]):
    """Publish a ticker update to subscribed clients"""
    await manager.broadcast_ticker_update(ticker, ticker_data)

async def publish_sentiment_event(event_data: Dict[str, Any]):
    """Publish a sentiment event to subscribed clients"""
    await manager.broadcast_sentiment_event(event_data)

async def publish_system_stats(stats_data: Dict[str, Any]):
    """Publish system stats to all clients"""
    await manager.broadcast_system_stats(stats_data)

async def publish_data_flow(data_point: Dict[str, Any]):
    """Publish a data flow point to all clients"""
    await manager.broadcast_data_flow(data_point)

def get_connection_stats():
    """Get WebSocket connection statistics"""
    return manager.get_stats()