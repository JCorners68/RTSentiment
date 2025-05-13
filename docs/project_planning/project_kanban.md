# Simple CLI Kanban Board for Sentimark Project Management

## Implementation Prompt

```
Implement a lightweight CLI Kanban board system for the Sentimark project that meets these requirements:

1. Create a simple JSON-based task tracking system with predefined columns
2. Provide basic CLI commands for task management (add, move, update, list, show)
3. Include Claude AI integration for task processing and evidence collection
4. Ensure error handling for common issues (missing files, invalid IDs, etc.)
5. Keep implementation minimal but functional - focus on reliability over features
6. Include verification steps in the task workflow
7. Store evidence of task completion for review
8. implement /help command to display usage instructions.

The solution should work entirely from the command line without external dependencies beyond jq.
Ensure all scripts have proper error handling and input validation to prevent common issues.
```
## Implementation

### 1. Setup the Kanban Structure

Create a `kanban.json` file in your project /kanban with this initial structure:

```json
{
  "columns": [
    "Project Backlog",
    "To Define",
    "Prompt Ready",
    "In Progress",
    "Needs Review",
    "Done"
  ],
  "tasks": []
}
```

### 2. Create CLI Scripts for Board Management

Create a `kanban.sh` script in your project with robust error handling:

```bash
#!/bin/bash

KANBAN_FILE="$(pwd)/kanban.json"

# Check if kanban.json exists, create if not
if [ ! -f "$KANBAN_FILE" ]; then
  echo '{"columns":["Project Backlog","To Define","Prompt Ready","In Progress","Needs Review","Done"],"tasks":[]}' > "$KANBAN_FILE"
  echo "Created new kanban board at $KANBAN_FILE"
fi

# Error handling function
function error_exit() {
  echo "Error: $1" >&2
  exit 1
}

# Check if jq is installed
if ! command -v jq &> /dev/null; then
  error_exit "jq is required but not installed. Please install jq first."
fi

# Create a new task
function add_task() {
  local title="$1"
  local description="$2"
  local type="${3:-Task}"  # Default type is 'Task'
  
  # Input validation
  [ -z "$title" ] && error_exit "Title is required"
  [ -z "$description" ] && error_exit "Description is required"
  
  # Generate task ID with timestamp
  local task_id="SENTI-$(date +%s)"
  
  # Add task to kanban.json
  local jq_cmd=".tasks += [{\"id\": \"$task_id\", \"title\": \"$title\", \"description\": \"$description\", \"type\": \"$type\", \"column\": \"Project Backlog\", \"created\": \"$(date -Iseconds)\", \"updated\": \"$(date -Iseconds)\", \"evidence\": \"\"}]"
  
  jq "$jq_cmd" "$KANBAN_FILE" > "${KANBAN_FILE}.tmp" && mv "${KANBAN_FILE}.tmp" "$KANBAN_FILE" || error_exit "Failed to add task"
  
  echo "Task added: $task_id - $title"
  echo "Use './kanban.sh show $task_id' to view details"
}

# Move a task to a different column
function move_task() {
  local task_id="$1"
  local column="$2"
  
  # Input validation
  [ -z "$task_id" ] && error_exit "Task ID is required"
  [ -z "$column" ] && error_exit "Column name is required"
  
  # Check if task exists
  local task_exists=$(jq -r ".tasks[] | select(.id == \"$task_id\") | .id" "$KANBAN_FILE")
  [ -z "$task_exists" ] && error_exit "Task $task_id not found"
  
  # Check if column exists
  local column_exists=$(jq -r ".columns[] | select(. == \"$column\")" "$KANBAN_FILE")
  [ -z "$column_exists" ] && error_exit "Column '$column' not found"
  
  # Move task
  local jq_cmd=".tasks = (.tasks | map(if .id == \"$task_id\" then .column = \"$column\" | .updated = \"$(date -Iseconds)\" else . end))"
  
  jq "$jq_cmd" "$KANBAN_FILE" > "${KANBAN_FILE}.tmp" && mv "${KANBAN_FILE}.tmp" "$KANBAN_FILE" || error_exit "Failed to move task"
  
  echo "Task $task_id moved to $column"
}

# Add evidence to a task
function add_evidence() {
  local task_id="$1"
  local evidence="$2"
  
  # Input validation
  [ -z "$task_id" ] && error_exit "Task ID is required"
  [ -z "$evidence" ] && error_exit "Evidence is required"
  
  # Check if task exists
  local task_exists=$(jq -r ".tasks[] | select(.id == \"$task_id\") | .id" "$KANBAN_FILE")
  [ -z "$task_exists" ] && error_exit "Task $task_id not found"
  
  # Add evidence
  local jq_cmd=".tasks = (.tasks | map(if .id == \"$task_id\" then .evidence = \"$evidence\" | .updated = \"$(date -Iseconds)\" else . end))"
  
  jq "$jq_cmd" "$KANBAN_FILE" > "${KANBAN_FILE}.tmp" && mv "${KANBAN_FILE}.tmp" "$KANBAN_FILE" || error_exit "Failed to add evidence"
  
  echo "Evidence added to task $task_id"
}

# List tasks (all or by column)
function list_tasks() {
  local column="$1"
  
  if [ -z "$column" ]; then
    # List all tasks
    local tasks=$(jq -r '.tasks[] | "[\(.id)] \(.title) [\(.column)]"' "$KANBAN_FILE")
    if [ -z "$tasks" ]; then
      echo "No tasks found"
    else
      echo "$tasks" | column -t
    fi
  else
    # Check if column exists
    local column_exists=$(jq -r ".columns[] | select(. == \"$column\")" "$KANBAN_FILE")
    [ -z "$column_exists" ] && error_exit "Column '$column' not found"
    
    # List tasks in column
    local tasks=$(jq -r ".tasks[] | select(.column == \"$column\") | \"[\(.id)] \(.title)\"" "$KANBAN_FILE")
    if [ -z "$tasks" ]; then
      echo "No tasks in column '$column'"
    else
      echo "$tasks" | column -t
    fi
  fi
}

# Show task details
function show_task() {
  local task_id="$1"
  
  # Input validation
  [ -z "$task_id" ] && error_exit "Task ID is required"
  
  # Get task details
  local task_details=$(jq -r ".tasks[] | select(.id == \"$task_id\") | \"ID: \(.id)\nTitle: \(.title)\nType: \(.type)\nDescription: \(.description)\nColumn: \(.column)\nCreated: \(.created)\nUpdated: \(.updated)\nEvidence: \(.evidence)\"" "$KANBAN_FILE")
  
  # Check if task exists
  [ -z "$task_details" ] && error_exit "Task $task_id not found"
  
  echo "$task_details"
}

# Display board visualization
function show_board() {
  # Get columns
  local columns=$(jq -r '.columns[]' "$KANBAN_FILE")
  
  echo "=== SENTIMARK KANBAN BOARD ==="
  echo ""
  
  # For each column, print its name and tasks
  for column in $columns; do
    echo "=== $column ==="
    list_tasks "$column" 2>/dev/null || echo "No tasks"
    echo ""
  done
}

# Main command processing
case "$1" in
  add)
    add_task "$2" "$3" "$4"
    ;;
  move)
    move_task "$2" "$3"
    ;;
  evidence)
    add_evidence "$2" "$3"
    ;;
  list)
    list_tasks "$2"
    ;;
  show)
    show_task "$2"
    ;;
  board)
    show_board
    ;;
  *)
    echo "Sentimark CLI Kanban Board"
    echo "Usage:"
    echo "  ./kanban.sh add 'Task Title' 'Task Description' ['Task Type']"
    echo "  ./kanban.sh move TASK-ID 'Column Name'"
    echo "  ./kanban.sh evidence TASK-ID 'Verification Evidence'"
    echo "  ./kanban.sh list ['Column Name']"
    echo "  ./kanban.sh show TASK-ID"
    echo "  ./kanban.sh board"
    ;;
esac
Make the script executable:

```bash
chmod +x kanban.sh
```

### 3. Claude AI Integration

Create a separate script called `cca-task.sh` for Claude integration with proper error handling:

```bash
#!/bin/bash

KANBAN_FILE="$(pwd)/kanban.json"

# Error handling function
function error_exit() {
  echo "Error: $1" >&2
  exit 1
}

# Process a task with Claude
function process_task() {
  local task_id="$1"
  
  # Input validation
  [ -z "$task_id" ] && error_exit "Task ID is required"
  
  # Get task details
  local task_details=$(./kanban.sh show "$task_id" 2>/dev/null)
  [ $? -ne 0 ] && error_exit "Task $task_id not found or kanban.sh script error"
  
  # Extract title and description
  local title=$(echo "$task_details" | grep "Title:" | cut -d' ' -f2-)
  local description=$(echo "$task_details" | grep "Description:" | cut -d' ' -f2-)
  
  # Move task to In Progress
  ./kanban.sh move "$task_id" "In Progress" || error_exit "Failed to move task to In Progress"
  
  echo "Working on task: $task_id"
  echo "$task_details"
  echo ""
  
  # Prepare Claude prompt
  echo "Prompting Claude with task context..."
  echo ""
  echo "=== CLAUDE PROMPT ==="
  echo "I'm working on task $task_id: $title"
  echo "Description: $description"
  echo ""
  echo "After you complete this task, provide your solution along with CLI verification commands."
  echo "End your response with a line in this exact format:"
  echo "TASK-EVIDENCE: [your one-line summary of what was done with verification steps]"
  echo "=== END PROMPT ==="
  echo ""
  
  # Instructions for after Claude completes the task
  echo "When Claude completes the task, copy the TASK-EVIDENCE line and run:"
  echo "./cca-task.sh complete $task_id 'paste evidence here'"
}

# Complete a task with evidence
function complete_task() {
  local task_id="$1"
  local evidence="$2"
  
  # Input validation
  [ -z "$task_id" ] && error_exit "Task ID is required"
  [ -z "$evidence" ] && error_exit "Evidence is required"
  
  # Add evidence
  ./kanban.sh evidence "$task_id" "$evidence" || error_exit "Failed to add evidence"
  
  # Move to Needs Review
  ./kanban.sh move "$task_id" "Needs Review" || error_exit "Failed to move task to Needs Review"
  
  echo "Task $task_id updated with evidence and moved to Needs Review"
}

# Main command processing
case "$1" in
  process)
    process_task "$2"
    ;;
  complete)
    complete_task "$2" "$3"
    ;;
  *)
    echo "Claude Task Integration"
    echo "Usage:"
    echo "  ./cca-task.sh process TASK-ID"
    echo "  ./cca-task.sh complete TASK-ID 'Evidence'"
    ;;
esac
```

Make the Claude integration script executable:

```bash
chmod +x cca-task.sh
```
### 4. Installation and Setup

1. Save both scripts to your project root
2. Make them executable:

```bash
chmod +x kanban.sh cca-task.sh
```

3. Ensure `jq` is installed:

```bash
# For Ubuntu/Debian
sudo apt-get install jq

# For macOS
brew install jq

# For Windows (with Chocolatey)
choco install jq
```

### 5. Usage Examples

```bash
# Create a new task
./kanban.sh add "Implement PostgreSQL Repository" "Create a data repository for sentiment records using PostgreSQL" "Backend"

# View the board
./kanban.sh board

# Start working on a task with Claude
./cca-task.sh process SENTI-1683654321

# After Claude completes the task
./cca-task.sh complete SENTI-1683654321 "Implemented PostgreSQL repository with CRUD operations. Verified with 'curl -X POST http://localhost:3000/api/records' and database query 'SELECT * FROM sentiment_records'"

# Review task details
./kanban.sh show SENTI-1683654321

# Mark task as done after review
./kanban.sh move SENTI-1683654321 "Done"
```

## Benefits

- **Simple**: Minimal implementation with just two scripts
- **Reliable**: Error handling for common issues
- **Portable**: Works on any system with Bash and jq
- **Integrated**: Works seamlessly with Claude AI
- **Traceable**: Maintains evidence of task completion
- **Version-controlled**: JSON file can be committed to git

## Potential Enhancements (Optional)

- Add task priorities
- Add due dates
- Add assignees
- Add task dependencies
- Add task tags/labels
- Add task comments
- Add task attachments
- Add task time tracking

This approach gives you a simple but effective way to implement Kanban directly in your command-line workflow, making it easy for both you and Claude to track tasks and maintain a structured development process.