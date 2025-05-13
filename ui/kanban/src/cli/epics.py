"""
Epic command group for the Kanban CLI.

This module implements the epic-related commands for the Kanban CLI.
"""
import click
from typing import Optional, List, Dict, Any
import json

from ..data.storage import EpicStorage, TaskStorage
from ..ui.display import (
    console, print_header, print_success, print_error, 
    print_warning, print_info, create_task_table, print_panel, confirm
)
from ..utils.logging import setup_logging

# Setup logger
logger = setup_logging(name="kanban.cli.epics")

@click.group(name="epic")
def epic_group():
    """Manage epics (groups of related tasks)."""
    pass

@epic_group.command(name="list")
@click.option("--status", help="Filter by status")
@click.option("--owner", help="Filter by owner")
@click.option("--title", help="Filter by title (substring match)")
@click.option("--format", type=click.Choice(["table", "json"]), default="table", 
              help="Output format")
def list_epics(status, owner, title, format):
    """List epics with optional filtering."""
    try:
        # Log command execution
        logger.info(f"Executing epic list command with filters: status={status}, owner={owner}, title={title}")
        
        # Get epics from storage
        storage = EpicStorage()
        
        # Build filters
        filters = {}
        if status:
            filters["status"] = status
        if owner:
            filters["owner"] = owner
        if title:
            filters["title"] = title
        
        # Get filtered epics
        epics = storage.list(filters)
        
        if not epics:
            print_warning("No epics found matching the criteria.")
            return
        
        # Display epics
        print_header(f"Epics ({len(epics)})", "Filtered by provided criteria" if filters else "All epics")
        
        if format == "json":
            import json
            console.print_json(json.dumps([epic.to_dict() for epic in epics], indent=2))
        else:
            # Display epics in a nice format
            for i, epic in enumerate(epics):
                console.print(f"[bold]{i+1}. {epic.title}[/bold] ({epic.id})")
                console.print(f"   Status: {epic.status}")
                if epic.owner:
                    console.print(f"   Owner: {epic.owner}")
                
                # Date information
                console.print(f"   Created: {epic.created_at.isoformat()}")
                if epic.start_date:
                    console.print(f"   Start Date: {epic.start_date.isoformat()}")
                if epic.end_date:
                    console.print(f"   End Date: {epic.end_date.isoformat()}")
                
                # Related evidence count
                if epic.related_evidence_ids:
                    console.print(f"   Evidence Items: {len(epic.related_evidence_ids)}")
                
                # Get tasks for this epic
                task_storage = TaskStorage()
                tasks = task_storage.list({"epic_id": epic.id})
                console.print(f"   Tasks: {len(tasks)}")
                
                # Brief description preview
                if epic.description:
                    desc_preview = epic.description[:100] + "..." if len(epic.description) > 100 else epic.description
                    console.print(f"   Description: {desc_preview}")
                
                console.print("")  # Empty line between epics
        
        logger.info(f"Listed {len(epics)} epics")
    
    except Exception as e:
        print_error(f"Error listing epics: {str(e)}")
        logger.exception("Error in epic list command")

@epic_group.command(name="get")
@click.argument("epic_id")
@click.option("--with-tasks", is_flag=True, help="Include tasks in the output")
def get_epic(epic_id, with_tasks):
    """Get detailed information about a specific epic."""
    try:
        # Log command execution
        logger.info(f"Executing epic get command for epic_id={epic_id}")
        
        # Get epic from storage
        epic_storage = EpicStorage()
        epic = epic_storage.get(epic_id)
        
        if not epic:
            print_error(f"Epic not found: {epic_id}")
            return
        
        # Display epic details
        print_header(f"Epic: {epic.title}", f"ID: {epic.id}")
        
        # Basic info
        console.print(f"[bold]Status:[/bold] {epic.status}")
        
        if epic.owner:
            console.print(f"[bold]Owner:[/bold] {epic.owner}")
        
        # Dates
        console.print(f"[bold]Created:[/bold] {epic.created_at.isoformat()}")
        console.print(f"[bold]Updated:[/bold] {epic.updated_at.isoformat()}")
        
        if epic.start_date:
            console.print(f"[bold]Start Date:[/bold] {epic.start_date.isoformat()}")
        
        if epic.end_date:
            console.print(f"[bold]End Date:[/bold] {epic.end_date.isoformat()}")
        
        # Related evidence
        if epic.related_evidence_ids:
            console.print(f"\n[bold]Related Evidence:[/bold]")
            for evidence_id in epic.related_evidence_ids:
                console.print(f"  - {evidence_id}")
        
        # Description
        console.print(f"\n[bold]Description:[/bold]")
        console.print(epic.description or "[italic]No description provided[/italic]")
        
        # Tasks
        if with_tasks:
            task_storage = TaskStorage()
            tasks = task_storage.list({"epic_id": epic.id})
            
            if tasks:
                console.print(f"\n[bold]Tasks ({len(tasks)}):[/bold]")
                task_dicts = [task.to_dict() for task in tasks]
                table = create_task_table(task_dicts)
                console.print(table)
            else:
                console.print("\n[italic]No tasks associated with this epic[/italic]")
        
        logger.info(f"Retrieved epic {epic_id}")
    
    except Exception as e:
        print_error(f"Error retrieving epic: {str(e)}")
        logger.exception("Error in epic get command")

@epic_group.command(name="create")
@click.option("--title", prompt="Epic title", help="Epic title")
@click.option("--description", prompt="Description", default="", help="Epic description")
@click.option("--status", default="Open", help="Epic status")
@click.option("--owner", help="Epic owner")
def create_epic(title, description, status, owner):
    """Create a new epic."""
    try:
        # Log command execution
        logger.info(f"Executing epic create command for epic '{title}'")
        
        # Get epic storage
        epic_storage = EpicStorage()
        
        # Create epic data
        epic_data = {
            "title": title,
            "description": description,
            "status": status
        }
        
        if owner:
            epic_data["owner"] = owner
        
        # Create epic
        epic = epic_storage.create(epic_data)
        
        print_success(f"Created epic '{epic.title}' with ID: {epic.id}")
        logger.info(f"Created epic {epic.id}")
    
    except Exception as e:
        print_error(f"Error creating epic: {str(e)}")
        logger.exception("Error in epic create command")

@epic_group.command(name="update")
@click.argument("epic_id")
@click.option("--title", help="Epic title")
@click.option("--description", help="Epic description")
@click.option("--status", help="Epic status")
@click.option("--owner", help="Epic owner")
def update_epic(epic_id, title, description, status, owner):
    """Update an existing epic."""
    try:
        # Log command execution
        logger.info(f"Executing epic update command for epic_id={epic_id}")
        
        # Get epic storage
        epic_storage = EpicStorage()
        
        # Check if epic exists
        existing_epic = epic_storage.get(epic_id)
        if not existing_epic:
            print_error(f"Epic not found: {epic_id}")
            return
        
        # Build update data
        update_data = {}
        if title:
            update_data["title"] = title
        if description:
            update_data["description"] = description
        if status:
            update_data["status"] = status
        if owner:
            update_data["owner"] = owner
        
        if not update_data:
            print_warning("No updates specified.")
            return
        
        # Update epic
        epic = epic_storage.update(epic_id, update_data)
        
        print_success(f"Updated epic '{epic.title}'")
        logger.info(f"Updated epic {epic.id}")
    
    except Exception as e:
        print_error(f"Error updating epic: {str(e)}")
        logger.exception("Error in epic update command")

@epic_group.command(name="delete")
@click.argument("epic_id")
@click.option("--force", is_flag=True, help="Skip confirmation")
def delete_epic(epic_id, force):
    """Delete an epic."""
    try:
        # Log command execution
        logger.info(f"Executing epic delete command for epic_id={epic_id}")
        
        # Get epic storage
        epic_storage = EpicStorage()
        
        # Check if epic exists
        existing_epic = epic_storage.get(epic_id)
        if not existing_epic:
            print_error(f"Epic not found: {epic_id}")
            return
        
        # Get associated tasks
        task_storage = TaskStorage()
        tasks = task_storage.list({"epic_id": epic_id})
        
        # Confirm deletion
        if not force:
            message = f"Are you sure you want to delete epic '{existing_epic.title}'?"
            if tasks:
                message += f" This epic has {len(tasks)} associated tasks."
            
            if not confirm(message, default=False):
                print_info("Deletion cancelled.")
                return
        
        # Delete epic
        success = epic_storage.delete(epic_id)
        
        if success:
            print_success(f"Deleted epic '{existing_epic.title}'")
            logger.info(f"Deleted epic {epic_id}")
        else:
            print_error(f"Failed to delete epic {epic_id}")
    
    except Exception as e:
        print_error(f"Error deleting epic: {str(e)}")
        logger.exception("Error in epic delete command")

# This will be implemented in Phase 3.3
@epic_group.command(name="create-ai")
@click.option("--title", prompt="Epic title", help="Epic title")
@click.option("--description", prompt="Description", default="", help="Epic description")
def create_epic_ai(title, description):
    """Create an epic with AI planning."""
    print_info("AI planning for epics will be implemented in Phase 3.3")
    print_info(f"Would create epic '{title}' with AI planning")

# This will be implemented in Phase 3.3
@epic_group.command(name="context")
@click.argument("epic_id")
@click.option("--answers", help="Path to JSON file with context answers")
def epic_context(epic_id, answers):
    """Provide context answers for an epic."""
    print_info("Epic context feature will be implemented in Phase 3.3")
    print_info(f"Would add context to epic {epic_id}")
    
    if answers:
        print_info(f"Using answers from: {answers}")

# This will be implemented in Phase 3.4
@epic_group.command(name="breakdown")
@click.argument("epic_id")
@click.option("--ai", is_flag=True, help="Use AI for breakdown")
@click.option("--complexity", is_flag=True, help="Include complexity assessment")
def epic_breakdown(epic_id, ai, complexity):
    """Break down an epic into tasks."""
    print_info("Epic breakdown feature will be implemented in Phase 3.4")
    print_info(f"Would break down epic {epic_id} into tasks")
    
    if ai:
        print_info("Using AI for task breakdown")
    
    if complexity:
        print_info("Including complexity assessment")
