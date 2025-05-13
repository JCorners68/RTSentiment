"""
API Versioning Strategy for Evidence Management System.

This module implements a comprehensive versioning strategy for the Evidence API,
supporting path versioning, header negotiation, and backward compatibility.
"""
import re
import logging
import inspect
from typing import Dict, List, Any, Optional, Union, Callable, Tuple
from functools import wraps

from flask import Blueprint, request, jsonify, abort, g, current_app, Response

# Configure module logger
logger = logging.getLogger(__name__)


class ApiVersion:
    """API version definition."""
    
    def __init__(self, 
                version: str,
                internal_version: int,
                release_date: str,
                deprecated: bool = False,
                sunset_date: Optional[str] = None,
                description: Optional[str] = None):
        """
        Initialize API version.
        
        Args:
            version: Public version string (e.g., "v1")
            internal_version: Internal version number for comparisons
            release_date: ISO date of release
            deprecated: Whether this version is deprecated
            sunset_date: Optional ISO date when this version will be removed
            description: Optional description of this version
        """
        self.version = version
        self.internal_version = internal_version
        self.release_date = release_date
        self.deprecated = deprecated
        self.sunset_date = sunset_date
        self.description = description or f"API {version}"
        
        # Map of endpoint names to their backwards compatibility functions
        self.compatibility_map = {}
    
    def __str__(self) -> str:
        """String representation."""
        return self.version
    
    def __lt__(self, other) -> bool:
        """Compare versions based on internal version number."""
        if isinstance(other, ApiVersion):
            return self.internal_version < other.internal_version
        return NotImplemented
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "version": self.version,
            "internal_version": self.internal_version,
            "release_date": self.release_date,
            "deprecated": self.deprecated,
            "sunset_date": self.sunset_date,
            "description": self.description
        }
    
    def register_compatibility_handler(self, 
                                      endpoint: str, 
                                      handler: Callable) -> None:
        """
        Register a compatibility handler for an endpoint.
        
        Args:
            endpoint: Endpoint name
            handler: Function that transforms request/response data
        """
        self.compatibility_map[endpoint] = handler
        logger.debug(f"Registered compatibility handler for {endpoint} in {self.version}")
    
    def get_compatibility_handler(self, endpoint: str) -> Optional[Callable]:
        """
        Get compatibility handler for an endpoint.
        
        Args:
            endpoint: Endpoint name
            
        Returns:
            Handler function or None if not found
        """
        return self.compatibility_map.get(endpoint)


class VersionManager:
    """
    Manages API versioning for the Evidence Management System.
    
    This class handles API versioning, including path-based versioning,
    header-based version negotiation, and backwards compatibility.
    """
    
    def __init__(self):
        """Initialize the version manager."""
        # Map of version string to ApiVersion object
        self.versions: Dict[str, ApiVersion] = {}
        
        # The latest stable version
        self.latest_version: Optional[ApiVersion] = None
        
        logger.info("Initialized API version manager")
    
    def register_version(self, api_version: ApiVersion) -> None:
        """
        Register an API version.
        
        Args:
            api_version: ApiVersion object to register
        """
        self.versions[api_version.version] = api_version
        
        # Update latest version if this is newer
        if self.latest_version is None or api_version > self.latest_version:
            if not api_version.deprecated:
                self.latest_version = api_version
                
        logger.info(f"Registered API version: {api_version.version}")
    
    def get_version(self, version_str: str) -> Optional[ApiVersion]:
        """
        Get an API version by string.
        
        Args:
            version_str: Version string (e.g., "v1")
            
        Returns:
            ApiVersion object or None if not found
        """
        return self.versions.get(version_str)
    
    def get_latest_version(self) -> Optional[ApiVersion]:
        """
        Get the latest stable API version.
        
        Returns:
            Latest ApiVersion object or None if no versions registered
        """
        return self.latest_version
    
    def parse_version_from_request(self) -> Tuple[ApiVersion, str]:
        """
        Parse API version from the current request.
        
        This function tries to determine the API version from:
        1. URL path (e.g., /api/v1/evidence)
        2. Accept header (e.g., Accept: application/json; version=v1)
        3. Custom X-API-Version header
        
        If no version is specified, the latest stable version is used.
        
        Returns:
            Tuple of (ApiVersion object, source of version)
        """
        # Check URL path first
        path = request.path
        match = re.search(r'/api/(v[0-9]+)/', path)
        if match:
            version_str = match.group(1)
            version = self.get_version(version_str)
            if version:
                return version, "path"
        
        # Check Accept header
        accept = request.headers.get('Accept', '')
        match = re.search(r'version=(v[0-9]+)', accept)
        if match:
            version_str = match.group(1)
            version = self.get_version(version_str)
            if version:
                return version, "accept"
        
        # Check X-API-Version header
        version_str = request.headers.get('X-API-Version')
        if version_str:
            version = self.get_version(version_str)
            if version:
                return version, "header"
        
        # Default to latest version
        if self.latest_version:
            return self.latest_version, "default"
        
        # No version found
        logger.error("No API version found and no latest version available")
        abort(400, "No valid API version specified and no default version available")
    
    def get_all_versions(self) -> List[ApiVersion]:
        """
        Get all registered API versions.
        
        Returns:
            List of ApiVersion objects
        """
        return list(self.versions.values())
    
    def transform_for_version(self, 
                             data: Any, 
                             endpoint: str,
                             target_version: ApiVersion) -> Any:
        """
        Transform data for a specific API version.
        
        This function applies version-specific transformations to ensure
        backwards compatibility.
        
        Args:
            data: Data to transform (request or response)
            endpoint: Endpoint name
            target_version: Target ApiVersion
            
        Returns:
            Transformed data
        """
        # Get compatibility handler for this endpoint
        handler = target_version.get_compatibility_handler(endpoint)
        if handler:
            return handler(data)
        
        # No handler, return data as is
        return data


# Flask extension for API versioning
class FlaskApiVersioning:
    """Flask extension for API versioning."""
    
    def __init__(self, app=None):
        """
        Initialize the extension.
        
        Args:
            app: Optional Flask application
        """
        self.version_manager = VersionManager()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """
        Initialize the extension with a Flask application.
        
        Args:
            app: Flask application
        """
        app.api_versioning = self
        app.version_manager = self.version_manager
        
        # Register a blueprint for API version information
        bp = Blueprint('api_version', __name__, url_prefix='/api')
        
        @bp.route('/versions', methods=['GET'])
        def get_versions():
            """Get all available API versions."""
            versions = [v.to_dict() for v in self.version_manager.get_all_versions()]
            return jsonify({
                "versions": versions,
                "latest": self.version_manager.get_latest_version().to_dict() if self.version_manager.get_latest_version() else None
            })
            
        app.register_blueprint(bp)
        
        # Register before_request handler to set version in g
        @app.before_request
        def detect_api_version():
            # Only process API routes
            if request.path.startswith('/api/'):
                try:
                    version, source = self.version_manager.parse_version_from_request()
                    g.api_version = version
                    g.api_version_source = source
                    
                    # Add warning header for deprecated versions
                    if version.deprecated:
                        sunset_info = f", sunset on {version.sunset_date}" if version.sunset_date else ""
                        message = f"API {version.version} is deprecated{sunset_info}. Please upgrade to the latest version."
                        
                        # This will be added in after_request
                        g.deprecated_version_message = message
                except Exception as e:
                    logger.exception(f"Error detecting API version: {str(e)}")
                    # Continue without version information
                    
        # Register after_request handler to add version headers
        @app.after_request
        def add_api_version_headers(response):
            if hasattr(g, 'api_version'):
                response.headers['X-API-Version'] = g.api_version.version
                
                # Add deprecation warning if needed
                if g.api_version.deprecated and hasattr(g, 'deprecated_version_message'):
                    response.headers['Warning'] = g.deprecated_version_message
                    
                    if g.api_version.sunset_date:
                        response.headers['Sunset'] = g.api_version.sunset_date
                    
            return response
    
    def register_version(self, **kwargs):
        """
        Register an API version.
        
        This function accepts the same arguments as ApiVersion.__init__
        """
        version = ApiVersion(**kwargs)
        self.version_manager.register_version(version)
        return version
    
    def route_version(self, version_str, **options):
        """
        Decorator for registering a route with a specific API version.
        
        This decorator generates a versioned route for a function.
        
        Args:
            version_str: Version string (e.g., "v1")
            **options: Options to pass to Flask route decorator
            
        Returns:
            Decorator function
        """
        def decorator(f):
            # Make sure extension is initialized
            if not hasattr(current_app, 'api_versioning'):
                raise RuntimeError("Flask-ApiVersioning extension not initialized")
                
            # Get module and blueprint
            module = inspect.getmodule(f)
            if not module or not hasattr(module, 'bp'):
                raise RuntimeError("Cannot find blueprint in module")
                
            bp = getattr(module, 'bp')
            
            # Create versioned route
            endpoint = options.pop('endpoint', f.__name__)
            url_rule = options.pop('rule', f"/{f.__name__}")
            
            # Register the function with the blueprint
            bp.add_url_rule(url_rule, endpoint=endpoint, view_func=f, **options)
            
            return f
            
        return decorator
    
    def version_compatible(self, min_version=None, max_version=None):
        """
        Decorator for making a function compatible with multiple API versions.
        
        Args:
            min_version: Minimum version string (e.g., "v1")
            max_version: Maximum version string (e.g., "v3")
            
        Returns:
            Decorator function
        """
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                # Get current API version
                current_version = getattr(g, 'api_version', self.version_manager.get_latest_version())
                
                # Check version constraints
                if min_version:
                    min_ver = self.version_manager.get_version(min_version)
                    if min_ver and current_version.internal_version < min_ver.internal_version:
                        abort(400, f"API endpoint requires minimum version {min_version}")
                
                if max_version:
                    max_ver = self.version_manager.get_version(max_version)
                    if max_ver and current_version.internal_version > max_ver.internal_version:
                        abort(400, f"API endpoint requires maximum version {max_version}")
                
                # Call the function
                return f(*args, **kwargs)
                
            return wrapped
            
        return decorator
    
    def register_compatibility_handler(self, version_str, endpoint, handler):
        """
        Register a compatibility handler for an endpoint.
        
        Args:
            version_str: Version string (e.g., "v1")
            endpoint: Endpoint name
            handler: Function that transforms request/response data
        """
        version = self.version_manager.get_version(version_str)
        if not version:
            raise ValueError(f"Unknown API version: {version_str}")
            
        version.register_compatibility_handler(endpoint, handler)


# Helper function to create the extension
def create_versioning_extension(app=None):
    """
    Create the API versioning extension.
    
    Args:
        app: Optional Flask application
        
    Returns:
        FlaskApiVersioning instance
    """
    return FlaskApiVersioning(app)
