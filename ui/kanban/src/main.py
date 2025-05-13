#!/usr/bin/env python
"""
Kanban CLI - Main entry point

This is the main entry point for the Kanban CLI application, which integrates
the CLI command groups including the Evidence Management System (priority).
"""
import os
import sys
import click
from rich.console import Console
from rich.panel import Panel

# Add the parent directory to sys.path
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(parent_dir)

# Import command groups
from .cli import cli_group
from .ui.display import console, print_header, print_info
from .utils.logging import setup_logging
from .config.settings import load_config

# Setup logger
logger = setup_logging(name="kanban.main")

@click.group()
@click.version_option(version='0.1.0')
def cli():
    """Kanban CLI - Task and project management from the command line."""
    pass

# Add splash command
@cli.command()
def splash():
    """Display information about the Kanban CLI."""
    config = load_config()
    app_name = config.get('app', {}).get('name', 'Kanban CLI')
    app_version = config.get('app', {}).get('version', '0.1.0')
    
    print_header(f"{app_name} v{app_version}")
    
    # Display welcome message
    panel_content = (
        "Welcome to the Kanban CLI!\n\n"
        "[bold]Available Commands:[/bold]\n"
        "  kanban task - Task management commands\n"
        "  kanban board - Board visualization commands\n"
        "  kanban epic - Epic management commands\n"
        "  kanban evidence - Evidence management commands (priority)\n\n"
        "Use [italic]kanban --help[/italic] for more information."
    )
    
    console.print(Panel(panel_content, title="Getting Started", border_style="primary"))
    
    # Note about priority feature
    print_info("The Evidence Management System is a priority feature of this application.")
    
    logger.info("Displayed splash screen")

# Add init command
@cli.command()
def init():
    """Initialize a new Kanban board configuration."""
    try:
        from .data.storage import BoardStorage

        logger.info("Initializing Kanban CLI")
        print_header("Initializing Kanban CLI")

        # Check if board already exists
        board_storage = BoardStorage()
        boards = board_storage.list()

        if boards:
            print_info(f"Board already exists: {boards[0].name}")
            print_info("Use 'kanban board list' to view available boards")
            return

        # Create default board
        default_board = board_storage.create({
            "name": "Default Board",
            "columns": ["Backlog", "Ready", "In Progress", "Review", "Done"]
        })

        print_info(f"Created default board: {default_board.name}")
        print_info(f"Board columns: {', '.join(default_board.columns)}")
        print_info("Use 'kanban board show' to view the board")

        logger.info(f"Created default board {default_board.id}")

    except Exception as e:
        from .ui.display import print_error
        print_error(f"Error initializing Kanban CLI: {str(e)}")
        logger.exception("Error in init command")

# Register the command groups
cli.add_command(cli_group, name="kanban")

if __name__ == '__main__':
    cli()
