#!/bin/bash

# Simple script to add, commit, and push changes to Git.

# Define the commit message
COMMIT_MESSAGE="post phase4  UAT testing."

# Define the remote name (usually 'origin')
REMOTE_NAME="origin"

# Define the branch to push (optional, assumes current branch if not specified)
# BRANCH_NAME="main" # Uncomment and set if you want to specify the branch

echo "--- Starting Git Check-in ---"

# 1. Add all changes (new, modified, deleted files) to the staging area
echo "1. Staging all changes..."
git add .
if [ $? -ne 0 ]; then
  echo "Error: Failed to stage changes."
  exit 1
fi
echo "   Changes staged successfully."

# 2. Commit the staged changes with the specified message
echo "2. Committing changes..."
git commit -m "$COMMIT_MESSAGE"
if [ $? -ne 0 ]; then
  # Check if the error was 'nothing to commit' which is not a failure
  if [[ $(git status --porcelain) ]]; then
    echo "Error: Failed to commit changes."
    exit 1
  else
    echo "   No changes to commit."
    # Exit gracefully if there's nothing to commit
    echo "--- Git Check-in Finished (No changes) ---"
    exit 0
  fi
fi
echo "   Commit successful."

# 3. Push the commit to the remote repository
echo "3. Pushing changes to remote '$REMOTE_NAME'..."
# If you uncommented BRANCH_NAME above, use: git push $REMOTE_NAME $BRANCH_NAME
git push $REMOTE_NAME
if [ $? -ne 0 ]; then
  echo "Error: Failed to push changes to remote '$REMOTE_NAME'."
  exit 1
fi
echo "   Push successful."

echo "--- Git Check-in Finished Successfully ---"

exit 0
