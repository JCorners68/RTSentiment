/**
 * Attachments Routes
 * 
 * Handles API endpoints for evidence attachment operations
 * Part of the Evidence Management System enhancement
 * Provides secure file upload/download with content validation
 */

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const multer = require('multer');
const rateLimit = require('express-rate-limit');
const crypto = require('crypto');
const fileType = require('file-type');
const sanitizeFilename = require('sanitize-filename');

// Path to data files
const dataDir = path.join(__dirname, '../../data');
const evidenceDir = path.join(dataDir, 'evidence');
const evidenceFile = path.join(evidenceDir, 'index', 'evidence.json');
const attachmentsDir = path.join(evidenceDir, 'attachments');

// Ensure directories exist
if (!fs.existsSync(evidenceDir)) {
  fs.mkdirSync(evidenceDir, { recursive: true });
}

if (!fs.existsSync(attachmentsDir)) {
  fs.mkdirSync(attachmentsDir, { recursive: true });
}

// Generate a secure token for file access
const generateSecureToken = () => {
  return crypto.randomBytes(32).toString('hex');
};

// Validate allowed file types
const allowedMimeTypes = [
  // Documents
  'application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'text/plain', 'text/markdown', 'text/csv',
  // Images
  'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
  // Code/data
  'application/json', 'application/xml', 'text/xml',
  // Archives (limited)
  'application/zip'
];

const fileFilter = (req, file, cb) => {
  // Check if the mime type is allowed
  if (allowedMimeTypes.includes(file.mimetype)) {
    cb(null, true);
  } else {
    cb(new Error(`File type not allowed. Allowed types: ${allowedMimeTypes.join(', ')}`), false);
  }
};

// Configure multer for file uploads with additional security
const storage = multer.diskStorage({
  destination: function(req, file, cb) {
    cb(null, attachmentsDir);
  },
  filename: function(req, file, cb) {
    // Use UUID for filename to avoid path traversal attacks
    const fileId = uuidv4();
    cb(null, fileId);
  }
});

const upload = multer({ 
  storage: storage,
  limits: {
    fileSize: 10 * 1024 * 1024, // 10MB limit
    files: 1 // Only allow one file at a time
  },
  fileFilter: fileFilter
});

// Helper to read evidence
const getEvidence = () => {
  try {
    if (fs.existsSync(evidenceFile)) {
      const data = fs.readFileSync(evidenceFile, 'utf8');
      return JSON.parse(data);
    }
    return { evidence: [] };
  } catch (error) {
    console.error('Error reading evidence file:', error);
    return { evidence: [] };
  }
};

// Helper to write evidence
const saveEvidence = (evidence) => {
  try {
    // Ensure index directory exists
    if (!fs.existsSync(path.join(evidenceDir, 'index'))) {
      fs.mkdirSync(path.join(evidenceDir, 'index'), { recursive: true });
    }
    
    fs.writeFileSync(evidenceFile, JSON.stringify(evidence, null, 2));
    return true;
  } catch (error) {
    console.error('Error writing evidence file:', error);
    return false;
  }
};

// Apply stricter rate limiting to attachment endpoints
const attachmentLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 25, // 25 requests per windowMs
  message: { error: 'Too many attachment requests, please try again later' },
  standardHeaders: true, // Return rate limit info in the `RateLimit-*` headers
  legacyHeaders: false, // Disable the `X-RateLimit-*` headers
  keyGenerator: (req) => {
    // Use IP and evidenceId to prevent abuse per evidence item
    return `${req.ip}:${req.params.evidenceId || 'default'}`;
  }
});

// Apply separate, stricter rate limiter for upload operations
const uploadLimiter = rateLimit({
  windowMs: 60 * 60 * 1000, // 1 hour
  max: 10, // 10 uploads per hour
  message: { error: 'Upload limit reached, please try again later' },
  standardHeaders: true,
  legacyHeaders: false
});

// Apply general rate limiter to all attachment routes
router.use(attachmentLimiter);

// Async helper to verify file content matches its claimed type
const verifyFileType = async (filePath, mimeType) => {
  try {
    const fileInfo = await fileType.fromFile(filePath);
    // If file type detection fails or doesn't match claimed type, it's suspicious
    if (!fileInfo || !allowedMimeTypes.includes(fileInfo.mime)) {
      return false;
    }
    return true;
  } catch (error) {
    console.error('Error verifying file type:', error);
    return false;
  }
};

// POST /api/kanban/attachments/:evidenceId - Upload attachment for an evidence item
router.post('/:evidenceId', uploadLimiter, upload.single('file'), async (req, res) => {
  const { evidenceId } = req.params;
  const { description } = req.body;
  
  if (!req.file) {
    return res.status(400).json({ error: 'No file uploaded' });
  }
  
  // Verify file content matches its claimed type
  const isValidFileType = await verifyFileType(req.file.path, req.file.mimetype);
  if (!isValidFileType) {
    // Clean up the suspicious file
    if (fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }
    return res.status(400).json({ error: 'Invalid file content detected' });
  }
  
  const evidenceData = getEvidence();
  const evidenceIndex = evidenceData.evidence.findIndex(e => e.id === evidenceId);
  
  if (evidenceIndex === -1) {
    // If file was uploaded but evidence not found, clean up
    if (req.file && fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }
    return res.status(404).json({ error: 'Evidence not found' });
  }
  
  const fileId = path.basename(req.file.path);
  // Generate access token for secure downloads
  const accessToken = generateSecureToken();
  
  const attachment = {
    id: `ATCH-${uuidv4().substring(0, 8)}`,
    file_id: fileId,
    filename: sanitizeFilename(req.file.originalname), // Sanitize filename for security
    description: description || '',
    mime_type: req.file.mimetype,
    size_bytes: req.file.size,
    uploaded_at: new Date().toISOString(),
    access_token: accessToken, // Add token for secure access
    content_hash: crypto.createHash('sha256')
      .update(fs.readFileSync(req.file.path))
      .digest('hex') // Add content hash for integrity verification
  };
  
  if (!evidenceData.evidence[evidenceIndex].attachments) {
    evidenceData.evidence[evidenceIndex].attachments = [];
  }
  
  evidenceData.evidence[evidenceIndex].attachments.push(attachment);
  evidenceData.evidence[evidenceIndex].updated_at = new Date().toISOString();
  
  if (saveEvidence(evidenceData)) {
    // Trigger webhook for attachment upload
    const webhookPayload = {
      event: 'attachment_created',
      evidence_id: evidenceId,
      attachment: attachment,
      timestamp: new Date().toISOString()
    };
    
    // This would call webhook handler, we'll implement this in webhooks.js
    // triggerWebhook(webhookPayload);
    
    return res.status(201).json({ 
      evidence_id: evidenceId, 
      attachment: attachment 
    });
  } else {
    // If saving failed, clean up the uploaded file
    if (fs.existsSync(req.file.path)) {
      fs.unlinkSync(req.file.path);
    }
    return res.status(500).json({ error: 'Failed to save attachment metadata' });
  }
});

// GET /api/kanban/attachments/:evidenceId/:attachmentId - Download attachment
// Optional token-based access: /api/kanban/attachments/:evidenceId/:attachmentId?token=xyz
router.get('/:evidenceId/:attachmentId', (req, res) => {
  const { evidenceId, attachmentId } = req.params;
  
  const evidenceData = getEvidence();
  const evidence = evidenceData.evidence.find(e => e.id === evidenceId);
  
  if (!evidence) {
    return res.status(404).json({ error: 'Evidence not found' });
  }
  
  if (!evidence.attachments) {
    return res.status(404).json({ error: 'No attachments found for this evidence' });
  }
  
  const attachment = evidence.attachments.find(a => a.id === attachmentId);
  
  if (!attachment) {
    return res.status(404).json({ error: 'Attachment not found' });
  }
  
  // Validate access token if attachment has one and we're not in development mode
  if (attachment.access_token && process.env.NODE_ENV !== 'development') {
    const providedToken = req.query.token;
    
    // If no token provided, check if this is an authenticated request
    if (!providedToken) {
      const authHeader = req.headers['authorization'] || '';
      const apiKey = req.headers['x-api-key'] || '';
      
      // If not authenticated and no token, deny access
      if (!authHeader.startsWith('Bearer ') && !apiKey) {
        return res.status(401).json({ 
          error: 'Unauthorized', 
          message: 'Access token required for this attachment'
        });
      }
    } else if (providedToken !== attachment.access_token) {
      return res.status(403).json({ 
        error: 'Forbidden', 
        message: 'Invalid access token'
      });
    }
  }
  
  const filePath = path.join(attachmentsDir, attachment.file_id);
  
  if (!fs.existsSync(filePath)) {
    return res.status(404).json({ error: 'Attachment file not found' });
  }
  
  // Verify file integrity if hash is available
  if (attachment.content_hash) {
    try {
      const fileHash = crypto.createHash('sha256')
        .update(fs.readFileSync(filePath))
        .digest('hex');
      
      if (fileHash !== attachment.content_hash) {
        console.error(`File integrity check failed for attachment ${attachment.id}`);
        return res.status(500).json({ error: 'File integrity check failed' });
      }
    } catch (error) {
      console.error(`Error verifying file integrity: ${error.message}`);
    }
  }
  
  // Set secure headers
  res.setHeader('Content-Disposition', `attachment; filename="${attachment.filename}"`);
  res.setHeader('Content-Type', attachment.mime_type || 'application/octet-stream');
  res.setHeader('Content-Length', attachment.size_bytes);
  res.setHeader('X-Content-Type-Options', 'nosniff'); // Prevent MIME type sniffing
  res.setHeader('Cache-Control', 'private, max-age=3600'); // Limited caching
  
  const fileStream = fs.createReadStream(filePath);
  fileStream.pipe(res);
});

// DELETE /api/kanban/attachments/:evidenceId/:attachmentId - Delete attachment
router.delete('/:evidenceId/:attachmentId', (req, res) => {
  const { evidenceId, attachmentId } = req.params;
  
  const evidenceData = getEvidence();
  const evidenceIndex = evidenceData.evidence.findIndex(e => e.id === evidenceId);
  
  if (evidenceIndex === -1) {
    return res.status(404).json({ error: 'Evidence not found' });
  }
  
  if (!evidenceData.evidence[evidenceIndex].attachments) {
    return res.status(404).json({ error: 'No attachments found for this evidence' });
  }
  
  const attachmentIndex = evidenceData.evidence[evidenceIndex].attachments.findIndex(
    a => a.id === attachmentId
  );
  
  if (attachmentIndex === -1) {
    return res.status(404).json({ error: 'Attachment not found' });
  }
  
  const attachment = evidenceData.evidence[evidenceIndex].attachments[attachmentIndex];
  const filePath = path.join(attachmentsDir, attachment.file_id);
  
  // Remove attachment metadata
  evidenceData.evidence[evidenceIndex].attachments.splice(attachmentIndex, 1);
  evidenceData.evidence[evidenceIndex].updated_at = new Date().toISOString();
  
  // Try to delete the file
  let fileDeleted = false;
  if (fs.existsSync(filePath)) {
    try {
      fs.unlinkSync(filePath);
      fileDeleted = true;
    } catch (error) {
      console.error(`Failed to delete attachment file ${filePath}:`, error);
    }
  }
  
  if (saveEvidence(evidenceData)) {
    // Trigger webhook for attachment deletion
    const webhookPayload = {
      event: 'attachment_deleted',
      evidence_id: evidenceId,
      attachment: attachment,
      timestamp: new Date().toISOString()
    };
    
    // triggerWebhook(webhookPayload);
    
    return res.json({
      success: true,
      evidence_id: evidenceId,
      attachment: attachment,
      file_deleted: fileDeleted
    });
  } else {
    return res.status(500).json({ error: 'Failed to update attachment metadata' });
  }
});

module.exports = router;
