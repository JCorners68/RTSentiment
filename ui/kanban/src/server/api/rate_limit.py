"""
Rate Limiting for API Endpoints.

This module provides rate limiting functionality for the Evidence Management
System API, allowing configuration of rate limits per endpoint.
"""
import time
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from functools import wraps
from datetime import datetime
import threading
from flask import request, jsonify, current_app, g

# Configure module logger
logger = logging.getLogger(__name__)

# Thread-safe lock for the rate limiter
rate_limit_lock = threading.RLock()


class RateLimiter:
    """
    Rate limiter for API endpoints.
    
    This class tracks request rates and enforces configurable rate limits
    to prevent abuse of API endpoints.
    """
    
    def __init__(self):
        """Initialize the rate limiter."""
        # Format: {ip: {endpoint: [(timestamp, count)]}}
        self.request_records = {}
        
        # Format: {endpoint: {limit: n, period: seconds}}
        self.endpoint_limits = {}
        
        # Global limits
        self.global_limits = {
            "limit": 100,  # 100 requests
            "period": 60,  # per minute
        }
        
        logger.info("Rate limiter initialized")
    
    def configure_endpoint(self, endpoint: str, limit: int, period: int) -> None:
        """
        Configure rate limits for an endpoint.
        
        Args:
            endpoint: Endpoint path or function name
            limit: Maximum number of requests
            period: Time period in seconds
        """
        with rate_limit_lock:
            self.endpoint_limits[endpoint] = {
                "limit": limit,
                "period": period,
            }
            
        logger.info(f"Configured rate limit for {endpoint}: {limit} requests per {period} seconds")
    
    def configure_global(self, limit: int, period: int) -> None:
        """
        Configure global rate limits.
        
        Args:
            limit: Maximum number of requests
            period: Time period in seconds
        """
        with rate_limit_lock:
            self.global_limits = {
                "limit": limit,
                "period": period,
            }
            
        logger.info(f"Configured global rate limit: {limit} requests per {period} seconds")
    
    def is_rate_limited(self, 
                       ip: str, 
                       endpoint: str,
                       increment: bool = True) -> Dict[str, Any]:
        """
        Check if a request is rate limited.
        
        Args:
            ip: IP address of the requester
            endpoint: Endpoint being accessed
            increment: Whether to increment the counter for this request
            
        Returns:
            Dictionary with rate limit information
        """
        with rate_limit_lock:
            now = time.time()
            
            # Initialize data structures if needed
            if ip not in self.request_records:
                self.request_records[ip] = {}
            if endpoint not in self.request_records[ip]:
                self.request_records[ip][endpoint] = []
                
            # Get endpoint and global limits
            endpoint_limit = self.endpoint_limits.get(endpoint, self.global_limits)
            limit = endpoint_limit["limit"]
            period = endpoint_limit["period"]
            
            # Clean up old records
            self.request_records[ip][endpoint] = [
                rec for rec in self.request_records[ip][endpoint]
                if now - rec[0] < period
            ]
            
            # Check current request count within the period
            request_count = sum(rec[1] for rec in self.request_records[ip][endpoint])
            
            # Increment counter if requested
            if increment and request_count < limit:
                if not self.request_records[ip][endpoint]:
                    self.request_records[ip][endpoint].append((now, 1))
                else:
                    # Increment the latest record
                    latest = self.request_records[ip][endpoint][-1]
                    self.request_records[ip][endpoint][-1] = (latest[0], latest[1] + 1)
                request_count += 1
                
            # Prepare response
            is_limited = request_count >= limit
            reset_time = min([rec[0] for rec in self.request_records[ip][endpoint]], default=now) + period
            
            result = {
                "limited": is_limited,
                "limit": limit,
                "remaining": max(0, limit - request_count),
                "reset": reset_time,
                "endpoint": endpoint,
            }
            
            if is_limited:
                logger.warning(f"Rate limit exceeded for {ip} on {endpoint}: {request_count}/{limit}")
                
            return result
            
    def get_client_ip(self) -> str:
        """
        Get the client IP address from the request.
        
        Returns:
            IP address as a string
        """
        # Check for X-Forwarded-For header
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Use the first IP in the list
            return forwarded_for.split(',')[0].strip()
            
        # Otherwise use remote_addr
        return request.remote_addr or '127.0.0.1'
            
    def clean_expired_records(self) -> None:
        """Clean up expired rate limit records."""
        with rate_limit_lock:
            now = time.time()
            
            # Clean up for each IP and endpoint
            for ip in list(self.request_records.keys()):
                for endpoint in list(self.request_records[ip].keys()):
                    # Get the period for this endpoint
                    period = self.endpoint_limits.get(endpoint, self.global_limits)["period"]
                    
                    # Remove expired records
                    self.request_records[ip][endpoint] = [
                        rec for rec in self.request_records[ip][endpoint]
                        if now - rec[0] < period
                    ]
                    
                    # Remove empty endpoint records
                    if not self.request_records[ip][endpoint]:
                        del self.request_records[ip][endpoint]
                        
                # Remove empty IP records
                if not self.request_records[ip]:
                    del self.request_records[ip]
            
            logger.debug("Cleaned expired rate limit records")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """
        Get rate limit usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        with rate_limit_lock:
            # Clean expired records first
            self.clean_expired_records()
            
            # Calculate statistics
            total_ips = len(self.request_records)
            total_endpoints = sum(len(endpoints) for endpoints in self.request_records.values())
            
            # Count endpoints approaching limits
            approaching_limit = 0
            for ip, endpoints in self.request_records.items():
                for endpoint, records in endpoints.items():
                    # Get limit for this endpoint
                    limit = self.endpoint_limits.get(endpoint, self.global_limits)["limit"]
                    
                    # Sum the count for this endpoint
                    count = sum(rec[1] for rec in records)
                    
                    # Check if approaching limit (>75%)
                    if count > limit * 0.75:
                        approaching_limit += 1
            
            return {
                "total_ips": total_ips,
                "total_endpoints": total_endpoints,
                "approaching_limit": approaching_limit,
                "endpoint_limits": self.endpoint_limits,
                "global_limits": self.global_limits,
            }


# Global rate limiter instance
_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance.
    
    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limit(limit: int = None, period: int = None):
    """
    Rate limiting decorator for Flask routes.
    
    This decorator applies rate limiting to the decorated function.
    If the rate limit is exceeded, it returns a 429 Too Many Requests response.
    
    Args:
        limit: Maximum number of requests (overrides global setting)
        period: Time period in seconds (overrides global setting)
        
    Returns:
        Decorator function
    """
    def decorator(f):
        # Configure the endpoint with specific limits if provided
        endpoint = f.__name__
        rate_limiter = get_rate_limiter()
        
        if limit is not None and period is not None:
            rate_limiter.configure_endpoint(endpoint, limit, period)
        
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Get client IP
            client_ip = rate_limiter.get_client_ip()
            
            # Check rate limit
            result = rate_limiter.is_rate_limited(client_ip, endpoint)
            
            # Store rate limit info in Flask g object for headers
            g.rate_limit_info = result
            
            # If rate limited, return 429 response
            if result["limited"]:
                response = jsonify({
                    "error": "Rate limit exceeded",
                    "limit": result["limit"],
                    "reset": datetime.fromtimestamp(result["reset"]).isoformat(),
                })
                response.status_code = 429
                
                # Add rate limit headers
                response.headers["X-RateLimit-Limit"] = str(result["limit"])
                response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
                response.headers["X-RateLimit-Reset"] = str(int(result["reset"]))
                response.headers["Retry-After"] = str(int(result["reset"] - time.time()))
                
                return response
            
            # Otherwise proceed with the request
            return f(*args, **kwargs)
        
        return wrapped
    
    return decorator


def add_rate_limit_headers(response):
    """
    Add rate limit headers to the response.
    
    This function should be called after every request to add rate limit
    headers to the response.
    
    Args:
        response: Flask response object
        
    Returns:
        Modified response
    """
    if hasattr(g, 'rate_limit_info'):
        info = g.rate_limit_info
        response.headers["X-RateLimit-Limit"] = str(info["limit"])
        response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
        response.headers["X-RateLimit-Reset"] = str(int(info["reset"]))
    
    return response
