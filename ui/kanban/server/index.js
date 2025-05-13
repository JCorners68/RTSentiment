/**
 * CLI Kanban Companion Server
 * 
 * This Express.js server runs alongside the CLI Kanban tool to provide
 * API endpoints for integration with n8n workflows and external systems.
 */

const express = require('express');
const path = require('path');
const fs = require('fs');
const helmet = require('helmet');
const cors = require('cors');
const semver = require('semver');

// Load configuration
const config = require('./config');

// Load middleware modules
const { rateLimitMiddleware } = require('./middleware/rateLimit');
const { 
  versioningMiddleware, 
  versionNegotiationMiddleware, 
  createVersionedRouter,
  API_VERSIONS,
  DEFAULT_VERSION
} = require('./middleware/versioning');

// Create Express app
const app = express();

// Basic security middleware
app.use(helmet());
app.use(cors());

// Body parsers
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true, limit: '1mb' }));

// Add request logging
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.url}`);
  next();
});

// Initialize rate limiting with config path
const configDir = path.join(__dirname, '../config');
if (!fs.existsSync(configDir)) {
  fs.mkdirSync(configDir, { recursive: true });
}
const rateLimitConfigPath = path.join(configDir, 'rate-limit.json');
const rateLimit = rateLimitMiddleware({ configPath: rateLimitConfigPath });

// Apply rate limiting to all API routes
app.use('/api/', rateLimit);



// Import route modules
const taskRoutes = require('./routes/tasks');
const epicRoutes = require('./routes/epics');
const evidenceRoutes = require('./routes/evidence');
const attachmentRoutes = require('./routes/attachments');
const batchRoutes = require('./routes/batch');
const webhookRoutes = require('./routes/webhooks');

// Secure webhook endpoints with shared secret
const apiAuthMiddleware = (req, res, next) => {
  // Skip authentication for GET requests to allow public access to evidence data
  // or if this is running in development mode
  if ((req.method === 'GET' && !req.path.includes('/attachments/')) || 
      process.env.NODE_ENV === 'development') {
    return next();
  }
  
  const secret = req.headers['x-api-key'] || req.headers['x-webhook-secret'];
  if (secret !== process.env.API_SECRET && secret !== config.apiSecret) {
    return res.status(403).json({ error: 'Unauthorized. Invalid API key.' });
  }
  next();
};

// Apply version negotiation middleware
app.use('/api', versionNegotiationMiddleware);

// Apply versioning middleware
app.use('/api', versioningMiddleware);

// Create versioned router for API paths
const versionedRouter = createVersionedRouter(app);

// Set up v1 routes (current stable version)
app.use('/api/v1/kanban', apiAuthMiddleware);
app.use('/api/v1/kanban/tasks', taskRoutes);
app.use('/api/v1/kanban/task', taskRoutes);
app.use('/api/v1/kanban/epics', epicRoutes);
app.use('/api/v1/kanban/epic', epicRoutes);
app.use('/api/v1/kanban/evidence', evidenceRoutes);
app.use('/api/v1/kanban/attachments', attachmentRoutes);
app.use('/api/v1/kanban/batch', batchRoutes);
app.use('/api/v1/kanban/webhooks', webhookRoutes);

// Keep legacy unversioned routes for backward compatibility
// These will be removed in a future release
app.use('/api/kanban', (req, res, next) => {
  // Set a deprecation warning header
  res.set('Warning', '299 - "Unversioned API endpoints are deprecated. Please use /api/v1/ paths instead."');
  next();
});

// Backward compatibility layer for old routes
app.use('/api/kanban', apiAuthMiddleware);
app.use('/api/kanban/tasks', taskRoutes);
app.use('/api/kanban/task', taskRoutes);
app.use('/api/kanban/epics', epicRoutes);
app.use('/api/kanban/epic', epicRoutes);
app.use('/api/kanban/evidence', evidenceRoutes);
app.use('/api/kanban/attachments', attachmentRoutes);
app.use('/api/kanban/batch', batchRoutes);
app.use('/api/kanban/webhooks', webhookRoutes);

// API version and status endpoints
app.get('/api/version', (req, res) => {
  const versions = {};
  
  // Format version information for response
  Object.keys(API_VERSIONS).forEach(key => {
    const versionInfo = API_VERSIONS[key];
    versions[key] = {
      version: versionInfo.version,
      status: versionInfo.status,
      releaseDate: versionInfo.releaseDate,
      endOfLife: versionInfo.endOfLife,
      supportsFeatures: versionInfo.supportsFeatures
    };
  });
  
  res.json({
    current_version: API_VERSIONS[DEFAULT_VERSION].version,
    default_version: DEFAULT_VERSION,
    versions: versions,
    status: 'operational',
    timestamp: new Date().toISOString()
  });
});

// API Version compatibility check endpoint
app.get('/api/version/compatibility', (req, res) => {
  const clientVersion = req.query.version;
  
  if (!clientVersion) {
    return res.status(400).json({
      error: 'Missing version parameter',
      message: 'Please provide a version parameter to check compatibility'
    });
  }
  
  // Find matching API version
  const matchingVersion = Object.keys(API_VERSIONS).find(key => {
    return semver.satisfies(API_VERSIONS[key].version, clientVersion);
  });
  
  if (matchingVersion) {
    return res.json({
      compatible: true,
      recommended_version: matchingVersion,
      features: API_VERSIONS[matchingVersion].supportsFeatures
    });
  } else {
    return res.status(400).json({
      compatible: false,
      message: `No compatible API version for ${clientVersion}`,
      available_versions: Object.keys(API_VERSIONS).map(key => ({
        version: key,
        semver: API_VERSIONS[key].version
      }))
    });
  }
});

// Rate limiting configuration API
app.get('/api/admin/rate-limit', apiAuthMiddleware, (req, res) => {
  const { getRateLimitStatus } = require('./middleware/rateLimit');
  res.json(getRateLimitStatus());
});

app.put('/api/admin/rate-limit', apiAuthMiddleware, (req, res) => {
  const { updateRateLimitConfig } = require('./middleware/rateLimit');
  const newConfig = updateRateLimitConfig(req.body);
  res.json(newConfig);
});

// Serve OpenAPI/Swagger documentation
app.use('/api-docs', express.static(path.join(__dirname, 'docs')));

// Health check endpoint (not secured)
app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Error handling middleware
app.use((err, req, res, next) => {
  console.error(`Error processing request: ${err.stack}`);
  res.status(500).json({ 
    error: 'Internal server error', 
    message: err.message,
    timestamp: new Date().toISOString()
  });
});

// Start server
const PORT = process.env.PORT || config.port || 3000;
const server = app.listen(PORT, () => {
  console.log(`CLI Kanban companion server listening on port ${PORT}`);
});

// Handle shutdown gracefully
process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);

function shutdown() {
  console.log('Shutting down server...');
  server.close(() => {
    console.log('Server has been gracefully terminated');
    process.exit(0);
  });
  
  // Force close if takes too long
  setTimeout(() => {
    console.error('Server shutdown timed out, forcing exit');
    process.exit(1);
  }, 5000);
}

module.exports = { app, server };