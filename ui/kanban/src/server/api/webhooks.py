"""
Webhook Handlers for Evidence Automation.

This module provides webhook handlers for automating evidence management,
including creation, updates, categorization, and relationship management.
"""
import json
import uuid
import hmac
import hashlib
import logging
import requests
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
from functools import wraps

from flask import Blueprint, request, jsonify, current_app, g, abort
import queue

from ...data.evidence_storage import EvidenceStorage
from ...models.evidence_schema import EvidenceSchema
from ...models.relationship_models import RelationshipRegistry
from ..auth import require_auth, current_user
from .rate_limit import rate_limit

# Configure module logger
logger = logging.getLogger(__name__)

# Create blueprint
webhook_bp = Blueprint('webhooks', __name__, url_prefix='/api/webhooks')

# Global webhook queue for retry processing
webhook_queue = queue.PriorityQueue()

# Global registry of webhook handlers
webhook_handlers = {}

# Global registry of webhook subscriptions
webhook_subscriptions = {}

# Lock for thread safety
webhook_lock = threading.RLock()


class WebhookEvent:
    """Represents a webhook event type."""
    
    # Evidence events
    EVIDENCE_CREATED = "evidence.created"
    EVIDENCE_UPDATED = "evidence.updated"
    EVIDENCE_DELETED = "evidence.deleted"
    
    # Attachment events
    ATTACHMENT_ADDED = "attachment.added"
    ATTACHMENT_REMOVED = "attachment.removed"
    
    # Categorization events
    CATEGORY_ASSIGNED = "category.assigned"
    CATEGORY_REMOVED = "category.removed"
    
    # Tag events
    TAG_ADDED = "tag.added"
    TAG_REMOVED = "tag.removed"
    
    # Relationship events
    RELATIONSHIP_CREATED = "relationship.created"
    RELATIONSHIP_UPDATED = "relationship.updated"
    RELATIONSHIP_DELETED = "relationship.deleted"
    
    @classmethod
    def all_events(cls) -> List[str]:
        """Get all available event types."""
        return [
            cls.EVIDENCE_CREATED,
            cls.EVIDENCE_UPDATED,
            cls.EVIDENCE_DELETED,
            cls.ATTACHMENT_ADDED,
            cls.ATTACHMENT_REMOVED,
            cls.CATEGORY_ASSIGNED,
            cls.CATEGORY_REMOVED,
            cls.TAG_ADDED,
            cls.TAG_REMOVED,
            cls.RELATIONSHIP_CREATED,
            cls.RELATIONSHIP_UPDATED,
            cls.RELATIONSHIP_DELETED,
        ]


class WebhookSubscription:
    """Represents a webhook subscription."""
    
    def __init__(self, 
                 id: str,
                 url: str,
                 events: List[str],
                 description: Optional[str] = None,
                 secret: Optional[str] = None,
                 created_by: Optional[str] = None,
                 active: bool = True):
        """
        Initialize a webhook subscription.
        
        Args:
            id: Unique identifier for the subscription
            url: URL to send webhook events to
            events: List of event types to subscribe to
            description: Optional description
            secret: Optional secret for signing webhook payloads
            created_by: Optional user ID who created the subscription
            active: Whether the subscription is active
        """
        self.id = id
        self.url = url
        self.events = events
        self.description = description or f"Webhook subscription to {url}"
        self.secret = secret
        self.created_by = created_by
        self.active = active
        
        # Statistics
        self.created_at = datetime.now()
        self.last_delivery = None
        self.successful_deliveries = 0
        self.failed_deliveries = 0
    
    def to_dict(self, include_secret: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary for API responses.
        
        Args:
            include_secret: Whether to include the secret in the response
        
        Returns:
            Dictionary representation of the subscription
        """
        result = {
            "id": self.id,
            "url": self.url,
            "events": self.events,
            "description": self.description,
            "active": self.active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "last_delivery": self.last_delivery.isoformat() if self.last_delivery else None,
            "stats": {
                "successful_deliveries": self.successful_deliveries,
                "failed_deliveries": self.failed_deliveries,
            }
        }
        
        if include_secret and self.secret:
            result["secret"] = self.secret
            
        return result
    
    def sign_payload(self, payload: str) -> str:
        """
        Sign a webhook payload.
        
        Args:
            payload: JSON payload as string
            
        Returns:
            HMAC signature as hex string
        """
        if not self.secret:
            return ""
            
        return hmac.new(
            self.secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def matches_event(self, event_type: str) -> bool:
        """
        Check if this subscription matches an event type.
        
        Args:
            event_type: Event type to check
            
        Returns:
            True if the subscription matches the event
        """
        # Check if subscription is active
        if not self.active:
            return False
            
        # Check if event is in the subscription's event list
        return event_type in self.events or "*" in self.events


class WebhookDelivery:
    """Represents a webhook delivery attempt."""
    
    def __init__(self, 
                 event_type: str,
                 payload: Dict[str, Any],
                 subscription_id: str,
                 delivery_id: Optional[str] = None):
        """
        Initialize a webhook delivery.
        
        Args:
            event_type: Type of event
            payload: Event payload
            subscription_id: ID of the subscription
            delivery_id: Optional unique ID for the delivery
        """
        self.event_type = event_type
        self.payload = payload
        self.subscription_id = subscription_id
        self.delivery_id = delivery_id or f"del_{uuid.uuid4()}"
        
        # Delivery status
        self.attempts = 0
        self.max_attempts = 5
        self.last_attempt = None
        self.next_attempt = None
        self.status = "pending"
        self.response = None
        self.error = None
        
        # Calculate retry delays using exponential backoff
        self.retry_delays = [30, 60, 300, 600, 1800]  # 30s, 1m, 5m, 10m, 30m
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for API responses.
        
        Returns:
            Dictionary representation of the delivery
        """
        return {
            "delivery_id": self.delivery_id,
            "event_type": self.event_type,
            "subscription_id": self.subscription_id,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "last_attempt": self.last_attempt.isoformat() if self.last_attempt else None,
            "next_attempt": self.next_attempt.isoformat() if self.next_attempt else None,
            "status": self.status,
            "response": self.response,
            "error": self.error,
        }
    
    def prepare_for_retry(self) -> None:
        """Prepare the delivery for retry."""
        self.attempts += 1
        self.last_attempt = datetime.now()
        
        # Calculate next retry time
        if self.attempts < len(self.retry_delays):
            delay = self.retry_delays[self.attempts - 1]
            self.next_attempt = datetime.now() + timedelta(seconds=delay)
        else:
            # Maximum retries reached
            self.status = "failed"
            self.next_attempt = None
    
    def get_priority(self) -> int:
        """
        Get the priority for the queue.
        
        Returns:
            Priority value (lower is higher priority)
        """
        if self.next_attempt:
            # Convert to Unix timestamp for priority
            return int(self.next_attempt.timestamp())
        return int(datetime.now().timestamp()) + 999999  # Very low priority for failed deliveries


# Webhook delivery functions

def deliver_webhook(delivery: WebhookDelivery) -> bool:
    """
    Deliver a webhook to its destination.
    
    Args:
        delivery: WebhookDelivery object
        
    Returns:
        True if delivery was successful, False otherwise
    """
    # Get the subscription
    subscription = webhook_subscriptions.get(delivery.subscription_id)
    if not subscription or not subscription.active:
        logger.warning(f"Subscription {delivery.subscription_id} not found or inactive")
        delivery.status = "failed"
        delivery.error = "Subscription not found or inactive"
        return False
    
    try:
        # Prepare payload
        payload = {
            "id": delivery.delivery_id,
            "event": delivery.event_type,
            "timestamp": datetime.now().isoformat(),
            "attempt": delivery.attempts + 1,
            "data": delivery.payload
        }
        
        # Convert to JSON string
        json_payload = json.dumps(payload)
        
        # Sign payload if secret is present
        signature = subscription.sign_payload(json_payload) if subscription.secret else ""
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Kanban-Evidence-Webhook/1.0",
            "X-Webhook-ID": delivery.delivery_id,
            "X-Webhook-Event": delivery.event_type,
            "X-Webhook-Signature": signature
        }
        
        # Send the webhook
        start_time = time.time()
        response = requests.post(
            subscription.url,
            data=json_payload,
            headers=headers,
            timeout=10  # 10 second timeout
        )
        duration = time.time() - start_time
        
        # Update delivery stats
        delivery.attempts += 1
        delivery.last_attempt = datetime.now()
        
        # Update subscription stats
        subscription.last_delivery = datetime.now()
        
        # Check if delivery was successful
        if response.status_code >= 200 and response.status_code < 300:
            # Success
            delivery.status = "delivered"
            delivery.response = {
                "status_code": response.status_code,
                "body": response.text[:1000],  # Limit response body size
                "duration_ms": int(duration * 1000)
            }
            subscription.successful_deliveries += 1
            logger.info(f"Webhook delivered successfully: {delivery.delivery_id} to {subscription.url}")
            return True
        else:
            # Error
            delivery.prepare_for_retry()
            delivery.response = {
                "status_code": response.status_code,
                "body": response.text[:1000],  # Limit response body size
                "duration_ms": int(duration * 1000)
            }
            subscription.failed_deliveries += 1
            logger.warning(f"Webhook delivery failed: {delivery.delivery_id} to {subscription.url}. Status code: {response.status_code}")
            return False
            
    except requests.RequestException as e:
        # Connection error
        delivery.prepare_for_retry()
        delivery.error = f"Connection error: {str(e)}"
        subscription.failed_deliveries += 1
        logger.warning(f"Webhook delivery failed: {delivery.delivery_id} to {subscription.url}. Error: {str(e)}")
        return False
    except Exception as e:
        # Unexpected error
        delivery.prepare_for_retry()
        delivery.error = f"Unexpected error: {str(e)}"
        subscription.failed_deliveries += 1
        logger.exception(f"Unexpected error delivering webhook: {delivery.delivery_id} to {subscription.url}")
        return False


def queue_webhook(event_type: str, payload: Dict[str, Any]) -> List[str]:
    """
    Queue a webhook for delivery to all matching subscriptions.
    
    Args:
        event_type: Type of event
        payload: Event payload
        
    Returns:
        List of delivery IDs
    """
    delivery_ids = []
    
    with webhook_lock:
        # Find matching subscriptions
        for subscription_id, subscription in webhook_subscriptions.items():
            if subscription.matches_event(event_type):
                # Create a delivery for this subscription
                delivery = WebhookDelivery(
                    event_type=event_type,
                    payload=payload,
                    subscription_id=subscription_id
                )
                
                # Add to queue with immediate delivery
                webhook_queue.put((0, delivery))
                delivery_ids.append(delivery.delivery_id)
                
                logger.debug(f"Queued webhook delivery {delivery.delivery_id} for event {event_type} to {subscription.url}")
    
    return delivery_ids


def process_webhook_queue():
    """
    Process the webhook delivery queue.
    
    This function should be called periodically to process the queue.
    """
    processed = 0
    now = datetime.now().timestamp()
    
    while not webhook_queue.empty():
        try:
            # Peek at the next item
            priority, delivery = webhook_queue.queue[0]
            
            # Check if it's time to process this delivery
            if delivery.next_attempt and delivery.next_attempt.timestamp() > now:
                # Not yet time to process
                break
                
            # Get the item from the queue
            priority, delivery = webhook_queue.get()
            
            # Deliver the webhook
            success = deliver_webhook(delivery)
            
            # Check if we need to retry
            if not success and delivery.status == "retrying":
                # Re-queue with updated priority
                webhook_queue.put((delivery.get_priority(), delivery))
            
            processed += 1
            
            # Don't process too many at once
            if processed >= 10:
                break
                
        except Exception as e:
            logger.exception(f"Error processing webhook queue: {str(e)}")
            break
    
    return processed


# Start a background thread to process the webhook queue
class WebhookProcessor(threading.Thread):
    """Background thread to process webhooks."""
    
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
        
    def run(self):
        logger.info("Started webhook processor thread")
        
        while self.running:
            try:
                # Process the queue
                processed = process_webhook_queue()
                
                # Sleep based on whether we processed anything
                if processed > 0:
                    # Sleep a short time if we processed items
                    time.sleep(1)
                else:
                    # Sleep longer if the queue was empty
                    time.sleep(15)
            except Exception as e:
                logger.exception(f"Error in webhook processor thread: {str(e)}")
                time.sleep(30)  # Sleep longer after an error
        
        logger.info("Stopped webhook processor thread")
        
    def stop(self):
        self.running = False


# Create and register webhook handlers
def register_webhook_handler(event_type: str, handler: Callable):
    """
    Register a handler for an event type.
    
    Args:
        event_type: Event type to handle
        handler: Function to handle the event
    """
    webhook_handlers[event_type] = handler
    logger.info(f"Registered webhook handler for {event_type}")


# API routes for webhook management
@webhook_bp.route('/subscriptions', methods=['GET'])
@require_auth
def list_subscriptions():
    """
    List all webhook subscriptions.
    
    Returns:
        JSON response with subscriptions
    """
    # Get all subscriptions
    subscriptions = [s.to_dict() for s in webhook_subscriptions.values()]
    
    return jsonify({
        "subscriptions": subscriptions
    })


@webhook_bp.route('/subscriptions', methods=['POST'])
@require_auth
@rate_limit(limit=10, period=60)  # 10 subscription creations per minute
def create_subscription():
    """
    Create a new webhook subscription.
    
    Returns:
        JSON response with the new subscription
    """
    try:
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400
            
        url = data.get('url')
        events = data.get('events', [])
        description = data.get('description')
        
        # Validate URL
        if not url:
            return jsonify({"error": "Missing URL"}), 400
            
        # Validate events
        if not events:
            return jsonify({"error": "No events specified"}), 400
            
        # Check if events are valid
        for event in events:
            if event != "*" and event not in WebhookEvent.all_events():
                return jsonify({"error": f"Invalid event type: {event}"}), 400
                
        # Generate secret if not provided
        secret = data.get('secret') or hashlib.sha256(str(uuid.uuid4()).encode()).hexdigest()
        
        # Create subscription
        subscription_id = f"sub_{uuid.uuid4()}"
        subscription = WebhookSubscription(
            id=subscription_id,
            url=url,
            events=events,
            description=description,
            secret=secret,
            created_by=current_user()
        )
        
        # Add to registry
        with webhook_lock:
            webhook_subscriptions[subscription_id] = subscription
            
        logger.info(f"Created webhook subscription {subscription_id} for {url}")
        
        # Return subscription with secret
        return jsonify(subscription.to_dict(include_secret=True)), 201
        
    except Exception as e:
        logger.exception(f"Error creating webhook subscription: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500


@webhook_bp.route('/subscriptions/<subscription_id>', methods=['GET'])
@require_auth
def get_subscription(subscription_id):
    """
    Get a webhook subscription.
    
    Args:
        subscription_id: ID of the subscription
        
    Returns:
        JSON response with the subscription
    """
    # Get the subscription
    subscription = webhook_subscriptions.get(subscription_id)
    if not subscription:
        return jsonify({"error": "Subscription not found"}), 404
        
    return jsonify(subscription.to_dict())


@webhook_bp.route('/subscriptions/<subscription_id>', methods=['PUT'])
@require_auth
def update_subscription(subscription_id):
    """
    Update a webhook subscription.
    
    Args:
        subscription_id: ID of the subscription
        
    Returns:
        JSON response with the updated subscription
    """
    try:
        # Get the subscription
        subscription = webhook_subscriptions.get(subscription_id)
        if not subscription:
            return jsonify({"error": "Subscription not found"}), 404
            
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing request body"}), 400
            
        # Update fields
        if 'url' in data:
            subscription.url = data['url']
            
        if 'events' in data:
            events = data['events']
            # Validate events
            for event in events:
                if event != "*" and event not in WebhookEvent.all_events():
                    return jsonify({"error": f"Invalid event type: {event}"}), 400
            subscription.events = events
            
        if 'description' in data:
            subscription.description = data['description']
            
        if 'secret' in data:
            subscription.secret = data['secret']
            
        if 'active' in data:
            subscription.active = bool(data['active'])
            
        logger.info(f"Updated webhook subscription {subscription_id}")
        
        return jsonify(subscription.to_dict())
        
    except Exception as e:
        logger.exception(f"Error updating webhook subscription: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500


@webhook_bp.route('/subscriptions/<subscription_id>', methods=['DELETE'])
@require_auth
def delete_subscription(subscription_id):
    """
    Delete a webhook subscription.
    
    Args:
        subscription_id: ID of the subscription
        
    Returns:
        JSON response with success confirmation
    """
    # Get the subscription
    subscription = webhook_subscriptions.get(subscription_id)
    if not subscription:
        return jsonify({"error": "Subscription not found"}), 404
        
    # Remove from registry
    with webhook_lock:
        del webhook_subscriptions[subscription_id]
        
    logger.info(f"Deleted webhook subscription {subscription_id}")
    
    return jsonify({"success": True})


@webhook_bp.route('/events', methods=['GET'])
@require_auth
def list_events():
    """
    List all available webhook event types.
    
    Returns:
        JSON response with event types
    """
    return jsonify({
        "events": WebhookEvent.all_events()
    })


@webhook_bp.route('/test/<subscription_id>', methods=['POST'])
@require_auth
@rate_limit(limit=5, period=60)  # 5 test deliveries per minute
def test_webhook(subscription_id):
    """
    Send a test webhook to a subscription.
    
    Args:
        subscription_id: ID of the subscription
        
    Returns:
        JSON response with delivery result
    """
    try:
        # Get the subscription
        subscription = webhook_subscriptions.get(subscription_id)
        if not subscription:
            return jsonify({"error": "Subscription not found"}), 404
            
        # Create a test payload
        payload = {
            "test": True,
            "timestamp": datetime.now().isoformat(),
            "message": "This is a test webhook delivery"
        }
        
        # Create a delivery
        delivery = WebhookDelivery(
            event_type="test",
            payload=payload,
            subscription_id=subscription_id
        )
        
        # Deliver immediately
        success = deliver_webhook(delivery)
        
        return jsonify({
            "success": success,
            "delivery": delivery.to_dict()
        })
        
    except Exception as e:
        logger.exception(f"Error testing webhook: {str(e)}")
        return jsonify({"error": "Server error", "details": str(e)}), 500


# Define handlers for webhook events

def handle_categorization(evidence_id: str, category_path: List[str]) -> None:
    """
    Handle the category.assigned event.
    
    Args:
        evidence_id: ID of the evidence item
        category_path: New category path
    """
    # Queue the webhook
    payload = {
        "evidence_id": evidence_id,
        "category_path": category_path,
        "timestamp": datetime.now().isoformat()
    }
    
    queue_webhook(WebhookEvent.CATEGORY_ASSIGNED, payload)


def handle_tag_added(evidence_id: str, tag: str) -> None:
    """
    Handle the tag.added event.
    
    Args:
        evidence_id: ID of the evidence item
        tag: Tag that was added
    """
    # Queue the webhook
    payload = {
        "evidence_id": evidence_id,
        "tag": tag,
        "timestamp": datetime.now().isoformat()
    }
    
    queue_webhook(WebhookEvent.TAG_ADDED, payload)


def handle_relationship_created(source_id: str, target_id: str, rel_type: str, strength: str) -> None:
    """
    Handle the relationship.created event.
    
    Args:
        source_id: ID of the source entity
        target_id: ID of the target entity
        rel_type: Relationship type
        strength: Relationship strength
    """
    # Queue the webhook
    payload = {
        "source_id": source_id,
        "target_id": target_id,
        "relationship_type": rel_type,
        "strength": strength,
        "timestamp": datetime.now().isoformat()
    }
    
    queue_webhook(WebhookEvent.RELATIONSHIP_CREATED, payload)


# Register the handlers
register_webhook_handler(WebhookEvent.CATEGORY_ASSIGNED, handle_categorization)
register_webhook_handler(WebhookEvent.TAG_ADDED, handle_tag_added)
register_webhook_handler(WebhookEvent.RELATIONSHIP_CREATED, handle_relationship_created)


# Initialize the webhook processor thread
webhook_processor = None

def init_app(app):
    """
    Initialize the webhook module with a Flask application.
    
    Args:
        app: Flask application
    """
    global webhook_processor
    
    # Register the blueprint
    app.register_blueprint(webhook_bp)
    
    # Start the webhook processor thread
    webhook_processor = WebhookProcessor()
    webhook_processor.start()
    
    # Register a shutdown function
    @app.teardown_appcontext
    def shutdown_webhook_processor(exception=None):
        if webhook_processor and webhook_processor.is_alive():
            webhook_processor.stop()
            webhook_processor.join(timeout=5)
    
    logger.info("Initialized webhook module")
