"""
Task command group for the Kanban CLI.

This module implements the task-related commands for the Kanban CLI.
"""
import click
from typing import Optional, List

from ..data.storage import TaskStorage
from ..ui.display import (
    console, print_header, print_success, print_error, 
    print_warning, print_info, create_task_table, confirm
)
from ..utils.logging import setup_logging

# Setup logger
logger = setup_logging(name="kanban.cli.tasks")

@click.group(name="task")
def task_group():
    """Manage tasks on the Kanban board."""
    pass

@task_group.command(name="list")
@click.option("--status", help="Filter by status")
@click.option("--epic", help="Filter by epic ID")
@click.option("--title", help="Filter by title (substring match)")
@click.option("--assignee", help="Filter by assignee")
@click.option("--format", type=click.Choice(["table", "json"]), default="table", 
              help="Output format")
def list_tasks(status, epic, title, assignee, format):
    """List tasks with optional filtering."""
    try:
        # Log command execution
        logger.info(f"Executing task list command with filters: status={status}, epic={epic}, title={title}, assignee={assignee}")
        
        # Get tasks from storage
        storage = TaskStorage()
        
        # Build filters
        filters = {}
        if status:
            filters["status"] = status
        if epic:
            filters["epic_id"] = epic
        if title:
            filters["title"] = title
        if assignee:
            filters["assignee"] = assignee
        
        # Get filtered tasks
        tasks = storage.list(filters)
        
        if not tasks:
            print_warning("No tasks found matching the criteria.")
            return
        
        # Display tasks
        print_header(f"Tasks ({len(tasks)})", "Filtered by provided criteria" if filters else "All tasks")
        
        if format == "json":
            import json
            console.print_json(json.dumps([task.to_dict() for task in tasks], indent=2))
        else:
            # Convert tasks to dicts for table display
            task_dicts = [task.to_dict() for task in tasks]
            table = create_task_table(task_dicts)
            console.print(table)
            
        logger.info(f"Listed {len(tasks)} tasks")
    
    except Exception as e:
        print_error(f"Error listing tasks: {str(e)}")
        logger.exception("Error in task list command")

@task_group.command(name="get")
@click.argument("task_id")
def get_task(task_id):
    """Get detailed information about a specific task."""
    try:
        # Log command execution
        logger.info(f"Executing task get command for task_id={task_id}")
        
        # Get task from storage
        storage = TaskStorage()
        task = storage.get(task_id)
        
        if not task:
            print_error(f"Task not found: {task_id}")
            return
        
        # Display task details
        print_header(f"Task: {task.title}", f"ID: {task.id}")
        
        # Basic info
        console.print(f"[bold]Status:[/bold] {task.status.value}")
        console.print(f"[bold]Priority:[/bold] {task.priority.value}")
        
        if task.assignee:
            console.print(f"[bold]Assignee:[/bold] {task.assignee}")
        
        if task.complexity:
            console.print(f"[bold]Complexity:[/bold] {task.complexity}/5")
        
        if task.epic_id:
            console.print(f"[bold]Epic:[/bold] {task.epic_id}")
        
        # Tags
        if task.tags:
            console.print(f"[bold]Tags:[/bold] {', '.join(task.tags)}")
        
        # Dates
        console.print(f"[bold]Created:[/bold] {task.created_at.isoformat()}")
        console.print(f"[bold]Updated:[/bold] {task.updated_at.isoformat()}")
        
        if task.due_date:
            console.print(f"[bold]Due Date:[/bold] {task.due_date.isoformat()}")
        
        # Related evidence
        if task.related_evidence_ids:
            console.print(f"\n[bold]Related Evidence:[/bold]")
            for evidence_id in task.related_evidence_ids:
                console.print(f"  - {evidence_id}")
        
        # Description
        console.print(f"\n[bold]Description:[/bold]")
        console.print(task.description or "[italic]No description provided[/italic]")
        
        logger.info(f"Retrieved task {task_id}")
    
    except Exception as e:
        print_error(f"Error retrieving task: {str(e)}")
        logger.exception("Error in task get command")

@task_group.command(name="add")
@click.option("--title", prompt="Task title", help="Task title")
@click.option("--description", prompt="Description", default="", help="Task description")
@click.option("--status", default="Backlog",
              type=click.Choice(["Backlog", "Ready", "In Progress", "Review", "Done"]),
              help="Task status")
@click.option("--priority", default="Medium",
              type=click.Choice(["Low", "Medium", "High", "Critical"]),
              help="Task priority")
@click.option("--epic", help="Parent epic ID")
@click.option("--assignee", help="Person assigned to this task")
@click.option("--due-date", help="Due date in YYYY-MM-DD format")
@click.option("--complexity", type=click.IntRange(1, 5), default=1,
              help="Task complexity (1-5)")
@click.option("--tags", help="Comma-separated list of tags")
def add_task(title, description, status, priority, epic, assignee,
            due_date, complexity, tags):
    """Add a new task to the board."""
    try:
        # Log command execution
        logger.info(f"Executing task add command for task '{title}'")

        # Get task storage
        storage = TaskStorage()

        # Create task data
        task_data = {
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "complexity": complexity
        }

        # Add optional fields if provided
        if epic:
            task_data["epic_id"] = epic
        if assignee:
            task_data["assignee"] = assignee
        if due_date:
            from datetime import datetime
            try:
                task_data["due_date"] = datetime.fromisoformat(due_date)
            except ValueError:
                print_error(f"Invalid date format: {due_date}. Use YYYY-MM-DD.")
                return

        # Process tags
        if tags:
            task_data["tags"] = [tag.strip() for tag in tags.split(",")]

        # Attempt to create task
        task = storage.create(task_data)

        # Show success message
        print_success(f"Created task '{task.title}' with ID: {task.id}")

        # Show additional details
        print_info(f"Status: {task.status.value}")
        print_info(f"Priority: {task.priority.value}")
        if task.epic_id:
            print_info(f"Epic: {task.epic_id}")
        if task.assignee:
            print_info(f"Assignee: {task.assignee}")

        logger.info(f"Created task {task.id}")

    except Exception as e:
        print_error(f"Error creating task: {str(e)}")
        logger.exception("Error in task add command")

@task_group.command(name="update")
@click.argument("task_id")
@click.option("--title", help="Task title")
@click.option("--description", help="Task description")
@click.option("--status",
              type=click.Choice(["Backlog", "Ready", "In Progress", "Review", "Done"]),
              help="Task status")
@click.option("--priority",
              type=click.Choice(["Low", "Medium", "High", "Critical"]),
              help="Task priority")
@click.option("--epic", help="Parent epic ID")
@click.option("--assignee", help="Person assigned to this task")
@click.option("--due-date", help="Due date in YYYY-MM-DD format")
@click.option("--complexity", type=click.IntRange(1, 5), help="Task complexity (1-5)")
@click.option("--tags", help="Comma-separated list of tags")
@click.option("--add-tags", help="Comma-separated list of tags to add")
@click.option("--remove-tags", help="Comma-separated list of tags to remove")
def update_task(task_id, title, description, status, priority, epic, assignee,
               due_date, complexity, tags, add_tags, remove_tags):
    """Update an existing task."""
    try:
        # Log command execution
        logger.info(f"Executing task update command for task_id={task_id}")

        # Get task storage
        storage = TaskStorage()

        # Check if task exists
        existing_task = storage.get(task_id)
        if not existing_task:
            print_error(f"Task not found: {task_id}")
            return

        # Build update data
        update_data = {}
        if title:
            update_data["title"] = title
        if description:
            update_data["description"] = description
        if status:
            update_data["status"] = status
        if priority:
            update_data["priority"] = priority
        if epic:
            update_data["epic_id"] = epic
        if assignee:
            update_data["assignee"] = assignee
        if complexity:
            update_data["complexity"] = complexity

        # Process due date
        if due_date:
            from datetime import datetime
            try:
                update_data["due_date"] = datetime.fromisoformat(due_date)
            except ValueError:
                print_error(f"Invalid date format: {due_date}. Use YYYY-MM-DD.")
                return

        # Process tags replacement
        if tags:
            update_data["tags"] = [tag.strip() for tag in tags.split(",")]

        # Process tag additions/removals
        current_tags = existing_task.tags.copy() if existing_task.tags else []
        if add_tags:
            new_tags = [tag.strip() for tag in add_tags.split(",")]
            for tag in new_tags:
                if tag and tag not in current_tags:
                    current_tags.append(tag)

            if "tags" not in update_data:  # Don't override a full tag replacement
                update_data["tags"] = current_tags

        if remove_tags:
            remove_list = [tag.strip() for tag in remove_tags.split(",")]
            remaining_tags = [tag for tag in current_tags if tag not in remove_list]

            if "tags" not in update_data:  # Don't override a full tag replacement
                update_data["tags"] = remaining_tags

        if not update_data:
            print_warning("No updates specified.")
            return

        # Update task
        task = storage.update(task_id, update_data)

        # Show success message
        print_success(f"Updated task '{task.title}'")

        # Show updated fields
        if "title" in update_data:
            print_info(f"Title: {task.title}")
        if "status" in update_data:
            print_info(f"Status: {task.status.value}")
        if "priority" in update_data:
            print_info(f"Priority: {task.priority.value}")
        if "epic_id" in update_data:
            print_info(f"Epic: {task.epic_id}")
        if "assignee" in update_data:
            print_info(f"Assignee: {task.assignee}")
        if "complexity" in update_data:
            print_info(f"Complexity: {task.complexity}/5")
        if "tags" in update_data:
            print_info(f"Tags: {', '.join(task.tags)}")

        logger.info(f"Updated task {task.id}")

    except Exception as e:
        print_error(f"Error updating task: {str(e)}")
        logger.exception("Error in task update command")

@task_group.command(name="delete")
@click.argument("task_id")
@click.option("--force", is_flag=True, help="Skip confirmation")
def delete_task(task_id, force):
    """Delete a task from the board."""
    try:
        # Log command execution
        logger.info(f"Executing task delete command for task_id={task_id}")

        # Get task storage
        storage = TaskStorage()

        # Check if task exists
        existing_task = storage.get(task_id)
        if not existing_task:
            print_error(f"Task not found: {task_id}")
            return

        # Confirm deletion
        if not force:
            if not confirm(f"Are you sure you want to delete task '{existing_task.title}'?", default=False):
                print_info("Deletion cancelled.")
                return

        # Delete task
        success = storage.delete(task_id)

        if success:
            print_success(f"Deleted task '{existing_task.title}'")
            logger.info(f"Deleted task {task_id}")
        else:
            print_error(f"Failed to delete task {task_id}")

    except Exception as e:
        print_error(f"Error deleting task: {str(e)}")
        logger.exception("Error in task delete command")
