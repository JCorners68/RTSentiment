/**
 * Batch Operations Routes
 * 
 * Handles API endpoints for bulk evidence operations
 * Part of the Evidence Management System enhancement
 */

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

// Path to data files
const dataDir = path.join(__dirname, '../../data');
const evidenceDir = path.join(dataDir, 'evidence');
const evidenceFile = path.join(evidenceDir, 'index', 'evidence.json');

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
    // Ensure directories exist
    if (!fs.existsSync(evidenceDir)) {
      fs.mkdirSync(evidenceDir, { recursive: true });
    }
    
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

// POST /api/kanban/batch/evidence - Create multiple evidence items at once
router.post('/evidence', (req, res) => {
  const evidenceItems = req.body.evidence || [];
  
  if (!Array.isArray(evidenceItems) || evidenceItems.length === 0) {
    return res.status(400).json({ error: 'No evidence items provided' });
  }
  
  if (evidenceItems.length > 100) {
    return res.status(400).json({ 
      error: 'Batch size too large', 
      message: 'Maximum batch size is 100 items'
    });
  }
  
  const evidenceData = getEvidence();
  const newEvidenceItems = [];
  const errors = [];
  
  evidenceItems.forEach((item, index) => {
    if (!item.title) {
      errors.push({ 
        index, 
        error: 'Title is required',
        item
      });
      return;
    }
    
    const newEvidence = {
      id: `EVID-${uuidv4().substring(0, 8)}`,
      title: item.title,
      description: item.description || '',
      source: item.source || 'batch-import',
      date_collected: new Date().toISOString(),
      category: item.category || 'uncategorized',
      subcategory: item.subcategory || '',
      relevance_score: item.relevance_score || 5,
      tags: item.tags || [],
      related_evidence_ids: item.related_evidence_ids || [],
      project_id: item.project_id || null,
      epic_id: item.epic_id || null,
      attachments: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
    
    evidenceData.evidence.push(newEvidence);
    newEvidenceItems.push(newEvidence);
  });
  
  if (newEvidenceItems.length === 0) {
    return res.status(400).json({ 
      error: 'No valid evidence items provided',
      errors
    });
  }
  
  if (saveEvidence(evidenceData)) {
    // Create webhook payload for batch import
    const webhookPayload = {
      event: 'evidence_batch_created',
      count: newEvidenceItems.length,
      evidence_ids: newEvidenceItems.map(e => e.id),
      timestamp: new Date().toISOString()
    };
    
    // This would call webhook handler in webhooks.js
    // triggerWebhook(webhookPayload);
    
    return res.status(201).json({ 
      success: true,
      count: newEvidenceItems.length,
      evidence: newEvidenceItems,
      errors: errors.length > 0 ? errors : undefined
    });
  } else {
    return res.status(500).json({ error: 'Failed to save evidence batch' });
  }
});

// PUT /api/kanban/batch/categorize - Update categories for multiple evidence items
router.put('/categorize', (req, res) => {
  const { category, subcategory, evidence_ids } = req.body;
  
  if (!category) {
    return res.status(400).json({ error: 'Category is required' });
  }
  
  if (!Array.isArray(evidence_ids) || evidence_ids.length === 0) {
    return res.status(400).json({ error: 'No evidence IDs provided' });
  }
  
  if (evidence_ids.length > 100) {
    return res.status(400).json({ 
      error: 'Batch size too large', 
      message: 'Maximum batch size is 100 items'
    });
  }
  
  const evidenceData = getEvidence();
  const updated = [];
  const notFound = [];
  
  evidence_ids.forEach(id => {
    const evidenceIndex = evidenceData.evidence.findIndex(e => e.id === id);
    
    if (evidenceIndex === -1) {
      notFound.push(id);
      return;
    }
    
    // Update the evidence item
    evidenceData.evidence[evidenceIndex].category = category;
    
    if (subcategory !== undefined) {
      evidenceData.evidence[evidenceIndex].subcategory = subcategory;
    }
    
    evidenceData.evidence[evidenceIndex].updated_at = new Date().toISOString();
    updated.push(evidenceData.evidence[evidenceIndex]);
  });
  
  if (updated.length === 0) {
    return res.status(404).json({ 
      error: 'No evidence items found',
      not_found: notFound
    });
  }
  
  if (saveEvidence(evidenceData)) {
    // Create webhook payload for batch categorization
    const webhookPayload = {
      event: 'evidence_batch_categorized',
      category,
      subcategory,
      count: updated.length,
      evidence_ids: updated.map(e => e.id),
      timestamp: new Date().toISOString()
    };
    
    // triggerWebhook(webhookPayload);
    
    return res.json({ 
      success: true,
      count: updated.length,
      updated: updated.map(e => e.id),
      not_found: notFound.length > 0 ? notFound : undefined
    });
  } else {
    return res.status(500).json({ error: 'Failed to update evidence batch' });
  }
});

// PUT /api/kanban/batch/tag - Add tags to multiple evidence items
router.put('/tag', (req, res) => {
  const { tags, evidence_ids, remove } = req.body;
  
  if (!Array.isArray(tags) || tags.length === 0) {
    return res.status(400).json({ error: 'No tags provided' });
  }
  
  if (!Array.isArray(evidence_ids) || evidence_ids.length === 0) {
    return res.status(400).json({ error: 'No evidence IDs provided' });
  }
  
  if (evidence_ids.length > 100) {
    return res.status(400).json({ 
      error: 'Batch size too large', 
      message: 'Maximum batch size is 100 items'
    });
  }
  
  const evidenceData = getEvidence();
  const updated = [];
  const notFound = [];
  
  evidence_ids.forEach(id => {
    const evidenceIndex = evidenceData.evidence.findIndex(e => e.id === id);
    
    if (evidenceIndex === -1) {
      notFound.push(id);
      return;
    }
    
    const evidence = evidenceData.evidence[evidenceIndex];
    
    if (!evidence.tags) {
      evidence.tags = [];
    }
    
    if (remove) {
      // Remove specified tags
      evidence.tags = evidence.tags.filter(tag => !tags.includes(tag));
    } else {
      // Add new tags (avoiding duplicates)
      const currentTags = new Set(evidence.tags);
      tags.forEach(tag => currentTags.add(tag));
      evidence.tags = Array.from(currentTags);
    }
    
    evidence.updated_at = new Date().toISOString();
    updated.push(evidence);
  });
  
  if (updated.length === 0) {
    return res.status(404).json({ 
      error: 'No evidence items found',
      not_found: notFound
    });
  }
  
  if (saveEvidence(evidenceData)) {
    // Create webhook payload for batch tagging
    const webhookPayload = {
      event: remove ? 'evidence_batch_tags_removed' : 'evidence_batch_tagged',
      tags,
      count: updated.length,
      evidence_ids: updated.map(e => e.id),
      timestamp: new Date().toISOString()
    };
    
    // triggerWebhook(webhookPayload);
    
    return res.json({ 
      success: true,
      count: updated.length,
      updated: updated.map(e => ({ id: e.id, tags: e.tags })),
      not_found: notFound.length > 0 ? notFound : undefined
    });
  } else {
    return res.status(500).json({ error: 'Failed to update evidence batch' });
  }
});

// DELETE /api/kanban/batch/evidence - Delete multiple evidence items
router.delete('/evidence', (req, res) => {
  const { evidence_ids } = req.body;
  
  if (!Array.isArray(evidence_ids) || evidence_ids.length === 0) {
    return res.status(400).json({ error: 'No evidence IDs provided' });
  }
  
  if (evidence_ids.length > 50) {
    return res.status(400).json({ 
      error: 'Batch size too large', 
      message: 'Maximum batch delete size is 50 items'
    });
  }
  
  const evidenceData = getEvidence();
  const deleted = [];
  const notFound = [];
  
  // Process in reverse to avoid index shifting issues when deleting
  evidence_ids.forEach(id => {
    const evidenceIndex = evidenceData.evidence.findIndex(e => e.id === id);
    
    if (evidenceIndex === -1) {
      notFound.push(id);
      return;
    }
    
    const deletedEvidence = evidenceData.evidence[evidenceIndex];
    evidenceData.evidence.splice(evidenceIndex, 1);
    deleted.push(deletedEvidence);
  });
  
  if (deleted.length === 0) {
    return res.status(404).json({ 
      error: 'No evidence items found',
      not_found: notFound
    });
  }
  
  if (saveEvidence(evidenceData)) {
    // Create webhook payload for batch deletion
    const webhookPayload = {
      event: 'evidence_batch_deleted',
      count: deleted.length,
      evidence_ids: deleted.map(e => e.id),
      timestamp: new Date().toISOString()
    };
    
    // triggerWebhook(webhookPayload);
    
    return res.json({ 
      success: true,
      count: deleted.length,
      deleted: deleted.map(e => e.id),
      not_found: notFound.length > 0 ? notFound : undefined
    });
  } else {
    return res.status(500).json({ error: 'Failed to delete evidence batch' });
  }
});

module.exports = router;
