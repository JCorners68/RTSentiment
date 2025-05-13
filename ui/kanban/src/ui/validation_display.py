"""
Validation Display Utilities

This module provides functions for displaying validation results and issues.
"""

from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.style import Style
from rich.box import ROUNDED

# Use the same console as the main display module
from .display import console

def display_validation_results(is_valid: bool, error_messages: List[str], config_file: str) -> None:
    """
    Display validation results.
    
    Args:
        is_valid: Whether the configuration is valid
        error_messages: List of error messages if not valid
        config_file: Path to the configuration file that was validated
    """
    if is_valid:
        console.print(
            Panel(
                f"[bold success]Configuration is valid![/bold success]\n\n"
                f"File: {config_file}",
                title="Validation Results",
                border_style="success",
                box=ROUNDED
            )
        )
    else:
        error_table = Table(show_header=True, header_style="bold", box=ROUNDED)
        error_table.add_column("Error", style="error")
        
        for error in error_messages:
            error_table.add_row(error)
        
        console.print(
            Panel(
                f"[bold error]Configuration validation failed![/bold error]\n\n"
                f"File: {config_file}\n\n"
                f"{error_table}",
                title="Validation Results",
                border_style="error",
                box=ROUNDED
            )
        )


def display_environment_issues(issues: List[Dict[str, Any]], config_file: str) -> None:
    """
    Display environment issues.
    
    Args:
        issues: List of environment issues
        config_file: Path to the configuration file
    """
    if not issues:
        console.print(
            Panel(
                f"[bold success]No environment issues found![/bold success]\n\n"
                f"Configuration file: {config_file}",
                title="Environment Check",
                border_style="success",
                box=ROUNDED
            )
        )
        return
    
    # Group issues by severity
    critical_issues = [i for i in issues if i["severity"] == "critical"]
    warning_issues = [i for i in issues if i["severity"] == "warning"]
    info_issues = [i for i in issues if i["severity"] == "info"]
    
    # Create tables for each severity
    tables = []
    
    if critical_issues:
        critical_table = Table(show_header=True, header_style="bold", title="Critical Issues", box=ROUNDED)
        critical_table.add_column("Issue", style="error")
        critical_table.add_column("Fixable")
        
        for issue in critical_issues:
            fixable = "Yes" if issue.get("fixable") else "No"
            critical_table.add_row(issue["message"], fixable)
        
        tables.append(critical_table)
    
    if warning_issues:
        warning_table = Table(show_header=True, header_style="bold", title="Warning Issues", box=ROUNDED)
        warning_table.add_column("Issue", style="warning")
        warning_table.add_column("Fixable")
        
        for issue in warning_issues:
            fixable = "Yes" if issue.get("fixable") else "No"
            warning_table.add_row(issue["message"], fixable)
        
        tables.append(warning_table)
    
    if info_issues:
        info_table = Table(show_header=True, header_style="bold", title="Info Issues", box=ROUNDED)
        info_table.add_column("Issue", style="info")
        info_table.add_column("Fixable")
        
        for issue in info_issues:
            fixable = "Yes" if issue.get("fixable") else "No"
            info_table.add_row(issue["message"], fixable)
        
        tables.append(info_table)
    
    # Determine overall status
    if critical_issues:
        status = "[bold error]Critical issues found![/bold error]"
        border_style = "error"
    elif warning_issues:
        status = "[bold warning]Warning issues found![/bold warning]"
        border_style = "warning"
    else:
        status = "[bold info]Minor issues found![/bold info]"
        border_style = "info"
    
    # Build the content
    content = f"{status}\n\nConfiguration file: {config_file}\n\n"
    
    for table in tables:
        content += f"{table}\n\n"
    
    if any(issue.get("fixable") for issue in issues):
        content += "[bold]Some issues can be fixed automatically. Run 'kanban config repair' to attempt repair.[/bold]"
    
    console.print(Panel(content, title="Environment Check", border_style=border_style, box=ROUNDED))


def display_healing_results(success: bool, messages: List[str], config_file: str) -> None:
    """
    Display healing results.
    
    Args:
        success: Whether the healing was successful
        messages: List of messages about actions taken or failures
        config_file: Path to the configuration file
    """
    if success:
        message_table = Table(show_header=True, header_style="bold", box=ROUNDED)
        message_table.add_column("Action Taken", style="success")
        
        for message in messages:
            message_table.add_row(message)
        
        console.print(
            Panel(
                f"[bold success]Configuration healed successfully![/bold success]\n\n"
                f"File: {config_file}\n\n"
                f"{message_table}",
                title="Healing Results",
                border_style="success",
                box=ROUNDED
            )
        )
    else:
        message_table = Table(show_header=True, header_style="bold", box=ROUNDED)
        message_table.add_column("Error", style="error")
        
        for message in messages:
            message_table.add_row(message)
        
        console.print(
            Panel(
                f"[bold error]Configuration healing failed![/bold error]\n\n"
                f"File: {config_file}\n\n"
                f"{message_table}",
                title="Healing Results",
                border_style="error",
                box=ROUNDED
            )
        )


def display_syntax_highlighted(text: str, language: str, title: Optional[str] = None) -> None:
    """
    Display syntax highlighted text.
    
    Args:
        text: The text to highlight
        language: The language for syntax highlighting
        title: Optional title for the panel
    """
    syntax = Syntax(text, language, theme="monokai", line_numbers=True)
    
    if title:
        console.print(Panel(syntax, title=title, box=ROUNDED))
    else:
        console.print(syntax)


def display_markdown(text: str, title: Optional[str] = None) -> None:
    """
    Display markdown formatted text.
    
    Args:
        text: Markdown text to display
        title: Optional title for the panel
    """
    markdown = Markdown(text)
    
    if title:
        console.print(Panel(markdown, title=title, box=ROUNDED))
    else:
        console.print(markdown)