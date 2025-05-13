"""
Unit tests for data storage functionality.

This module tests the storage classes for all data models, with particular
focus on the Evidence Management System storage which is a priority feature.
"""
import sys
import os
import unittest
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import the src module
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

from src.data.storage import FileStorage, TaskStorage, EpicStorage, BoardStorage, StorageError
# Import evidence storage when implemented
# from src.data.evidence_storage import EvidenceStorage


class TestFileStorage(unittest.TestCase):
    """Test case for base file storage functionality."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'paths': {
                'data': self.temp_dir
            }
        }
        self.storage = FileStorage(config=self.config)
    
    def tearDown(self):
        """Clean up after the test."""
        shutil.rmtree(self.temp_dir)
    
    def test_ensure_dir(self):
        """Test directory creation."""
        test_dir = Path(self.temp_dir) / "test_dir"
        self.storage._ensure_dir(test_dir)
        self.assertTrue(test_dir.exists())
        self.assertTrue(test_dir.is_dir())
    
    def test_write_read_yaml(self):
        """Test writing and reading YAML files."""
        test_data = {"key": "value", "list": [1, 2, 3]}
        test_file = Path(self.temp_dir) / "test_file.yaml"
        
        # Write data
        self.storage._write_yaml(test_file, test_data)
        self.assertTrue(test_file.exists())
        
        # Read data back
        read_data = self.storage._read_yaml(test_file)
        self.assertEqual(read_data, test_data)
    
    def test_write_read_json(self):
        """Test writing and reading JSON files."""
        test_data = {"key": "value", "list": [1, 2, 3]}
        test_file = Path(self.temp_dir) / "test_file.json"
        
        # Write data
        self.storage._write_json(test_file, test_data)
        self.assertTrue(test_file.exists())
        
        # Read data back
        read_data = self.storage._read_json(test_file)
        self.assertEqual(read_data, test_data)
    
    def test_read_nonexistent_file(self):
        """Test reading a non-existent file returns None."""
        nonexistent_file = Path(self.temp_dir) / "does_not_exist.json"
        data = self.storage._read_json(nonexistent_file)
        self.assertIsNone(data)


class TestTaskStorage(unittest.TestCase):
    """Test case for task storage functionality."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'paths': {
                'data': self.temp_dir
            }
        }
        self.storage = TaskStorage(config=self.config)
    
    def tearDown(self):
        """Clean up after the test."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_task(self):
        """Test creating a task."""
        task_data = {
            "title": "Test Task",
            "description": "This is a test task",
            "status": "Backlog",
            "priority": "Medium"
        }
        
        task = self.storage.create(task_data)
        
        # Verify task was created
        self.assertIsNotNone(task)
        self.assertIsNotNone(task.id)
        self.assertEqual(task.title, "Test Task")
        self.assertEqual(task.status.value, "Backlog")
        
        # Verify task file was created
        task_file = Path(self.temp_dir) / "tasks" / f"{task.id}.json"
        self.assertTrue(task_file.exists())
        
        # Verify task ID was added to index
        index_file = Path(self.temp_dir) / "tasks" / "index.json"
        self.assertTrue(index_file.exists())
        with open(index_file, 'r') as f:
            import json
            index_data = json.load(f)
            self.assertIn(task.id, index_data.get('tasks', []))
    
    def test_get_task(self):
        """Test retrieving a task by ID."""
        # Create a task first
        task_data = {
            "title": "Task to Retrieve",
            "status": "Ready"
        }
        created_task = self.storage.create(task_data)
        
        # Now retrieve it
        retrieved_task = self.storage.get(created_task.id)
        
        # Verify task was retrieved correctly
        self.assertIsNotNone(retrieved_task)
        self.assertEqual(retrieved_task.id, created_task.id)
        self.assertEqual(retrieved_task.title, "Task to Retrieve")
        self.assertEqual(retrieved_task.status.value, "Ready")
    
    def test_update_task(self):
        """Test updating a task."""
        # Create a task first
        task_data = {
            "title": "Original Title",
            "status": "Backlog",
            "priority": "Low"
        }
        created_task = self.storage.create(task_data)
        
        # Update the task
        update_data = {
            "title": "Updated Title",
            "status": "In Progress",
            "priority": "High"
        }
        updated_task = self.storage.update(created_task.id, update_data)
        
        # Verify task was updated
        self.assertIsNotNone(updated_task)
        self.assertEqual(updated_task.id, created_task.id)
        self.assertEqual(updated_task.title, "Updated Title")
        self.assertEqual(updated_task.status.value, "In Progress")
        self.assertEqual(updated_task.priority.value, "High")
        
        # Retrieve again to confirm persistence
        retrieved_task = self.storage.get(created_task.id)
        self.assertEqual(retrieved_task.title, "Updated Title")
    
    def test_delete_task(self):
        """Test deleting a task."""
        # Create a task first
        task_data = {
            "title": "Task to Delete",
            "status": "Backlog"
        }
        created_task = self.storage.create(task_data)
        
        # Delete the task
        success = self.storage.delete(created_task.id)
        
        # Verify deletion was successful
        self.assertTrue(success)
        
        # Verify task no longer exists
        task_file = Path(self.temp_dir) / "tasks" / f"{created_task.id}.json"
        self.assertFalse(task_file.exists())
        
        # Verify task ID was removed from index
        index_file = Path(self.temp_dir) / "tasks" / "index.json"
        with open(index_file, 'r') as f:
            import json
            index_data = json.load(f)
            self.assertNotIn(created_task.id, index_data.get('tasks', []))
    
    def test_list_tasks(self):
        """Test listing all tasks."""
        # Create multiple tasks
        task_data_1 = {"title": "Task 1", "status": "Backlog", "priority": "Low"}
        task_data_2 = {"title": "Task 2", "status": "Ready", "priority": "Medium"}
        task_data_3 = {"title": "Task 3", "status": "In Progress", "priority": "High"}
        
        task1 = self.storage.create(task_data_1)
        task2 = self.storage.create(task_data_2)
        task3 = self.storage.create(task_data_3)
        
        # List all tasks
        all_tasks = self.storage.list()
        
        # Verify all tasks are listed
        self.assertEqual(len(all_tasks), 3)
        task_ids = [task.id for task in all_tasks]
        self.assertIn(task1.id, task_ids)
        self.assertIn(task2.id, task_ids)
        self.assertIn(task3.id, task_ids)
    
    def test_list_tasks_with_filters(self):
        """Test listing tasks with filters."""
        # Create multiple tasks with different attributes
        task_data_1 = {"title": "Low Priority Task", "status": "Backlog", "priority": "Low"}
        task_data_2 = {"title": "Medium Task", "status": "Ready", "priority": "Medium"}
        task_data_3 = {"title": "High Priority", "status": "In Progress", "priority": "High"}
        
        task1 = self.storage.create(task_data_1)
        task2 = self.storage.create(task_data_2)
        task3 = self.storage.create(task_data_3)
        
        # Test filtering by status
        status_tasks = self.storage.list({"status": "Ready"})
        self.assertEqual(len(status_tasks), 1)
        self.assertEqual(status_tasks[0].id, task2.id)
        
        # Test filtering by title substring
        title_tasks = self.storage.list({"title": "Priority"})
        self.assertEqual(len(title_tasks), 2)  # Should match tasks 1 and 3
        title_ids = [task.id for task in title_tasks]
        self.assertIn(task1.id, title_ids)
        self.assertIn(task3.id, title_ids)
        
        # Test filtering by priority
        priority_tasks = self.storage.list({"priority": "High"})
        self.assertEqual(len(priority_tasks), 1)
        self.assertEqual(priority_tasks[0].id, task3.id)


class TestEpicStorage(unittest.TestCase):
    """Test case for epic storage functionality."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'paths': {
                'data': self.temp_dir
            }
        }
        self.storage = EpicStorage(config=self.config)
    
    def tearDown(self):
        """Clean up after the test."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_epic(self):
        """Test creating an epic."""
        epic_data = {
            "title": "Test Epic",
            "description": "This is a test epic",
            "status": "Open",
            "owner": "John Doe"
        }
        
        epic = self.storage.create(epic_data)
        
        # Verify epic was created
        self.assertIsNotNone(epic)
        self.assertIsNotNone(epic.id)
        self.assertEqual(epic.title, "Test Epic")
        self.assertEqual(epic.status, "Open")
        
        # Verify epic file was created
        epic_file = Path(self.temp_dir) / "epics" / f"{epic.id}.json"
        self.assertTrue(epic_file.exists())
        
        # Verify epic ID was added to index
        index_file = Path(self.temp_dir) / "epics" / "index.json"
        self.assertTrue(index_file.exists())
        with open(index_file, 'r') as f:
            import json
            index_data = json.load(f)
            self.assertIn(epic.id, index_data.get('epics', []))
    
    def test_update_epic(self):
        """Test updating an epic."""
        # Create an epic first
        epic_data = {
            "title": "Original Epic",
            "status": "Open"
        }
        created_epic = self.storage.create(epic_data)
        
        # Update the epic
        update_data = {
            "title": "Updated Epic",
            "status": "In Progress",
            "owner": "Jane Smith"
        }
        updated_epic = self.storage.update(created_epic.id, update_data)
        
        # Verify epic was updated
        self.assertIsNotNone(updated_epic)
        self.assertEqual(updated_epic.id, created_epic.id)
        self.assertEqual(updated_epic.title, "Updated Epic")
        self.assertEqual(updated_epic.status, "In Progress")
        self.assertEqual(updated_epic.owner, "Jane Smith")


class TestBoardStorage(unittest.TestCase):
    """Test case for board storage functionality."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'paths': {
                'data': self.temp_dir
            }
        }
        self.storage = BoardStorage(config=self.config)
    
    def tearDown(self):
        """Clean up after the test."""
        shutil.rmtree(self.temp_dir)
    
    def test_create_board(self):
        """Test creating a board."""
        board_data = {
            "name": "Test Board",
            "columns": ["Backlog", "Ready", "In Progress", "Review", "Done"]
        }
        
        board = self.storage.create(board_data)
        
        # Verify board was created
        self.assertIsNotNone(board)
        self.assertIsNotNone(board.id)
        self.assertEqual(board.name, "Test Board")
        self.assertEqual(len(board.columns), 5)
        
        # Verify board file was created
        board_file = Path(self.temp_dir) / "boards" / f"{board.id}.json"
        self.assertTrue(board_file.exists())


# Tests for evidence storage will be added when the feature is implemented

if __name__ == "__main__":
    unittest.main()
