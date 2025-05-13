"""
Evidence command group for the Kanban CLI.

This module implements the evidence-related commands for the Kanban CLI,
supporting the Evidence Management System which is a priority feature.
"""
import click
from typing import Optional, List, Dict, Any, Tuple
import json
from datetime import datetime
import os
import sys
from pathlib import Path
import tempfile
import shutil

from ..data.storage import TaskStorage, EpicStorage
from ..data.evidence_storage import EvidenceStorage
from ..models.evidence_schema import EvidenceCategory, EvidenceRelevance, EvidenceSchema
from ..models.evidence_validation import validate_evidence, validate_attachment
from ..utils.logging import setup_logging
from ..utils.exceptions import StorageError, ValidationError, EntityNotFoundError, AttachmentError
from ..ui.display import (
    console, print_header, print_success, print_error, print_warning,
    print_info, create_evidence_table, print_panel, confirm, print_evidence_details,
    create_progress_context
)

# Setup logger
logger = setup_logging(name="kanban.cli.evidence")

# Initialize the evidence storage
evidence_storage = EvidenceStorage()

@click.group(name="evidence")
def evidence_group():
    """
    Manage evidence items in the Evidence Management System.
    
    The Evidence Management System allows storing, categorizing, and 
    searching various types of evidence related to tasks and epics.
    """
    pass

@evidence_group.command(name="list")
@click.option("--category", help="Filter by category")
@click.option("--tag", help="Filter by tag")
@click.option("--relevance", help="Filter by relevance score")
@click.option("--epic", help="Filter by related epic ID")
@click.option("--task", help="Filter by related task ID")
@click.option("--project", help="Filter by project ID")
@click.option("--source", help="Filter by source")
@click.option("--date-from", help="Filter by date collected (format: YYYY-MM-DD)")
@click.option("--date-to", help="Filter by date collected (format: YYYY-MM-DD)")
@click.option("--sort-by", type=click.Choice(["title", "category", "relevance_score",
                                             "date_collected", "created_at", "updated_at"]),
              default="updated_at", help="Field to sort by")
@click.option("--sort-order", type=click.Choice(["asc", "desc"]), default="desc",
              help="Sort order (ascending or descending)")
@click.option("--limit", type=int, default=None, help="Maximum number of items to return")
@click.option("--offset", type=int, default=0, help="Number of items to skip")
@click.option("--format", type=click.Choice(["table", "json", "csv"]), default="table",
              help="Output format")
@click.option("--columns", help="Comma-separated list of columns to display in table format")
def list_evidence(category, tag, relevance, epic, task, project, source,
                 date_from, date_to, sort_by, sort_order, limit, offset, format, columns):
    """List evidence items with optional filtering and sorting."""
    try:
        # Log command execution
        logger.info(f"Executing evidence list command with filters")

        # Prepare filters dictionary
        filters = {}
        if category:
            filters["category"] = category
        if tag:
            filters["tags"] = [tag.strip()]
        if relevance:
            filters["relevance_score"] = relevance
        if epic:
            filters["epic_id"] = epic
        if task:
            filters["task_id"] = task
        if project:
            filters["project_id"] = project
        if source:
            filters["source"] = source

        # Date filters require conversion to datetime
        if date_from:
            try:
                date_obj = datetime.fromisoformat(date_from)
                filters["date_from"] = date_obj
            except ValueError:
                print_warning(f"Invalid date format for date-from: {date_from}. Using ISO format YYYY-MM-DD")

        if date_to:
            try:
                date_obj = datetime.fromisoformat(date_to)
                filters["date_to"] = date_obj
            except ValueError:
                print_warning(f"Invalid date format for date-to: {date_to}. Using ISO format YYYY-MM-DD")

        # Custom columns for table display
        display_columns = None
        if columns:
            display_columns = [col.strip() for col in columns.split(",")]

        # Get evidence items with progress indicator
        with create_progress_context() as progress:
            task_id = progress.add_task("Listing evidence...", total=1)

            try:
                # Search for evidence items
                evidence_items = evidence_storage.list(
                    filters=filters,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    limit=limit,
                    offset=offset
                )
                progress.update(task_id, completed=1)

            except ValidationError as ve:
                print_error(f"Filter validation error: {str(ve)}")
                if hasattr(ve, "validation_errors") and ve.validation_errors:
                    for error in ve.validation_errors:
                        print_error(f"- {error}")
                return

            except StorageError as se:
                print_error(f"Storage error: {str(se)}")
                return

        # Get evidence items as dictionaries for display
        evidence_dicts = [e.to_dict() for e in evidence_items]

        if not evidence_dicts:
            print_warning("No evidence items found matching the criteria.")
            return

        # Display evidence items
        if filters:
            print_header(f"Evidence Items ({len(evidence_dicts)}) - Filtered")
            # Display applied filters
            filter_str = ", ".join([f"{k}={v}" for k, v in filters.items() if v])
            print_info(f"Applied filters: {filter_str}")
        else:
            print_header(f"Evidence Items ({len(evidence_dicts)})")

        # Format output based on user preference
        if format == "json":
            console.print_json(json.dumps(evidence_dicts, indent=2, default=str))
        elif format == "csv":
            # Create simple CSV output
            if not display_columns:
                display_columns = ["id", "title", "category", "relevance_score", "tags", "created_at"]

            # Print header
            header = ",".join(display_columns)
            console.print(header)

            # Print rows
            for evidence in evidence_dicts:
                row = []
                for col in display_columns:
                    if col == "tags" and "tags" in evidence:
                        tags_str = ";".join(evidence.get("tags", []))
                        row.append(f'"{tags_str}"')  # Quote tag lists
                    elif col in evidence:
                        val = str(evidence[col]).replace('"', '""')  # Escape quotes for CSV
                        row.append(f'"{val}"')
                    else:
                        row.append('""')
                console.print(",".join(row))
        else:
            # Display evidence items in a table
            table = create_evidence_table(evidence_dicts, columns=display_columns)
            console.print(table)

        logger.info(f"Listed {len(evidence_dicts)} evidence items")

    except Exception as e:
        print_error(f"Error listing evidence: {str(e)}")
        logger.exception("Error in evidence list command")

@evidence_group.command(name="get")
@click.argument("evidence_id")
@click.option("--format", type=click.Choice(["console", "json"]), default="console",
              help="Output format")
@click.option("--with-related", is_flag=True, help="Show related evidence items")
@click.option("--with-attachments", is_flag=True, help="Show detailed attachment information")
def get_evidence(evidence_id, format, with_related, with_attachments):
    """Get detailed information about a specific evidence item."""
    try:
        # Log command execution
        logger.info(f"Executing evidence get command for evidence_id={evidence_id}")

        # Get evidence with progress indicator
        with create_progress_context() as progress:
            task_id = progress.add_task("Retrieving evidence...", total=1)

            try:
                # Get evidence item
                evidence = evidence_storage.get(evidence_id)
                progress.update(task_id, completed=1)

            except EntityNotFoundError:
                print_error(f"Evidence not found: {evidence_id}")
                return

            except StorageError as se:
                print_error(f"Storage error: {str(se)}")
                return

        if not evidence:
            print_error(f"Evidence not found: {evidence_id}")
            return

        # Get related evidence if requested
        related_evidence = []
        if with_related and evidence.related_evidence_ids:
            with create_progress_context() as progress:
                task_id = progress.add_task("Retrieving related evidence...", total=1)
                try:
                    related_evidence = evidence_storage.get_related_evidence("evidence", evidence_id)
                    progress.update(task_id, completed=1)
                except Exception as e:
                    logger.error(f"Failed to get related evidence: {str(e)}")
                    print_warning("Failed to retrieve related evidence items.")

        # Format output based on user preference
        if format == "json":
            output = evidence.to_dict()

            # Add related evidence if requested
            if with_related and related_evidence:
                output["related_evidence_details"] = [rel.to_dict() for rel in related_evidence]

            # Add attachment details if requested
            if with_attachments and evidence.attachments:
                for i, att in enumerate(output["attachments"]):
                    # Add preview summary if available
                    if att.get("content_preview"):
                        preview = att["content_preview"]
                        # Truncate preview if very long
                        if len(preview) > 500:
                            att["content_preview_summary"] = preview[:500] + "..."

            console.print_json(json.dumps(output, indent=2, default=str))
        else:
            # Display evidence details
            print_evidence_details(evidence.to_dict())

            # Show related evidence if requested
            if with_related and related_evidence:
                print_header(f"Related Evidence ({len(related_evidence)})")
                table = create_evidence_table([rel.to_dict() for rel in related_evidence])
                console.print(table)

            # Show detailed attachment info if requested
            if with_attachments and evidence.attachments:
                print_header(f"Attachments ({len(evidence.attachments)})")
                for i, att in enumerate(evidence.attachments):
                    att_dict = att.to_dict()
                    console.print(f"\n[bold]Attachment {i+1}:[/bold] {att_dict['file_name']}")
                    console.print(f"ID: {att_dict['id']}")
                    console.print(f"Type: {att_dict['file_type']}")
                    console.print(f"Size: {att_dict['file_size']} bytes")

                    if att_dict.get('content_preview'):
                        preview = att_dict['content_preview']
                        if len(preview) > 200:
                            preview = preview[:200] + "..."
                        console.print(f"\nPreview:")
                        print_panel(preview, style="info")

        logger.info(f"Successfully retrieved evidence {evidence_id}")

    except Exception as e:
        print_error(f"Error retrieving evidence: {str(e)}")
        logger.exception("Error in evidence get command")

@evidence_group.command(name="add")
@click.option("--title", prompt="Evidence title", help="Evidence title")
@click.option("--description", prompt="Description", help="Evidence description")
@click.option("--category", type=click.Choice([c.value for c in EvidenceCategory]),
              default="Other", help="Evidence category")
@click.option("--subcategory", help="Optional subcategory for more specific categorization")
@click.option("--relevance", type=click.Choice([r.value for r in EvidenceRelevance]),
              default="Medium", help="Relevance score")
@click.option("--tags", help="Comma-separated list of tags")
@click.option("--source", help="Source of the evidence")
@click.option("--epic", help="Related epic ID")
@click.option("--task", help="Related task ID")
@click.option("--attachment", "attachments", multiple=True,
              type=click.Path(exists=True, file_okay=True, dir_okay=False),
              help="Path to file to attach (can be specified multiple times)")
@click.option("--project", help="Project ID this evidence belongs to")
@click.option("--interactive", is_flag=True, help="Use interactive mode with more detailed prompts")
@click.option("--metadata", help="JSON string with metadata key-value pairs")
def add_evidence(title, description, category, subcategory, relevance, tags, source,
                epic, task, attachments, project, interactive, metadata):
    """Add a new evidence item with optional attachments."""
    try:
        # Log command execution
        logger.info(f"Executing evidence add command for '{title}'")

        # Interactive mode for more detailed evidence entry
        if interactive:
            return _interactive_add_evidence()

        # Prepare evidence data
        evidence_data = {
            "title": title,
            "description": description,
            "category": category,
            "relevance_score": relevance,
            "source": source or "",
            "project_id": project,
            "epic_id": epic,
            "task_id": task
        }

        if subcategory:
            evidence_data["subcategory"] = subcategory

        # Parse tags
        if tags:
            evidence_data["tags"] = [tag.strip() for tag in tags.split(",")]

        # Parse metadata if provided
        if metadata:
            try:
                evidence_data["metadata"] = json.loads(metadata)
            except json.JSONDecodeError:
                print_error("Invalid JSON format for metadata. Using empty metadata.")
                evidence_data["metadata"] = {}

        # Display progress spinner for evidence creation
        with create_progress_context() as progress:
            task_id = progress.add_task("Creating evidence...", total=1)

            try:
                # Validate the evidence data
                is_valid, errors = validate_evidence(evidence_data)
                if not is_valid:
                    for error in errors:
                        print_error(error)
                    return

                # Create evidence
                new_evidence = evidence_storage.create(evidence_data, list(attachments) if attachments else None)
                progress.update(task_id, completed=1)

            except ValidationError as ve:
                print_error(f"Validation error: {str(ve)}")
                if hasattr(ve, "validation_errors") and ve.validation_errors:
                    for error in ve.validation_errors:
                        print_error(f"- {error}")
                return

            except AttachmentError as ae:
                print_error(f"Attachment error: {str(ae)}")
                return

            except StorageError as se:
                print_error(f"Storage error: {str(se)}")
                return

        # Display success message and evidence details
        print_success(f"Evidence created successfully with ID: {new_evidence.id}")
        print_evidence_details(new_evidence.to_dict())

        logger.info(f"Successfully created evidence with ID: {new_evidence.id}")

    except Exception as e:
        print_error(f"Error adding evidence: {str(e)}")
        logger.exception("Error in evidence add command")

def _interactive_add_evidence():
    """Interactive workflow for adding evidence with detailed prompts."""
    print_header("Interactive Evidence Creation")
    print_info("You'll be guided through creating a detailed evidence item.")

    try:
        # Basic information
        title = click.prompt("Evidence title")
        description = click.prompt("Description (can be multi-line, press Enter twice to finish)")

        # Category selection with list
        categories = [c.value for c in EvidenceCategory]
        for i, cat in enumerate(categories, 1):
            console.print(f"{i}. {cat}")

        category_idx = click.prompt("Select category number", type=int, default=9)  # Other is usually last
        if 1 <= category_idx <= len(categories):
            category = categories[category_idx - 1]
        else:
            category = "Other"

        subcategory = click.prompt("Subcategory (optional)", default="")

        # Relevance selection
        relevances = [r.value for r in EvidenceRelevance]
        for i, rel in enumerate(relevances, 1):
            console.print(f"{i}. {rel}")

        relevance_idx = click.prompt("Select relevance number", type=int, default=2)  # Medium
        if 1 <= relevance_idx <= len(relevances):
            relevance = relevances[relevance_idx - 1]
        else:
            relevance = "Medium"

        # Additional metadata
        source = click.prompt("Source of evidence", default="")
        tags_input = click.prompt("Tags (comma-separated)", default="")
        tags = [tag.strip() for tag in tags_input.split(",")] if tags_input else []

        # Related items
        project_id = click.prompt("Project ID (optional)", default="")
        epic_id = click.prompt("Epic ID (optional)", default="")
        task_id = click.prompt("Task ID (optional)", default="")

        # Prepare evidence data
        evidence_data = {
            "title": title,
            "description": description,
            "category": category,
            "subcategory": subcategory,
            "relevance_score": relevance,
            "source": source,
            "tags": tags,
            "project_id": project_id or None,
            "epic_id": epic_id or None,
            "task_id": task_id or None,
        }

        # Check for attachments
        attachments = []
        while click.confirm("Would you like to add an attachment?", default=False):
            # Create a file browser dialog would be ideal here, but we'll use prompt for CLI
            file_path = click.prompt("Enter the path to the file")

            if not os.path.exists(file_path):
                print_error("File not found. Please try again.")
                continue

            description = click.prompt("Description for this attachment", default="")
            attachments.append(file_path)
            print_success(f"Added attachment: {os.path.basename(file_path)}")

        # Display final preview
        print_header("Evidence Preview")
        for key, value in evidence_data.items():
            if value and value != []:  # Skip empty values
                console.print(f"[bold]{key}:[/bold] {value}")

        if attachments:
            console.print(f"[bold]Attachments:[/bold] {len(attachments)} files")

        # Confirm creation
        if not click.confirm("Create this evidence item?", default=True):
            print_info("Evidence creation cancelled.")
            return

        # Create evidence
        with create_progress_context() as progress:
            task_id = progress.add_task("Creating evidence...", total=1)

            try:
                # Validate and create
                is_valid, errors = validate_evidence(evidence_data)
                if not is_valid:
                    for error in errors:
                        print_error(error)
                    return

                new_evidence = evidence_storage.create(evidence_data, attachments if attachments else None)
                progress.update(task_id, completed=1)

                # Display success and details
                print_success(f"Evidence created successfully with ID: {new_evidence.id}")
                print_evidence_details(new_evidence.to_dict())

                logger.info(f"Successfully created evidence with ID: {new_evidence.id} using interactive mode")
                return

            except ValidationError as ve:
                print_error(f"Validation error: {str(ve)}")
                if hasattr(ve, "validation_errors") and ve.validation_errors:
                    for error in ve.validation_errors:
                        print_error(f"- {error}")
                return

            except AttachmentError as ae:
                print_error(f"Attachment error: {str(ae)}")
                return

            except StorageError as se:
                print_error(f"Storage error: {str(se)}")
                return

    except Exception as e:
        print_error(f"Error in interactive evidence creation: {str(e)}")
        logger.exception("Error in interactive evidence creation")

@evidence_group.command(name="categorize")
@click.argument("evidence_id")
@click.argument("category", type=click.Choice([c.value for c in EvidenceCategory]))
@click.option("--subcategory", help="Optional subcategory")
@click.option("--force", is_flag=True, help="Skip confirmation")
def categorize_evidence(evidence_id, category, subcategory, force):
    """Update the category and optional subcategory of an evidence item."""
    try:
        # Log command execution
        logger.info(f"Executing evidence categorize command for evidence_id={evidence_id}")

        # Verify evidence exists
        try:
            evidence = evidence_storage.get(evidence_id)
            if not evidence:
                print_error(f"Evidence not found: {evidence_id}")
                return
        except EntityNotFoundError:
            print_error(f"Evidence not found: {evidence_id}")
            return
        except StorageError as se:
            print_error(f"Storage error: {str(se)}")
            return

        # Get current category for comparison
        current_category = evidence.category.value
        current_subcategory = evidence.subcategory

        # Show current and new category
        print_header(f"Update Evidence Category: {evidence_id}")
        console.print(f"[bold]Title:[/bold] {evidence.title}")
        console.print(f"[bold]Current Category:[/bold] {current_category}")
        console.print(f"[bold]New Category:[/bold] {category}")

        if current_subcategory:
            console.print(f"[bold]Current Subcategory:[/bold] {current_subcategory}")

        if subcategory:
            console.print(f"[bold]New Subcategory:[/bold] {subcategory}")
        elif current_subcategory and not subcategory:
            console.print("[bold]Subcategory:[/bold] (will be cleared)")

        # Confirm update if not forced
        if not force:
            if not confirm("Update category?", default=True):
                print_info("Category update cancelled.")
                return

        # Prepare update data
        update_data = {
            "category": category
        }

        if subcategory is not None:  # None means no change, empty string means clear
            update_data["subcategory"] = subcategory

        # Update evidence with progress spinner
        with create_progress_context() as progress:
            task_id = progress.add_task("Updating evidence category...", total=1)

            try:
                # Update evidence with new category
                updated_evidence = evidence_storage.update(evidence_id, update_data)
                progress.update(task_id, completed=1)

                if updated_evidence:
                    print_success(f"Evidence {evidence_id} category updated successfully")
                    if subcategory is not None:
                        if subcategory:
                            print_info(f"Subcategory set to: {subcategory}")
                        else:
                            print_info("Subcategory cleared")
                else:
                    print_error(f"Failed to update evidence {evidence_id}")

            except ValidationError as ve:
                print_error(f"Validation error: {str(ve)}")
                if hasattr(ve, "validation_errors") and ve.validation_errors:
                    for error in ve.validation_errors:
                        print_error(f"- {error}")
                return

            except EntityNotFoundError:
                print_error(f"Evidence not found: {evidence_id}")
                return

            except StorageError as se:
                print_error(f"Storage error: {str(se)}")
                return

        logger.info(f"Evidence {evidence_id} category updated to {category}")

    except Exception as e:
        print_error(f"Error categorizing evidence: {str(e)}")
        logger.exception("Error in evidence categorize command")

@evidence_group.command(name="tag")
@click.argument("evidence_id")
@click.argument("tags")
@click.option("--remove", is_flag=True, help="Remove the specified tags instead of adding them")
@click.option("--force", is_flag=True, help="Skip confirmation")
def tag_evidence(evidence_id, tags, remove, force):
    """Add or remove tags from an evidence item."""
    try:
        # Log command execution
        logger.info(f"Executing evidence tag command for evidence_id={evidence_id}")

        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        if not tag_list:
            print_error("No valid tags specified")
            return

        # Verify evidence exists
        try:
            evidence = evidence_storage.get(evidence_id)
            if not evidence:
                print_error(f"Evidence not found: {evidence_id}")
                return
        except EntityNotFoundError:
            print_error(f"Evidence not found: {evidence_id}")
            return
        except StorageError as se:
            print_error(f"Storage error: {str(se)}")
            return

        # Get current tags for comparison
        current_tags = evidence.tags or []

        # Show current and new tags
        action = "Remove" if remove else "Add"
        print_header(f"{action} Evidence Tags: {evidence_id}")
        console.print(f"[bold]Title:[/bold] {evidence.title}")
        if current_tags:
            console.print(f"[bold]Current Tags:[/bold] {', '.join(current_tags)}")
        else:
            console.print("[bold]Current Tags:[/bold] None")

        console.print(f"[bold]Tags to {action.lower()}:[/bold] {', '.join(tag_list)}")

        # Show what the result will be
        result_tags = current_tags.copy()
        if remove:
            result_tags = [tag for tag in result_tags if tag not in tag_list]
        else:
            for tag in tag_list:
                if tag not in result_tags:
                    result_tags.append(tag)

        console.print(f"[bold]Result:[/bold] {', '.join(result_tags) if result_tags else 'No tags'}")

        # Confirm update if not forced
        if not force:
            if not confirm(f"{action} these tags?", default=True):
                print_info("Tag update cancelled.")
                return

        # Prepare update data
        update_data = {
            "tags": result_tags
        }

        # Update evidence with progress spinner
        with create_progress_context() as progress:
            task_id = progress.add_task(f"{action}ing tags...", total=1)

            try:
                # Update evidence with new tags
                updated_evidence = evidence_storage.update(evidence_id, update_data)
                progress.update(task_id, completed=1)

                if updated_evidence:
                    print_success(f"Evidence {evidence_id} tags updated successfully")
                    if updated_evidence.tags:
                        print_info(f"New tags: {', '.join(updated_evidence.tags)}")
                    else:
                        print_info("No tags remain on evidence")
                else:
                    print_error(f"Failed to update evidence {evidence_id}")

            except ValidationError as ve:
                print_error(f"Validation error: {str(ve)}")
                if hasattr(ve, "validation_errors") and ve.validation_errors:
                    for error in ve.validation_errors:
                        print_error(f"- {error}")
                return

            except EntityNotFoundError:
                print_error(f"Evidence not found: {evidence_id}")
                return

            except StorageError as se:
                print_error(f"Storage error: {str(se)}")
                return

        logger.info(f"Evidence {evidence_id} tags updated: {action.lower()}ed {', '.join(tag_list)}")

    except Exception as e:
        print_error(f"Error tagging evidence: {str(e)}")
        logger.exception("Error in evidence tag command")

@evidence_group.command(name="attach")
@click.argument("evidence_id")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--description", help="Attachment description")
@click.option("--force", is_flag=True, help="Skip confirmation")
def attach_file(evidence_id, file_path, description, force):
    """Attach a file to an evidence item."""
    try:
        # Log command execution
        logger.info(f"Executing evidence attach command for evidence_id={evidence_id}")

        # Get file information
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        # Verify evidence exists
        try:
            evidence = evidence_storage.get(evidence_id)
            if not evidence:
                print_error(f"Evidence not found: {evidence_id}")
                return
        except EntityNotFoundError:
            print_error(f"Evidence not found: {evidence_id}")
            return
        except StorageError as se:
            print_error(f"Storage error: {str(se)}")
            return

        # Display information
        print_header(f"Attach File to Evidence: {evidence_id}")
        console.print(f"[bold]Evidence:[/bold] {evidence.title}")
        console.print(f"[bold]File:[/bold] {file_name}")
        console.print(f"[bold]Size:[/bold] {file_size} bytes")

        if description:
            console.print(f"[bold]Description:[/bold] {description}")

        # Confirm attachment if not forced
        if not force:
            if not confirm("Attach this file?", default=True):
                print_info("Attachment cancelled.")
                return

        # Attach file with progress spinner
        with create_progress_context() as progress:
            task_id = progress.add_task(f"Attaching file...", total=1)

            try:
                # Add custom description to file before attaching
                if description:
                    # Create attachment data with custom description
                    attachment_data = {
                        "description": description
                    }

                    # Update evidence with new attachment
                    updated_evidence = evidence_storage.update(
                        evidence_id,
                        {},
                        attachment_paths=[file_path],
                        attachment_metadata=attachment_data
                    )
                else:
                    # Just attach the file with default description
                    updated_evidence = evidence_storage.update(
                        evidence_id,
                        {},
                        attachment_paths=[file_path]
                    )

                progress.update(task_id, completed=1)

                if updated_evidence:
                    # Get the newly added attachment (assuming it's the last one)
                    if updated_evidence.attachments:
                        new_attachment = updated_evidence.attachments[-1]
                        print_success(f"File attached successfully with ID: {new_attachment.id}")
                    else:
                        print_success(f"File attached successfully")
                else:
                    print_error(f"Failed to attach file to evidence {evidence_id}")

            except AttachmentError as ae:
                print_error(f"Attachment error: {str(ae)}")
                return

            except ValidationError as ve:
                print_error(f"Validation error: {str(ve)}")
                if hasattr(ve, "validation_errors") and ve.validation_errors:
                    for error in ve.validation_errors:
                        print_error(f"- {error}")
                return

            except EntityNotFoundError:
                print_error(f"Evidence not found: {evidence_id}")
                return

            except StorageError as se:
                print_error(f"Storage error: {str(se)}")
                return

        logger.info(f"File {file_name} attached to evidence {evidence_id}")

    except Exception as e:
        print_error(f"Error attaching file: {str(e)}")
        logger.exception("Error in evidence attach command")

@evidence_group.command(name="detach")
@click.argument("evidence_id")
@click.argument("attachment_id")
@click.option("--force", is_flag=True, help="Skip confirmation")
def detach_file(evidence_id, attachment_id, force):
    """Remove an attachment from an evidence item."""
    try:
        # Log command execution
        logger.info(f"Executing evidence detach command for evidence_id={evidence_id}, attachment_id={attachment_id}")

        # Verify evidence exists
        try:
            evidence = evidence_storage.get(evidence_id)
            if not evidence:
                print_error(f"Evidence not found: {evidence_id}")
                return
        except EntityNotFoundError:
            print_error(f"Evidence not found: {evidence_id}")
            return
        except StorageError as se:
            print_error(f"Storage error: {str(se)}")
            return

        # Find the attachment
        attachment = None
        for att in evidence.attachments:
            if att.id == attachment_id:
                attachment = att
                break

        if not attachment:
            print_error(f"Attachment {attachment_id} not found in evidence {evidence_id}")
            return

        # Display information
        print_header(f"Remove Attachment from Evidence: {evidence_id}")
        console.print(f"[bold]Evidence:[/bold] {evidence.title}")
        console.print(f"[bold]Attachment ID:[/bold] {attachment.id}")
        console.print(f"[bold]File Name:[/bold] {attachment.file_name}")
        if attachment.description:
            console.print(f"[bold]Description:[/bold] {attachment.description}")

        # Confirm removal if not forced
        if not force:
            if not confirm("Are you sure you want to remove this attachment?", default=False):
                print_info("Detachment cancelled.")
                return

        # Remove attachment with progress spinner
        with create_progress_context() as progress:
            task_id = progress.add_task(f"Removing attachment...", total=1)

            try:
                # Update evidence by removing attachment
                updated_evidence = evidence_storage.update(
                    evidence_id,
                    {},
                    remove_attachments=[attachment_id]
                )

                progress.update(task_id, completed=1)

                if updated_evidence:
                    print_success(f"Attachment {attachment_id} removed successfully")
                else:
                    print_error(f"Failed to remove attachment from evidence {evidence_id}")

            except ValidationError as ve:
                print_error(f"Validation error: {str(ve)}")
                if hasattr(ve, "validation_errors") and ve.validation_errors:
                    for error in ve.validation_errors:
                        print_error(f"- {error}")
                return

            except EntityNotFoundError:
                print_error(f"Evidence not found: {evidence_id}")
                return

            except StorageError as se:
                print_error(f"Storage error: {str(se)}")
                return

        logger.info(f"Attachment {attachment_id} removed from evidence {evidence_id}")

    except Exception as e:
        print_error(f"Error detaching file: {str(e)}")
        logger.exception("Error in evidence detach command")

@evidence_group.command(name="search")
@click.option("--text", help="Full-text search across all text fields")
@click.option("--title", help="Search in title field")
@click.option("--description", help="Search in description field")
@click.option("--category", type=click.Choice([c.value for c in EvidenceCategory]),
              help="Filter by category")
@click.option("--tag", multiple=True, help="Filter by tag (can specify multiple times)")
@click.option("--source", help="Filter by source")
@click.option("--date-from", help="Filter by date collected (format: YYYY-MM-DD)")
@click.option("--date-to", help="Filter by date collected (format: YYYY-MM-DD)")
@click.option("--relevance", type=click.Choice([r.value for r in EvidenceRelevance]),
              help="Filter by relevance score")
@click.option("--epic", help="Filter by related epic ID")
@click.option("--task", help="Filter by related task ID")
@click.option("--project", help="Filter by project ID")
@click.option("--sort-by", type=click.Choice(["title", "category", "relevance_score",
                                             "date_collected", "created_at", "updated_at"]),
              default="relevance_score", help="Field to sort by")
@click.option("--sort-order", type=click.Choice(["asc", "desc"]), default="desc",
              help="Sort order (ascending or descending)")
@click.option("--limit", type=int, default=20, help="Maximum number of results")
@click.option("--offset", type=int, default=0, help="Number of items to skip")
@click.option("--format", type=click.Choice(["table", "json", "csv"]), default="table",
              help="Output format")
@click.option("--detailed", is_flag=True, help="Show detailed results instead of table")
@click.option("--interactive", is_flag=True, help="Interactive search mode with refinement")
def search_evidence(text, title, description, category, tag, source, date_from, date_to,
                   relevance, epic, task, project, sort_by, sort_order, limit, offset,
                   format, detailed, interactive):
    """
    Search for evidence with advanced filtering and full-text search.

    The search command goes beyond simple listing by supporting text search
    across multiple fields, with intelligent ranking of results by relevance.
    """
    # Handle interactive mode
    if interactive:
        return _interactive_search()

    try:
        # Log command execution
        logger.info(f"Executing evidence search command with filters")

        # Prepare filters dictionary
        filters = {}
        if text:
            filters["text"] = text
        if title:
            filters["title"] = title
        if description:
            filters["description"] = description
        if category:
            filters["category"] = category
        if tag:
            filters["tags"] = list(tag)  # Convert tuple to list
        if source:
            filters["source"] = source
        if epic:
            filters["epic_id"] = epic
        if task:
            filters["task_id"] = task
        if project:
            filters["project_id"] = project
        if relevance:
            filters["relevance_score"] = relevance

        # Date filters require conversion to datetime
        if date_from:
            try:
                date_obj = datetime.fromisoformat(date_from)
                filters["date_from"] = date_obj
            except ValueError:
                print_warning(f"Invalid date format for date-from: {date_from}. Using ISO format YYYY-MM-DD")

        if date_to:
            try:
                date_obj = datetime.fromisoformat(date_to)
                filters["date_to"] = date_obj
            except ValueError:
                print_warning(f"Invalid date format for date-to: {date_to}. Using ISO format YYYY-MM-DD")

        # Display search criteria
        if filters:
            print_header("Evidence Search")
            for key, value in filters.items():
                if isinstance(value, list):
                    value_str = ", ".join(value)
                else:
                    value_str = str(value)
                console.print(f"[bold]{key}:[/bold] {value_str}")
        else:
            print_header("Evidence Search - All Items")

        # Get evidence items with progress indicator
        with create_progress_context() as progress:
            task_id = progress.add_task("Searching...", total=1)

            try:
                # Search for evidence items
                evidence_items = evidence_storage.list(
                    filters=filters,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    limit=limit,
                    offset=offset
                )
                progress.update(task_id, completed=1)

            except ValidationError as ve:
                print_error(f"Filter validation error: {str(ve)}")
                if hasattr(ve, "validation_errors") and ve.validation_errors:
                    for error in ve.validation_errors:
                        print_error(f"- {error}")
                return

            except StorageError as se:
                print_error(f"Storage error: {str(se)}")
                return

        # Get evidence items as dictionaries for display
        evidence_dicts = [e.to_dict() for e in evidence_items]

        if not evidence_dicts:
            print_warning("No evidence items found matching the search criteria.")
            return

        # Display results count
        console.print(f"\n[bold]Search Results:[/bold] {len(evidence_dicts)} items found")

        # Format output based on user preference
        if format == "json":
            console.print_json(json.dumps(evidence_dicts, indent=2, default=str))
        elif format == "csv":
            # Create simple CSV output
            columns = ["id", "title", "category", "relevance_score", "tags", "created_at"]

            # Print header
            header = ",".join(columns)
            console.print(header)

            # Print rows
            for evidence in evidence_dicts:
                row = []
                for col in columns:
                    if col == "tags" and "tags" in evidence:
                        tags_str = ";".join(evidence.get("tags", []))
                        row.append(f'"{tags_str}"')  # Quote tag lists
                    elif col in evidence:
                        val = str(evidence[col]).replace('"', '""')  # Escape quotes for CSV
                        row.append(f'"{val}"')
                    else:
                        row.append('""')
                console.print(",".join(row))
        elif detailed:
            # Show detailed output for each evidence item
            for i, evidence in enumerate(evidence_dicts):
                if i > 0:
                    console.print("\n" + "─" * 80 + "\n")
                print_evidence_details(evidence)
        else:
            # Display evidence items in a table
            table = create_evidence_table(evidence_dicts)
            console.print(table)

        # Show pagination info if relevant
        if len(evidence_dicts) == limit:
            print_info(f"Showing {len(evidence_dicts)} results. Use --offset to see more.")

        logger.info(f"Found {len(evidence_dicts)} evidence items matching search criteria")

    except Exception as e:
        print_error(f"Error searching evidence: {str(e)}")
        logger.exception("Error in evidence search command")

def _interactive_search():
    """Interactive evidence search workflow with refinement."""
    print_header("Interactive Evidence Search")
    print_info("This mode allows you to interactively search and refine your evidence queries.")

    # Start with empty filters
    filters = {}
    sort_by = "relevance_score"
    sort_order = "desc"
    limit = 20
    offset = 0

    while True:
        # Show current search criteria if any
        if filters:
            console.print("\n[bold]Current Search Criteria:[/bold]")
            for key, value in filters.items():
                if isinstance(value, list):
                    value_str = ", ".join(value)
                else:
                    value_str = str(value)
                console.print(f"[bold]{key}:[/bold] {value_str}")

        # Execute search with current filters
        try:
            with create_progress_context() as progress:
                task_id = progress.add_task("Searching...", total=1)

                evidence_items = evidence_storage.list(
                    filters=filters,
                    sort_by=sort_by,
                    sort_order=sort_order,
                    limit=limit,
                    offset=offset
                )

                progress.update(task_id, completed=1)

            evidence_dicts = [e.to_dict() for e in evidence_items]

            if not evidence_dicts:
                print_warning("No evidence items found matching the search criteria.")
            else:
                console.print(f"\n[bold]Search Results:[/bold] {len(evidence_dicts)} items found")
                table = create_evidence_table(evidence_dicts)
                console.print(table)

                # Show pagination info if relevant
                if len(evidence_dicts) == limit:
                    print_info(f"Showing {offset+1}-{offset+len(evidence_dicts)} results. You can view more results.")

            # Prompt for next action
            console.print("\n[bold]Search Options:[/bold]")
            console.print("1. Add text search term")
            console.print("2. Filter by category")
            console.print("3. Filter by tag")
            console.print("4. Filter by date range")
            console.print("5. Filter by relevance")
            console.print("6. Filter by related items (epic/task/project)")
            console.print("7. Change sort order")
            console.print("8. View next page of results")
            console.print("9. View previous page of results")
            console.print("10. View details of specific evidence item")
            console.print("11. Clear all filters and start over")
            console.print("12. Exit search")

            choice = click.prompt("Select an option", type=int, default=1)

            if choice == 1:
                # Add text search
                search_term = click.prompt("Enter search term")
                search_field = click.prompt(
                    "Search in which field?",
                    type=click.Choice(["all", "title", "description", "source"]),
                    default="all"
                )

                if search_field == "all":
                    filters["text"] = search_term
                else:
                    filters[search_field] = search_term

            elif choice == 2:
                # Filter by category
                categories = [c.value for c in EvidenceCategory]
                for i, cat in enumerate(categories, 1):
                    console.print(f"{i}. {cat}")

                cat_idx = click.prompt("Select category number", type=int, default=1)
                if 1 <= cat_idx <= len(categories):
                    filters["category"] = categories[cat_idx - 1]

            elif choice == 3:
                # Filter by tag
                tag = click.prompt("Enter tag to filter by")
                if "tags" not in filters:
                    filters["tags"] = []

                if tag not in filters["tags"]:
                    filters["tags"].append(tag)

            elif choice == 4:
                # Filter by date range
                date_from = click.prompt("Enter start date (YYYY-MM-DD)", default="")
                date_to = click.prompt("Enter end date (YYYY-MM-DD)", default="")

                if date_from:
                    try:
                        filters["date_from"] = datetime.fromisoformat(date_from)
                    except ValueError:
                        print_error("Invalid date format. Use YYYY-MM-DD.")

                if date_to:
                    try:
                        filters["date_to"] = datetime.fromisoformat(date_to)
                    except ValueError:
                        print_error("Invalid date format. Use YYYY-MM-DD.")

            elif choice == 5:
                # Filter by relevance
                relevances = [r.value for r in EvidenceRelevance]
                for i, rel in enumerate(relevances, 1):
                    console.print(f"{i}. {rel}")

                rel_idx = click.prompt("Select relevance number", type=int, default=1)
                if 1 <= rel_idx <= len(relevances):
                    filters["relevance_score"] = relevances[rel_idx - 1]

            elif choice == 6:
                # Filter by related items
                related_type = click.prompt(
                    "Filter by which related item?",
                    type=click.Choice(["epic", "task", "project"]),
                    default="epic"
                )

                related_id = click.prompt(f"Enter {related_type} ID")

                if related_type == "epic":
                    filters["epic_id"] = related_id
                elif related_type == "task":
                    filters["task_id"] = related_id
                else:
                    filters["project_id"] = related_id

            elif choice == 7:
                # Change sort order
                sort_field = click.prompt(
                    "Sort by which field?",
                    type=click.Choice(["title", "category", "relevance_score",
                                     "date_collected", "created_at", "updated_at"]),
                    default="relevance_score"
                )

                sort_direction = click.prompt(
                    "Sort direction",
                    type=click.Choice(["asc", "desc"]),
                    default="desc"
                )

                sort_by = sort_field
                sort_order = sort_direction

            elif choice == 8:
                # View next page
                if len(evidence_dicts) == limit:
                    offset += limit
                    print_info(f"Showing next page of results (offset: {offset})")
                else:
                    print_info("No more results to show.")

            elif choice == 9:
                # View previous page
                if offset >= limit:
                    offset -= limit
                    print_info(f"Showing previous page of results (offset: {offset})")
                else:
                    print_info("Already at the first page.")

            elif choice == 10:
                # View evidence details
                evidence_idx = click.prompt("Enter evidence number to view (1 to N)", type=int, default=1)

                if 1 <= evidence_idx <= len(evidence_dicts):
                    evidence = evidence_dicts[evidence_idx - 1]
                    print_evidence_details(evidence)
                    click.pause("Press any key to continue...")
                else:
                    print_error("Invalid evidence number.")

            elif choice == 11:
                # Clear all filters
                filters = {}
                sort_by = "relevance_score"
                sort_order = "desc"
                offset = 0
                print_info("All filters cleared.")

            elif choice == 12:
                # Exit search
                print_info("Exiting interactive search.")
                return

            else:
                print_error("Invalid option.")

        except ValidationError as ve:
            print_error(f"Filter validation error: {str(ve)}")
            if hasattr(ve, "validation_errors") and ve.validation_errors:
                for error in ve.validation_errors:
                    print_error(f"- {error}")

        except StorageError as se:
            print_error(f"Storage error: {str(se)}")

        except Exception as e:
            print_error(f"Error during interactive search: {str(e)}")
            logger.exception("Error in interactive evidence search")

@evidence_group.command(name="delete")
@click.argument("evidence_id")
@click.option("--force", is_flag=True, help="Skip confirmation")
@click.option("--keep-attachments", is_flag=True,
              help="Keep attachment files (otherwise they will be deleted)")
def delete_evidence(evidence_id, force, keep_attachments):
    """Delete an evidence item and optionally its attachment files."""
    try:
        # Log command execution
        logger.info(f"Executing evidence delete command for evidence_id={evidence_id}")

        # Verify evidence exists
        try:
            evidence = evidence_storage.get(evidence_id)
            if not evidence:
                print_error(f"Evidence not found: {evidence_id}")
                return
        except EntityNotFoundError:
            print_error(f"Evidence not found: {evidence_id}")
            return
        except StorageError as se:
            print_error(f"Storage error: {str(se)}")
            return

        # Display information
        print_header(f"Delete Evidence: {evidence_id}")
        console.print(f"[bold]Title:[/bold] {evidence.title}")
        console.print(f"[bold]Category:[/bold] {evidence.category.value}")
        if evidence.tags:
            console.print(f"[bold]Tags:[/bold] {', '.join(evidence.tags)}")

        # Show attachment information if present
        if evidence.attachments:
            console.print(f"[bold]Attachments:[/bold] {len(evidence.attachments)} files")
            if keep_attachments:
                console.print("[italic]Attachment files will be kept.[/italic]")
            else:
                console.print("[italic]Attachment files will also be deleted.[/italic]")

        # Warn about relationships if present
        if evidence.related_evidence_ids:
            print_warning(f"This evidence is related to {len(evidence.related_evidence_ids)} other evidence items.")
            print_warning("Deleting it will remove these relationships.")

        # Confirm deletion with extra warning if has attachments
        if not force:
            message = f"Are you sure you want to delete evidence {evidence_id}?"
            if evidence.attachments and not keep_attachments:
                message = f"Are you sure you want to delete evidence {evidence_id} and its {len(evidence.attachments)} attachments?"

            if not confirm(message, default=False):
                print_info("Deletion cancelled.")
                return

        # Delete evidence with progress spinner
        with create_progress_context() as progress:
            task_id = progress.add_task(f"Deleting evidence...", total=1)

            try:
                # Delete evidence
                success = evidence_storage.delete(evidence_id, delete_attachments=not keep_attachments)
                progress.update(task_id, completed=1)

                if success:
                    print_success(f"Evidence {evidence_id} deleted successfully")
                    if evidence.attachments and keep_attachments:
                        print_info(f"Attachment files were kept as requested")
                    elif evidence.attachments:
                        print_info(f"{len(evidence.attachments)} attachment files were also deleted")
                else:
                    print_error(f"Failed to delete evidence {evidence_id}")

            except ValidationError as ve:
                print_error(f"Validation error: {str(ve)}")
                if hasattr(ve, "validation_errors") and ve.validation_errors:
                    for error in ve.validation_errors:
                        print_error(f"- {error}")
                return

            except StorageError as se:
                print_error(f"Storage error: {str(se)}")
                return

        logger.info(f"Evidence {evidence_id} deleted")

    except Exception as e:
        print_error(f"Error deleting evidence: {str(e)}")
        logger.exception("Error in evidence delete command")

@evidence_group.command(name="relate")
@click.argument("evidence_id")
@click.option("--epic", help="Related epic ID")
@click.option("--task", help="Related task ID")
@click.option("--evidence", help="Related evidence ID")
@click.option("--force", is_flag=True, help="Skip confirmation")
@click.option("--remove", is_flag=True, help="Remove the relationship instead of adding it")
def relate_evidence(evidence_id, epic, task, evidence, force, remove):
    """Create or remove relationships between evidence and tasks, epics, or other evidence."""
    try:
        # Log command execution
        logger.info(f"Executing evidence relate command for evidence_id={evidence_id}")

        if not any([epic, task, evidence]):
            print_error("You must specify at least one related item (epic, task, or evidence).")
            return

        # Verify evidence exists
        try:
            source_evidence = evidence_storage.get(evidence_id)
            if not source_evidence:
                print_error(f"Evidence not found: {evidence_id}")
                return
        except EntityNotFoundError:
            print_error(f"Evidence not found: {evidence_id}")
            return
        except StorageError as se:
            print_error(f"Storage error: {str(se)}")
            return

        # Display information
        action = "Remove" if remove else "Create"
        print_header(f"{action} Evidence Relationship: {evidence_id}")
        console.print(f"[bold]Evidence:[/bold] {source_evidence.title}")

        # Prepare update data
        update_data = {}

        # Handle different relationship types
        if epic:
            # Check if epic exists in storage
            try:
                epic_storage = EpicStorage()
                epic_obj = epic_storage.get(epic)
                if not epic_obj:
                    if not force:
                        print_warning(f"Epic {epic} not found in storage. Continue anyway?")
                        if not confirm("Continue?", default=False):
                            print_info("Relationship update cancelled.")
                            return
            except Exception as e:
                if not force:
                    print_warning(f"Couldn't verify epic {epic}: {str(e)}. Continue anyway?")
                    if not confirm("Continue?", default=False):
                        print_info("Relationship update cancelled.")
                        return

            # Update epic relationship
            if remove:
                if source_evidence.epic_id == epic:
                    update_data['epic_id'] = None
                    console.print(f"[bold]Removing relationship:[/bold] Epic {epic}")
                else:
                    print_warning(f"Evidence {evidence_id} is not related to epic {epic}")
                    if not force:
                        print_info("No change needed.")
            else:
                current_epic = source_evidence.epic_id
                if current_epic and current_epic != epic and not force:
                    print_warning(f"Evidence {evidence_id} is already related to epic {current_epic}")
                    print_warning(f"This will replace the existing relationship.")
                    if not confirm("Replace existing epic relationship?", default=False):
                        print_info("Epic relationship update cancelled.")
                    else:
                        update_data['epic_id'] = epic
                        console.print(f"[bold]Creating relationship:[/bold] Epic {epic}")
                else:
                    update_data['epic_id'] = epic
                    console.print(f"[bold]Creating relationship:[/bold] Epic {epic}")

        # Handle task relationship
        if task:
            # Check if task exists in storage
            try:
                task_storage = TaskStorage()
                task_obj = task_storage.get(task)
                if not task_obj:
                    if not force:
                        print_warning(f"Task {task} not found in storage. Continue anyway?")
                        if not confirm("Continue?", default=False):
                            print_info("Relationship update cancelled.")
                            return
            except Exception as e:
                if not force:
                    print_warning(f"Couldn't verify task {task}: {str(e)}. Continue anyway?")
                    if not confirm("Continue?", default=False):
                        print_info("Relationship update cancelled.")
                        return

            # Update task relationship
            if remove:
                if source_evidence.task_id == task:
                    update_data['task_id'] = None
                    console.print(f"[bold]Removing relationship:[/bold] Task {task}")
                else:
                    print_warning(f"Evidence {evidence_id} is not related to task {task}")
                    if not force:
                        print_info("No change needed.")
            else:
                current_task = source_evidence.task_id
                if current_task and current_task != task and not force:
                    print_warning(f"Evidence {evidence_id} is already related to task {current_task}")
                    print_warning(f"This will replace the existing relationship.")
                    if not confirm("Replace existing task relationship?", default=False):
                        print_info("Task relationship update cancelled.")
                    else:
                        update_data['task_id'] = task
                        console.print(f"[bold]Creating relationship:[/bold] Task {task}")
                else:
                    update_data['task_id'] = task
                    console.print(f"[bold]Creating relationship:[/bold] Task {task}")

        # Handle evidence relationship (bidirectional)
        if evidence:
            # Check if related evidence exists
            try:
                related_evidence = evidence_storage.get(evidence)
                if not related_evidence:
                    print_error(f"Related evidence not found: {evidence}")
                    return
            except EntityNotFoundError:
                print_error(f"Related evidence not found: {evidence}")
                return
            except StorageError as se:
                print_error(f"Storage error: {str(se)}")
                return

            # Get current related evidence
            current_related_ids = source_evidence.related_evidence_ids or []

            # Update evidence relationship
            if remove:
                if evidence in current_related_ids:
                    new_related_ids = [rel_id for rel_id in current_related_ids if rel_id != evidence]
                    update_data['related_evidence_ids'] = new_related_ids
                    console.print(f"[bold]Removing relationship:[/bold] Evidence {evidence}")
                else:
                    print_warning(f"Evidence {evidence_id} is not related to evidence {evidence}")
                    if not force:
                        print_info("No change needed.")
                        return
            else:
                if evidence in current_related_ids:
                    print_warning(f"Evidence {evidence_id} is already related to evidence {evidence}")
                    if not force:
                        print_info("No change needed.")
                        return
                else:
                    new_related_ids = current_related_ids.copy()
                    new_related_ids.append(evidence)
                    update_data['related_evidence_ids'] = new_related_ids
                    console.print(f"[bold]Creating relationship:[/bold] Evidence {evidence}")

        # If no changes were made, exit
        if not update_data:
            print_warning("No relationship changes to apply.")
            return

        # Confirm update if not forced
        if not force:
            action_text = "Remove" if remove else "Create"
            if not confirm(f"{action_text} these relationships?", default=True):
                print_info("Relationship update cancelled.")
                return

        # Update evidence with progress spinner
        with create_progress_context() as progress:
            task_id = progress.add_task(f"Updating relationships...", total=1)

            try:
                # Update source evidence
                updated_evidence = evidence_storage.update(evidence_id, update_data)

                # If we're relating to another evidence, update that one too
                if evidence and not remove:
                    # This will update the related evidence to include a link back to this one
                    related_update = {
                        'related_evidence_ids': None  # Special case, automatic bidirectional update
                    }
                    evidence_storage.update(evidence, related_update)

                # If we're removing a relation to another evidence, update that one too
                if evidence and remove:
                    try:
                        related_ev = evidence_storage.get(evidence)
                        if related_ev and evidence_id in related_ev.related_evidence_ids:
                            new_related = [e for e in related_ev.related_evidence_ids if e != evidence_id]
                            evidence_storage.update(evidence, {'related_evidence_ids': new_related})
                    except Exception as e:
                        logger.warning(f"Could not update reverse relationship for {evidence}: {str(e)}")

                progress.update(task_id, completed=1)

                if updated_evidence:
                    print_success(f"Evidence {evidence_id} relationships updated successfully")

                    # Show all current relationships
                    if updated_evidence.epic_id:
                        console.print(f"[bold]Epic:[/bold] {updated_evidence.epic_id}")

                    if updated_evidence.task_id:
                        console.print(f"[bold]Task:[/bold] {updated_evidence.task_id}")

                    if updated_evidence.related_evidence_ids:
                        console.print(f"[bold]Related Evidence:[/bold] {', '.join(updated_evidence.related_evidence_ids)}")
                else:
                    print_error(f"Failed to update evidence {evidence_id} relationships")

            except ValidationError as ve:
                print_error(f"Validation error: {str(ve)}")
                if hasattr(ve, "validation_errors") and ve.validation_errors:
                    for error in ve.validation_errors:
                        print_error(f"- {error}")
                return

            except EntityNotFoundError:
                print_error(f"Evidence not found: {evidence_id}")
                return

            except StorageError as se:
                print_error(f"Storage error: {str(se)}")
                return

        logger.info(f"Evidence {evidence_id} relationships updated")

    except Exception as e:
        print_error(f"Error relating evidence: {str(e)}")
        logger.exception("Error in evidence relate command")
