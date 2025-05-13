#!/bin/bash
# Script to fix file permissions for CLI Kanban
# This script ensures all executable files have the correct permissions
# and all scripts have Unix line endings (LF)

# Exit on error
set -e

# Display help message
show_help() {
    echo "Usage: $0 [options]"
    echo "Fix permissions and line endings for CLI Kanban files."
    echo
    echo "Options:"
    echo "  -h, --help      Show this help message"
    echo "  -v, --verbose   Enable verbose output"
    echo "  -d, --dry-run   Show what would be done without making changes"
    echo "  -f, --force     Force fix even if files appear to be correct"
    echo
    echo "Examples:"
    echo "  $0              Run with default settings"
    echo "  $0 --verbose    Run with verbose output"
    echo "  $0 --dry-run    Show what would be changed without making changes"
}

# Initialize variables
VERBOSE=0
DRY_RUN=0
FORCE=0
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_NAME=$(basename "$0")

# Process command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -h|--help)
            show_help
            exit 0
            ;;
        -v|--verbose)
            VERBOSE=1
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=1
            shift
            ;;
        -f|--force)
            FORCE=1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Log message with timestamp
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")
    
    if [ "$level" == "INFO" ] && [ $VERBOSE -eq 0 ]; then
        return
    fi
    
    echo "[$timestamp] $level: $message"
}

# Find Python files
find_python_files() {
    log "INFO" "Finding Python files..."
    find "$ROOT_DIR" -name "*.py" | grep -v "__pycache__" | grep -v ".pytest_cache" | grep -v "venv"
}

# Find Shell scripts
find_shell_scripts() {
    log "INFO" "Finding shell scripts..."
    find "$ROOT_DIR" -name "*.sh" | grep -v "venv"
}

# Find JavaScript files
find_js_files() {
    log "INFO" "Finding JavaScript files..."
    find "$ROOT_DIR" -name "*.js" | grep -v "node_modules"
}

# Fix permissions for file
fix_permissions() {
    local file="$1"
    local current_perms=$(stat -c "%a" "$file")
    
    # Check if file is a script and starts with shebang
    if head -n1 "$file" | grep -q "^#!"; then
        # Script file should be executable
        if [ "$current_perms" != "755" ] || [ $FORCE -eq 1 ]; then
            if [ $DRY_RUN -eq 0 ]; then
                chmod 755 "$file"
                log "CHANGED" "Made executable: $file (from $current_perms to 755)"
            else
                log "WOULD_CHANGE" "Would make executable: $file (from $current_perms to 755)"
            fi
        else
            log "INFO" "Already executable: $file"
        fi
    else
        # Regular file should be 644
        if [ "$current_perms" != "644" ] || [ $FORCE -eq 1 ]; then
            if [ $DRY_RUN -eq 0 ]; then
                chmod 644 "$file"
                log "CHANGED" "Fixed permissions: $file (from $current_perms to 644)"
            else
                log "WOULD_CHANGE" "Would fix permissions: $file (from $current_perms to 644)"
            fi
        else
            log "INFO" "Permissions OK: $file"
        fi
    fi
}

# Fix line endings
fix_line_endings() {
    local file="$1"
    
    # Check if file has CRLF line endings
    if grep -q $'\r' "$file"; then
        if [ $DRY_RUN -eq 0 ]; then
            # Create a temporary file
            temp_file=$(mktemp)
            # Convert CRLF to LF
            tr -d '\r' < "$file" > "$temp_file"
            # Replace original file
            mv "$temp_file" "$file"
            log "CHANGED" "Fixed line endings: $file"
        else
            log "WOULD_CHANGE" "Would fix line endings: $file"
        fi
    else
        log "INFO" "Line endings OK: $file"
    fi
}

# Ensure correct permissions for directories
fix_directory_permissions() {
    local directory="$1"
    local current_perms=$(stat -c "%a" "$directory")
    
    # Directories should be 755
    if [ "$current_perms" != "755" ] || [ $FORCE -eq 1 ]; then
        if [ $DRY_RUN -eq 0 ]; then
            chmod 755 "$directory"
            log "CHANGED" "Fixed directory permissions: $directory (from $current_perms to 755)"
        else
            log "WOULD_CHANGE" "Would fix directory permissions: $directory (from $current_perms to 755)"
        fi
    else
        log "INFO" "Directory permissions OK: $directory"
    fi
}

# Main function
main() {
    log "INFO" "Starting permission and line ending fixes in $ROOT_DIR"
    
    # Fix directories
    log "INFO" "Checking directory permissions..."
    find "$ROOT_DIR" -type d | while read -r dir; do
        if [[ "$dir" != *"venv"* ]] && [[ "$dir" != *"node_modules"* ]]; then
            fix_directory_permissions "$dir"
        fi
    done
    
    # Fix Python files
    log "INFO" "Checking Python files..."
    find_python_files | while read -r file; do
        fix_permissions "$file"
        fix_line_endings "$file"
    done
    
    # Fix shell scripts
    log "INFO" "Checking shell scripts..."
    find_shell_scripts | while read -r file; do
        fix_permissions "$file"
        fix_line_endings "$file"
    done
    
    # Fix JavaScript files
    log "INFO" "Checking JavaScript files..."
    find_js_files | while read -r file; do
        fix_permissions "$file"
        fix_line_endings "$file"
    done
    
    # Fix this script itself
    if [ $DRY_RUN -eq 0 ] && [ "$0" != "/dev/stdin" ]; then
        chmod 755 "$0"
        log "INFO" "Made this script executable: $0"
    fi
    
    log "INFO" "Completed permission and line ending fixes"
}

# Run the main function
main