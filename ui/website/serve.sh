#!/bin/bash
# Script to build and serve the Jekyll site locally

# Function for logging
log() {
  echo "[$(date +"%Y-%m-%d %H:%M:%S")] $1"
}

log "Setting up local development server for Sentimark website"

# Install dependencies if needed
if [ ! -f "Gemfile.lock" ]; then
  log "Installing dependencies..."
  bundle install
fi

# Get WSL IP address for access from Windows
WSL_IP=$(ip addr show eth0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')

log "Starting Jekyll server with livereload..."
log "Once running, you can access the site at:"
log "- From WSL: http://localhost:4000"
log "- From Windows: http://$WSL_IP:4000"

# Start Jekyll server with livereload enabled
bundle exec jekyll serve --livereload --host=0.0.0.0
