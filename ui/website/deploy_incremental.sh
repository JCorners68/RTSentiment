#!/bin/bash
# Sentimark Incremental FTP Deployment Script
# This script deploys only changed files to the Bluehost server

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    echo -e "${BLUE}Loading configuration from .env file...${NC}"
    export $(grep -v '^#' .env | xargs)
fi

# Configuration
FTP_SERVER="${SENTIMARK_FTP_SERVER:-ftp.yubacityplumbingpro.com}"
FTP_PORT="${SENTIMARK_FTP_PORT:-21}"
FTP_USERNAME="${SENTIMARK_FTP_USERNAME:-sm_service@sentimark.ai}"
LOCAL_DIR="_site"  # Jekyll's output directory
REMOTE_DIR="${SENTIMARK_FTP_REMOTE_DIR:-}"
CACHE_DIR=".ftp-cache"
LAST_SYNC_FILE="$CACHE_DIR/last_sync_time"
CHANGED_FILES_LIST="$CACHE_DIR/changed_files.txt"

# Display script header
echo -e "${GREEN}=========================================${NC}"
echo -e "${GREEN}  Sentimark Incremental FTP Deployment${NC}"
echo -e "${GREEN}=========================================${NC}"

# Check if password is set in environment variable
if [ -z "$SENTIMARK_FTP_PASSWORD" ]; then
    echo -e "${RED}Error: FTP password not set in environment variable.${NC}"
    echo -e "${YELLOW}Please set the SENTIMARK_FTP_PASSWORD environment variable:${NC}"
    echo -e "${YELLOW}export SENTIMARK_FTP_PASSWORD='your_password'${NC}"
    exit 1
fi

# Check if Jekyll site has been built
if [ ! -d "$LOCAL_DIR" ]; then
    echo -e "${YELLOW}The _site directory does not exist. Building Jekyll site now...${NC}"
    bundle exec jekyll build
    
    if [ ! -d "$LOCAL_DIR" ]; then
        echo -e "${RED}Error: Failed to build Jekyll site.${NC}"
        exit 1
    fi
fi

# Create cache directory if it doesn't exist
mkdir -p "$CACHE_DIR"
touch "$CHANGED_FILES_LIST"

# Get current time for this sync
CURRENT_TIME=$(date +%s)

# Check for deployment exclude file and remove utility files
if [ -f "assets/images/.deployment_exclude" ]; then
    echo -e "${YELLOW}Found deployment exclusion rules, removing utility files from _site...${NC}"

    # Special handling for venv directories
    find "$LOCAL_DIR" -path "*/venv*" -type d -exec rm -rf {} + 2>/dev/null || true
    echo -e "${BLUE}Removed venv directories${NC}"

    # Read exclude patterns and remove matching files from _site
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip comments and empty lines
        if [[ "$line" =~ ^#.*$ ]] || [[ -z "$line" ]]; then
            continue
        fi

        # Skip venv patterns (already handled)
        if [[ "$line" == "venv/" ]] || [[ "$line" == "*venv/*" ]]; then
            continue
        fi

        # Find and remove files matching the pattern
        FOUND=$(find "$LOCAL_DIR" -name "$line" -type f | wc -l)
        if [ "$FOUND" -gt 0 ]; then
            echo -e "${BLUE}Removing $FOUND files matching '$line'${NC}"
            find "$LOCAL_DIR" -name "$line" -type f -delete
        fi
    done < "assets/images/.deployment_exclude"

    echo -e "${GREEN}Utility files removed from deployment${NC}"
fi

# Function to find changed files since last sync
find_changed_files() {
    if [ -f "$LAST_SYNC_FILE" ]; then
        LAST_SYNC_TIME=$(cat "$LAST_SYNC_FILE")
        echo -e "${BLUE}Last synchronization: $(date -d @$LAST_SYNC_TIME)${NC}"
        
        echo -e "${YELLOW}Finding files changed since last upload...${NC}"
        cd "$LOCAL_DIR" || exit 1
        
        # Find all files that have been modified since last sync
        find . -type f -newer "$LAST_SYNC_FILE" | sort > "$CHANGED_FILES_LIST"
        
        # Count changed files
        CHANGED_COUNT=$(wc -l < "$CHANGED_FILES_LIST")
        if [ "$CHANGED_COUNT" -eq 0 ]; then
            echo -e "${GREEN}No files have changed since last upload.${NC}"
            echo -e "${GREEN}Deployment not needed.${NC}"
            exit 0
        else
            echo -e "${YELLOW}$CHANGED_COUNT file(s) have changed since last upload.${NC}"
            if [ "$CHANGED_COUNT" -lt 10 ]; then
                echo -e "${BLUE}Changed files:${NC}"
                cat "$CHANGED_FILES_LIST" | sed 's/^\.\///'
            else
                echo -e "${BLUE}First 10 changed files:${NC}"
                head -10 "$CHANGED_FILES_LIST" | sed 's/^\.\///'
                echo -e "${BLUE}...and $(($CHANGED_COUNT - 10)) more${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}No previous sync found. All files will be uploaded.${NC}"
        cd "$LOCAL_DIR" || exit 1
        find . -type f | sort > "$CHANGED_FILES_LIST"
        CHANGED_COUNT=$(wc -l < "$CHANGED_FILES_LIST")
        echo -e "${YELLOW}$CHANGED_COUNT file(s) will be uploaded.${NC}"
    fi
}

# Function to determine if we should do a full sync
should_full_sync() {
    # If there's no last sync file, do a full sync
    if [ ! -f "$LAST_SYNC_FILE" ]; then
        return 0  # True
    fi
    
    # If number of changed files is more than 25% of total files, do a full sync
    TOTAL_FILES=$(find "$LOCAL_DIR" -type f | wc -l)
    PERCENT_CHANGED=$((CHANGED_COUNT * 100 / TOTAL_FILES))
    
    if [ "$PERCENT_CHANGED" -gt 25 ]; then
        echo -e "${YELLOW}$PERCENT_CHANGED% of files have changed. Performing full sync for efficiency.${NC}"
        return 0  # True
    else
        return 1  # False
    fi
}

# Find changed files
find_changed_files

# Determine sync method
if should_full_sync; then
    SYNC_METHOD="full"
else
    SYNC_METHOD="incremental"
fi

echo -e "${GREEN}Starting $SYNC_METHOD deployment to Bluehost...${NC}"
echo -e "${YELLOW}Connecting to FTP server: ${FTP_SERVER} on port ${FTP_PORT}${NC}"
echo -e "${YELLOW}Using username: ${FTP_USERNAME}${NC}"
echo -e "${YELLOW}Remote directory: ${REMOTE_DIR}${NC}"

# Create a temporary script file for lftp commands
TEMP_SCRIPT=$(mktemp)

# Common settings
cat > "$TEMP_SCRIPT" << EOF
# Connect to the FTP server
open -u "$FTP_USERNAME","$SENTIMARK_FTP_PASSWORD" -p "$FTP_PORT" "$FTP_SERVER"

# Set transfer mode and options
set ftp:ssl-allow true
set ssl:verify-certificate no
set ftp:list-options -a
set ftp:passive-mode on
set net:timeout 30
set net:max-retries 5
set net:reconnect-interval-base 5
set net:reconnect-interval-multiplier 1
EOF

# Add sync commands based on method
if [ "$SYNC_METHOD" = "full" ]; then
    # Full sync - mirror the entire directory
    cat >> "$TEMP_SCRIPT" << EOF
# Full sync - mirror the local directory to the remote directory
echo "Starting full file transfer to remote directory: root"
mirror --reverse --verbose=1 --parallel=5 \\
      --exclude-glob "venv/" \\
      --exclude-glob "__pycache__/" \\
      --exclude-glob "*.pyc" \\
      --exclude-glob "*.pyo" \\
      --exclude-glob "*.pyd" \\
      --exclude-glob "*.git/" \\
      --exclude-glob "node_modules/" \\
      . /
EOF
else
    # Incremental sync - only upload changed files
    echo -e "${YELLOW}Preparing incremental upload of $CHANGED_COUNT file(s)...${NC}"
    
    cat >> "$TEMP_SCRIPT" << EOF
# Change to the local directory for relative paths
lcd "$LOCAL_DIR"

# Strip leading slash from remote dir if present (prevents double slashes)
REMOTE_DIR_CLEAN="${REMOTE_DIR#/}"
# If remote dir is empty, don't add a trailing slash
if [ -n "$REMOTE_DIR_CLEAN" ]; then
    REMOTE_DIR_CLEAN="${REMOTE_DIR_CLEAN}/"
fi

# Create remote directories if needed and upload changed files
echo "Starting incremental file transfer to remote directory: ${REMOTE_DIR_CLEAN:-root}"
EOF
    
    # Add commands to upload each changed file
    while IFS= read -r file; do
        # Get the directory part of the file
        dir=$(dirname "$file")
        if [ "$dir" != "." ]; then
            # Create remote directory if it doesn't exist (ignore any errors)
            echo "mkdir -p \"${REMOTE_DIR_CLEAN}${dir#./}\"" >> "$TEMP_SCRIPT"
        fi

        # Upload the file
        echo "put -O \"${REMOTE_DIR_CLEAN}${dir#./}\" \"$file\"" >> "$TEMP_SCRIPT"
    done < "$CHANGED_FILES_LIST"
fi

# Add exit command
cat >> "$TEMP_SCRIPT" << EOF

# Exit lftp
bye
EOF

# Check if lftp is installed
if ! command -v lftp &> /dev/null; then
    echo -e "${RED}Error: lftp is not installed.${NC}"
    echo -e "${YELLOW}Please install lftp using the following command:${NC}"
    echo -e "sudo apt-get install lftp"
    rm "$TEMP_SCRIPT"
    exit 1
fi

# Execute the lftp commands
echo -e "${YELLOW}Executing FTP commands...${NC}"
cd "$LOCAL_DIR"
lftp -f "$TEMP_SCRIPT"

# Check if deployment was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Deployment to Bluehost completed successfully!${NC}"
    echo -e "${GREEN}Website is now live!${NC}"
    
    # Update the last sync time
    echo "$CURRENT_TIME" > "$LAST_SYNC_FILE"
    echo -e "${BLUE}Sync time updated: $(date -d @$CURRENT_TIME)${NC}"
else
    echo -e "${RED}Error: Deployment to Bluehost failed.${NC}"
    echo -e "${YELLOW}Please check your connection and credentials.${NC}"
fi

# Clean up the temporary script file
rm "$TEMP_SCRIPT"

echo -e "${GREEN}Deployment script completed.${NC}"