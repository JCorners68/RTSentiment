/**
 * API Versioning Middleware
 * 
 * Handles API versioning, backward compatibility, and version negotiation
 * Part of the Evidence Management System enhancement
 */

const semver = require('semver');

// Available API versions and their compatibility
const API_VERSIONS = {
  // Current major version
  'v1': {
    version: '1.0.0',
    status: 'stable',
    releaseDate: '2025-01-01',
    endOfLife: null, // No end-of-life date set
    supportsFeatures: [
      'evidence.crud',
      'evidence.search',
      'evidence.attachments',
      'evidence.batch',
      'evidence.relationships'
    ]
  },
  // Future placeholder for backwards compatibility demonstration
  'v2': {
    version: '2.0.0',
    status: 'beta',
    releaseDate: '2025-05-01',
    endOfLife: null,
    supportsFeatures: [
      'evidence.crud',
      'evidence.search',
      'evidence.attachments',
      'evidence.batch',
      'evidence.relationships',
      'evidence.ai',
      'evidence.analytics'
    ]
  }
};

// Default API version to use if none specified
const DEFAULT_VERSION = 'v1';

// Feature compatibility matrix between versions
const FEATURE_COMPATIBILITY = {
  // v2 features that need to be transformed to v1 format
  'v2': {
    'toV1': {
      // Define transformations needed for backwards compatibility
      'evidence': {
        // Convert v2 evidence format to v1 format
        transform: (data) => {
          // Example: map new fields to legacy format
          if (data.metadata) {
            data.tags = data.tags || [];
            // Merge metadata tags into regular tags
            if (data.metadata.tags) {
              data.tags = [...new Set([...data.tags, ...data.metadata.tags])];
            }
            // Move relevant metadata fields to top level
            if (data.metadata.source_information) {
              data.source = data.metadata.source_information;
            }
            delete data.metadata;
          }
          return data;
        }
      },
      'search': {
        // Transform v2 search parameters to v1 format
        transform: (params) => {
          // Example: map advanced search parameters to basic ones
          if (params.advanced_filters) {
            if (params.advanced_filters.relevance_range) {
              params.relevance = params.advanced_filters.relevance_range.min;
            }
            delete params.advanced_filters;
          }
          return params;
        }
      }
    }
  },
  // v1 features that need to be transformed to v2 format
  'v1': {
    'toV2': {
      // Define transformations needed for forward compatibility
      'evidence': {
        transform: (data) => {
          // Example: restructure data to match v2 format
          data.metadata = data.metadata || {};
          // Move certain tags to metadata
          if (data.tags && data.tags.length > 0) {
            data.metadata.tags = data.tags.filter(tag => 
              tag.startsWith('meta:') || tag.startsWith('system:')
            );
            // Keep only regular tags in the main tags array
            data.tags = data.tags.filter(tag => 
              !tag.startsWith('meta:') && !tag.startsWith('system:')
            );
          }
          // Move source to metadata
          if (data.source) {
            data.metadata.source_information = data.source;
          }
          return data;
        }
      }
    }
  }
};

/**
 * Extract version from different sources
 * Priority:
 * 1. URL path (/api/v1/...)
 * 2. Accept header with version (Accept: application/json; version=v1)
 * 3. Explicit version header (X-API-Version: v1)
 * 4. Default version
 */
function extractVersion(req) {
  // Try to extract from URL path
  const urlMatch = req.path.match(/^\/api\/(v[0-9]+)\//);
  if (urlMatch && API_VERSIONS[urlMatch[1]]) {
    return urlMatch[1];
  }
  
  // Try to extract from Accept header
  const acceptHeader = req.get('Accept');
  if (acceptHeader) {
    const versionMatch = acceptHeader.match(/version=(v[0-9]+)/);
    if (versionMatch && API_VERSIONS[versionMatch[1]]) {
      return versionMatch[1];
    }
  }
  
  // Try explicit version header
  const versionHeader = req.get('X-API-Version');
  if (versionHeader && API_VERSIONS[versionHeader]) {
    return versionHeader;
  }
  
  // Fall back to default
  return DEFAULT_VERSION;
}

/**
 * Middleware for API versioning
 */
function versioningMiddleware(req, res, next) {
  const requestedVersion = extractVersion(req);
  
  // Store version information in the request for later use
  req.apiVersion = requestedVersion;
  req.apiVersionInfo = API_VERSIONS[requestedVersion];
  
  // Add versioning functions to the request object
  req.transformRequest = (data, targetVersion) => {
    // If the requested version is the same as the target, no transform needed
    if (requestedVersion === targetVersion) return data;
    
    // Get source and target versions for the transformation
    const sourceVersion = requestedVersion;
    
    // Determine which transformation to apply
    const direction = 'to' + targetVersion.charAt(0).toUpperCase() + targetVersion.slice(1);
    const entityType = req.path.split('/').pop(); // Simplistic determination of entity type
    
    // Apply transformation if available
    if (FEATURE_COMPATIBILITY[sourceVersion] && 
        FEATURE_COMPATIBILITY[sourceVersion][direction] && 
        FEATURE_COMPATIBILITY[sourceVersion][direction][entityType]) {
      return FEATURE_COMPATIBILITY[sourceVersion][direction][entityType].transform(data);
    }
    
    // No transformation available, return data as is
    return data;
  };
  
  // Add version response headers
  res.set('X-API-Version', requestedVersion);
  res.set('X-API-Supported-Versions', Object.keys(API_VERSIONS).join(', '));
  
  // Add API deprecation warning for end-of-life versions
  const versionInfo = API_VERSIONS[requestedVersion];
  if (versionInfo.endOfLife && new Date(versionInfo.endOfLife) < new Date()) {
    res.set(
      'Warning', 
      `299 - "This API version ${requestedVersion} was deprecated on ${versionInfo.endOfLife} and will be removed soon. Please upgrade to a newer version."`
    );
  }
  
  // Expose a function to transform response data based on requested version
  res.sendVersioned = (data) => {
    // Always send the data in the format expected by the requested version
    // Transformations would happen in the route handlers before calling this
    return res.json(data);
  };
  
  next();
}

/**
 * Create versioned routes for an Express router
 * This is used to register the same handler for multiple API versions
 */
function createVersionedRouter(app, versions = Object.keys(API_VERSIONS)) {
  const routeVersions = {};
  
  // Create router for each version
  versions.forEach(version => {
    routeVersions[version] = express.Router();
    app.use(`/api/${version}`, routeVersions[version]);
  });
  
  return {
    /**
     * Register a route handler for multiple API versions
     * @param {string} method - HTTP method (get, post, put, delete)
     * @param {string} path - Route path
     * @param {Function[]} handlers - Route handlers
     */
    route(method, path, ...handlers) {
      versions.forEach(version => {
        routeVersions[version][method](path, ...handlers);
      });
    },
    
    /**
     * Get routers for each version
     */
    routers: routeVersions
  };
}

// Middleware for handling version negotiation via Accept header
function versionNegotiationMiddleware(req, res, next) {
  // Check for version header or Accept header with version parameter
  const acceptHeader = req.get('Accept');
  if (acceptHeader && acceptHeader.includes('application/json')) {
    // Handle Accept header version negotiation
    const versionMatch = acceptHeader.match(/version=(v[0-9]+)/);
    if (versionMatch) {
      const requestedVersion = versionMatch[1];
      
      // If specified version exists, set it in request
      if (API_VERSIONS[requestedVersion]) {
        req.negotiatedVersion = requestedVersion;
        res.set('Content-Type', `application/json; version=${requestedVersion}`);
      } else {
        // Version not supported, suggest available versions
        return res.status(406).json({
          error: 'Not Acceptable',
          message: `Requested API version ${requestedVersion} is not supported`,
          supported_versions: Object.keys(API_VERSIONS)
        });
      }
    }
  }
  
  next();
}

// Export all versioning utilities
module.exports = {
  versioningMiddleware,
  versionNegotiationMiddleware,
  createVersionedRouter,
  API_VERSIONS,
  DEFAULT_VERSION
};
