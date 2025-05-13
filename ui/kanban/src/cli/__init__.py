"""
CLI command groups for the Kanban CLI application.

This module organizes the command groups for the Kanban CLI, including
the Evidence Management System which is a priority feature.
"""
import click

from . import tasks
from . import board
from . import epics
from . import evidence  # Priority feature
from . import migration  # Schema migration framework

@click.group()
def cli_group():
    """Main entry point for the Kanban CLI command groups."""
    pass

# Register command groups
cli_group.add_command(tasks.task_group)
cli_group.add_command(board.board_group)
cli_group.add_command(epics.epic_group)
cli_group.add_command(evidence.evidence_group)  # Priority feature
cli_group.add_command(migration.migration_group)  # Schema migration framework
