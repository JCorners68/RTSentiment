# Kanban CLI Command Reference

This document provides a comprehensive reference for all commands available in the Kanban CLI application, with particular focus on the Evidence Management System commands which are a priority feature.

## Table of Contents

- [Task Management Commands](#task-management-commands)
- [Board Visualization Commands](#board-visualization-commands)
- [Epic Management Commands](#epic-management-commands)
- [Evidence Management Commands](#evidence-management-commands) (Priority Feature)
- [Global Options](#global-options)

## Task Management Commands

### List Tasks

```bash
kanban task list [OPTIONS]
```

Lists all tasks with optional filtering.

**Options:**
- `--status TEXT`: Filter by status (Backlog, Ready, In Progress, Review, Done)
- `--epic TEXT`: Filter by epic ID
- `--title TEXT`: Filter by title (substring match)
- `--assignee TEXT`: Filter by assignee
- `--format [table|json]`: Output format (default: table)

**Example:**
```bash
kanban task list --status "In Progress" --format json
```

### Get Task Details

```bash
kanban task get <TASK_ID>
```

Display detailed information about a specific task.

**Example:**
```bash
kanban task get TSK-123
```

### Add Task

```bash
kanban task add [OPTIONS]
```

Add a new task to the board.

**Options:**
- `--title TEXT`: Task title
- `--description TEXT`: Task description
- `--status TEXT`: Task status (default: Backlog)
- `--priority TEXT`: Task priority (Low, Medium, High, Critical)
- `--epic TEXT`: Parent epic ID
- `--assignee TEXT`: Person assigned to the task
- `--complexity INTEGER`: Task complexity (1-5)

**Example:**
```bash
kanban task add --title "Implement search feature" --description "Add search capabilities to the UI" --priority "High"
```

### Update Task

```bash
kanban task update <TASK_ID> [OPTIONS]
```

Update an existing task.

**Options:**
- `--title TEXT`: New task title
- `--description TEXT`: New task description
- `--status TEXT`: New task status
- `--priority TEXT`: New task priority
- `--epic TEXT`: New parent epic ID
- `--assignee TEXT`: New assignee
- `--complexity INTEGER`: New task complexity (1-5)
- `--add-tags TEXT`: Comma-separated list of tags to add
- `--remove-tags TEXT`: Comma-separated list of tags to remove

**Example:**
```bash
kanban task update TSK-123 --status "In Progress" --assignee "John Doe" --add-tags "urgent,sprint2"
```

### Delete Task

```bash
kanban task delete <TASK_ID> [OPTIONS]
```

Delete a task from the board.

**Options:**
- `--force`: Skip confirmation prompt

**Example:**
```bash
kanban task delete TSK-123 --force
```

## Board Visualization Commands

### Show Board

```bash
kanban board show [OPTIONS]
```

Show the current Kanban board with tasks grouped by status.

**Options:**
- `--compact`: Use compact display mode (less details)
- `--detailed`: Show more task details
- `--filter TEXT`: Filter tasks by substring match in title or description
- `--by-priority`: Group tasks by priority instead of status

**Example:**
```bash
kanban board show --detailed --filter "important"
```

### View Board

```bash
kanban board view [OPTIONS]
```

View the board in different display modes.

**Options:**
- `--mode [list|kanban|compact]`: Display mode (default: kanban)
- `--sort-by [priority|status|created|updated]`: Sort order for tasks (default: status)

**Example:**
```bash
kanban board view --mode list --sort-by priority
```

### Move Task

```bash
kanban board move <TASK_ID> <COLUMN>
```

Move a task to a different column on the board.

**Options:**
- `--force`: Skip validation of column name

**Example:**
```bash
kanban board move TSK-123 "In Progress"
```

### Create Board

```bash
kanban board create [OPTIONS]
```

Create a new Kanban board configuration.

**Options:**
- `--name TEXT`: Board name
- `--columns TEXT`: Comma-separated list of column names

**Example:**
```bash
kanban board create --name "Sprint Board" --columns "To Do,Doing,Done"
```

### List Boards

```bash
kanban board list
```

List all available boards.

## Epic Management Commands

### List Epics

```bash
kanban epic list [OPTIONS]
```

List epics with optional filtering.

**Options:**
- `--status TEXT`: Filter by status
- `--owner TEXT`: Filter by owner
- `--title TEXT`: Filter by title (substring match)
- `--format [table|json]`: Output format (default: table)

**Example:**
```bash
kanban epic list --status "Open" --owner "John"
```

### Get Epic

```bash
kanban epic get <EPIC_ID> [OPTIONS]
```

Get detailed information about a specific epic.

**Options:**
- `--with-tasks`: Include tasks in the output

**Example:**
```bash
kanban epic get EPC-123 --with-tasks
```

### Create Epic

```bash
kanban epic create [OPTIONS]
```

Create a new epic.

**Options:**
- `--title TEXT`: Epic title
- `--description TEXT`: Epic description
- `--status TEXT`: Epic status (default: Open)
- `--owner TEXT`: Epic owner

**Example:**
```bash
kanban epic create --title "User Authentication" --description "Implement user login and registration" --owner "Jane"
```

### Update Epic

```bash
kanban epic update <EPIC_ID> [OPTIONS]
```

Update an existing epic.

**Options:**
- `--title TEXT`: New epic title
- `--description TEXT`: New epic description
- `--status TEXT`: New epic status
- `--owner TEXT`: New epic owner

**Example:**
```bash
kanban epic update EPC-123 --status "In Progress" --owner "Alex"
```

### Delete Epic

```bash
kanban epic delete <EPIC_ID> [OPTIONS]
```

Delete an epic.

**Options:**
- `--force`: Skip confirmation

**Example:**
```bash
kanban epic delete EPC-123 --force
```

## Evidence Management Commands

> **Priority Feature**: The Evidence Management System is a priority feature of this application.

### List Evidence

```bash
kanban evidence list [OPTIONS]
```

List evidence items with optional filtering.

**Options:**
- `--category TEXT`: Filter by category (Requirement, Bug, Design, Test, Result, Reference, User Feedback, Decision, Other)
- `--tag TEXT`: Filter by tag
- `--relevance TEXT`: Filter by relevance score (Low, Medium, High, Critical)
- `--epic TEXT`: Filter by related epic ID
- `--task TEXT`: Filter by related task ID
- `--format [table|json]`: Output format (default: table)

**Example:**
```bash
kanban evidence list --category "Requirement" --tag "priority-feature"
```

### Get Evidence

```bash
kanban evidence get <EVIDENCE_ID>
```

Get detailed information about a specific evidence item.

**Example:**
```bash
kanban evidence get EVD-123
```

### Add Evidence

```bash
kanban evidence add [OPTIONS]
```

Add a new evidence item.

**Options:**
- `--title TEXT`: Evidence title
- `--description TEXT`: Evidence description
- `--category TEXT`: Evidence category (see categories above)
- `--subcategory TEXT`: More specific categorization
- `--relevance TEXT`: Relevance score (Low, Medium, High, Critical)
- `--tags TEXT`: Comma-separated list of tags
- `--source TEXT`: Source of the evidence
- `--epic TEXT`: Related epic ID
- `--task TEXT`: Related task ID

**Example:**
```bash
kanban evidence add --title "User Authentication Requirements" --description "Requirements for the login system" --category "Requirement" --relevance "High" --tags "auth,security,requirements"
```

### Categorize Evidence

```bash
kanban evidence categorize <EVIDENCE_ID> <CATEGORY> [OPTIONS]
```

Update the category of an evidence item.

**Options:**
- `--subcategory TEXT`: Optional subcategory

**Example:**
```bash
kanban evidence categorize EVD-123 "Design" --subcategory "User Interface"
```

### Tag Evidence

```bash
kanban evidence tag <EVIDENCE_ID> <TAGS> [OPTIONS]
```

Add or remove tags from an evidence item.

**Options:**
- `--remove`: Remove the specified tags instead of adding them

**Example:**
```bash
kanban evidence tag EVD-123 "important,ui,design"
```

### Attach File

```bash
kanban evidence attach <EVIDENCE_ID> <FILE_PATH> [OPTIONS]
```

Attach a file to an evidence item.

**Options:**
- `--description TEXT`: Attachment description

**Example:**
```bash
kanban evidence attach EVD-123 ./docs/design.pdf --description "UI design document"
```

### Detach File

```bash
kanban evidence detach <EVIDENCE_ID> <ATTACHMENT_ID> [OPTIONS]
```

Remove an attachment from an evidence item.

**Options:**
- `--force`: Skip confirmation

**Example:**
```bash
kanban evidence detach EVD-123 ATT-456 --force
```

### Search Evidence

```bash
kanban evidence search [OPTIONS]
```

Search for evidence with advanced filtering.

**Options:**
- `--text TEXT`: Search for text in title, description, content
- `--category TEXT`: Filter by category
- `--tag TEXT`: Filter by tag
- `--date-from TEXT`: Filter by date collected (format: YYYY-MM-DD)
- `--date-to TEXT`: Filter by date collected (format: YYYY-MM-DD)
- `--limit INTEGER`: Maximum number of results (default: 20)

**Example:**
```bash
kanban evidence search --text "authentication" --category "Requirement" --date-from "2025-01-01"
```

### Relate Evidence

```bash
kanban evidence relate <EVIDENCE_ID> [OPTIONS]
```

Create a relationship between evidence and tasks, epics, or other evidence.

**Options:**
- `--epic TEXT`: Related epic ID
- `--task TEXT`: Related task ID
- `--evidence TEXT`: Related evidence ID

**Example:**
```bash
kanban evidence relate EVD-123 --task TSK-456 --evidence EVD-789
```

## Global Options

These options are available for all commands:

- `--help`: Show help message for a command
- `--version`: Show the version of the Kanban CLI

## Command Groups

The Kanban CLI organizes commands into logical groups:

- `kanban task`: Task management commands
- `kanban board`: Board visualization commands
- `kanban epic`: Epic management commands
- `kanban evidence`: Evidence management commands (priority feature)

To see help for a specific command group, use:

```bash
kanban <group> --help
```

Example:
```bash
kanban evidence --help
```
