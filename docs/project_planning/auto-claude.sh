#!/bin/bash

# auto-claude.sh - Automatically updates Kanban based on Claude's responses

TASK_ID="$1"
[ -z "$TASK_ID" ] && echo "Error: Task ID required" && exit 1

# Verify task exists
./kanban.sh show "$TASK_ID" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "Error: Task $TASK_ID not found"
  exit 1
fi

# Move task to In Progress
./kanban.sh move "$TASK_ID" "In Progress"

# Get task details
TASK_DETAILS=$(./kanban.sh show "$TASK_ID")
TITLE=$(echo "$TASK_DETAILS" | grep "Title:" | cut -d' ' -f2-)
DESCRIPTION=$(echo "$TASK_DETAILS" | grep "Description:" | cut -d' ' -f2-)

# Create temporary file for Claude's output
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

# Inform user
echo "Starting Claude for task $TASK_ID: $TITLE"
echo "Claude's response will be captured and the Kanban board will be updated automatically"
echo "Press Enter to start..."
read

# Run Claude and capture its output
(claude << EOF
I'm working on task $TASK_ID: $TITLE
Description: $DESCRIPTION

Please implement this task completely, providing CLI commands to verify functionality.
End your response with a TASK-EVIDENCE line as specified in CLAUDE.md.
EOF
) | tee $TEMP_FILE

# Extract TASK-EVIDENCE line
EVIDENCE=$(grep "TASK-EVIDENCE:" $TEMP_FILE | sed 's/TASK-EVIDENCE: //')

# If evidence was found, update the Kanban
if [ -n "$EVIDENCE" ]; then
  echo -e "\n\nTask completed! Updating Kanban board..."
  ./kanban.sh evidence "$TASK_ID" "$EVIDENCE"
  ./kanban.sh move "$TASK_ID" "Needs Review"
  echo "Kanban updated successfully. Task moved to Needs Review."
else
  echo -e "\n\nNo TASK-EVIDENCE line found in Claude's response."
  echo "Please manually extract the evidence and update the Kanban using:"
  echo "./kanban.sh evidence $TASK_ID \"your evidence here\""
  echo "./kanban.sh move $TASK_ID \"Needs Review\""
fi
