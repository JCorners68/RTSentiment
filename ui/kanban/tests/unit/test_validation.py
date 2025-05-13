"""
Unit tests for data model validation functions.

This module tests the validation functions for all data models, with particular
focus on the Evidence Management System validation which is a priority feature.
"""
import sys
import os
import unittest
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import the src module
parent_dir = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(parent_dir))

from src.models import validation, evidence_validation
from src.models.schemas import TaskSchema, EpicSchema, BoardSchema
from src.models.evidence_schema import EvidenceSchema, AttachmentSchema, EvidenceCategory, EvidenceRelevance


class TaskValidationTest(unittest.TestCase):
    """Test case for task validation functions."""
    
    def test_valid_task(self):
        """Test validation of a valid task."""
        valid_task = {
            "title": "Test Task",
            "description": "This is a test task",
            "status": "Backlog",
            "priority": "Medium",
            "complexity": 3
        }
        is_valid, errors = validation.validate_task(valid_task)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_missing_title(self):
        """Test validation fails with missing title."""
        invalid_task = {
            "description": "This task has no title",
            "status": "Backlog"
        }
        is_valid, errors = validation.validate_task(invalid_task)
        self.assertFalse(is_valid)
        self.assertIn("title", errors[0].lower())
    
    def test_invalid_status(self):
        """Test validation fails with invalid status."""
        invalid_task = {
            "title": "Invalid Status Task",
            "status": "NotARealStatus"
        }
        is_valid, errors = validation.validate_task(invalid_task)
        self.assertFalse(is_valid)
        self.assertIn("status", errors[0].lower())
    
    def test_invalid_priority(self):
        """Test validation fails with invalid priority."""
        invalid_task = {
            "title": "Invalid Priority Task",
            "priority": "Super Important"
        }
        is_valid, errors = validation.validate_task(invalid_task)
        self.assertFalse(is_valid)
        self.assertIn("priority", errors[0].lower())
    
    def test_invalid_complexity(self):
        """Test validation fails with out-of-range complexity."""
        invalid_task = {
            "title": "Out of Range Complexity",
            "complexity": 6
        }
        is_valid, errors = validation.validate_task(invalid_task)
        self.assertFalse(is_valid)
        self.assertIn("complexity", errors[0].lower())


class EpicValidationTest(unittest.TestCase):
    """Test case for epic validation functions."""
    
    def test_valid_epic(self):
        """Test validation of a valid epic."""
        valid_epic = {
            "title": "Test Epic",
            "description": "This is a test epic",
            "status": "Open",
            "owner": "John Doe"
        }
        is_valid, errors = validation.validate_epic(valid_epic)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_missing_title(self):
        """Test validation fails with missing title."""
        invalid_epic = {
            "description": "This epic has no title",
            "status": "Open"
        }
        is_valid, errors = validation.validate_epic(invalid_epic)
        self.assertFalse(is_valid)
        self.assertIn("title", errors[0].lower())
    
    def test_invalid_dates(self):
        """Test validation of invalid date ranges."""
        invalid_epic = {
            "title": "Invalid Date Range",
            "start_date": "2025-06-01T00:00:00",
            "end_date": "2025-05-01T00:00:00"  # End before start
        }
        is_valid, errors = validation.validate_epic(invalid_epic)
        self.assertFalse(is_valid)
        self.assertIn("date", errors[0].lower())


class BoardValidationTest(unittest.TestCase):
    """Test case for board validation functions."""
    
    def test_valid_board(self):
        """Test validation of a valid board."""
        valid_board = {
            "name": "Test Board",
            "columns": ["Backlog", "Ready", "In Progress", "Review", "Done"]
        }
        is_valid, errors = validation.validate_board(valid_board)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_missing_name(self):
        """Test validation fails with missing name."""
        invalid_board = {
            "columns": ["Backlog", "In Progress", "Done"]
        }
        is_valid, errors = validation.validate_board(invalid_board)
        self.assertFalse(is_valid)
        self.assertIn("name", errors[0].lower())
    
    def test_too_few_columns(self):
        """Test validation fails with too few columns."""
        invalid_board = {
            "name": "One Column Board",
            "columns": ["Todo"]
        }
        is_valid, errors = validation.validate_board(invalid_board)
        self.assertFalse(is_valid)
        self.assertIn("column", errors[0].lower())
    
    def test_duplicate_columns(self):
        """Test validation fails with duplicate columns."""
        invalid_board = {
            "name": "Duplicate Columns",
            "columns": ["Backlog", "In Progress", "Done", "In Progress"]
        }
        is_valid, errors = validation.validate_board(invalid_board)
        self.assertFalse(is_valid)
        self.assertIn("duplicate", errors[0].lower())


class EvidenceValidationTest(unittest.TestCase):
    """Test case for evidence validation functions (priority feature)."""
    
    def test_valid_evidence(self):
        """Test validation of a valid evidence item."""
        valid_evidence = {
            "title": "Test Evidence",
            "description": "This is a test evidence item",
            "category": "Requirement",
            "subcategory": "Functional",
            "relevance_score": "High",
            "tags": ["test", "requirement", "functional"],
            "source": "Test Source"
        }
        is_valid, errors = evidence_validation.validate_evidence(valid_evidence)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_missing_title(self):
        """Test validation fails with missing title."""
        invalid_evidence = {
            "description": "This evidence has no title",
            "category": "Requirement"
        }
        is_valid, errors = evidence_validation.validate_evidence(invalid_evidence)
        self.assertFalse(is_valid)
        self.assertIn("title", errors[0].lower())
    
    def test_missing_description(self):
        """Test validation fails with missing description."""
        invalid_evidence = {
            "title": "No Description Evidence",
            "category": "Requirement"
        }
        is_valid, errors = evidence_validation.validate_evidence(invalid_evidence)
        self.assertFalse(is_valid)
        self.assertIn("description", errors[0].lower())
    
    def test_invalid_category(self):
        """Test validation fails with invalid category."""
        invalid_evidence = {
            "title": "Invalid Category",
            "description": "Evidence with invalid category",
            "category": "NotARealCategory"
        }
        is_valid, errors = evidence_validation.validate_evidence(invalid_evidence)
        self.assertFalse(is_valid)
        self.assertIn("category", errors[0].lower())
    
    def test_invalid_relevance(self):
        """Test validation fails with invalid relevance score."""
        invalid_evidence = {
            "title": "Invalid Relevance",
            "description": "Evidence with invalid relevance",
            "relevance_score": "Super Relevant"
        }
        is_valid, errors = evidence_validation.validate_evidence(invalid_evidence)
        self.assertFalse(is_valid)
        self.assertIn("relevance", errors[0].lower())
    
    def test_invalid_date_format(self):
        """Test validation fails with invalid date format."""
        invalid_evidence = {
            "title": "Invalid Date Format",
            "description": "Evidence with invalid date",
            "date_collected": "not-a-date"
        }
        is_valid, errors = evidence_validation.validate_evidence(invalid_evidence)
        self.assertFalse(is_valid)
        self.assertIn("date", errors[0].lower())
    

class AttachmentValidationTest(unittest.TestCase):
    """Test case for attachment validation functions (priority feature)."""
    
    def test_valid_attachment(self):
        """Test validation of a valid attachment."""
        valid_attachment = {
            "file_path": "attachments/document.pdf",
            "file_name": "document.pdf",
            "file_type": "application/pdf",
            "file_size": 1024,
            "description": "Test document"
        }
        errors = evidence_validation.validate_attachment(valid_attachment)
        self.assertEqual(len(errors), 0)
    
    def test_missing_file_path(self):
        """Test validation fails with missing file path."""
        invalid_attachment = {
            "file_name": "document.pdf",
            "file_type": "application/pdf"
        }
        errors = evidence_validation.validate_attachment(invalid_attachment)
        self.assertTrue(len(errors) > 0)
        self.assertIn("file path", errors[0].lower())
    
    def test_absolute_file_path(self):
        """Test validation fails with absolute file path (security check)."""
        invalid_attachment = {
            "file_path": "/absolute/path/document.pdf",
            "file_name": "document.pdf"
        }
        errors = evidence_validation.validate_attachment(invalid_attachment)
        self.assertTrue(len(errors) > 0)
        self.assertIn("absolute", errors[0].lower())
    
    def test_path_traversal_attempt(self):
        """Test validation fails with path traversal attempt (security check)."""
        invalid_attachment = {
            "file_path": "../../../etc/passwd",
            "file_name": "passwd"
        }
        errors = evidence_validation.validate_attachment(invalid_attachment)
        self.assertTrue(len(errors) > 0)
        self.assertIn("path", errors[0].lower())
    
    def test_negative_file_size(self):
        """Test validation fails with negative file size."""
        invalid_attachment = {
            "file_path": "attachments/document.pdf",
            "file_size": -500
        }
        errors = evidence_validation.validate_attachment(invalid_attachment)
        self.assertTrue(len(errors) > 0)
        self.assertIn("size", errors[0].lower())


class EvidenceSearchValidationTest(unittest.TestCase):
    """Test case for evidence search parameter validation (priority feature)."""
    
    def test_valid_search_params(self):
        """Test validation of valid search parameters."""
        valid_params = {
            "category": "Requirement",
            "tags": ["important", "urgent"],
            "date_from": "2025-01-01T00:00:00",
            "date_to": "2025-12-31T23:59:59"
        }
        is_valid, normalized, errors = evidence_validation.validate_evidence_search_params(valid_params)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        self.assertIn("category", normalized)
        self.assertIn("tags", normalized)
    
    def test_invalid_category(self):
        """Test validation fails with invalid category."""
        invalid_params = {
            "category": "NotARealCategory"
        }
        is_valid, normalized, errors = evidence_validation.validate_evidence_search_params(invalid_params)
        self.assertFalse(is_valid)
        self.assertIn("category", errors[0].lower())
    
    def test_invalid_date_range(self):
        """Test validation fails with invalid date range."""
        invalid_params = {
            "date_from": "2025-12-31T00:00:00",
            "date_to": "2025-01-01T00:00:00"  # End before start
        }
        is_valid, normalized, errors = evidence_validation.validate_evidence_search_params(invalid_params)
        self.assertFalse(is_valid)
        self.assertIn("date", errors[0].lower())
    
    def test_normalize_tags(self):
        """Test tags are properly normalized from string to list."""
        params = {
            "tags": "important,urgent,priority"
        }
        is_valid, normalized, errors = evidence_validation.validate_evidence_search_params(params)
        self.assertTrue(is_valid)
        self.assertIsInstance(normalized["tags"], list)
        self.assertEqual(len(normalized["tags"]), 3)
        self.assertIn("important", normalized["tags"])
        self.assertIn("urgent", normalized["tags"])
        self.assertIn("priority", normalized["tags"])


if __name__ == "__main__":
    unittest.main()
