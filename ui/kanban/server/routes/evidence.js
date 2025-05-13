/**
 * Evidence Routes
 * 
 * Handles API endpoints for evidence operations
 * This is a key part of the Evidence Management System
 */

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

// Path to data files - normally this would come from configuration
const dataDir = path.join(__dirname, '../../data');
const evidenceDir = path.join(dataDir, 'evidence');
const evidenceFile = path.join(evidenceDir, 'index', 'evidence.json');
const attachmentsDir = path.join(evidenceDir, 'attachments');

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
    
    if (!fs.existsSync(attachmentsDir)) {
      fs.mkdirSync(attachmentsDir, { recursive: true });
    }
    
    fs.writeFileSync(evidenceFile, JSON.stringify(evidence, null, 2));
    return true;
  } catch (error) {
    console.error('Error writing evidence file:', error);
    return false;
  }
};

// GET /api/kanban/evidence - List all evidence with optional filtering
router.get('/', (req, res) => {
  const evidenceData = getEvidence();
  
  // Apply filters if provided
  let filteredEvidence = [...evidenceData.evidence];
  
  if (req.query.category) {
    filteredEvidence = filteredEvidence.filter(item => 
      item.category === req.query.category);
  }
  
  if (req.query.relevance) {
    const minRelevance = parseInt(req.query.relevance);
    if (!isNaN(minRelevance)) {
      filteredEvidence = filteredEvidence.filter(item => 
        (item.relevance_score || 0) >= minRelevance);
    }
  }
  
  if (req.query.tags) {
    const requiredTags = req.query.tags.split(',').map(tag => tag.trim().toLowerCase());
    filteredEvidence = filteredEvidence.filter(item => 
      item.tags && requiredTags.every(tag => 
        item.tags.map(t => t.toLowerCase()).includes(tag)));
  }
  
  if (req.query.search) {
    const searchLower = req.query.search.toLowerCase();
    filteredEvidence = filteredEvidence.filter(item => 
      item.title.toLowerCase().includes(searchLower) || 
      (item.description && item.description.toLowerCase().includes(searchLower)));
  }
  
  res.json({ evidence: filteredEvidence });
});

// GET /api/kanban/evidence/:id - Get a specific evidence item by ID
router.get('/:id', (req, res) => {
  const { id } = req.params;
  const evidenceData = getEvidence();
  const evidenceItem = evidenceData.evidence.find(e => e.id === id);
  
  if (!evidenceItem) {
    return res.status(404).json({ error: 'Evidence not found' });
  }
  
  res.json({ evidence: evidenceItem });
});

// POST /api/kanban/evidence - Create a new evidence item
router.post('/', (req, res) => {
  const { 
    title, 
    description, 
    source, 
    category, 
    subcategory, 
    relevance_score, 
    tags, 
    related_evidence_ids, 
    project_id, 
    epic_id 
  } = req.body;
  
  if (!title) {
    return res.status(400).json({ error: 'Title is required' });
  }
  
  const newEvidence = {
    id: `EVID-${uuidv4().substring(0, 8)}`,
    title,
    description: description || '',
    source: source || 'manual',
    date_collected: new Date().toISOString(),
    category: category || 'uncategorized',
    subcategory: subcategory || '',
    relevance_score: relevance_score || 5,
    tags: tags || [],
    related_evidence_ids: related_evidence_ids || [],
    project_id: project_id || null,
    epic_id: epic_id || null,
    attachments: []
  };
  
  const evidenceData = getEvidence();
  evidenceData.evidence.push(newEvidence);
  
  if (saveEvidence(evidenceData)) {
    res.status(201).json({ evidence: newEvidence });
  } else {
    res.status(500).json({ error: 'Failed to save evidence' });
  }
});

// PUT /api/kanban/evidence/:id - Update an evidence item
router.put('/:id', (req, res) => {
  const { id } = req.params;
  const evidenceData = getEvidence();
  const evidenceIndex = evidenceData.evidence.findIndex(e => e.id === id);
  
  if (evidenceIndex === -1) {
    return res.status(404).json({ error: 'Evidence not found' });
  }
  
  const updatedEvidence = {
    ...evidenceData.evidence[evidenceIndex],
    ...req.body,
    updated_at: new Date().toISOString()
  };
  
  evidenceData.evidence[evidenceIndex] = updatedEvidence;
  
  if (saveEvidence(evidenceData)) {
    res.json({ evidence: updatedEvidence });
  } else {
    res.status(500).json({ error: 'Failed to update evidence' });
  }
});

// DELETE /api/kanban/evidence/:id - Delete an evidence item
router.delete('/:id', (req, res) => {
  const { id } = req.params;
  const evidenceData = getEvidence();
  const evidenceIndex = evidenceData.evidence.findIndex(e => e.id === id);
  
  if (evidenceIndex === -1) {
    return res.status(404).json({ error: 'Evidence not found' });
  }
  
  const deletedEvidence = evidenceData.evidence[evidenceIndex];
  
  // Delete any associated attachments
  if (deletedEvidence.attachments && deletedEvidence.attachments.length > 0) {
    deletedEvidence.attachments.forEach(attachment => {
      const attachmentPath = path.join(attachmentsDir, attachment.file_id);
      if (fs.existsSync(attachmentPath)) {
        try {
          fs.unlinkSync(attachmentPath);
        } catch (error) {
          console.error(`Failed to delete attachment ${attachment.file_id}:`, error);
        }
      }
    });
  }
  
  evidenceData.evidence.splice(evidenceIndex, 1);
  
  if (saveEvidence(evidenceData)) {
    res.json({ success: true, evidence: deletedEvidence });
  } else {
    res.status(500).json({ error: 'Failed to delete evidence' });
  }
});

// GET /api/kanban/evidence/:id/attachments - List all attachments for an evidence item
router.get('/:id/attachments', (req, res) => {
  const { id } = req.params;
  const evidenceData = getEvidence();
  const evidenceItem = evidenceData.evidence.find(e => e.id === id);
  
  if (!evidenceItem) {
    return res.status(404).json({ error: 'Evidence not found' });
  }
  
  res.json({ 
    evidence_id: id,
    attachments: evidenceItem.attachments || [] 
  });
});

// POST /api/kanban/evidence/:id/attachments - Add attachment to evidence
// This endpoint is placeholder as file upload requires multipart handling
router.post('/:id/attachments', (req, res) => {
  res.status(501).json({ 
    error: 'Not implemented',
    message: 'File uploads should be handled through the CLI tool which has access to the local filesystem'
  });
});

module.exports = router;