"""
Display utilities for the Kanban CLI using Rich.

This module provides colorful and formatted output for the Kanban CLI
using the Rich library.
"""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.box import Box, ROUNDED
from rich.theme import Theme
from rich.style import Style
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing import List, Dict, Any, Optional, Union

from ..config.settings import load_config

# Load color theme from config
config = load_config()
colors = config.get('cli', {}).get('colors', {})

# Create custom theme
custom_theme = Theme({
    "primary": colors.get('primary', "#4B8BBE"),
    "success": colors.get('success', "#69A85C"),
    "warning": colors.get('warning', "#F7C325"),
    "error": colors.get('error', "#D35E60"),
    "info": colors.get('info', "#61D2DC"),
    "task.backlog": "#8E8EA0",
    "task.ready": "#61D2DC",
    "task.in_progress": "#F7C325",
    "task.review": "#4B8BBE",
    "task.done": "#69A85C",
    "evidence.requirement": "#4B8BBE", 
    "evidence.bug": "#D35E60",
    "evidence.design": "#61D2DC",
    "evidence.test": "#8E8EA0",
    "evidence.result": "#69A85C",
    "evidence.reference": "#F7C325",
    "evidence.decision": "#9575CD",
})

# Create console with theme
console = Console(theme=custom_theme)

def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """
    Print a formatted header with optional subtitle.
    
    Args:
        title: The main title to display
        subtitle: Optional subtitle
    """
    console.print(f"\n[bold primary]{title}[/bold primary]")
    if subtitle:
        console.print(f"[italic]{subtitle}[/italic]\n")
    console.print("─" * min(len(title), 80))

def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[success]✓ {message}[/success]")

def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[error]✗ {message}[/error]")

def print_warning(message: str) -> None:
    """Print a warning message."""
    console.print(f"[warning]⚠ {message}[/warning]")

def print_info(message: str) -> None:
    """Print an info message."""
    console.print(f"[info]ℹ {message}[/info]")

def confirm(message: str, default: bool = False) -> bool:
    """
    Ask for user confirmation.
    
    Args:
        message: The confirmation message to display
        default: Default value if user just presses Enter
    
    Returns:
        Boolean indicating user's choice
    """
    default_text = "[Y/n]" if default else "[y/N]"
    response = console.input(f"{message} {default_text}: ")
    
    if not response:
        return default
    
    return response.lower().startswith('y')

def create_task_table(tasks: List[Dict[str, Any]], 
                     columns: Optional[List[str]] = None,
                     compact: bool = False) -> Table:
    """
    Create a Rich table for displaying tasks.
    
    Args:
        tasks: List of task dictionaries
        columns: Optional list of columns to include
        compact: Whether to use compact display mode
    
    Returns:
        Rich Table object
    """
    if not columns:
        columns = ["ID", "Title", "Status", "Priority"]
    
    table = Table(box=ROUNDED, show_header=True, header_style="bold")
    
    # Add columns
    for column in columns:
        table.add_column(column)
    
    # Add rows
    for task in tasks:
        row = []
        for column in columns:
            key = column.lower().replace(' ', '_')
            
            if key == "id":
                row.append(task.get("id", ""))
            elif key == "title":
                row.append(task.get("title", ""))
            elif key == "status":
                status = task.get("status", "")
                status_style = f"task.{status.lower().replace(' ', '_')}"
                row.append(f"[{status_style}]{status}[/{status_style}]")
            elif key == "priority":
                priority = task.get("priority", "")
                if priority == "High" or priority == "Critical":
                    row.append(f"[bold]{priority}[/bold]")
                else:
                    row.append(priority)
            elif key in task:
                row.append(str(task[key]))
            else:
                row.append("")
        
        table.add_row(*row)
    
    return table

def create_evidence_table(evidence_items: List[Dict[str, Any]], 
                         columns: Optional[List[str]] = None) -> Table:
    """
    Create a Rich table for displaying evidence items.
    
    Args:
        evidence_items: List of evidence dictionaries
        columns: Optional list of columns to include
    
    Returns:
        Rich Table object
    """
    if not columns:
        columns = ["ID", "Title", "Category", "Relevance", "Tags"]
    
    table = Table(box=ROUNDED, show_header=True, header_style="bold")
    
    # Add columns
    for column in columns:
        table.add_column(column)
    
    # Add rows
    for evidence in evidence_items:
        row = []
        for column in columns:
            key = column.lower().replace(' ', '_')
            
            if key == "id":
                row.append(evidence.get("id", ""))
            elif key == "title":
                row.append(evidence.get("title", ""))
            elif key == "category":
                category = evidence.get("category", "")
                category_style = f"evidence.{category.lower().replace(' ', '_')}"
                row.append(f"[{category_style}]{category}[/{category_style}]")
            elif key == "relevance" or key == "relevance_score":
                relevance = evidence.get("relevance_score", "")
                if relevance == "High" or relevance == "Critical":
                    row.append(f"[bold]{relevance}[/bold]")
                else:
                    row.append(relevance)
            elif key == "tags":
                tags = evidence.get("tags", [])
                if tags:
                    row.append(", ".join(tags))
                else:
                    row.append("")
            elif key in evidence:
                row.append(str(evidence[key]))
            else:
                row.append("")
        
        table.add_row(*row)
    
    return table

def print_panel(content: str, title: Optional[str] = None, 
               style: str = "primary") -> None:
    """
    Print content in a panel with optional title.
    
    Args:
        content: The content to display
        title: Optional panel title
        style: Panel style/color
    """
    panel = Panel(content, title=title, border_style=style, box=ROUNDED)
    console.print(panel)

def create_progress_context(message: str = "Processing"):
    """
    Create a progress context for long-running operations.
    
    Args:
        message: Message to display with the spinner
    
    Returns:
        Rich Progress object
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    )

def print_evidence_details(evidence: Dict[str, Any]) -> None:
    """
    Print detailed information about an evidence item.
    
    Args:
        evidence: Evidence data dictionary
    """
    # Title and basic info
    console.print(f"\n[bold primary]Evidence: {evidence.get('title')}[/bold primary]")
    console.print("─" * min(len(evidence.get('title', '')) + 10, 80))
    
    # ID and dates
    console.print(f"[bold]ID:[/bold] {evidence.get('id', '')}")
    console.print(f"[bold]Created:[/bold] {evidence.get('created_at', '')}")
    if evidence.get('updated_at'):
        console.print(f"[bold]Updated:[/bold] {evidence.get('updated_at', '')}")
    if evidence.get('date_collected'):
        console.print(f"[bold]Collected:[/bold] {evidence.get('date_collected', '')}")
    
    # Category and relevance
    category = evidence.get('category', '')
    category_style = f"evidence.{category.lower().replace(' ', '_')}"
    console.print(f"[bold]Category:[/bold] [{category_style}]{category}[/{category_style}]")
    
    if evidence.get('subcategory'):
        console.print(f"[bold]Subcategory:[/bold] {evidence.get('subcategory', '')}")
    
    relevance = evidence.get('relevance_score', '')
    console.print(f"[bold]Relevance:[/bold] {relevance}")
    
    # Source and creator
    if evidence.get('source'):
        console.print(f"[bold]Source:[/bold] {evidence.get('source', '')}")
    if evidence.get('created_by'):
        console.print(f"[bold]Created by:[/bold] {evidence.get('created_by', '')}")
    
    # Tags
    if evidence.get('tags'):
        tags = ", ".join([f"[italic]{tag}[/italic]" for tag in evidence.get('tags', [])])
        console.print(f"[bold]Tags:[/bold] {tags}")
    
    # Related items
    if evidence.get('task_id'):
        console.print(f"[bold]Related Task:[/bold] {evidence.get('task_id', '')}")
    if evidence.get('epic_id'):
        console.print(f"[bold]Related Epic:[/bold] {evidence.get('epic_id', '')}")
    if evidence.get('related_evidence_ids'):
        rel_ids = ", ".join(evidence.get('related_evidence_ids', []))
        console.print(f"[bold]Related Evidence:[/bold] {rel_ids}")
    
    # Description
    console.print("\n[bold]Description:[/bold]")
    print_panel(evidence.get('description', ''), style="info")
    
    # Attachments
    if evidence.get('attachments'):
        console.print("\n[bold]Attachments:[/bold]")
        for i, attachment in enumerate(evidence.get('attachments', [])):
            console.print(f"  {i+1}. [italic]{attachment.get('file_name', '')}[/italic] " +
                         f"({attachment.get('file_type', '')})")
            if attachment.get('description'):
                console.print(f"     {attachment.get('description', '')}")
    
    # Metadata
    if evidence.get('metadata') and evidence['metadata']:
        console.print("\n[bold]Additional Metadata:[/bold]")
        for key, value in evidence.get('metadata', {}).items():
            console.print(f"  [italic]{key}:[/italic] {value}")
    
    console.print()  # Empty line at the end
