/**
 * Epic Routes
 * 
 * Handles API endpoints for epic operations
 */

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

// Path to data file - normally this would come from configuration
const dataDir = path.join(__dirname, '../../data');
const epicsFile = path.join(dataDir, 'epics.json');

// Helper to read epics
const getEpics = () => {
  try {
    if (fs.existsSync(epicsFile)) {
      const data = fs.readFileSync(epicsFile, 'utf8');
      return JSON.parse(data);
    }
    return { epics: [] };
  } catch (error) {
    console.error('Error reading epics file:', error);
    return { epics: [] };
  }
};

// Helper to write epics
const saveEpics = (epics) => {
  try {
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }
    fs.writeFileSync(epicsFile, JSON.stringify(epics, null, 2));
    return true;
  } catch (error) {
    console.error('Error writing epics file:', error);
    return false;
  }
};

// GET /api/kanban/epics - List all epics
router.get('/', (req, res) => {
  const epics = getEpics();
  
  // Apply filters if provided
  let filteredEpics = [...epics.epics];
  
  if (req.query.status) {
    filteredEpics = filteredEpics.filter(epic => 
      epic.status.toLowerCase() === req.query.status.toLowerCase());
  }
  
  if (req.query.search) {
    const searchLower = req.query.search.toLowerCase();
    filteredEpics = filteredEpics.filter(epic => 
      epic.title.toLowerCase().includes(searchLower) || 
      (epic.description && epic.description.toLowerCase().includes(searchLower)));
  }
  
  res.json({ epics: filteredEpics });
});

// GET /api/kanban/epic/:id - Get a specific epic by ID
router.get('/:id', (req, res) => {
  const { id } = req.params;
  const epics = getEpics();
  const epic = epics.epics.find(e => e.id === id);
  
  if (!epic) {
    return res.status(404).json({ error: 'Epic not found' });
  }
  
  res.json({ epic });
});

// POST /api/kanban/epics - Create a new epic
router.post('/', (req, res) => {
  const { title, description, status, priority } = req.body;
  
  if (!title) {
    return res.status(400).json({ error: 'Title is required' });
  }
  
  const newEpic = {
    id: `EPIC-${uuidv4().substring(0, 8)}`,
    title,
    description: description || '',
    status: status || 'Planning',
    priority: priority || 'Medium',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    tasks: []
  };
  
  const epics = getEpics();
  epics.epics.push(newEpic);
  
  if (saveEpics(epics)) {
    res.status(201).json({ epic: newEpic });
  } else {
    res.status(500).json({ error: 'Failed to save epic' });
  }
});

// PUT /api/kanban/epic/:id - Update an epic
router.put('/:id', (req, res) => {
  const { id } = req.params;
  const epics = getEpics();
  const epicIndex = epics.epics.findIndex(e => e.id === id);
  
  if (epicIndex === -1) {
    return res.status(404).json({ error: 'Epic not found' });
  }
  
  const updatedEpic = {
    ...epics.epics[epicIndex],
    ...req.body,
    updated_at: new Date().toISOString()
  };
  
  epics.epics[epicIndex] = updatedEpic;
  
  if (saveEpics(epics)) {
    res.json({ epic: updatedEpic });
  } else {
    res.status(500).json({ error: 'Failed to update epic' });
  }
});

// DELETE /api/kanban/epic/:id - Delete an epic
router.delete('/:id', (req, res) => {
  const { id } = req.params;
  const epics = getEpics();
  const epicIndex = epics.epics.findIndex(e => e.id === id);
  
  if (epicIndex === -1) {
    return res.status(404).json({ error: 'Epic not found' });
  }
  
  const deletedEpic = epics.epics[epicIndex];
  epics.epics.splice(epicIndex, 1);
  
  if (saveEpics(epics)) {
    res.json({ success: true, epic: deletedEpic });
  } else {
    res.status(500).json({ error: 'Failed to delete epic' });
  }
});

// POST /api/kanban/epic/:id/update - Special endpoint for n8n callbacks
router.post('/:id/update', (req, res) => {
  const { id } = req.params;
  const updateData = req.body;
  const epics = getEpics();
  const epicIndex = epics.epics.findIndex(e => e.id === id);
  
  if (epicIndex === -1) {
    return res.status(404).json({ error: 'Epic not found' });
  }
  
  // Apply updates
  const updatedEpic = {
    ...epics.epics[epicIndex],
    ...updateData,
    updated_at: new Date().toISOString()
  };
  
  epics.epics[epicIndex] = updatedEpic;
  
  if (saveEpics(epics)) {
    // Here we would notify any active CLI sessions
    // This would be implemented in the Python wrapper
    
    res.json({ 
      success: true, 
      epic: updatedEpic,
      message: 'Epic updated via webhook'
    });
  } else {
    res.status(500).json({ error: 'Failed to update epic' });
  }
});

module.exports = router;