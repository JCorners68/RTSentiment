#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the new branch name
BRANCH_NAME="data_tier"

# Define the commit message
COMMIT_MESSAGE="Add local changes to data_tier branch"

echo "--- Creating and switching to new branch: $BRANCH_NAME ---"
git checkout -b $BRANCH_NAME

echo "--- Excluding sensitive files and workflows ---"
# Remove sensitive files and workflow files from git tracking
git rm --cached infrastructure/terraform/azure/credentials.json 2>/dev/null || true
git rm --cached infrastructure/terraform/azure/terraform.auto.tfvars 2>/dev/null || true
git rm --cached to_delete/rt-sentiment/.github/workflows/sit_to_uat.yml 2>/dev/null || true
git rm --cached .github/workflows/sit_to_uat.yml 2>/dev/null || true

echo "--- Updating gitignore ---"
# Add to .gitignore if not already there
grep -q "infrastructure/terraform/azure/credentials.json" .gitignore || echo "infrastructure/terraform/azure/credentials.json" >> .gitignore
grep -q "infrastructure/terraform/azure/terraform.auto.tfvars" .gitignore || echo "infrastructure/terraform/azure/terraform.auto.tfvars" >> .gitignore
grep -q ".github/workflows/" .gitignore || echo ".github/workflows/" >> .gitignore
grep -q "to_delete/rt-sentiment/.github/workflows/" .gitignore || echo "to_delete/rt-sentiment/.github/workflows/" >> .gitignore

echo "--- Adding all current changes to the staging area ---"
# Add all files in the current directory and subdirectories to the staging area
git add .

echo "--- Committing changes ---"
# Commit the staged changes with the predefined message
git commit -m "$COMMIT_MESSAGE"

echo "--- Pushing the new branch '$BRANCH_NAME' to origin ---"
# Push the new branch to the remote repository named 'origin'
git push -u origin $BRANCH_NAME

echo "--- Script finished successfully! ---"
echo "Branch '$BRANCH_NAME' created, changes committed, and pushed to origin."
echo "NOTE: Sensitive files and workflow files were excluded from the commit and push."