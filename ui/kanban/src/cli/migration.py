"""
Migration CLI commands for the Kanban CLI.

This module provides command-line tools for managing schema migrations
in the Evidence Management System.
"""
import click
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from ..data.migration import get_migration_manager, MigrationManager
from ..models.evidence_validation import validate_evidence
from ..utils.exceptions import MigrationError, ValidationError
from ..ui.display import (
    console, print_header, print_success, print_error, print_warning,
    print_info, create_progress_context, confirm
)

# Setup logger
logger = logging.getLogger(__name__)


@click.group(name="migration")
def migration_group():
    """
    Manage schema migrations for the Evidence Management System.
    
    These commands provide tools for administrators to upgrade evidence schemas,
    monitor migration status, and rollback failed migrations.
    """
    pass


@migration_group.command(name="list")
@click.option("--format", type=click.Choice(["table", "json"]), default="table",
              help="Output format")
def list_migrations(format):
    """List available and completed migrations."""
    try:
        # Log command execution
        logger.info("Executing migration list command")
        
        # Get migration manager
        manager = get_migration_manager()
        
        # Get available migrations
        available_migrations = manager.get_available_migrations()
        
        # Get migration history
        history = manager.migration_log.get_migration_history()
        
        # Display information
        print_header("Schema Migrations")
        
        # Display available migrations
        console.print("[bold]Available Migration Paths:[/bold]")
        if format == "json":
            console.print(json.dumps(available_migrations, indent=2))
        else:
            for migration in available_migrations:
                console.print(f"- {migration['from_version']} → {migration['to_version']}: {migration['description']}")
        
        console.print()
        
        # Display migration history
        console.print("[bold]Migration History:[/bold]")
        if not history:
            console.print("No migrations have been performed yet.")
        elif format == "json":
            console.print(json.dumps(history, indent=2))
        else:
            for migration in history:
                status_color = {
                    'completed': 'green',
                    'completed_with_errors': 'yellow',
                    'failed': 'red',
                    'rolled_back': 'magenta',
                    'in_progress': 'blue'
                }.get(migration.get('status', ''), 'white')
                
                console.print(
                    f"- ID: {migration['migration_id']}, "
                    f"From: {migration['from_version']} → {migration['to_version']}, "
                    f"Status: [{status_color}]{migration.get('status', 'unknown')}[/{status_color}], "
                    f"Started: {migration['started_at']}"
                )
                
                # Show summary if available
                if 'summary' in migration:
                    summary = migration['summary']
                    console.print(f"  Entities: {summary.get('total', 0)} total, "
                                f"{summary.get('succeeded', 0)} succeeded, "
                                f"{summary.get('failed', 0)} failed, "
                                f"{summary.get('rolled_back', 0)} rolled back")
                
        logger.info("Migration list command completed")
    except Exception as e:
        print_error(f"Error listing migrations: {str(e)}")
        logger.exception("Error in migration list command")


@migration_group.command(name="details")
@click.argument("migration_id")
def migration_details(migration_id):
    """Show detailed information about a specific migration."""
    try:
        # Log command execution
        logger.info(f"Executing migration details command for {migration_id}")
        
        # Get migration manager
        manager = get_migration_manager()
        
        # Get migration history
        migrations = manager.migration_log.get_migration_history()
        target_migration = None
        
        for migration in migrations:
            if migration['migration_id'] == migration_id:
                target_migration = migration
                break
                
        if not target_migration:
            print_error(f"Migration not found: {migration_id}")
            return
            
        # Display migration details
        print_header(f"Migration Details: {migration_id}")
        console.print(f"[bold]Description:[/bold] {target_migration.get('description', 'N/A')}")
        console.print(f"[bold]From Version:[/bold] {target_migration['from_version']}")
        console.print(f"[bold]To Version:[/bold] {target_migration['to_version']}")
        console.print(f"[bold]Started At:[/bold] {target_migration['started_at']}")
        
        if 'completed_at' in target_migration:
            console.print(f"[bold]Completed At:[/bold] {target_migration['completed_at']}")
        
        status_color = {
            'completed': 'green',
            'completed_with_errors': 'yellow',
            'failed': 'red',
            'rolled_back': 'magenta',
            'in_progress': 'blue'
        }.get(target_migration.get('status', ''), 'white')
        
        console.print(f"[bold]Status:[/bold] [{status_color}]{target_migration.get('status', 'unknown')}[/{status_color}]")
        
        # Show summary if available
        if 'summary' in target_migration:
            summary = target_migration['summary']
            console.print("\n[bold]Summary:[/bold]")
            console.print(f"Total Entities: {summary.get('total', 0)}")
            console.print(f"Succeeded: {summary.get('succeeded', 0)}")
            console.print(f"Failed: {summary.get('failed', 0)}")
            console.print(f"Rolled Back: {summary.get('rolled_back', 0)}")
            console.print(f"Skipped: {summary.get('skipped', 0)}")
            
            if 'error' in summary:
                console.print(f"[bold red]Error:[/bold red] {summary['error']}")
        
        # Show affected entities
        if 'affected_entities' in target_migration and target_migration['affected_entities']:
            console.print("\n[bold]Affected Entities:[/bold]")
            
            # Count by status
            status_counts = {}
            for entity in target_migration['affected_entities']:
                status = entity.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
                
            for status, count in status_counts.items():
                console.print(f"{status}: {count}")
            
            # Show errors if any
            if 'errors' in target_migration and target_migration['errors']:
                console.print("\n[bold red]Errors:[/bold red]")
                for error in target_migration['errors'][:5]:  # Show only first 5 errors
                    console.print(f"- Entity {error['entity_id']}: {error['error']}")
                
                if len(target_migration['errors']) > 5:
                    console.print(f"...and {len(target_migration['errors']) - 5} more errors.")
        
        # Show log file
        if 'log_file' in target_migration:
            console.print(f"\n[bold]Log File:[/bold] {target_migration['log_file']}")
            
            # Show log excerpt
            log_content = manager.migration_log.get_migration_log(migration_id)
            if log_content:
                console.print("\n[bold]Log Excerpt (first 10 lines):[/bold]")
                lines = log_content.split('\n')[:10]
                for line in lines:
                    console.print(line)
                    
                if len(lines) > 10:
                    console.print("...")
                    console.print(f"Full log contains {len(log_content.split('\\n'))} lines.")
        
        logger.info(f"Migration details command completed for {migration_id}")
    except Exception as e:
        print_error(f"Error getting migration details: {str(e)}")
        logger.exception("Error in migration details command")


@migration_group.command(name="run")
@click.option("--from-version", required=True, help="Source schema version")
@click.option("--to-version", required=True, help="Target schema version")
@click.option("--description", default="Schema upgrade", help="Migration description")
@click.option("--batch-size", type=int, default=100, help="Number of entities to process in each batch")
@click.option("--dry-run", is_flag=True, help="Simulate migration without making changes")
@click.option("--force", is_flag=True, help="Skip confirmation")
def run_migration(from_version, to_version, description, batch_size, dry_run, force):
    """Run a schema migration for all evidence items."""
    try:
        # Log command execution
        logger.info(f"Executing migration run command from {from_version} to {to_version}")
        
        # Get migration manager
        manager = get_migration_manager()
        
        # Validate migration path
        is_valid, error = manager.validate_migration_path(from_version, to_version)
        if not is_valid:
            print_error(f"Invalid migration path: {error}")
            return
            
        # Display information
        print_header("Run Schema Migration")
        console.print(f"[bold]From Version:[/bold] {from_version}")
        console.print(f"[bold]To Version:[/bold] {to_version}")
        console.print(f"[bold]Description:[/bold] {description}")
        console.print(f"[bold]Batch Size:[/bold] {batch_size}")
        console.print(f"[bold]Dry Run:[/bold] {'Yes' if dry_run else 'No'}")
        
        # Warning about migration
        if not dry_run:
            print_warning("This operation will modify evidence data. Make sure you have a backup.")
        
        # Confirm migration
        if not force and not dry_run:
            if not confirm("Are you sure you want to run this migration?", default=False):
                print_info("Migration cancelled.")
                return
                
        # Run migration with progress spinner
        with create_progress_context() as progress:
            task_id = progress.add_task(f"Running migration...", total=1)
            
            # Use validation function
            def validate_migrated_data(data):
                return validate_evidence(data)
            
            # Run migration
            summary = manager.migrate_all_entities(
                from_version=from_version,
                to_version=to_version,
                description=description,
                validation_func=validate_migrated_data,
                batch_size=batch_size,
                dry_run=dry_run
            )
            
            progress.update(task_id, completed=1)
        
        # Display results
        if dry_run:
            print_success("Dry run completed successfully.")
        else:
            print_success("Migration completed.")
            
        console.print("\n[bold]Migration Summary:[/bold]")
        console.print(f"Total Entities: {summary.get('total', 0)}")
        console.print(f"Succeeded: {summary.get('succeeded', 0)}")
        console.print(f"Failed: {summary.get('failed', 0)}")
        console.print(f"Rolled Back: {summary.get('rolled_back', 0)}")
        console.print(f"Skipped: {summary.get('skipped', 0)}")
        
        # Show migration ID for potential rollback
        migration_id = manager.migration_log.get_migration_history()[-1]['migration_id']
        console.print(f"\nMigration ID: {migration_id}")
        console.print(f"Use this ID with 'migration details {migration_id}' for more information.")
        
        if summary.get('failed', 0) > 0:
            print_warning(f"{summary['failed']} entities failed to migrate. Check logs for details.")
            
        logger.info(f"Migration run command completed from {from_version} to {to_version}")
    except MigrationError as e:
        print_error(f"Migration error: {str(e)}")
        logger.error(f"Migration error: {str(e)}")
    except ValidationError as e:
        print_error(f"Validation error: {str(e)}")
        logger.error(f"Validation error: {str(e)}")
    except Exception as e:
        print_error(f"Error running migration: {str(e)}")
        logger.exception("Error in migration run command")


@migration_group.command(name="rollback")
@click.argument("migration_id")
@click.option("--force", is_flag=True, help="Skip confirmation")
def rollback_migration(migration_id, force):
    """Rollback a previously executed migration."""
    try:
        # Log command execution
        logger.info(f"Executing migration rollback command for {migration_id}")
        
        # Get migration manager
        manager = get_migration_manager()
        
        # Display information
        print_header("Rollback Migration")
        console.print(f"[bold]Migration ID:[/bold] {migration_id}")
        
        # Warning about rollback
        print_warning("This operation will restore evidence data from backups.")
        print_warning("Any changes made after the migration will be lost.")
        
        # Confirm rollback
        if not force:
            if not confirm("Are you sure you want to roll back this migration?", default=False):
                print_info("Rollback cancelled.")
                return
                
        # Rollback migration with progress spinner
        with create_progress_context() as progress:
            task_id = progress.add_task(f"Rolling back migration...", total=1)
            
            # Run rollback
            summary = manager.rollback_migration(migration_id)
            
            progress.update(task_id, completed=1)
        
        # Display results
        print_success("Rollback completed.")
        console.print("\n[bold]Rollback Summary:[/bold]")
        console.print(f"Total Entities: {summary.get('total', 0)}")
        console.print(f"Succeeded: {summary.get('succeeded', 0)}")
        console.print(f"Failed: {summary.get('failed', 0)}")
        
        if summary.get('failed', 0) > 0:
            print_warning(f"{summary['failed']} entities failed to roll back. Check logs for details.")
            
        logger.info(f"Migration rollback command completed for {migration_id}")
    except MigrationError as e:
        print_error(f"Rollback error: {str(e)}")
        logger.error(f"Rollback error: {str(e)}")
    except Exception as e:
        print_error(f"Error rolling back migration: {str(e)}")
        logger.exception("Error in migration rollback command")


@migration_group.command(name="log")
@click.argument("migration_id")
@click.option("--format", type=click.Choice(["text", "json"]), default="text",
              help="Output format")
def view_migration_log(migration_id, format):
    """View the full log for a specific migration."""
    try:
        # Log command execution
        logger.info(f"Executing migration log command for {migration_id}")
        
        # Get migration manager
        manager = get_migration_manager()
        
        # Get migration log
        log_content = manager.migration_log.get_migration_log(migration_id)
        if not log_content:
            print_error(f"Migration log not found for: {migration_id}")
            return
            
        # Display log
        print_header(f"Migration Log: {migration_id}")
        
        if format == "json":
            # Parse log to JSON format (simplified)
            lines = log_content.split('\n')
            log_data = {
                'header': lines[:6],
                'entries': lines[6:]
            }
            console.print(json.dumps(log_data, indent=2))
        else:
            console.print(log_content)
            
        logger.info(f"Migration log command completed for {migration_id}")
    except Exception as e:
        print_error(f"Error viewing migration log: {str(e)}")
        logger.exception("Error in migration log command")


# Add migration commands to the main CLI
def register_migration_commands(cli):
    """Register migration commands with the main CLI."""
    cli.add_command(migration_group)
