#!/bin/bash
# Enhanced script for committing and pushing changes
# Includes additional safety checks, branch management, and interactive selection

set -e  # Exit on error

# Colors for terminal output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function for logging with timestamps
log() {
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    echo -e "${timestamp} - $1"
}

# Function to handle errors
handle_error() {
    ERROR_MSG="$1"
    log "${RED}Error: $ERROR_MSG${NC}"
    exit 1
}

# Function to display usage
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -m, --message \"MSG\"       Specify commit message (skips prompt)"
    echo "  -b, --branch BRANCH       Specify branch to push to (default: current branch)"
    echo "  -s, --select              Interactively select files to commit"
    echo "  -f, --force               Force push to remote"
    echo "  -h, --help                Display this help message"
    echo ""
    echo "Example:"
    echo "  $0 -m \"Fix deployment scripts\" -b feature/deployment"
    echo ""
    exit 1
}

# Default values
COMMIT_MESSAGE=""
BRANCH=""
SELECT_FILES=false
FORCE_PUSH=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -m|--message)
            COMMIT_MESSAGE="$2"
            shift 2
            ;;
        -b|--branch)
            BRANCH="$2"
            shift 2
            ;;
        -s|--select)
            SELECT_FILES=true
            shift
            ;;
        -f|--force)
            FORCE_PUSH=true
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Display banner
log "${BLUE}=====================================================${NC}"
log "${BLUE}      Git Commit and Push Assistant                   ${NC}"
log "${BLUE}=====================================================${NC}"

# Navigate to repository root
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
if [ -z "$REPO_ROOT" ]; then
    handle_error "Could not determine repository root. Are you in a git repository?"
fi

log "${YELLOW}Repository root identified as: ${GREEN}$REPO_ROOT${NC}"

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    handle_error "Not inside a git repository."
fi

# Save current directory to return to later
CURRENT_DIR=$(pwd)

# Move to repository root
cd "$REPO_ROOT"

# Get current branch
CURRENT_BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null || echo "DETACHED_HEAD")
if [ -z "$BRANCH" ]; then
    BRANCH="$CURRENT_BRANCH"
fi

if [ "$CURRENT_BRANCH" = "DETACHED_HEAD" ]; then
    handle_error "You are in 'detached HEAD' state. Please checkout a branch first."
fi

log "${YELLOW}Working on branch: ${GREEN}$BRANCH${NC}"

# Check for uncommitted changes
if [ -z "$(git status --porcelain)" ]; then
    log "${YELLOW}No changes to commit. Repository is clean.${NC}"
    exit 0
fi

# Show status before staging
log "${YELLOW}Current status:${NC}"
git status --short

# Handle file selection or stage all changes
if [ "$SELECT_FILES" = true ]; then
    log "${YELLOW}Entering interactive mode to select files...${NC}"
    git add -i
else
    log "${YELLOW}Staging all changes...${NC}"
    git add .
fi

# Count staged files
STAGED_COUNT=$(git diff --cached --name-only | wc -l)
if [ "$STAGED_COUNT" -eq 0 ]; then
    handle_error "No files staged for commit."
fi

log "${GREEN}$STAGED_COUNT files staged for commit${NC}"

# Show what's being committed
log "${YELLOW}Files to be committed:${NC}"
git diff --cached --name-only | sed 's/^/  /'

# Get commit message if not provided
if [ -z "$COMMIT_MESSAGE" ]; then
    echo ""
    echo -e "${YELLOW}Enter your commit message:${NC}"
    read -e COMMIT_MESSAGE
    
    # Validate commit message
    if [ -z "$COMMIT_MESSAGE" ]; then
        handle_error "Commit message cannot be empty."
    fi
fi

# Handle large commits
if [ "$STAGED_COUNT" -gt 1000 ]; then
    log "${YELLOW}Preparing to commit a large number of files ($STAGED_COUNT)...${NC}"
    git config --local core.compression 9
    git config --local http.postBuffer 524288000
fi

# Commit changes
log "${YELLOW}Committing changes with message:${NC}"
log "${GREEN}\"$COMMIT_MESSAGE\"${NC}"
git commit -m "$COMMIT_MESSAGE"

# Check if branch exists on remote
REMOTE_EXISTS=$(git ls-remote --heads origin "$BRANCH" | wc -l)

# Push to origin
log "${YELLOW}Pushing to origin/$BRANCH...${NC}"
PUSH_COMMAND="git push origin $BRANCH"

if [ "$FORCE_PUSH" = true ]; then
    log "${RED}WARNING: Force push enabled${NC}"
    PUSH_COMMAND="$PUSH_COMMAND --force"
elif [ "$REMOTE_EXISTS" -eq 0 ]; then
    log "${YELLOW}Remote branch doesn't exist yet. Setting upstream.${NC}"
    PUSH_COMMAND="$PUSH_COMMAND --set-upstream"
fi

# Execute push command
$PUSH_COMMAND
PUSH_STATUS=$?

# Final status
if [ $PUSH_STATUS -eq 0 ]; then
    log "${GREEN}Successfully committed and pushed changes!${NC}"
    
    # Show commit information
    COMMIT_HASH=$(git rev-parse HEAD)
    log "${YELLOW}Commit: ${GREEN}$COMMIT_HASH${NC}"
    log "${YELLOW}Branch: ${GREEN}$BRANCH${NC}"
    log "${YELLOW}Message: ${GREEN}$COMMIT_MESSAGE${NC}"
else
    log "${RED}Error pushing changes. You may need to push manually.${NC}"
    log "${YELLOW}Try: git push origin $BRANCH --force${NC}"
fi

# Return to original directory
cd "$CURRENT_DIR"

log "${BLUE}=====================================================${NC}"