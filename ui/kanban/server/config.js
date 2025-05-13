/**
 * Server Configuration
 * 
 * Central configuration for the CLI Kanban companion server.
 * Values can be overridden by environment variables.
 */

const path = require('path');
const fs = require('fs');

// Determine project root directory
const projectRoot = path.resolve(__dirname, '..');

// Try to load .env file if it exists
try {
  if (fs.existsSync(path.join(projectRoot, '.env'))) {
    require('dotenv').config({ path: path.join(projectRoot, '.env') });
  }
} catch (err) {
  console.warn('Warning: Error loading .env file:', err.message);
}

/**
 * Configuration object with defaults and environment variable overrides
 */
const config = {
  // Server settings
  port: process.env.KANBAN_SERVER_PORT || 3000,
  host: process.env.KANBAN_SERVER_HOST || 'localhost',
  
  // Security settings
  webhookSecret: process.env.WEBHOOK_SECRET || 'default-development-secret',
  
  // CORS settings for API
  corsOrigins: process.env.CORS_ORIGINS ? 
    process.env.CORS_ORIGINS.split(',') : 
    ['http://localhost:3000', 'http://localhost:8080', 'http://localhost:5678'],
  
  // Logging settings
  logLevel: process.env.LOG_LEVEL || 'info',
  logFile: process.env.LOG_FILE || path.join(projectRoot, 'logs', 'server.log'),
  
  // n8n integration
  n8nWebhookUrl: process.env.N8N_WEBHOOK_URL || 'http://localhost:5678/webhook',
  
  // File paths
  dataDir: process.env.DATA_DIR || path.join(projectRoot, 'data'),
  
  // Feature flags
  features: {
    enableWebhooks: process.env.ENABLE_WEBHOOKS !== 'false',
    enableCors: process.env.ENABLE_CORS !== 'false',
    enableRateLimit: process.env.ENABLE_RATE_LIMIT !== 'false',
    enableLogging: process.env.ENABLE_LOGGING !== 'false',
  },
  
  // Rate limiting
  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || 15 * 60 * 1000), // 15 minutes
    maxRequests: parseInt(process.env.RATE_LIMIT_MAX || 100), // Limit each IP to 100 requests per windowMs
  }
};

// Environment-specific overrides
if (process.env.NODE_ENV === 'production') {
  // Production-specific settings
  config.features.enableRateLimit = true;
  
  // Ensure we're not using the default webhook secret in production
  if (config.webhookSecret === 'default-development-secret') {
    console.error('ERROR: Using default webhook secret in production is not allowed. Please set WEBHOOK_SECRET environment variable.');
    process.exit(1);
  }
} else if (process.env.NODE_ENV === 'test') {
  // Test-specific settings
  config.port = 3001; // Use different port for tests
  config.dataDir = path.join(projectRoot, 'test-data');
  config.logFile = path.join(projectRoot, 'logs', 'test-server.log');
}

// Create directory structure if it doesn't exist
try {
  // Ensure data directory exists
  if (!fs.existsSync(config.dataDir)) {
    fs.mkdirSync(config.dataDir, { recursive: true });
  }
  
  // Ensure log directory exists
  const logDir = path.dirname(config.logFile);
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
} catch (err) {
  console.warn('Warning: Could not create required directories:', err.message);
}

// Validate configuration
function validateConfig() {
  // Port must be a number
  if (isNaN(config.port) || config.port < 1 || config.port > 65535) {
    throw new Error(`Invalid port number: ${config.port}`);
  }
  
  // Webhook URL must be valid (if webhooks are enabled)
  if (config.features.enableWebhooks) {
    try {
      new URL(config.n8nWebhookUrl);
    } catch (err) {
      throw new Error(`Invalid n8n webhook URL: ${config.n8nWebhookUrl}`);
    }
  }
}

// Run validation unless explicitly disabled
if (process.env.DISABLE_CONFIG_VALIDATION !== 'true') {
  try {
    validateConfig();
  } catch (err) {
    console.error('Configuration validation error:', err.message);
    process.exit(1);
  }
}

module.exports = config;