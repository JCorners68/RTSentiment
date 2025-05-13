#!/bin/bash
# Test script for removing utility files

# Read exclude patterns from file
if [ -f ".deployment_exclude" ]; then
  echo "Found deployment exclusion rules, removing utility files..."
  
  # Special handling for venv directories
  find ./images -path "*/venv*" -type d -exec rm -rf {} + 2>/dev/null || true
  echo "Removed venv directories"
  
  # Read exclude patterns and remove matching files from images
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
    FOUND=$(find ./images -name "$line" -type f | wc -l)
    if [ "$FOUND" -gt 0 ]; then
      echo "Removing $FOUND files matching '$line'"
      find ./images -name "$line" -type f -delete
    fi
  done < ".deployment_exclude"
  
  echo "Utility files removed from images directory"
fi

# Count remaining files
REMAINING=$(find ./images -name "*.py" -o -name "*.sh" -o -name "*_requirements.json" | wc -l)
echo "Remaining utility files: $REMAINING"