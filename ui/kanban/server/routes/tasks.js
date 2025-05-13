/**
 * Task Routes
 * 
 * Handles API endpoints for task operations
 */

const express = require('express');
const router = express.Router();
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

// Path to data file - normally this would come from configuration
const dataDir = path.join(__dirname, '../../data');
const tasksFile = path.join(dataDir, 'tasks.json');

// Helper to read tasks
const getTasks = () => {
  try {
    if (fs.existsSync(tasksFile)) {
      const data = fs.readFileSync(tasksFile, 'utf8');
      return JSON.parse(data);
    }
    return { tasks: [] };
  } catch (error) {
    console.error('Error reading tasks file:', error);
    return { tasks: [] };
  }
};

// Helper to write tasks
const saveTasks = (tasks) => {
  try {
    if (!fs.existsSync(dataDir)) {
      fs.mkdirSync(dataDir, { recursive: true });
    }
    fs.writeFileSync(tasksFile, JSON.stringify(tasks, null, 2));
    return true;
  } catch (error) {
    console.error('Error writing tasks file:', error);
    return false;
  }
};

// GET /api/kanban/tasks - List all tasks with optional filtering
router.get('/', (req, res) => {
  const tasks = getTasks();
  
  // Apply filters if provided
  let filteredTasks = [...tasks.tasks];
  
  if (req.query.status) {
    filteredTasks = filteredTasks.filter(task => 
      task.status.toLowerCase() === req.query.status.toLowerCase());
  }
  
  if (req.query.priority) {
    filteredTasks = filteredTasks.filter(task => 
      task.priority.toLowerCase() === req.query.priority.toLowerCase());
  }
  
  if (req.query.search) {
    const searchLower = req.query.search.toLowerCase();
    filteredTasks = filteredTasks.filter(task => 
      task.title.toLowerCase().includes(searchLower) || 
      (task.description && task.description.toLowerCase().includes(searchLower)));
  }
  
  res.json({ tasks: filteredTasks });
});

// GET /api/kanban/task/:id - Get a specific task by ID
router.get('/:id', (req, res) => {
  const { id } = req.params;
  const tasks = getTasks();
  const task = tasks.tasks.find(t => t.id === id);
  
  if (!task) {
    return res.status(404).json({ error: 'Task not found' });
  }
  
  res.json({ task });
});

// POST /api/kanban/tasks - Create a new task
router.post('/', (req, res) => {
  const { title, description, status, priority, epic_id, tags } = req.body;
  
  if (!title) {
    return res.status(400).json({ error: 'Title is required' });
  }
  
  const newTask = {
    id: `TSK-${uuidv4().substring(0, 8)}`,
    title,
    description: description || '',
    status: status || 'Ready',
    priority: priority || 'Medium',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    epic_id: epic_id || null,
    tags: tags || []
  };
  
  const tasks = getTasks();
  tasks.tasks.push(newTask);
  
  if (saveTasks(tasks)) {
    res.status(201).json({ task: newTask });
  } else {
    res.status(500).json({ error: 'Failed to save task' });
  }
});

// PUT /api/kanban/task/:id - Update a task
router.put('/:id', (req, res) => {
  const { id } = req.params;
  const tasks = getTasks();
  const taskIndex = tasks.tasks.findIndex(t => t.id === id);
  
  if (taskIndex === -1) {
    return res.status(404).json({ error: 'Task not found' });
  }
  
  const updatedTask = {
    ...tasks.tasks[taskIndex],
    ...req.body,
    updated_at: new Date().toISOString()
  };
  
  tasks.tasks[taskIndex] = updatedTask;
  
  if (saveTasks(tasks)) {
    res.json({ task: updatedTask });
  } else {
    res.status(500).json({ error: 'Failed to update task' });
  }
});

// DELETE /api/kanban/task/:id - Delete a task
router.delete('/:id', (req, res) => {
  const { id } = req.params;
  const tasks = getTasks();
  const taskIndex = tasks.tasks.findIndex(t => t.id === id);
  
  if (taskIndex === -1) {
    return res.status(404).json({ error: 'Task not found' });
  }
  
  const deletedTask = tasks.tasks[taskIndex];
  tasks.tasks.splice(taskIndex, 1);
  
  if (saveTasks(tasks)) {
    res.json({ success: true, task: deletedTask });
  } else {
    res.status(500).json({ error: 'Failed to delete task' });
  }
});

// POST /api/kanban/task/:id/update - Special endpoint for n8n callbacks
router.post('/:id/update', (req, res) => {
  const { id } = req.params;
  const updateData = req.body;
  const tasks = getTasks();
  const taskIndex = tasks.tasks.findIndex(t => t.id === id);
  
  if (taskIndex === -1) {
    return res.status(404).json({ error: 'Task not found' });
  }
  
  // Apply updates
  const updatedTask = {
    ...tasks.tasks[taskIndex],
    ...updateData,
    updated_at: new Date().toISOString()
  };
  
  tasks.tasks[taskIndex] = updatedTask;
  
  if (saveTasks(tasks)) {
    // Here we would notify any active CLI sessions
    // This would be implemented in the Python wrapper
    
    res.json({ 
      success: true, 
      task: updatedTask,
      message: 'Task updated via webhook'
    });
  } else {
    res.status(500).json({ error: 'Failed to update task' });
  }
});

module.exports = router;