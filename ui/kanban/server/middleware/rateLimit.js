/**
 * Rate Limiting Middleware
 * 
 * Provides configurable rate limiting for API endpoints
 * Part of the Evidence Management System enhancement
 */

const fs = require('fs');
const path = require('path');

// Configuration
const DEFAULT_WINDOW_MS = 15 * 60 * 1000; // 15 minutes
const DEFAULT_MAX_REQUESTS = 100;
const CLEANUP_INTERVAL_MS = 5 * 60 * 1000; // Clean up every 5 minutes

// In-memory store for request tracking
const requestStore = {
  requests: new Map(), // ip+path -> array of timestamps
  config: {
    enabled: true,
    defaultWindowMs: DEFAULT_WINDOW_MS,
    defaultMaxRequests: DEFAULT_MAX_REQUESTS,
    rules: [
      { 
        pathPattern: '/api/v1/kanban/evidence', 
        windowMs: 60 * 1000, 
        maxRequests: 50,
        description: 'Evidence operations'
      },
      { 
        pathPattern: '/api/v1/kanban/attachments', 
        windowMs: 60 * 1000, 
        maxRequests: 20,
        description: 'Attachment operations'
      },
      { 
        pathPattern: '/api/v1/kanban/batch', 
        windowMs: 60 * 1000, 
        maxRequests: 10,
        description: 'Batch operations (more intensive)'
      },
      { 
        pathPattern: '/api/v1/kanban/webhooks', 
        windowMs: 60 * 1000, 
        maxRequests: 30,
        description: 'Webhook operations'
      }
    ],
    excludedIps: ['127.0.0.1', '::1', 'localhost']
  },
  configPath: null,
  lastCleanup: Date.now()
};

// Initialize configuration
const initConfig = (configPath) => {
  if (configPath) {
    requestStore.configPath = configPath;
    
    try {
      if (fs.existsSync(configPath)) {
        const configData = fs.readFileSync(configPath, 'utf8');
        requestStore.config = JSON.parse(configData);
        console.log(`Loaded rate limit configuration from ${configPath}`);
      } else {
        // Save default config
        saveConfig();
      }
    } catch (error) {
      console.error(`Error loading rate limit configuration: ${error.message}`);
    }
  }
};

// Save configuration
const saveConfig = () => {
  if (!requestStore.configPath) {
    return;
  }
  
  try {
    // Ensure directory exists
    const configDir = path.dirname(requestStore.configPath);
    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true });
    }
    
    fs.writeFileSync(
      requestStore.configPath,
      JSON.stringify(requestStore.config, null, 2),
      'utf8'
    );
    console.log(`Saved rate limit configuration to ${requestStore.configPath}`);
  } catch (error) {
    console.error(`Error saving rate limit configuration: ${error.message}`);
  }
};

// Clean up old requests
const cleanupOldRequests = () => {
  const now = Date.now();
  
  // Don't clean up too frequently
  if (now - requestStore.lastCleanup < CLEANUP_INTERVAL_MS) {
    return;
  }
  
  requestStore.lastCleanup = now;
  
  // Find the maximum window size from all rules
  const maxWindowMs = Math.max(
    requestStore.config.defaultWindowMs,
    ...requestStore.config.rules.map(rule => rule.windowMs)
  );
  
  // Cutoff time
  const cutoff = now - maxWindowMs;
  
  // Clean up each entry
  for (const [key, timestamps] of requestStore.requests.entries()) {
    const filteredTimestamps = timestamps.filter(ts => ts >= cutoff);
    
    if (filteredTimestamps.length === 0) {
      requestStore.requests.delete(key);
    } else {
      requestStore.requests.set(key, filteredTimestamps);
    }
  }
};

// Match path against pattern
const matchPath = (path, pattern) => {
  // Exact match
  if (path === pattern) {
    return true;
  }
  
  // Wildcard at end
  if (pattern.endsWith('*')) {
    const prefix = pattern.slice(0, -1);
    return path.startsWith(prefix);
  }
  
  return false;
};

// Find most specific matching rule
const findMatchingRule = (path) => {
  let matchingRule = null;
  let matchScore = -1;
  
  for (const rule of requestStore.config.rules) {
    const { pathPattern } = rule;
    
    // Skip wildcard-only patterns initially
    if (pathPattern === '*') {
      continue;
    }
    
    if (matchPath(path, pathPattern)) {
      // Calculate specificity (longer non-wildcard part = more specific)
      const specificity = pathPattern.endsWith('*')
        ? pathPattern.length - 1
        : pathPattern.length;
        
      if (specificity > matchScore) {
        matchingRule = rule;
        matchScore = specificity;
      }
    }
  }
  
  // If no specific rule matched, try wildcard rules
  if (!matchingRule) {
    matchingRule = requestStore.config.rules.find(rule => rule.pathPattern === '*');
  }
  
  return matchingRule;
};

// Check if a request is rate limited
const isRateLimited = (ip, path) => {
  // Not enabled
  if (!requestStore.config.enabled) {
    return { limited: false };
  }
  
  // Excluded IP
  if (requestStore.config.excludedIps.includes(ip)) {
    return { limited: false };
  }
  
  // Find matching rule or use defaults
  const rule = findMatchingRule(path);
  const windowMs = rule ? rule.windowMs : requestStore.config.defaultWindowMs;
  const maxRequests = rule ? rule.maxRequests : requestStore.config.defaultMaxRequests;
  
  // Get current time
  const now = Date.now();
  
  // Calculate window start time
  const windowStart = now - windowMs;
  
  // Key for this IP and path
  const key = `${ip}:${path}`;
  
  // Get timestamps for this key
  const timestamps = requestStore.requests.get(key) || [];
  
  // Filter to current window
  const windowTimestamps = timestamps.filter(ts => ts >= windowStart);
  
  // Check if limit exceeded
  if (windowTimestamps.length >= maxRequests) {
    // Calculate retry after time (based on oldest request + window)
    const oldestTimestamp = Math.min(...windowTimestamps);
    const resetTime = oldestTimestamp + windowMs;
    const retryAfter = Math.ceil((resetTime - now) / 1000);
    
    return {
      limited: true,
      retryAfter: Math.max(0, retryAfter),
      limit: maxRequests,
      remaining: 0,
      windowMs
    };
  }
  
  // Record this request
  windowTimestamps.push(now);
  requestStore.requests.set(key, windowTimestamps);
  
  return {
    limited: false,
    remaining: maxRequests - windowTimestamps.length,
    limit: maxRequests,
    windowMs
  };
};

// Express middleware function
const rateLimitMiddleware = (options = {}) => {
  // Initialize with config path if provided
  if (options.configPath) {
    initConfig(options.configPath);
  }
  
  // Return the middleware function
  return (req, res, next) => {
    // Clean up periodically
    cleanupOldRequests();
    
    // Get client IP
    const ip = req.ip || 
               req.connection.remoteAddress || 
               req.headers['x-forwarded-for'] || 
               'unknown';
    
    // Check rate limit
    const result = isRateLimited(ip, req.path);
    
    // Set headers
    res.setHeader('X-RateLimit-Limit', result.limit);
    res.setHeader('X-RateLimit-Remaining', result.remaining);
    res.setHeader('X-RateLimit-Reset', Math.floor((Date.now() + (result.retryAfter || 0) * 1000) / 1000));
    
    // If limited, send error response
    if (result.limited) {
      res.setHeader('Retry-After', result.retryAfter);
      return res.status(429).json({
        error: 'Too Many Requests',
        message: `Rate limit exceeded. Try again in ${result.retryAfter} seconds.`,
        retry_after: result.retryAfter
      });
    }
    
    // Continue to next middleware
    next();
  };
};

// API for configuration
const getRateLimitConfig = () => {
  return { ...requestStore.config };
};

const updateRateLimitConfig = (config) => {
  requestStore.config = {
    ...requestStore.config,
    ...config
  };
  
  saveConfig();
  return requestStore.config;
};

const getRateLimitStatus = () => {
  // Clean up old requests first
  cleanupOldRequests();
  
  // Count requests by IP and path
  const ipCounts = {};
  for (const [key, timestamps] of requestStore.requests.entries()) {
    const [ip, path] = key.split(':');
    
    if (!ipCounts[ip]) {
      ipCounts[ip] = {
        total: 0,
        paths: {}
      };
    }
    
    ipCounts[ip].total += timestamps.length;
    ipCounts[ip].paths[path] = timestamps.length;
  }
  
  return {
    enabled: requestStore.config.enabled,
    total_tracked_ips: Object.keys(ipCounts).length,
    total_requests: Array.from(requestStore.requests.values())
      .reduce((sum, timestamps) => sum + timestamps.length, 0),
    ip_counts: ipCounts,
    rules: requestStore.config.rules
  };
};

module.exports = {
  rateLimitMiddleware,
  getRateLimitConfig,
  updateRateLimitConfig,
  getRateLimitStatus
};
