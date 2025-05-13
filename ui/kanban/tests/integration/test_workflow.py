"""
Integration tests for complete workflow scenarios.

This module tests the interaction between different components of the system
with a particular focus on the Evidence Management System workflows, which
are a priority feature.
"""
import sys
import os
import unittest
import tempfile
import shutil
from pathlib import Path
from click.testing import CliRunner

# Add the parent directory to the path so we can import the src module
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

from src.cli import cli_group


class EpicWorkflowTest(unittest.TestCase):
    """Test case for epic management workflow."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        # Copy necessary config files to temporary directory
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a runner for testing CLI commands
        self.runner = CliRunner()
    
    def tearDown(self):
        """Clean up after the test."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_create_epic_with_tasks(self):
        """Test creating an epic and associated tasks."""
        # Create an epic
        epic_result = self.runner.invoke(cli_group, 
                                      ['kanban', 'epic', 'create', 
                                       '--title', 'Test Epic',
                                       '--description', 'Integration test epic',
                                       '--status', 'Open'])
        
        # Check if epic creation was successful
        self.assertEqual(epic_result.exit_code, 0)
        
        # Extract epic ID from output (assumes ID is shown in output)
        import re
        epic_id_match = re.search(r'EPC-\w+', epic_result.output)
        self.assertIsNotNone(epic_id_match, "Epic ID not found in output")
        epic_id = epic_id_match.group(0)
        
        # Add a task to the epic
        task_result = self.runner.invoke(cli_group, 
                                      ['kanban', 'task', 'add',
                                       '--title', 'Epic Task',
                                       '--description', 'Task for integration test epic',
                                       '--status', 'Backlog',
                                       '--epic', epic_id])
        
        # Check if task creation was successful
        self.assertEqual(task_result.exit_code, 0)
        
        # View epic to verify task association
        view_result = self.runner.invoke(cli_group, 
                                      ['kanban', 'epic', 'get', epic_id, '--with-tasks'])
        
        # Check if the task appears in the epic details
        self.assertEqual(view_result.exit_code, 0)
        self.assertIn('Epic Task', view_result.output)


class TaskManagementWorkflowTest(unittest.TestCase):
    """Test case for task management workflow."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        # Copy necessary config files to temporary directory
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a runner for testing CLI commands
        self.runner = CliRunner()
    
    def tearDown(self):
        """Clean up after the test."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_task_lifecycle(self):
        """Test the complete lifecycle of a task."""
        # Create a task
        create_result = self.runner.invoke(cli_group, 
                                        ['kanban', 'task', 'add',
                                         '--title', 'Lifecycle Test',
                                         '--description', 'Testing task lifecycle',
                                         '--status', 'Backlog',
                                         '--priority', 'Medium'])
        
        # Check if task creation was successful
        self.assertEqual(create_result.exit_code, 0)
        
        # Extract task ID from output
        import re
        task_id_match = re.search(r'TSK-\w+', create_result.output)
        self.assertIsNotNone(task_id_match, "Task ID not found in output")
        task_id = task_id_match.group(0)
        
        # Update the task to move it to "In Progress"
        update_result = self.runner.invoke(cli_group, 
                                        ['kanban', 'board', 'move', 
                                         task_id, 'In Progress'])
        
        # Check if task update was successful
        self.assertEqual(update_result.exit_code, 0)
        
        # Verify task status has changed
        get_result = self.runner.invoke(cli_group, 
                                     ['kanban', 'task', 'get', task_id])
        self.assertEqual(get_result.exit_code, 0)
        self.assertIn('In Progress', get_result.output)
        
        # Delete the task
        delete_result = self.runner.invoke(cli_group, 
                                        ['kanban', 'task', 'delete', 
                                         task_id, '--force'])
        
        # Check if task deletion was successful
        self.assertEqual(delete_result.exit_code, 0)
        
        # Verify task no longer exists
        get_after_delete = self.runner.invoke(cli_group, 
                                           ['kanban', 'task', 'get', task_id])
        self.assertEqual(get_after_delete.exit_code, 0)
        self.assertIn('not found', get_after_delete.output.lower())


class EvidenceWorkflowTest(unittest.TestCase):
    """Test case for evidence management workflow (priority feature)."""
    
    def setUp(self):
        """Set up the test case with a temporary directory."""
        self.temp_dir = tempfile.mkdtemp()
        # Copy necessary config files to temporary directory
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        
        # Create a test attachment file
        self.attachment_path = os.path.join(self.temp_dir, "test_attachment.txt")
        with open(self.attachment_path, "w") as f:
            f.write("This is a test attachment for the evidence system.")
        
        # Create a runner for testing CLI commands
        self.runner = CliRunner()
    
    def tearDown(self):
        """Clean up after the test."""
        os.chdir(self.old_cwd)
        shutil.rmtree(self.temp_dir)
    
    def test_evidence_with_task_relation(self):
        """Test creating evidence and relating it to a task."""
        # First create a task
        task_result = self.runner.invoke(cli_group, 
                                      ['kanban', 'task', 'add',
                                       '--title', 'Evidence Related Task',
                                       '--description', 'Task for evidence test',
                                       '--status', 'Backlog'])
        
        # Check if task creation was successful
        self.assertEqual(task_result.exit_code, 0)
        
        # Extract task ID from output
        import re
        task_id_match = re.search(r'TSK-\w+', task_result.output)
        self.assertIsNotNone(task_id_match, "Task ID not found in output")
        task_id = task_id_match.group(0)
        
        # Create evidence related to the task (using placeholder until Phase 2)
        evidence_result = self.runner.invoke(cli_group, 
                                          ['kanban', 'evidence', 'add',
                                           '--title', 'Test Evidence',
                                           '--description', 'Evidence for integration test',
                                           '--category', 'Requirement',
                                           '--task', task_id])
        
        # Check if evidence creation was handled
        self.assertEqual(evidence_result.exit_code, 0)
        
        # This is a placeholder test since the evidence system 
        # will be fully implemented in Phase 2
        self.assertIn('phase 2', evidence_result.output.lower())
        self.assertIn('Test Evidence', evidence_result.output)
        self.assertIn(task_id, evidence_result.output)
    
    def test_evidence_with_attachment(self):
        """Test creating evidence with an attachment."""
        # Create evidence with attachment (using placeholder until Phase 2)
        evidence_result = self.runner.invoke(cli_group, 
                                          ['kanban', 'evidence', 'add',
                                           '--title', 'Evidence with Attachment',
                                           '--description', 'Testing attachment feature',
                                           '--category', 'Design'])
        
        # Check if evidence creation was handled
        self.assertEqual(evidence_result.exit_code, 0)
        
        # This is a placeholder test since the evidence system 
        # will be fully implemented in Phase 2
        self.assertIn('phase 2', evidence_result.output.lower())
        
        # Extract evidence ID from output (would work when implemented)
        # For now, we'll use a placeholder ID
        evidence_id = "EVD-001"  # Placeholder
        
        # Add attachment to evidence (placeholder until Phase 2.3)
        attach_result = self.runner.invoke(cli_group, 
                                        ['kanban', 'evidence', 'attach',
                                         evidence_id, self.attachment_path,
                                         '--description', 'Test attachment'])
        
        # Check if attachment command was handled
        self.assertEqual(attach_result.exit_code, 0)
        self.assertIn('phase 2', attach_result.output.lower())
        self.assertIn('attachment', attach_result.output.lower())
    
    def test_evidence_categorization_and_tagging(self):
        """Test categorizing and tagging evidence."""
        # These are placeholder tests until Phase 2 is implemented
        
        # Categorize evidence
        categorize_result = self.runner.invoke(cli_group, 
                                            ['kanban', 'evidence', 'categorize',
                                             'EVD-001', 'Bug',
                                             '--subcategory', 'UI'])
        
        # Check if command was handled
        self.assertEqual(categorize_result.exit_code, 0)
        self.assertIn('phase 2', categorize_result.output.lower())
        
        # Tag evidence
        tag_result = self.runner.invoke(cli_group, 
                                     ['kanban', 'evidence', 'tag',
                                      'EVD-001', 'critical,bug,ui'])
        
        # Check if command was handled
        self.assertEqual(tag_result.exit_code, 0)
        self.assertIn('phase 2', tag_result.output.lower())
        self.assertIn('tags', tag_result.output.lower())
    
    def test_evidence_search(self):
        """Test searching for evidence."""
        # This is a placeholder test until Phase 2 is implemented
        
        # Search for evidence
        search_result = self.runner.invoke(cli_group, 
                                        ['kanban', 'evidence', 'search',
                                         '--category', 'Requirement',
                                         '--tag', 'important',
                                         '--text', 'user'])
        
        # Check if command was handled
        self.assertEqual(search_result.exit_code, 0)
        self.assertIn('phase 2', search_result.output.lower())
        self.assertIn('search', search_result.output.lower())
        self.assertIn('requirement', search_result.output.lower())


if __name__ == "__main__":
    unittest.main()
