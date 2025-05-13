"""
Unit tests for CLI commands functionality.

This module tests the CLI command functionality for all modules, with particular
focus on the Evidence Management System commands which are a priority feature.
"""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
from click.testing import CliRunner

# Add the parent directory to the path so we can import the src module
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

from src.cli import cli_group
from src.cli import tasks, board, epics, evidence


class TaskCommandsTest(unittest.TestCase):
    """Test case for task management commands."""
    
    def setUp(self):
        """Set up the test case."""
        self.runner = CliRunner()
    
    @patch('src.cli.tasks.TaskStorage')
    def test_task_list(self, mock_storage):
        """Test the task list command."""
        # Mock the storage.list method to return some tasks
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.list.return_value = [
            MagicMock(to_dict=lambda: {"id": "TSK-1", "title": "Task 1", "status": "Backlog"}),
            MagicMock(to_dict=lambda: {"id": "TSK-2", "title": "Task 2", "status": "In Progress"})
        ]
        
        # Run the command
        result = self.runner.invoke(tasks.task_group, ['list'])
        
        # Verify the command executed successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify storage.list was called
        mock_storage_instance.list.assert_called_once()
        
        # Check the output includes task information
        self.assertIn("TSK-1", result.output)
        self.assertIn("Task 1", result.output)
        self.assertIn("TSK-2", result.output)
        self.assertIn("Task 2", result.output)
    
    @patch('src.cli.tasks.TaskStorage')
    def test_task_get(self, mock_storage):
        """Test the task get command."""
        # Mock the storage.get method to return a task
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_task = MagicMock()
        mock_task.id = "TSK-1"
        mock_task.title = "Test Task"
        mock_task.description = "Task description"
        mock_task.status.value = "In Progress"
        mock_task.priority.value = "High"
        mock_task.created_at.isoformat.return_value = "2025-05-10T00:00:00"
        mock_task.updated_at.isoformat.return_value = "2025-05-11T00:00:00"
        mock_task.tags = ["test", "important"]
        mock_task.related_evidence_ids = ["EVD-1"]
        mock_storage_instance.get.return_value = mock_task
        
        # Run the command
        result = self.runner.invoke(tasks.task_group, ['get', 'TSK-1'])
        
        # Verify the command executed successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify storage.get was called with the correct ID
        mock_storage_instance.get.assert_called_once_with("TSK-1")
        
        # Check the output includes task information
        self.assertIn("Test Task", result.output)
        self.assertIn("In Progress", result.output)
        self.assertIn("High", result.output)
        self.assertIn("test", result.output)  # Tag
        self.assertIn("EVD-1", result.output)  # Related evidence
    
    @patch('src.cli.tasks.TaskStorage')
    def test_task_add(self, mock_storage):
        """Test the task add command."""
        # Mock the storage.create method
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_task = MagicMock()
        mock_task.id = "TSK-1"
        mock_task.title = "New Task"
        mock_storage_instance.create.return_value = mock_task
        
        # Run the command with input data
        result = self.runner.invoke(tasks.task_group, 
                                  ['add', '--title', 'New Task', 
                                   '--status', 'Backlog', 
                                   '--priority', 'Medium'])
        
        # Verify the command executed successfully
        self.assertEqual(result.exit_code, 0)
        
        # Check that storage.create was called with appropriate data
        mock_storage_instance.create.assert_called_once()
        
        # Check the output includes task creation confirmation
        self.assertIn("New Task", result.output)
    
    @patch('src.cli.tasks.TaskStorage')
    def test_task_delete(self, mock_storage):
        """Test the task delete command."""
        # Mock the storage methods
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_task = MagicMock()
        mock_task.id = "TSK-1"
        mock_task.title = "Task to Delete"
        mock_storage_instance.get.return_value = mock_task
        mock_storage_instance.delete.return_value = True
        
        # Run the command with --force to skip confirmation
        result = self.runner.invoke(tasks.task_group, ['delete', 'TSK-1', '--force'])
        
        # Verify the command executed successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify storage.delete was called with the correct ID
        mock_storage_instance.delete.assert_called_once_with("TSK-1")
        
        # Check the output includes deletion confirmation
        self.assertIn("deleted", result.output.lower())


class BoardCommandsTest(unittest.TestCase):
    """Test case for board management commands."""
    
    def setUp(self):
        """Set up the test case."""
        self.runner = CliRunner()
    
    @patch('src.cli.board.BoardStorage')
    @patch('src.cli.board.TaskStorage')
    def test_board_show(self, mock_task_storage, mock_board_storage):
        """Test the board show command."""
        # Mock the storage
        mock_board_instance = MagicMock()
        mock_board_storage.return_value = mock_board_instance
        mock_board = MagicMock()
        mock_board.name = "Test Board"
        mock_board.columns = ["Backlog", "In Progress", "Done"]
        mock_board.updated_at.isoformat.return_value = "2025-05-12T00:00:00"
        mock_board_instance.list.return_value = [mock_board]
        
        mock_task_instance = MagicMock()
        mock_task_storage.return_value = mock_task_instance
        mock_task_instance.list.return_value = [
            MagicMock(status=MagicMock(value="Backlog"), 
                     to_dict=lambda: {"id": "TSK-1", "title": "Task 1", "status": "Backlog"}),
            MagicMock(status=MagicMock(value="In Progress"), 
                     to_dict=lambda: {"id": "TSK-2", "title": "Task 2", "status": "In Progress"})
        ]
        
        # Run the command
        result = self.runner.invoke(board.board_group, ['show'])
        
        # Verify the command executed successfully
        self.assertEqual(result.exit_code, 0)
        
        # Check the output includes board and task information
        self.assertIn("Test Board", result.output)
        self.assertIn("Backlog", result.output)
        self.assertIn("In Progress", result.output)
        self.assertIn("Done", result.output)
        self.assertIn("Task 1", result.output)
        self.assertIn("Task 2", result.output)
    
    @patch('src.cli.board.BoardStorage')
    def test_board_create(self, mock_storage):
        """Test the board create command."""
        # Mock the storage.create method
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        mock_board = MagicMock()
        mock_board.name = "New Board"
        mock_board.columns = ["Todo", "Doing", "Done"]
        mock_storage_instance.create.return_value = mock_board
        
        # Run the command
        result = self.runner.invoke(board.board_group, 
                                  ['create', '--name', 'New Board', 
                                   '--columns', 'Todo,Doing,Done'])
        
        # Verify the command executed successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify storage.create was called with appropriate data
        mock_storage_instance.create.assert_called_once()
        
        # Check the output includes board creation confirmation
        self.assertIn("New Board", result.output)
        self.assertIn("Todo", result.output)
        self.assertIn("Doing", result.output)
        self.assertIn("Done", result.output)
    
    @patch('src.cli.board.BoardStorage')
    @patch('src.cli.board.TaskStorage')
    def test_board_move(self, mock_task_storage, mock_board_storage):
        """Test the board move command."""
        # Mock the storages
        mock_board_instance = MagicMock()
        mock_board_storage.return_value = mock_board_instance
        mock_board = MagicMock()
        mock_board.name = "Test Board"
        mock_board.columns = ["Backlog", "In Progress", "Done"]
        mock_board_instance.list.return_value = [mock_board]
        
        mock_task_instance = MagicMock()
        mock_task_storage.return_value = mock_task_instance
        mock_task = MagicMock()
        mock_task.id = "TSK-1"
        mock_task.title = "Task to Move"
        mock_task.status = MagicMock(value="Backlog")
        mock_task_instance.get.return_value = mock_task
        
        mock_updated_task = MagicMock()
        mock_updated_task.id = "TSK-1"
        mock_updated_task.title = "Task to Move"
        mock_updated_task.status = MagicMock(value="In Progress")
        mock_updated_task.priority = MagicMock(value="Medium")
        mock_task_instance.update.return_value = mock_updated_task
        
        # Run the command
        result = self.runner.invoke(board.board_group, 
                                  ['move', 'TSK-1', 'In Progress'])
        
        # Verify the command executed successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify update was called with correct parameters
        mock_task_instance.update.assert_called_once_with("TSK-1", {"status": "In Progress"})
        
        # Check the output includes task move confirmation
        self.assertIn("Moved task TSK-1", result.output)
        self.assertIn("Backlog", result.output)  # Original status
        self.assertIn("In Progress", result.output)  # New status


class EpicCommandsTest(unittest.TestCase):
    """Test case for epic management commands."""
    
    def setUp(self):
        """Set up the test case."""
        self.runner = CliRunner()
    
    @patch('src.cli.epics.EpicStorage')
    def test_epic_list(self, mock_storage):
        """Test the epic list command."""
        # Mock the storage.list method to return some epics
        mock_storage_instance = MagicMock()
        mock_storage.return_value = mock_storage_instance
        
        # Create mock epics with the required properties
        mock_epic1 = MagicMock()
        mock_epic1.id = "EPC-1"
        mock_epic1.title = "Epic 1"
        mock_epic1.status = "Open"
        mock_epic1.created_at.isoformat.return_value = "2025-05-10T00:00:00"
        mock_epic1.related_evidence_ids = []
        
        mock_epic2 = MagicMock()
        mock_epic2.id = "EPC-2"
        mock_epic2.title = "Epic 2"
        mock_epic2.status = "In Progress"
        mock_epic2.created_at.isoformat.return_value = "2025-05-11T00:00:00"
        mock_epic2.related_evidence_ids = ["EVD-1", "EVD-2"]
        
        mock_storage_instance.list.return_value = [mock_epic1, mock_epic2]
        
        # Run the command
        result = self.runner.invoke(epics.epic_group, ['list'])
        
        # Verify the command executed successfully
        self.assertEqual(result.exit_code, 0)
        
        # Verify storage.list was called
        mock_storage_instance.list.assert_called_once()
        
        # Check the output includes epic information
        self.assertIn("EPC-1", result.output)
        self.assertIn("Epic 1", result.output)
        self.assertIn("EPC-2", result.output)
        self.assertIn("Epic 2", result.output)
        self.assertIn("Evidence Items: 2", result.output)  # Related evidence count for mock_epic2


class EvidenceCommandsTest(unittest.TestCase):
    """Test case for evidence management commands (priority feature)."""
    
    def setUp(self):
        """Set up the test case."""
        self.runner = CliRunner()
    
    def test_evidence_list(self):
        """Test the evidence list command."""
        # This is a placeholder test until EvidenceStorage is implemented
        result = self.runner.invoke(evidence.evidence_group, ['list'])
        
        # Verify the command executed successfully
        self.assertEqual(result.exit_code, 0)
        
        # Check the output includes the placeholder notice
        self.assertIn("placeholder", result.output.lower())
        self.assertIn("phase 2", result.output.lower())
    
    def test_evidence_get(self):
        """Test the evidence get command."""
        # This is a placeholder test until EvidenceStorage is implemented
        result = self.runner.invoke(evidence.evidence_group, ['get', 'EVD-001'])
        
        # Verify the command executed successfully
        self.assertEqual(result.exit_code, 0)
        
        # Check the output includes the placeholder notice and sample data
        self.assertIn("placeholder", result.output.lower())
        self.assertIn("phase 2", result.output.lower())
        self.assertIn("EVD-001", result.output)
        self.assertIn("Initial Requirements Document", result.output)
    
    def test_evidence_add(self):
        """Test the evidence add command."""
        # This is a placeholder test until EvidenceStorage is implemented
        result = self.runner.invoke(evidence.evidence_group, 
                                  ['add', '--title', 'Test Evidence', 
                                   '--description', 'Test description',
                                   '--category', 'Requirement',
                                   '--source', 'Test Source'])
        
        # Verify the command executed successfully
        self.assertEqual(result.exit_code, 0)
        
        # Check the output includes the placeholder notice and supplied data
        self.assertIn("placeholder", result.output.lower())
        self.assertIn("phase 2", result.output.lower())
        self.assertIn("Test Evidence", result.output)
        self.assertIn("Requirement", result.output)
    
    def test_evidence_search(self):
        """Test the evidence search command."""
        # This is a placeholder test until EvidenceStorage is implemented
        result = self.runner.invoke(evidence.evidence_group, 
                                  ['search', '--category', 'Requirement',
                                   '--text', 'important'])
        
        # Verify the command executed successfully
        self.assertEqual(result.exit_code, 0)
        
        # Check the output includes the placeholder notice and search criteria
        self.assertIn("placeholder", result.output.lower())
        self.assertIn("phase 2", result.output.lower())
        self.assertIn("Evidence Search", result.output)
        self.assertIn("Category: Requirement", result.output)


if __name__ == "__main__":
    unittest.main()
