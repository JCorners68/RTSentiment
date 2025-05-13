#!/bin/bash
# Script for deploying the Jekyll site to Bluehost

set -e

# Function for logging
log() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1"
}

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
  log "Loading configuration from .env file..."
  export $(grep -v '^#' .env | xargs)
fi

# Configuration
BUILD_DIR="_site"
FTP_HOST="${SENTIMARK_FTP_SERVER:-ftp.yubacityplumbingpro.com}"
FTP_PORT="${SENTIMARK_FTP_PORT:-21}"
FTP_USER="${SENTIMARK_FTP_USERNAME:-}"
FTP_PASS="${SENTIMARK_FTP_PASSWORD:-}"
REMOTE_DIR="${SENTIMARK_FTP_REMOTE_DIR:-}"

# Check if credentials are available
if [ -z "$FTP_USER" ] || [ -z "$FTP_PASS" ]; then
  log "Error: FTP credentials not found"
  log "Please create a .env file based on .env.example with your FTP credentials"
  exit 1
fi

# Build the site
log "Building Jekyll site..."
bundle install
JEKYLL_ENV=production bundle exec jekyll build

if [ ! -d "$BUILD_DIR" ]; then
  log "Error: Build failed. The _site directory was not created."
  exit 1
fi

# Check for deployment exclude file and remove utility files
if [ -f "assets/images/.deployment_exclude" ]; then
  log "Found deployment exclusion rules, removing utility files from _site..."

  # Special handling for venv directories
  find "$BUILD_DIR" -path "*/venv*" -type d -exec rm -rf {} + 2>/dev/null || true
  log "Removed venv directories"

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
    FOUND=$(find "$BUILD_DIR" -name "$line" -type f | wc -l)
    if [ "$FOUND" -gt 0 ]; then
      log "Removing $FOUND files matching '$line'"
      find "$BUILD_DIR" -name "$line" -type f -delete
    fi
  done < "assets/images/.deployment_exclude"

  log "Utility files removed from deployment"
fi

# Deploy via FTP
log "Deploying to Bluehost..."
cd "$BUILD_DIR"

# Create a temporary lftp script
LFTP_SCRIPT=$(mktemp)
cat > $LFTP_SCRIPT << EOF
open -u $FTP_USER,$FTP_PASS $FTP_HOST
lcd .
cd $REMOTE_DIR
# mirror with only newer files
mirror -R --only-newer .
bye
EOF

# Execute the lftp script
lftp -f $LFTP_SCRIPT

# Clean up
rm $LFTP_SCRIPT

log "Deployment completed successfully!"

# Verify deployment
log "Verifying deployment..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://sentimark.com/)
if [ "$HTTP_CODE" -eq 200 ]; then
  log "Verification successful: Site is accessible (HTTP 200)"
else
  log "Warning: Site verification returned HTTP code $HTTP_CODE. Please check manually."
fi

# Return to original directory
cd ..

log "Deployment process completed."
