/**
 * Webhook Routes
 * 
 * Handles API endpoints for webhook configuration and delivery
 * Part of the Evidence Management System enhancement
 */

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const axios = require('axios');
const { createHash } = require('crypto');
const multer = require('multer');
const fileType = require('file-type');

// Path to data files
const dataDir = path.join(__dirname, '../../data');
const configDir = path.join(dataDir, 'config');
const webhooksFile = path.join(configDir, 'webhooks.json');
const attachmentsDir = path.join(dataDir, 'attachments');

// Ensure attachment directory exists
if (!fs.existsSync(attachmentsDir)) {
  fs.mkdirSync(attachmentsDir, { recursive: true });
}

// Default retry configuration
const DEFAULT_RETRY_CONFIG = {
  maxRetries: 5,
  retryDelay: 5000, // 5 seconds initial delay
  backoffFactor: 2,  // Exponential backoff
  jitter: 0.25,     // 25% jitter to avoid "thundering herd" problem
  maxTimeout: 120000 // Never wait more than 2 minutes between retries
};

// Supported webhook event types
const WEBHOOK_EVENTS = {
  // Evidence events
  EVIDENCE_CREATED: 'evidence.created',
  EVIDENCE_UPDATED: 'evidence.updated',
  EVIDENCE_DELETED: 'evidence.deleted',
  
  // Attachment events
  ATTACHMENT_CREATED: 'attachment.created',
  ATTACHMENT_DELETED: 'attachment.deleted',
  ATTACHMENT_PROCESSED: 'attachment.processed',
  
  // Categorization and tagging events
  EVIDENCE_CATEGORIZED: 'evidence.categorized',
  EVIDENCE_TAGGED: 'evidence.tagged',
  EVIDENCE_UNTAGGED: 'evidence.untagged',
  
  // Relationship events
  RELATIONSHIP_CREATED: 'relationship.created',
  RELATIONSHIP_DELETED: 'relationship.deleted',
  
  // Webhook system events
  WEBHOOK_PING: 'webhook.ping'
};

// Initialize webhook storage
const initWebhooks = () => {
  try {
    if (!fs.existsSync(configDir)) {
      fs.mkdirSync(configDir, { recursive: true });
    }
    
    if (!fs.existsSync(webhooksFile)) {
      const initialData = {
        webhooks: [],
        retryConfig: DEFAULT_RETRY_CONFIG,
        lastUpdated: new Date().toISOString()
      };
      fs.writeFileSync(webhooksFile, JSON.stringify(initialData, null, 2));
      return initialData;
    }
    
    const data = fs.readFileSync(webhooksFile, 'utf8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Error initializing webhooks:', error);
    return {
      webhooks: [],
      retryConfig: DEFAULT_RETRY_CONFIG,
      lastUpdated: new Date().toISOString()
    };
  }
};

// Save webhook configuration
const saveWebhooks = (webhookData) => {
  try {
    webhookData.lastUpdated = new Date().toISOString();
    fs.writeFileSync(webhooksFile, JSON.stringify(webhookData, null, 2));
    return true;
  } catch (error) {
    console.error('Error saving webhooks:', error);
    return false;
  }
};

// Load webhooks on startup
let webhookData = initWebhooks();

// Helper functions for webhook delivery
// Generate HMAC signature for payload security
const generateSignature = (payload, secret) => {
  return createHash('sha256')
    .update(JSON.stringify(payload) + secret)
    .digest('hex');
};

// Calculate retry delay with exponential backoff and jitter
const calculateRetryDelay = (attempt, config) => {
  // Base delay with exponential backoff
  let calculatedDelay = config.retryDelay * Math.pow(config.backoffFactor, attempt);
  
  // Apply jitter to avoid thundering herd problem
  if (config.jitter > 0) {
    const jitterRange = calculatedDelay * config.jitter;
    calculatedDelay = calculatedDelay - (jitterRange / 2) + (Math.random() * jitterRange);
  }
  
  // Cap at max timeout
  return Math.min(calculatedDelay, config.maxTimeout);
};

// Helper to deliver webhook with retry logic
const deliverWebhook = async (webhook, payload) => {
  const { url, secret } = webhook;
  const retryConfig = webhookData.retryConfig || DEFAULT_RETRY_CONFIG;
  
  let attempts = 0;
  let success = false;
  let lastError = null;
  
  const deliveryId = uuidv4();
  
  // Add delivery metadata
  const fullPayload = {
    ...payload,
    delivery_id: deliveryId,
    webhook_id: webhook.id,
    delivery_timestamp: new Date().toISOString()
  };
  
  // Initialize webhook delivery logs if not exists
  if (!webhookData.deliveryLogs) {
    webhookData.deliveryLogs = [];
  }
  
  // Create log entry
  const logEntry = {
    id: deliveryId,
    webhook_id: webhook.id,
    payload: fullPayload,
    status: 'pending',
    attempts: [],
    created_at: new Date().toISOString()
  };
  
  // Add to beginning of logs array
  webhookData.deliveryLogs.unshift(logEntry);
  
  // Trim logs if there are too many
  if (webhookData.deliveryLogs.length > 100) {
    webhookData.deliveryLogs = webhookData.deliveryLogs.slice(0, 100);
  }
  
  saveWebhooks(webhookData);
  
  
  saveWebhooks(webhookData);

  // Attempt delivery with retries
  while (attempts <= retryConfig.maxRetries) {
    try {
      const signature = generateSignature(fullPayload, secret);
      
      const response = await axios({
        method: 'post',
        url,
        data: fullPayload,
        headers: {
          'Content-Type': 'application/json',
          'X-Webhook-Signature': signature,
          'X-Delivery-ID': deliveryId,
          'X-Webhook-Event': payload.event,
          'X-Retry-Count': attempts.toString()
        },
        timeout: 10000 // 10 second timeout
      });
      
      // Success
      success = true;
      
      // Update log
      logEntry.attempts.push({
        timestamp: new Date().toISOString(),
        status_code: response.status,
        success: true,
        duration_ms: Date.now() - new Date(logEntry.attempts[logEntry.attempts.length - 1]?.timestamp || logEntry.created_at).getTime()
      });
      
      logEntry.status = 'delivered';
      logEntry.completed_at = new Date().toISOString();
      
      saveWebhooks(webhookData);
      break;
    } catch (error) {
      lastError = error;
      
      // Get status code if available
      const statusCode = error.response?.status;
      const isClientError = statusCode >= 400 && statusCode < 500;
      
      // Log attempt
      logEntry.attempts.push({
        timestamp: new Date().toISOString(),
        error: error.message,
        status_code: statusCode,
        success: false
      });
      
      saveWebhooks(webhookData);
      
      // Don't retry if it's a permanent client error (except rate limiting)
      if (isClientError && statusCode !== 429 && statusCode !== 408) {
        logEntry.completed_at = new Date().toISOString();
        logEntry.status = 'failed';
        saveWebhooks(webhookData);
        break;
      }
      // Stop if we've reached max retries
      attempts++;
      if (attempts > retryConfig.maxRetries) break;
      
      // Calculate delay with exponential backoff and jitter
      const waitTime = calculateRetryDelay(attempts - 1, retryConfig);
      
      // Update the log with next retry information
      logEntry.next_retry = new Date(Date.now() + waitTime).toISOString();
      logEntry.status = 'pending_retry';
      saveWebhooks(webhookData);
      
      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, waitTime));
      
      console.log(`Retrying webhook ${webhook.id} delivery, attempt ${attempts} of ${retryConfig.maxRetries}`);
    }
    
    // Stop if we've reached max retries
    attempts++;
    if (attempts > retryConfig.maxRetries) break;
    
    // Calculate delay with exponential backoff and jitter
    const waitTime = calculateRetryDelay(attempts - 1, retryConfig);
    
    // Update the log with next retry information
    logEntry.next_retry = new Date(Date.now() + waitTime).toISOString();
    logEntry.status = 'pending_retry';
    saveWebhooks(webhookData);
    
    // Wait before retrying
    await new Promise(resolve => setTimeout(resolve, waitTime));
    
    console.log(`Retrying webhook ${webhook.id} delivery, attempt ${attempts} of ${retryConfig.maxRetries}`);
  }
}

// Final status update
if (!success) {
  logEntry.status = 'failed';
  logEntry.completed_at = new Date().toISOString();
  logEntry.failure_reason = lastError?.message || 'Unknown error';
  saveWebhooks(webhookData);
  
  // Queue for retry task if needed
  if (webhook.retry_failed && attempts > retryConfig.maxRetries) {
    queueFailedWebhookForRetry(webhook.id, deliveryId);
  }
}

// ... (rest of the code remains the same)

// Queue a failed webhook for a later retry batch process
const queueFailedWebhookForRetry = (webhookId, deliveryId) => {
  if (!webhookData.retryQueue) {
    webhookData.retryQueue = [];
  }
  
  webhookData.retryQueue.push({
    webhook_id: webhookId,
    delivery_id: deliveryId,
    queued_at: new Date().toISOString(),
    retry_attempts: 0
  });
  
  saveWebhooks(webhookData);
};

// Process webhook retry queue - would be called by a scheduled task
const processRetryQueue = async () => {
  if (!webhookData.retryQueue || webhookData.retryQueue.length === 0) {
    return { processed: 0 };
  }
  
  console.log(`Processing ${webhookData.retryQueue.length} failed webhooks in retry queue`);
  
  let processed = 0;
  let succeeded = 0;
  
  // Create a new queue for items still failing
  const newQueue = [];
  
  // Process each queued item
  for (const item of webhookData.retryQueue) {
    processed++;
    
    // Find the original webhook and log entry
    const webhook = webhookData.webhooks.find(w => w.id === item.webhook_id);
    const logEntry = webhookData.deliveryLogs.find(l => l.id === item.delivery_id);
    
    // Skip if webhook or log is missing, or webhook is now inactive
    if (!webhook || !logEntry || !webhook.active) {
      continue;
    }
    
    // Attempt to deliver again with a fresh retry sequence
    try {
      // Reconstruct payload from the log
      const payload = { ...logEntry.payload };
      
      const result = await deliverWebhook(webhook, payload);
      if (result.success) {
        succeeded++;
      } else if (item.retry_attempts < 3) { // Max batch retry attempts
        // Add back to queue with incremented attempt count
        newQueue.push({
          ...item,
          retry_attempts: item.retry_attempts + 1,
          last_retry: new Date().toISOString()
        });
      }
    } catch (error) {
      console.error(`Error processing retry for webhook ${webhook.id}:`, error);
      
      // Add back to queue if not too many attempts
      if (item.retry_attempts < 3) {
        newQueue.push({
          ...item,
          retry_attempts: item.retry_attempts + 1,
          last_retry: new Date().toISOString(),
          last_error: error.message
        });
      }
    }
  }
  
  // Update the queue
  webhookData.retryQueue = newQueue;
  saveWebhooks(webhookData);
  
  return {
    processed,
    succeeded,
    remaining: newQueue.length
  };
};

// Trigger all relevant webhooks for an event
const triggerWebhooks = (payload) => {
  if (!payload || !payload.event) {
    console.error('Invalid webhook payload, missing event');
    return;
  }
  
  // Find webhooks that subscribe to this event
  const relevantWebhooks = webhookData.webhooks.filter(webhook => 
    webhook.active && 
    (webhook.events.includes(payload.event) || webhook.events.includes('*'))
  );
  
  if (relevantWebhooks.length === 0) {
    console.log(`No active webhooks for event: ${payload.event}`);
    return;
  }
  
  console.log(`Triggering ${relevantWebhooks.length} webhooks for event: ${payload.event}`);
  
  // Deliver the webhook asynchronously to each subscriber
  relevantWebhooks.forEach(webhook => {
    deliverWebhook(webhook, payload)
      .catch(error => {
        console.error(`Error delivering webhook ${webhook.id}:`, error);
      });
  });
  
  return relevantWebhooks.length;
};

// Make webhook functions available globally
global.triggerWebhooks = triggerWebhooks;
global.processRetryQueue = processRetryQueue;

// GET /api/kanban/webhooks - List all webhooks
router.get('/', (req, res) => {
  // Don't return secrets or delivery logs
  const sanitizedWebhooks = webhookData.webhooks.map(webhook => {
    const { secret, ...rest } = webhook;
    return rest;
  });
  
  res.json({
    webhooks: sanitizedWebhooks,
    count: sanitizedWebhooks.length,
    retry_config: webhookData.retryConfig
  });
});

// POST /api/kanban/webhooks - Create a new webhook
router.post('/', (req, res) => {
  const { name, url, events, description } = req.body;
  
  // Validate required fields
  if (!name || !url) {
    return res.status(400).json({
      error: 'Validation failed',
      details: 'Name and URL are required'
    });
  }
  
  // Validate URL format
  try {
    new URL(url);
  } catch (error) {
    return res.status(400).json({
      error: 'Validation failed',
      details: 'Invalid URL format'
    });
  }
  
  // Validate events
  if (!Array.isArray(events) || events.length === 0) {
    return res.status(400).json({
      error: 'Validation failed',
      details: 'Events must be a non-empty array'
    });
  }
  
  const webhook = {
    id: `HOOK-${uuidv4().substring(0, 8)}`,
    name,
    url,
    events,
    description: description || '',
    secret: uuidv4(), // Generate a random secret
    active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
  
  webhookData.webhooks.push(webhook);
  
  if (saveWebhooks(webhookData)) {
    // Don't return the secret in the response
    const { secret, ...sanitizedWebhook } = webhook;
    
    return res.status(201).json({
      webhook: sanitizedWebhook,
      message: 'Webhook created successfully'
    });
  } else {
    return res.status(500).json({
      error: 'Failed to save webhook'
    });
  }
});

// GET /api/kanban/webhooks/:id - Get webhook details
router.get('/:id', (req, res) => {
  const { id } = req.params;
  
  const webhook = webhookData.webhooks.find(w => w.id === id);
  
  if (!webhook) {
    return res.status(404).json({
      error: 'Webhook not found'
    });
  }
  
  // Don't return the secret
  const { secret, ...sanitizedWebhook } = webhook;
  
  // Get recent delivery logs for this webhook
  const logs = (webhookData.deliveryLogs || [])
    .filter(log => log.webhook_id === id)
    .slice(0, 10); // Only get the 10 most recent logs
  
  return res.json({
    webhook: sanitizedWebhook,
    recent_deliveries: logs
  });
});

// PATCH /api/kanban/webhooks/:id - Update webhook
router.patch('/:id', (req, res) => {
  const { id } = req.params;
  const { name, url, events, description, active } = req.body;
  
  const webhookIndex = webhookData.webhooks.findIndex(w => w.id === id);
  
  if (webhookIndex === -1) {
    return res.status(404).json({
      error: 'Webhook not found'
    });
  }
  
  const webhook = webhookData.webhooks[webhookIndex];
  
  // Update fields if provided
  if (name !== undefined) webhook.name = name;
  if (url !== undefined) {
    // Validate URL format
    try {
      new URL(url);
      webhook.url = url;
    } catch (error) {
      return res.status(400).json({
        error: 'Validation failed',
        details: 'Invalid URL format'
      });
    }
  }
  
  if (events !== undefined) {
    if (!Array.isArray(events) || events.length === 0) {
      return res.status(400).json({
        error: 'Validation failed',
        details: 'Events must be a non-empty array'
      });
    }
    webhook.events = events;
  }
  
  if (description !== undefined) webhook.description = description;
  if (active !== undefined) webhook.active = !!active;
  
  webhook.updated_at = new Date().toISOString();
  
  if (saveWebhooks(webhookData)) {
    // Don't return the secret
    const { secret, ...sanitizedWebhook } = webhook;
    
    return res.json({
      webhook: sanitizedWebhook,
      message: 'Webhook updated successfully'
    });
  } else {
    return res.status(500).json({
      error: 'Failed to update webhook'
    });
  }
});

// DELETE /api/kanban/webhooks/:id - Delete webhook
router.delete('/:id', (req, res) => {
  const { id } = req.params;
  
  const webhookIndex = webhookData.webhooks.findIndex(w => w.id === id);
  
  if (webhookIndex === -1) {
    return res.status(404).json({
      error: 'Webhook not found'
    });
  }
  
  const webhook = webhookData.webhooks[webhookIndex];
  webhookData.webhooks.splice(webhookIndex, 1);
  
  if (saveWebhooks(webhookData)) {
    return res.json({
      success: true,
      message: 'Webhook deleted successfully',
      id
    });
  } else {
    return res.status(500).json({
      error: 'Failed to delete webhook'
    });
  }
});

// POST /api/kanban/webhooks/:id/test - Test a webhook by sending a ping
router.post('/:id/test', (req, res) => {
  const { id } = req.params;
  
  const webhook = webhookData.webhooks.find(w => w.id === id);
  
  if (!webhook) {
    return res.status(404).json({
      error: 'Webhook not found'
    });
  }
  
  // Create a test payload
  const testPayload = {
    event: WEBHOOK_EVENTS.WEBHOOK_PING,
    message: 'This is a test webhook delivery',
    webhook_name: webhook.name,
    timestamp: new Date().toISOString()
  };
  
  // Deliver the webhook asynchronously
  deliverWebhook(webhook, testPayload)
    .then(result => {
      console.log(`Test webhook ${id} delivery result:`, result);
    })
    .catch(error => {
      console.error(`Error delivering test webhook ${id}:`, error);
    });
  
  // Respond immediately as webhook delivery happens asynchronously
  return res.json({
    success: true,
    message: 'Test webhook delivery initiated',
    webhook_id: id
  });
});

// PUT /api/kanban/webhooks/retry-config - Update retry configuration
router.put('/retry-config', (req, res) => {
  const { maxRetries, retryDelay, backoffFactor } = req.body;
  
  // Validate fields
  if (maxRetries !== undefined && (typeof maxRetries !== 'number' || maxRetries < 0 || maxRetries > 10)) {
    return res.status(400).json({
      error: 'Validation failed',
      details: 'maxRetries must be a number between 0 and 10'
    });
  }
  
  if (retryDelay !== undefined && (typeof retryDelay !== 'number' || retryDelay < 1000 || retryDelay > 60000)) {
    return res.status(400).json({
      error: 'Validation failed',
      details: 'retryDelay must be a number between 1000 and 60000 (1-60 seconds)'
    });
  }
  
  if (backoffFactor !== undefined && (typeof backoffFactor !== 'number' || backoffFactor < 1 || backoffFactor > 5)) {
    return res.status(400).json({
      error: 'Validation failed',
      details: 'backoffFactor must be a number between 1 and 5'
    });
  }
  
  // Update retry configuration
  webhookData.retryConfig = {
    ...webhookData.retryConfig,
    ...(maxRetries !== undefined && { maxRetries }),
    ...(retryDelay !== undefined && { retryDelay }),
    ...(backoffFactor !== undefined && { backoffFactor })
  };
  
  if (saveWebhooks(webhookData)) {
    return res.json({
      success: true,
      retry_config: webhookData.retryConfig
    });
  } else {
    return res.status(500).json({
      error: 'Failed to update retry configuration'
    });
  }
});

// POST /api/kanban/webhooks/retry-queue/process - Process the retry queue
router.post('/retry-queue/process', async (req, res) => {
  try {
    const result = await processRetryQueue();
    return res.json({
      success: true,
      ...result
    });
  } catch (error) {
    console.error('Error processing retry queue:', error);
    return res.status(500).json({
      error: 'Failed to process retry queue',
      details: error.message
    });
  }
});

// GET /api/kanban/webhooks/events - List available event types
router.get('/events', (req, res) => {
  return res.json({
    events: Object.values(WEBHOOK_EVENTS),
    categories: {
      evidence: [WEBHOOK_EVENTS.EVIDENCE_CREATED, WEBHOOK_EVENTS.EVIDENCE_UPDATED, WEBHOOK_EVENTS.EVIDENCE_DELETED],
      attachment: [WEBHOOK_EVENTS.ATTACHMENT_CREATED, WEBHOOK_EVENTS.ATTACHMENT_DELETED, WEBHOOK_EVENTS.ATTACHMENT_PROCESSED],
      categorization: [WEBHOOK_EVENTS.EVIDENCE_CATEGORIZED, WEBHOOK_EVENTS.EVIDENCE_TAGGED, WEBHOOK_EVENTS.EVIDENCE_UNTAGGED],
      relationship: [WEBHOOK_EVENTS.RELATIONSHIP_CREATED, WEBHOOK_EVENTS.RELATIONSHIP_DELETED],
      system: [WEBHOOK_EVENTS.WEBHOOK_PING]
    }
  });
});

// GET /api/kanban/webhooks/retry-queue - View the retry queue status
router.get('/retry-queue', (req, res) => {
  if (!webhookData.retryQueue) {
    webhookData.retryQueue = [];
    saveWebhooks(webhookData);
  }
  
  // Don't return full payload details for queue items
  const queueSummary = webhookData.retryQueue.map(item => ({
    webhook_id: item.webhook_id,
    delivery_id: item.delivery_id,
    queued_at: item.queued_at,
    retry_attempts: item.retry_attempts,
    last_retry: item.last_retry
  }));
  
  return res.json({
    queue: queueSummary,
    count: queueSummary.length,
    retry_config: webhookData.retryConfig
  });
});

// Export the router
// POST /api/kanban/webhooks/attachment-processing - Process attachment for events
router.post('/attachment-processing', (req, res) => {
  const { attachment_id, evidence_id, operation, metadata } = req.body;
  
  if (!attachment_id || !evidence_id || !operation) {
    return res.status(400).json({
      error: 'Validation failed',
      details: 'attachment_id, evidence_id, and operation are required'
    });
  }
  
  let event;
  switch (operation) {
    case 'analyze':
      event = WEBHOOK_EVENTS.ATTACHMENT_PROCESSED;
      break;
    case 'create':
      event = WEBHOOK_EVENTS.ATTACHMENT_CREATED;
      break;
    case 'delete':
      event = WEBHOOK_EVENTS.ATTACHMENT_DELETED;
      break;
    default:
      return res.status(400).json({
        error: 'Validation failed',
        details: 'Invalid operation. Must be one of: analyze, create, delete'
      });
  }
  
  // Create a payload for the webhook
  const payload = {
    event,
    data: {
      attachment_id,
      evidence_id,
      operation,
      timestamp: new Date().toISOString(),
      metadata: metadata || {}
    }
  };
  
  // Trigger webhooks for this event
  const webhookCount = triggerWebhooks(payload);
  
  return res.json({
    success: true,
    message: `Triggered ${webhookCount || 0} webhooks for attachment ${operation} event`,
    event
  });
});

// POST /api/kanban/webhooks/categorization - Handle categorization and tagging events
router.post('/categorization', (req, res) => {
  const { evidence_ids, operation, category, subcategory, tags } = req.body;
  
  if (!evidence_ids || !Array.isArray(evidence_ids) || evidence_ids.length === 0) {
    return res.status(400).json({
      error: 'Validation failed',
      details: 'evidence_ids array is required and cannot be empty'
    });
  }
  
  if (!operation) {
    return res.status(400).json({
      error: 'Validation failed',
      details: 'operation is required'
    });
  }
  
  let event;
  switch (operation) {
    case 'categorize':
      event = WEBHOOK_EVENTS.EVIDENCE_CATEGORIZED;
      if (!category) {
        return res.status(400).json({
          error: 'Validation failed',
          details: 'category is required for categorize operation'
        });
      }
      break;
    case 'tag':
      event = WEBHOOK_EVENTS.EVIDENCE_TAGGED;
      if (!tags || !Array.isArray(tags) || tags.length === 0) {
        return res.status(400).json({
          error: 'Validation failed',
          details: 'tags array is required and cannot be empty for tag operation'
        });
      }
      break;
    case 'untag':
      event = WEBHOOK_EVENTS.EVIDENCE_UNTAGGED;
      if (!tags || !Array.isArray(tags) || tags.length === 0) {
        return res.status(400).json({
          error: 'Validation failed',
          details: 'tags array is required and cannot be empty for untag operation'
        });
      }
      break;
    default:
      return res.status(400).json({
        error: 'Validation failed',
        details: 'Invalid operation. Must be one of: categorize, tag, untag'
      });
  }
  
  // Create a payload for the webhook
  const payload = {
    event,
    data: {
      evidence_ids,
      operation,
      timestamp: new Date().toISOString(),
      ...(category && { category }),
      ...(subcategory && { subcategory }),
      ...(tags && { tags }),
      total_items: evidence_ids.length
    }
  };
  
  // Trigger webhooks for this event
  const webhookCount = triggerWebhooks(payload);
  
  return res.json({
    success: true,
    message: `Triggered ${webhookCount || 0} webhooks for evidence ${operation} event`,
    affected_items: evidence_ids.length,
    event
  });
});

// POST /api/kanban/webhooks/relationships - Handle relationship management events
router.post('/relationships', (req, res) => {
  const { source_id, target_id, relationship_type, operation } = req.body;
  
  if (!source_id || !target_id || !relationship_type) {
    return res.status(400).json({
      error: 'Validation failed',
      details: 'source_id, target_id, and relationship_type are required'
    });
  }
  
  if (!operation || !['create', 'delete'].includes(operation)) {
    return res.status(400).json({
      error: 'Validation failed',
      details: 'operation is required and must be one of: create, delete'
    });
  }
  
  const event = operation === 'create' ? 
    WEBHOOK_EVENTS.RELATIONSHIP_CREATED : 
    WEBHOOK_EVENTS.RELATIONSHIP_DELETED;
  
  // Create a payload for the webhook
  const payload = {
    event,
    data: {
      source_id,
      target_id,
      relationship_type,
      operation,
      timestamp: new Date().toISOString()
    }
  };
  
  // Trigger webhooks for this event
  const webhookCount = triggerWebhooks(payload);
  
  return res.json({
    success: true,
    message: `Triggered ${webhookCount || 0} webhooks for relationship ${operation} event`,
    event
  });
});

module.exports = router;
