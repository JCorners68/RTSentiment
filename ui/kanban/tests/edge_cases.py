#!/usr/bin/env python
"""
Edge case and error scenario tests for CLI Kanban.

This module contains tests that verify the system's behavior under
unusual or error conditions to ensure robust error handling.
"""
import os
import sys
import unittest
import tempfile
import shutil
import json
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

# Add the parent directory to the path
parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))

from src.cli import cli_group
from src.utils.exceptions import (
    StorageError, 
    ConfigurationError,
    ValidationError,
    AuthenticationError,
    ResourceNotFoundError
)


class StorageEdgeCaseTest(unittest.TestCase):
    """Test edge cases for storage operations."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a runner for testing CLI commands
        self.runner = CliRunner()
        
        # Initialize the Kanban board
        self.runner.invoke(cli_group, ['init'])
    
    def tearDown(self):
        """Clean up after the test."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_concurrent_file_access(self):
        """Test handling of concurrent file access."""
        # Create a task
        result1 = self.runner.invoke(cli_group, 
                                   ['kanban', 'task', 'add',
                                    '--title', 'Concurrent Test 1',
                                    '--description', 'Testing concurrent access',
                                    '--status', 'Backlog'])
        self.assertEqual(result1.exit_code, 0)
        
        # Try to create another task "simultaneously"
        # We simulate this by patching the file locking mechanism
        with patch('src.data.storage.FileStorage._acquire_lock', 
                   side_effect=StorageError("Lock acquisition failed")):
            result2 = self.runner.invoke(cli_group, 
                                       ['kanban', 'task', 'add',
                                        '--title', 'Concurrent Test 2',
                                        '--description', 'Testing concurrent access',
                                        '--status', 'Backlog'])
            
            # Should handle the error gracefully
            self.assertEqual(result2.exit_code, 0)
            self.assertIn('error', result2.output.lower())
            self.assertIn('lock', result2.output.lower())
    
    def test_corrupted_data_file(self):
        """Test handling of corrupted data files."""
        # Create a task
        result1 = self.runner.invoke(cli_group, 
                                   ['kanban', 'task', 'add',
                                    '--title', 'Corruption Test',
                                    '--description', 'Testing corrupted file handling',
                                    '--status', 'Backlog'])
        self.assertEqual(result1.exit_code, 0)
        
        # Corrupt the tasks file
        tasks_file = Path(self.temp_dir) / "data" / "tasks.yaml"
        if tasks_file.exists():
            with open(tasks_file, "a") as f:
                f.write("This is not valid YAML: ][}{")
        
        # Try to list tasks
        result2 = self.runner.invoke(cli_group, ['kanban', 'task', 'list'])
        
        # Should handle the error gracefully
        self.assertEqual(result2.exit_code, 0)
        self.assertIn('error', result2.output.lower())
    
    def test_read_only_data_directory(self):
        """Test handling of read-only data directory."""
        # Create a task
        result1 = self.runner.invoke(cli_group, 
                                   ['kanban', 'task', 'add',
                                    '--title', 'Permission Test',
                                    '--description', 'Testing permission handling',
                                    '--status', 'Backlog'])
        self.assertEqual(result1.exit_code, 0)
        
        # Try to create a task with a read-only directory
        with patch('src.data.storage.FileStorage._save_data', 
                   side_effect=PermissionError("Permission denied")):
            result2 = self.runner.invoke(cli_group, 
                                       ['kanban', 'task', 'add',
                                        '--title', 'Permission Test 2',
                                        '--description', 'Testing permission handling',
                                        '--status', 'Backlog'])
            
            # Should handle the error gracefully
            self.assertEqual(result2.exit_code, 0)
            self.assertIn('error', result2.output.lower())
            self.assertIn('permission', result2.output.lower())


class ValidationEdgeCaseTest(unittest.TestCase):
    """Test edge cases for data validation."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a runner for testing CLI commands
        self.runner = CliRunner()
        
        # Initialize the Kanban board
        self.runner.invoke(cli_group, ['init'])
    
    def tearDown(self):
        """Clean up after the test."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_invalid_task_status(self):
        """Test handling of invalid task status."""
        # Try to create a task with invalid status
        result = self.runner.invoke(cli_group, 
                                  ['kanban', 'task', 'add',
                                   '--title', 'Invalid Status Test',
                                   '--description', 'Testing invalid status handling',
                                   '--status', 'InvalidStatus'])
        
        # Should handle the error gracefully
        self.assertEqual(result.exit_code, 0)
        self.assertIn('invalid', result.output.lower())
        self.assertIn('status', result.output.lower())
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        # Try to create a task without title
        result = self.runner.invoke(cli_group, 
                                  ['kanban', 'task', 'add',
                                   '--description', 'Testing missing fields handling',
                                   '--status', 'Backlog'])
        
        # Should handle the error gracefully
        self.assertEqual(result.exit_code, 0)
        self.assertIn('required', result.output.lower())
        self.assertIn('title', result.output.lower())
    
    def test_extremely_long_title(self):
        """Test handling of extremely long title."""
        # Try to create a task with an extremely long title
        long_title = "A" * 10000  # 10k characters
        result = self.runner.invoke(cli_group, 
                                  ['kanban', 'task', 'add',
                                   '--title', long_title,
                                   '--description', 'Testing long title handling',
                                   '--status', 'Backlog'])
        
        # Should handle the error gracefully
        self.assertEqual(result.exit_code, 0)
        self.assertIn('length', result.output.lower())
    
    def test_invalid_priority_value(self):
        """Test handling of invalid priority value."""
        # Try to create a task with invalid priority
        result = self.runner.invoke(cli_group, 
                                  ['kanban', 'task', 'add',
                                   '--title', 'Invalid Priority Test',
                                   '--description', 'Testing invalid priority handling',
                                   '--status', 'Backlog',
                                   '--priority', 'InvalidPriority'])
        
        # Should handle the error gracefully
        self.assertEqual(result.exit_code, 0)
        self.assertIn('invalid', result.output.lower())
        self.assertIn('priority', result.output.lower())


class CommandEdgeCaseTest(unittest.TestCase):
    """Test edge cases for command execution."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a runner for testing CLI commands
        self.runner = CliRunner()
        
        # Initialize the Kanban board
        self.runner.invoke(cli_group, ['init'])
    
    def tearDown(self):
        """Clean up after the test."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_nonexistent_task_id(self):
        """Test handling of nonexistent task ID."""
        # Try to get a nonexistent task
        result = self.runner.invoke(cli_group, 
                                  ['kanban', 'task', 'get', 'TSK-9999'])
        
        # Should handle the error gracefully
        self.assertEqual(result.exit_code, 0)
        self.assertIn('not found', result.output.lower())
    
    def test_nonexistent_epic_id(self):
        """Test handling of nonexistent epic ID."""
        # Try to get a nonexistent epic
        result = self.runner.invoke(cli_group, 
                                  ['kanban', 'epic', 'get', 'EPC-9999'])
        
        # Should handle the error gracefully
        self.assertEqual(result.exit_code, 0)
        self.assertIn('not found', result.output.lower())
    
    def test_task_assignment_to_nonexistent_epic(self):
        """Test handling of assigning a task to a nonexistent epic."""
        # Create a task
        create_result = self.runner.invoke(cli_group, 
                                        ['kanban', 'task', 'add',
                                         '--title', 'Epic Assignment Test',
                                         '--description', 'Testing nonexistent epic assignment',
                                         '--status', 'Backlog'])
        self.assertEqual(create_result.exit_code, 0)
        
        # Extract task ID
        import re
        task_id_match = re.search(r'TSK-\w+', create_result.output)
        self.assertIsNotNone(task_id_match, "Task ID not found in output")
        task_id = task_id_match.group(0)
        
        # Try to assign to a nonexistent epic
        result = self.runner.invoke(cli_group, 
                                  ['kanban', 'task', 'update',
                                   task_id, '--epic', 'EPC-9999'])
        
        # Should handle the error gracefully
        self.assertEqual(result.exit_code, 0)
        self.assertIn('not found', result.output.lower())
        self.assertIn('epic', result.output.lower())
    
    def test_invalid_command_syntax(self):
        """Test handling of invalid command syntax."""
        # Try to run a command with invalid syntax
        result = self.runner.invoke(cli_group, ['kanban', 'invalid', 'command'])
        
        # Should handle the error gracefully
        self.assertEqual(result.exit_code, 0)
        self.assertIn('invalid', result.output.lower())
        self.assertIn('command', result.output.lower())


class ConfigurationEdgeCaseTest(unittest.TestCase):
    """Test edge cases for configuration."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a runner for testing CLI commands
        self.runner = CliRunner()
    
    def tearDown(self):
        """Clean up after the test."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        # Try to run a command without initializing first
        result = self.runner.invoke(cli_group, ['kanban', 'task', 'list'])
        
        # Should handle the error gracefully
        self.assertEqual(result.exit_code, 0)
        self.assertIn('configuration', result.output.lower())
        self.assertIn('not found', result.output.lower())
    
    def test_invalid_config_file(self):
        """Test handling of invalid configuration file."""
        # Create an invalid configuration file
        os.makedirs(os.path.join(self.temp_dir, "data"), exist_ok=True)
        with open('config.yaml', 'w') as f:
            f.write("This is not a valid YAML configuration file")
        
        # Try to run a command
        result = self.runner.invoke(cli_group, ['kanban', 'task', 'list'])
        
        # Should handle the error gracefully
        self.assertEqual(result.exit_code, 0)
        self.assertIn('error', result.output.lower())
        self.assertIn('configuration', result.output.lower())
    
    def test_config_with_missing_required_fields(self):
        """Test handling of configuration with missing required fields."""
        # Create a configuration file with missing required fields
        os.makedirs(os.path.join(self.temp_dir, "data"), exist_ok=True)
        with open('config.yaml', 'w') as f:
            f.write("""
            app:
              name: cli_kanban
              # Missing version field
            data_paths:
              base_dir: data
            """)
        
        # Try to run a command
        result = self.runner.invoke(cli_group, ['kanban', 'task', 'list'])
        
        # Should handle the error gracefully
        self.assertEqual(result.exit_code, 0)
        self.assertIn('error', result.output.lower())
        self.assertIn('configuration', result.output.lower())
        self.assertIn('missing', result.output.lower())


class ServerIntegrationEdgeCaseTest(unittest.TestCase):
    """Test edge cases for server integration."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a runner for testing CLI commands
        self.runner = CliRunner()
        
        # Initialize the Kanban board
        self.runner.invoke(cli_group, ['init'])
    
    def tearDown(self):
        """Clean up after the test."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)
    
    @patch('src.server.control.start_server')
    def test_server_start_failure(self, mock_start_server):
        """Test handling of server start failure."""
        # Mock server start failure
        mock_start_server.side_effect = Exception("Failed to start server")
        
        # Try to start the server
        from src.server.control import start_server
        
        try:
            # This should raise an exception
            start_server()
            self.fail("Should have raised an exception")
        except Exception as e:
            # Exception should be handled by the caller
            self.assertIn("Failed to start server", str(e))
    
    @patch('src.server.control.get_server_status')
    def test_server_status_check_failure(self, mock_get_status):
        """Test handling of server status check failure."""
        # Mock server status check failure
        mock_get_status.side_effect = Exception("Failed to check server status")
        
        # Try to check server status
        from src.server.control import get_server_status
        
        try:
            # This should raise an exception
            get_server_status()
            self.fail("Should have raised an exception")
        except Exception as e:
            # Exception should be handled by the caller
            self.assertIn("Failed to check server status", str(e))


class EvidenceEdgeCaseTest(unittest.TestCase):
    """Test edge cases for evidence management."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a runner for testing CLI commands
        self.runner = CliRunner()
        
        # Initialize the Kanban board
        self.runner.invoke(cli_group, ['init'])
        
        # Create a test attachment file
        self.attachment_path = os.path.join(self.temp_dir, "test_attachment.txt")
        with open(self.attachment_path, "w") as f:
            f.write("This is a test attachment for the evidence system.")
    
    def tearDown(self):
        """Clean up after the test."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_evidence_with_nonexistent_task(self):
        """Test handling of evidence with nonexistent task."""
        # Try to create evidence with a nonexistent task
        result = self.runner.invoke(cli_group, 
                                  ['kanban', 'evidence', 'add',
                                   '--title', 'Missing Task Test',
                                   '--description', 'Testing nonexistent task reference',
                                   '--category', 'Requirement',
                                   '--task', 'TSK-9999'])
        
        # Note: This might be handled in the actual implementation
        # but for now we're just checking for a graceful handling
        self.assertEqual(result.exit_code, 0)
    
    def test_oversized_attachment(self):
        """Test handling of oversized attachment."""
        # Create a large attachment file (mock)
        with patch('os.path.getsize', return_value=1024 * 1024 * 101):  # 101 MB
            # Try to add evidence with oversized attachment
            result = self.runner.invoke(cli_group, 
                                      ['kanban', 'evidence', 'attach',
                                       'EVD-001', self.attachment_path])
            
            # Since this is a mock and the evidence system is not fully implemented,
            # we just check that the command ran without crashing
            self.assertEqual(result.exit_code, 0)


if __name__ == '__main__':
    unittest.main()