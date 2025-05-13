"""
Template-Based Evidence Creation Utility.

This module provides functionality for creating evidence items based on
predefined templates for different evidence types.
"""
import logging
import os
import json
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.box import ROUNDED

from ..models.evidence_schema import EvidenceSchema, EvidenceCategory, EvidenceRelevance
from .display import console, print_success, print_error, print_info

# Configure module logger
logger = logging.getLogger(__name__)


class EvidenceTemplate:
    """
    Template for creating evidence items.
    
    This class defines a reusable template for evidence creation
    with predefined fields and prompts.
    """
    
    def __init__(self,
                name: str,
                description: str,
                category: EvidenceCategory,
                fields: Dict[str, Dict[str, Any]],
                suggested_tags: List[str] = None):
        """
        Initialize the evidence template.
        
        Args:
            name: Template name
            description: Template description
            category: Default evidence category
            fields: Dictionary of fields with their properties
            suggested_tags: Optional list of suggested tags
        """
        self.name = name
        self.description = description
        self.category = category
        self.fields = fields
        self.suggested_tags = suggested_tags or []
        
        logger.info(f"Initialized evidence template: {name}")
    
    def to_dict(self) -> Dict:
        """
        Convert template to dictionary for serialization.
        
        Returns:
            Dictionary representation of the template
        """
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "fields": self.fields,
            "suggested_tags": self.suggested_tags
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'EvidenceTemplate':
        """
        Create a template from a dictionary.
        
        Args:
            data: Dictionary with template data
            
        Returns:
            New EvidenceTemplate instance
        """
        # Convert category string to enum
        category = EvidenceCategory.OTHER
        try:
            category_value = data.get("category", "Other")
            category = EvidenceCategory(category_value)
        except:
            # Invalid category, use default
            logger.warning(f"Invalid category in template: {category_value}")
        
        return cls(
            name=data.get("name", "Unnamed Template"),
            description=data.get("description", ""),
            category=category,
            fields=data.get("fields", {}),
            suggested_tags=data.get("suggested_tags", [])
        )


class EvidenceTemplateManager:
    """
    Manager for evidence templates.
    
    This class provides functionality to load, save, and use
    evidence templates for standardized evidence creation.
    """
    
    def __init__(self, templates_dir: str = None, console: Optional[Console] = None):
        """
        Initialize the template manager.
        
        Args:
            templates_dir: Directory for template storage
            console: Optional console for display
        """
        self.console = console or Console()
        self.templates_dir = templates_dir or os.path.expanduser("~/.kanban/templates")
        self.templates: Dict[str, EvidenceTemplate] = {}
        
        # Create templates directory if it doesn't exist
        os.makedirs(self.templates_dir, exist_ok=True)
        
        # Load built-in templates
        self._initialize_builtin_templates()
        
        # Load saved templates
        self.load_templates()
        
        logger.info(f"Initialized evidence template manager with {len(self.templates)} templates")
    
    def _initialize_builtin_templates(self) -> None:
        """Initialize built-in evidence templates."""
        # Bug report template
        bug_template = EvidenceTemplate(
            name="Bug Report",
            description="Template for reporting software bugs",
            category=EvidenceCategory.BUG,
            fields={
                "title": {
                    "prompt": "Bug title",
                    "description": "A brief, descriptive title for the bug",
                    "required": True
                },
                "description": {
                    "prompt": "Bug description",
                    "description": "Detailed description of the bug",
                    "multiline": True,
                    "required": True
                },
                "steps_to_reproduce": {
                    "prompt": "Steps to reproduce",
                    "description": "Step-by-step instructions to reproduce the bug",
                    "multiline": True,
                    "required": True
                },
                "expected_behavior": {
                    "prompt": "Expected behavior",
                    "description": "What should happen when steps are followed",
                    "multiline": True,
                    "required": True
                },
                "actual_behavior": {
                    "prompt": "Actual behavior",
                    "description": "What actually happens when steps are followed",
                    "multiline": True,
                    "required": True
                },
                "environment": {
                    "prompt": "Environment",
                    "description": "System environment where bug occurs (OS, browser, etc.)",
                    "required": False
                },
                "severity": {
                    "prompt": "Severity",
                    "description": "How severe is the bug",
                    "choices": ["Critical", "High", "Medium", "Low"],
                    "default": "Medium",
                    "required": True
                }
            },
            suggested_tags=["bug", "defect", "issue"]
        )
        
        # Feature requirement template
        requirement_template = EvidenceTemplate(
            name="Feature Requirement",
            description="Template for documenting feature requirements",
            category=EvidenceCategory.REQUIREMENT,
            fields={
                "title": {
                    "prompt": "Requirement title",
                    "description": "A brief, descriptive title for the requirement",
                    "required": True
                },
                "description": {
                    "prompt": "Requirement description",
                    "description": "Detailed description of the requirement",
                    "multiline": True,
                    "required": True
                },
                "acceptance_criteria": {
                    "prompt": "Acceptance criteria",
                    "description": "Criteria that must be met for this requirement",
                    "multiline": True,
                    "required": True
                },
                "priority": {
                    "prompt": "Priority",
                    "description": "Requirement priority",
                    "choices": ["Critical", "High", "Medium", "Low"],
                    "default": "Medium",
                    "required": True
                },
                "dependencies": {
                    "prompt": "Dependencies",
                    "description": "Other requirements this depends on",
                    "required": False
                },
                "stakeholders": {
                    "prompt": "Stakeholders",
                    "description": "People or groups with interest in this requirement",
                    "required": False
                }
            },
            suggested_tags=["requirement", "feature", "user-story"]
        )
        
        # Design decision template
        decision_template = EvidenceTemplate(
            name="Design Decision",
            description="Template for documenting design decisions",
            category=EvidenceCategory.DECISION,
            fields={
                "title": {
                    "prompt": "Decision title",
                    "description": "A brief, descriptive title for the decision",
                    "required": True
                },
                "description": {
                    "prompt": "Decision description",
                    "description": "Detailed description of the decision",
                    "multiline": True,
                    "required": True
                },
                "context": {
                    "prompt": "Context",
                    "description": "Background and context for this decision",
                    "multiline": True,
                    "required": True
                },
                "alternatives": {
                    "prompt": "Alternatives considered",
                    "description": "Other options that were considered",
                    "multiline": True,
                    "required": True
                },
                "reasoning": {
                    "prompt": "Decision reasoning",
                    "description": "Reasoning behind the chosen solution",
                    "multiline": True,
                    "required": True
                },
                "consequences": {
                    "prompt": "Consequences",
                    "description": "Expected consequences of this decision",
                    "multiline": True,
                    "required": False
                }
            },
            suggested_tags=["decision", "architecture", "design"]
        )
        
        # Test case template
        test_template = EvidenceTemplate(
            name="Test Case",
            description="Template for documenting test cases",
            category=EvidenceCategory.TEST,
            fields={
                "title": {
                    "prompt": "Test case title",
                    "description": "A brief, descriptive title for the test case",
                    "required": True
                },
                "description": {
                    "prompt": "Test case description",
                    "description": "Detailed description of the test case",
                    "multiline": True,
                    "required": True
                },
                "preconditions": {
                    "prompt": "Preconditions",
                    "description": "Conditions that must be true before test execution",
                    "multiline": True,
                    "required": True
                },
                "steps": {
                    "prompt": "Test steps",
                    "description": "Step-by-step instructions to execute the test",
                    "multiline": True,
                    "required": True
                },
                "expected_results": {
                    "prompt": "Expected results",
                    "description": "Expected outcomes for each step",
                    "multiline": True,
                    "required": True
                },
                "test_data": {
                    "prompt": "Test data",
                    "description": "Data needed to execute the test",
                    "multiline": True,
                    "required": False
                }
            },
            suggested_tags=["test", "verification", "validation"]
        )
        
        # Add built-in templates to the manager
        self.templates["bug_report"] = bug_template
        self.templates["feature_requirement"] = requirement_template
        self.templates["design_decision"] = decision_template
        self.templates["test_case"] = test_template
    
    def load_templates(self) -> None:
        """Load templates from the templates directory."""
        try:
            # Find all template files
            template_files = [f for f in os.listdir(self.templates_dir) 
                            if f.endswith('.json')]
            
            for filename in template_files:
                try:
                    file_path = os.path.join(self.templates_dir, filename)
                    with open(file_path, 'r') as f:
                        template_data = json.load(f)
                        template = EvidenceTemplate.from_dict(template_data)
                        
                        # Use filename without extension as template ID
                        template_id = os.path.splitext(filename)[0]
                        self.templates[template_id] = template
                        
                        logger.info(f"Loaded template: {template.name} ({template_id})")
                        
                except Exception as e:
                    logger.error(f"Error loading template {filename}: {str(e)}")
        
        except Exception as e:
            logger.error(f"Error loading templates: {str(e)}")
    
    def save_template(self, template_id: str, template: EvidenceTemplate) -> bool:
        """
        Save a template to the templates directory.
        
        Args:
            template_id: Unique identifier for the template
            template: Template to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Format template ID
            template_id = template_id.lower().replace(' ', '_')
            file_path = os.path.join(self.templates_dir, f"{template_id}.json")
            
            # Save template to file
            with open(file_path, 'w') as f:
                json.dump(template.to_dict(), f, indent=2)
                
            # Add to in-memory templates
            self.templates[template_id] = template
            
            logger.info(f"Saved template: {template.name} ({template_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error saving template {template_id}: {str(e)}")
            return False
    
    def delete_template(self, template_id: str) -> bool:
        """
        Delete a template.
        
        Args:
            template_id: ID of the template to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if built-in template
            if template_id in ["bug_report", "feature_requirement", "design_decision", "test_case"]:
                logger.warning(f"Cannot delete built-in template: {template_id}")
                return False
                
            # Remove from in-memory templates
            if template_id in self.templates:
                template = self.templates.pop(template_id)
                
                # Delete file if it exists
                file_path = os.path.join(self.templates_dir, f"{template_id}.json")
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
                logger.info(f"Deleted template: {template.name} ({template_id})")
                return True
            else:
                logger.warning(f"Template not found: {template_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting template {template_id}: {str(e)}")
            return False
    
    def list_templates(self) -> None:
        """List all available templates."""
        if not self.templates:
            self.console.print("[italic]No templates available[/italic]")
            return
            
        # Create table for templates
        table = Table(title="Available Evidence Templates", box=ROUNDED)
        table.add_column("ID", style="bold")
        table.add_column("Name")
        table.add_column("Category")
        table.add_column("Description")
        
        # Add rows for each template
        for template_id, template in sorted(self.templates.items()):
            table.add_row(
                template_id,
                template.name,
                template.category.value,
                template.description[:50] + ('...' if len(template.description) > 50 else '')
            )
        
        self.console.print()
        self.console.print(table)
        self.console.print()
    
    def create_evidence_from_template(self, 
                                     template_id: str,
                                     interactive: bool = True) -> Optional[EvidenceSchema]:
        """
        Create an evidence item from a template.
        
        Args:
            template_id: ID of the template to use
            interactive: Whether to prompt for input interactively
            
        Returns:
            New EvidenceSchema instance or None if canceled
        """
        # Check if template exists
        if template_id not in self.templates:
            print_error(f"Template not found: {template_id}")
            return None
            
        template = self.templates[template_id]
        
        # Display template info
        print_info(f"Creating evidence using template: {template.name}")
        self.console.print(f"Category: {template.category.value}")
        self.console.print(f"Description: {template.description}")
        self.console.print()
        
        if interactive and not Confirm.ask("Continue with this template?", default=True):
            return None
            
        # Collect field values
        field_values = {}
        
        for field_name, field_properties in template.fields.items():
            prompt_text = field_properties.get("prompt", field_name.replace('_', ' ').title())
            description = field_properties.get("description", "")
            choices = field_properties.get("choices", None)
            default = field_properties.get("default", None)
            multiline = field_properties.get("multiline", False)
            required = field_properties.get("required", False)
            
            # Show field description
            if description:
                self.console.print(f"[dim]{description}[/dim]")
                
            # Collect input
            value = None
            if interactive:
                # Interactive input
                if multiline:
                    self.console.print(f"[bold]{prompt_text}:[/bold] (Press Enter then Ctrl+D when finished)")
                    lines = []
                    try:
                        while True:
                            line = input()
                            lines.append(line)
                    except EOFError:
                        value = "\n".join(lines)
                elif choices:
                    # Multiple choice
                    value = Prompt.ask(
                        f"[bold]{prompt_text}[/bold]",
                        choices=choices,
                        default=default
                    )
                else:
                    # Simple text input
                    value = Prompt.ask(
                        f"[bold]{prompt_text}[/bold]",
                        default=default
                    )
            else:
                # Non-interactive, use defaults
                value = default if default is not None else ""
                
            # Validate required fields
            if required and not value and interactive:
                self.console.print("[red]This field is required.[/red]")
                # Try again
                if choices:
                    value = Prompt.ask(
                        f"[bold]{prompt_text}[/bold]",
                        choices=choices,
                        default=default
                    )
                else:
                    value = Prompt.ask(
                        f"[bold]{prompt_text}[/bold]",
                        default=default
                    )
                    
            # Store field value
            field_values[field_name] = value
            
        # Handle tags
        tags = []
        if interactive:
            # Show suggested tags
            if template.suggested_tags:
                self.console.print(f"Suggested tags: {', '.join(template.suggested_tags)}")
                
            # Collect tags
            tags_input = Prompt.ask(
                "[bold]Tags[/bold] (comma-separated)",
                default=", ".join(template.suggested_tags)
            )
            
            if tags_input:
                tags = [tag.strip() for tag in tags_input.split(',')]
        else:
            # Use suggested tags in non-interactive mode
            tags = template.suggested_tags
            
        # Create the evidence item
        try:
            # Prepare evidence data
            evidence_data = {
                "title": field_values.get("title", "Untitled Evidence"),
                "description": field_values.get("description", ""),
                "category": template.category,
                "tags": tags,
                "source": field_values.get("source", "Template Generated"),
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "metadata": {}
            }
            
            # Add additional fields to metadata
            for field_name, value in field_values.items():
                if field_name not in ["title", "description", "source"]:
                    evidence_data["metadata"][field_name] = value
                    
            # Set relevance based on priority if available
            if "priority" in field_values:
                priority = field_values["priority"]
                if priority == "Critical":
                    evidence_data["relevance_score"] = EvidenceRelevance.CRITICAL
                elif priority == "High":
                    evidence_data["relevance_score"] = EvidenceRelevance.HIGH
                elif priority == "Medium":
                    evidence_data["relevance_score"] = EvidenceRelevance.MEDIUM
                elif priority == "Low":
                    evidence_data["relevance_score"] = EvidenceRelevance.LOW
                    
            # Create evidence item
            evidence = EvidenceSchema(**evidence_data)
            
            print_success(f"Created evidence item: {evidence.id}")
            return evidence
            
        except Exception as e:
            logger.error(f"Error creating evidence from template: {str(e)}")
            print_error(f"Error creating evidence: {str(e)}")
            return None


# Create a default template manager for importing
template_manager = EvidenceTemplateManager()