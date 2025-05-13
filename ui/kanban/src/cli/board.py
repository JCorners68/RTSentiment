"""
Board command group for the Kanban CLI.

This module implements the board-related commands for the Kanban CLI.
"""
import click
from typing import Optional, List, Dict, Any

from ..data.storage import BoardStorage, TaskStorage
from ..ui.display import (
    console, print_header, print_success, print_error, 
    print_warning, print_info, create_task_table, print_panel
)
from ..utils.logging import setup_logging

# Setup logger
logger = setup_logging(name="kanban.cli.board")

@click.group(name="board")
def board_group():
    """Manage and view the Kanban board."""
    pass

@board_group.command(name="show")
@click.option("--compact", is_flag=True, help="Use compact display mode")
@click.option("--detailed", is_flag=True, help="Show more task details")
@click.option("--filter", help="Filter tasks by substring match in title or description")
@click.option("--by-priority", is_flag=True, help="Group tasks by priority instead of status")
def show_board(compact, detailed, filter, by_priority):
    """Show the current Kanban board with tasks grouped by status or priority."""
    try:
        # Log command execution
        logger.info("Executing board show command")
        
        # Get board configuration and tasks
        board_storage = BoardStorage()
        task_storage = TaskStorage()
        
        # Get the first board (or create default if none exists)
        boards = board_storage.list()
        if not boards:
            logger.info("No board found, creating default board")
            board = board_storage.create({
                "name": "Default Board",
                "columns": ["Backlog", "Ready", "In Progress", "Review", "Done"]
            })
        else:
            board = boards[0]
        
        # Get all tasks
        filters = {}
        if filter:
            # Apply text filter to both title and description
            filters["title"] = filter
            # The storage layer will handle the OR logic
        
        tasks = task_storage.list(filters)
        
        # Group tasks by status or priority
        if by_priority:
            # Group by priority
            priorities = ["Critical", "High", "Medium", "Low"]
            tasks_by_group = {priority: [] for priority in priorities}
            group_name = "Priority"
            
            for task in tasks:
                priority = task.priority.value
                tasks_by_group[priority].append(task.to_dict())
                
            # Style mapping for priorities
            style_map = {
                "Critical": "error",
                "High": "warning",
                "Medium": "primary",
                "Low": "info"
            }
        else:
            # Group by status (default)
            tasks_by_group = {column: [] for column in board.columns}
            group_name = "Status"
            
            for task in tasks:
                status = task.status.value
                if status in tasks_by_group:
                    tasks_by_group[status].append(task.to_dict())
                else:
                    # Handle tasks with statuses not in board columns
                    if "Other" not in tasks_by_group:
                        tasks_by_group["Other"] = []
                    tasks_by_group["Other"].append(task.to_dict())
            
            # Style mapping for statuses
            style_map = {
                column: f"task.{column.lower().replace(' ', '_')}" 
                for column in board.columns
            }
            style_map["Other"] = "primary"
        
        # Display board
        board_title = f"Kanban Board: {board.name}"
        if filter:
            board_title += f" (Filtered: '{filter}')"
        if by_priority:
            board_title += " (Grouped by Priority)"
            
        print_header(board_title, f"Last updated: {board.updated_at.isoformat()}")
        
        if not tasks:
            print_warning("No tasks found on the board.")
            return
        
        # Determine which columns to display based on view mode
        if detailed:
            display_columns = ["ID", "Title", "Priority", "Assignee", "Complexity"]
        elif compact:
            display_columns = ["ID", "Title"]
        else:
            display_columns = ["ID", "Title", "Priority"]
        
        # Add epic_id to columns if in detailed mode
        if detailed:
            display_columns.append("Epic")
        
        # Print groups (columns or priorities)
        for group, group_tasks in tasks_by_group.items():
            # Skip empty groups in compact mode
            if compact and not group_tasks:
                continue
                
            style = style_map.get(group, "primary")
            
            print_panel(
                f"[bold]{group}[/bold] ({len(group_tasks)})",
                style=style
            )
            
            if group_tasks:
                # Sort tasks by priority within the group if not grouped by priority
                if not by_priority:
                    group_tasks.sort(key=lambda x: priority_sort_key(x.get('priority', 'Medium')), reverse=True)
                
                # Show tasks in this group
                table = create_task_table(group_tasks, columns=display_columns, compact=compact)
                console.print(table)
            else:
                console.print("[italic]No tasks in this group[/italic]")
            
            console.print("")  # Empty line between groups
        
        # Display help text for task movement
        console.print("[italic]Tip: Use 'kanban board move <task-id> <column>' to move tasks between columns[/italic]\n")
        
        logger.info(f"Displayed board with {len(tasks)} tasks")
    
    except Exception as e:
        print_error(f"Error displaying board: {str(e)}")
        logger.exception("Error in board show command")


def priority_sort_key(priority):
    """Helper function to sort tasks by priority."""
    priority_map = {
        "Critical": 3,
        "High": 2,
        "Medium": 1,
        "Low": 0
    }
    return priority_map.get(priority, 0)

@board_group.command(name="create")
@click.option("--name", prompt="Board name", help="Board name")
@click.option("--columns", help="Comma-separated list of column names")
def create_board(name, columns):
    """Create a new Kanban board configuration."""
    try:
        # Log command execution
        logger.info(f"Executing board create command for board '{name}'")
        
        # Get board storage
        board_storage = BoardStorage()
        
        # Process columns
        column_list = None
        if columns:
            column_list = [col.strip() for col in columns.split(",")]
        
        # Create board
        board = board_storage.create({
            "name": name,
            "columns": column_list
        })
        
        print_success(f"Created board '{board.name}' with columns: {', '.join(board.columns)}")
        logger.info(f"Created board {board.id}")
    
    except Exception as e:
        print_error(f"Error creating board: {str(e)}")
        logger.exception("Error in board create command")

@board_group.command(name="move")
@click.argument("task_id")
@click.argument("column")
@click.option("--force", is_flag=True, help="Skip validation of column name")
def move_task(task_id, column, force):
    """Move a task to a different column on the board."""
    try:
        # Log command execution
        logger.info(f"Executing board move command for task_id={task_id} to column={column}")
        
        # Get board and task
        board_storage = BoardStorage()
        task_storage = TaskStorage()
        
        # Get the task
        task = task_storage.get(task_id)
        if not task:
            print_error(f"Task not found: {task_id}")
            return
        
        # Get the first board
        boards = board_storage.list()
        if not boards:
            print_error("No board found. Please create a board first.")
            return
        
        board = boards[0]
        
        # Check if the column exists on the board
        if not force and column not in board.columns:
            print_error(f"Column '{column}' not found on board '{board.name}'")
            print_info(f"Available columns: {', '.join(board.columns)}")
            print_info("Use --force to skip this validation")
            return
        
        # Check if the task is already in this column
        if task.status.value == column:
            print_warning(f"Task {task_id} is already in the '{column}' column")
            return
        
        # Update the task status
        updated_task = task_storage.update(task_id, {"status": column})
        
        if updated_task:
            print_success(f"Moved task {task_id} from '{task.status.value}' to '{column}'")
            
            # Show brief task details
            console.print(f"[bold]Task:[/bold] {updated_task.title}")
            console.print(f"[bold]Current Status:[/bold] {updated_task.status.value}")
            console.print(f"[bold]Priority:[/bold] {updated_task.priority.value}")
            
            logger.info(f"Moved task {task_id} to column {column}")
        else:
            print_error(f"Failed to move task {task_id}")
    
    except Exception as e:
        print_error(f"Error moving task: {str(e)}")
        logger.exception("Error in board move command")
    
@board_group.command(name="list")
def list_boards():
    """List all available boards."""
    try:
        # Log command execution
        logger.info("Executing board list command")
        
        # Get boards
        board_storage = BoardStorage()
        boards = board_storage.list()
        
        if not boards:
            print_warning("No boards found.")
            return
        
        # Display boards
        print_header(f"Kanban Boards ({len(boards)})")
        
        for i, board in enumerate(boards):
            console.print(f"[bold]{i+1}. {board.name}[/bold]")
            console.print(f"   ID: {board.id}")
            console.print(f"   Columns: {', '.join(board.columns)}")
            console.print(f"   Created: {board.created_at.isoformat()}")
            console.print(f"   Updated: {board.updated_at.isoformat()}")
            console.print("")
        
        logger.info(f"Listed {len(boards)} boards")
    
    except Exception as e:
        print_error(f"Error listing boards: {str(e)}")
        logger.exception("Error in board list command")


@board_group.command(name="view")
@click.option("--mode", type=click.Choice(["list", "kanban", "compact"]), default="kanban", 
              help="Display mode (list, kanban, or compact)")
@click.option("--sort-by", type=click.Choice(["priority", "status", "created", "updated"]), 
              default="status", help="Sort order for tasks")
def view_board(mode, sort_by):
    """View the board in different display modes."""
    try:
        # Log command execution
        logger.info(f"Executing board view command with mode={mode}")
        
        # Get board and tasks
        board_storage = BoardStorage()
        task_storage = TaskStorage()
        
        # Get all tasks
        tasks = task_storage.list()
        
        # Get the first board
        boards = board_storage.list()
        if not boards:
            print_error("No board found. Please create a board first.")
            return
        
        board = boards[0]
        
        # Display board header
        print_header(f"Kanban Board: {board.name} ({mode.capitalize()} View)", 
                    f"Sorted by: {sort_by}")
        
        if not tasks:
            print_warning("No tasks found on the board.")
            return
        
        # Convert tasks to dictionaries
        task_dicts = [task.to_dict() for task in tasks]
        
        # Sort tasks based on sort_by parameter
        if sort_by == "priority":
            task_dicts.sort(key=lambda x: priority_sort_key(x.get('priority')), reverse=True)
        elif sort_by == "created":
            task_dicts.sort(key=lambda x: x.get('created_at'))
        elif sort_by == "updated":
            task_dicts.sort(key=lambda x: x.get('updated_at'), reverse=True)
        elif sort_by == "status":
            # Create a map of status to position for sorting
            status_position = {status: i for i, status in enumerate(board.columns)}
            task_dicts.sort(key=lambda x: status_position.get(x.get('status'), 999))
        
        # Display based on mode
        if mode == "list":
            # List view - show all tasks in a single table
            table = create_task_table(task_dicts, 
                                     columns=["ID", "Title", "Status", "Priority", "Assignee"])
            console.print(table)
            
        elif mode == "compact":
            # Compact view - minimalist display
            for task in task_dicts:
                status_style = f"task.{task.get('status', '').lower().replace(' ', '_')}"
                title = task.get('title', 'Untitled')
                task_id = task.get('id', 'NO-ID')
                
                console.print(
                    f"[{status_style}]\u25cf[/{status_style}] "
                    f"[bold]{task_id}[/bold] - {title}"
                )
            
        else:  # kanban view (default)
            # Group tasks by status
            tasks_by_status = {}
            for column in board.columns:
                tasks_by_status[column] = []
            
            for task in task_dicts:
                status = task.get('status')
                if status in tasks_by_status:
                    tasks_by_status[status].append(task)
            
            # Display each column
            for column in board.columns:
                column_tasks = tasks_by_status.get(column, [])
                style = f"task.{column.lower().replace(' ', '_')}"
                
                console.print(f"[{style}][bold]{column}[/bold] ({len(column_tasks)})[/{style}]")
                
                if column_tasks:
                    # Sort tasks by priority within each column
                    column_tasks.sort(
                        key=lambda x: priority_sort_key(x.get('priority')), 
                        reverse=True
                    )
                    
                    # Display tasks in compact format
                    for task in column_tasks:
                        priority = task.get('priority', 'Medium')
                        priority_style = "bold red" if priority in ["Critical", "High"] else ""
                        
                        console.print(
                            f"  [{priority_style}]{task.get('id')}[/{priority_style}] "
                            f"{task.get('title')}"
                        )
                else:
                    console.print("  [italic]No tasks[/italic]")
                
                console.print("")  # Empty line between columns
        
        logger.info(f"Displayed board in {mode} mode with {len(tasks)} tasks")
        
    except Exception as e:
        print_error(f"Error viewing board: {str(e)}")
        logger.exception("Error in board view command")
