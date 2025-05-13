/**
 * Authentication Middleware
 * 
 * This middleware handles authentication for API endpoints,
 * specifically securing webhook endpoints with shared secrets.
 */

const config = require('../config');

/**
 * Middleware to validate webhook requests using shared secrets
 * 
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {void}
 */
const validateWebhookSecret = (req, res, next) => {
  const secret = req.headers['x-webhook-secret'];
  
  // Check for secret in environment variable first, then in config
  const validSecret = process.env.WEBHOOK_SECRET || config.webhookSecret;
  
  if (!secret) {
    return res.status(401).json({ 
      error: 'Unauthorized', 
      message: 'Missing webhook secret',
      timestamp: new Date().toISOString()
    });
  }
  
  if (secret !== validSecret) {
    return res.status(403).json({ 
      error: 'Forbidden', 
      message: 'Invalid webhook secret',
      timestamp: new Date().toISOString()
    });
  }
  
  next();
};

/**
 * Rate limiting middleware to prevent abuse
 * This is a simple implementation; consider using a more robust solution for production
 * 
 * @param {Object} req - Express request object
 * @param {Object} res - Express response object
 * @param {Function} next - Express next middleware function
 * @returns {void}
 */
const rateLimit = (() => {
  const requests = {};
  const limit = 100; // Max requests per time window
  const windowMs = 15 * 60 * 1000; // 15 minutes
  
  return (req, res, next) => {
    const ip = req.ip || req.headers['x-forwarded-for'] || req.connection.remoteAddress;
    
    // Initialize or reset expired window
    if (!requests[ip] || Date.now() - requests[ip].windowStart > windowMs) {
      requests[ip] = {
        count: 1,
        windowStart: Date.now()
      };
      return next();
    }
    
    // Increment count for existing window
    requests[ip].count++;
    
    // Check if over limit
    if (requests[ip].count > limit) {
      return res.status(429).json({
        error: 'Too Many Requests',
        message: 'Rate limit exceeded. Please try again later.',
        retryAfter: Math.ceil((requests[ip].windowStart + windowMs - Date.now()) / 1000)
      });
    }
    
    next();
  };
})();

/**
 * Apply all auth middleware to a route
 * 
 * @param {Object} app - Express app instance
 * @returns {void}
 */
const applyAuthMiddleware = (app) => {
  // Apply rate limiting to all routes
  app.use(rateLimit);
  
  // Secure all webhook endpoints with shared secret
  app.use('/api/kanban/*', validateWebhookSecret);
};

module.exports = {
  validateWebhookSecret,
  rateLimit,
  applyAuthMiddleware
};