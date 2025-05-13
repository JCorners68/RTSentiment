#!/bin/bash

# Script to completely remove large model files from git history using the direct approach
# Created on: May 7, 2025

echo "Starting final cleanup of large files from git history..."

# The specific file paths we need to clean
file1="services/data-acquisition/data/models/models--ProsusAI--finbert/blobs/e15a7b5738df7f17553399b6d94c6e2ff69c89245d066e8e5d183f5803a554e3"
file2="services/data-acquisition/data/models/models--ProsusAI--finbert/blobs/e5897858ff819aad7629b96ce521ae5477952d03634ef5dd30ed2d76357a9f00"

# Define new repo directory
new_repo_dir="/tmp/clean_repo"
current_dir=$(pwd)

# Ensure we're starting fresh
rm -rf "$new_repo_dir"
mkdir -p "$new_repo_dir"

# Get current branch name
current_branch=$(git rev-parse --abbrev-ref HEAD)
new_branch="${current_branch}_final"

# Create a complete .gitignore file with all model paths
cat > .gitignore << EOL
# Project specific ignores
node_modules/
*.log
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Large model files that exceeded GitHub limits
data/models/
services/data-acquisition/data/models/
models--ProsusAI--finbert/

# Model file extensions
*.bin
*.pt
*.pth
*.h5
*.onnx
*.model
*.safetensors
*.tflite
*.pb

# Temporary files
*.swp
*.swo
.DS_Store
.idea/
.vscode/
*.tmp
EOL

echo "Updated .gitignore file with all necessary exclusions"

# Create a new git repo without the large files
echo "Creating a clean git repository..."
git init "$new_repo_dir"
cd "$new_repo_dir"

# Set up remote
remote_url=$(cd "$current_dir" && git remote get-url origin)
git remote add origin "$remote_url"

# Create a README for the first commit
echo "# Real-time Sentiment Analysis" > README.md
git add README.md
git commit -m "Initial commit with README"

# Create new branch
git checkout -b "$new_branch"

# Copy over all files from original repo except excluded ones
echo "Copying files from original repository (excluding large files)..."
find "$current_dir" -type f -not -path "*/\.*" -not -path "*/.git/*" \
  -not -path "*/data/models/*" \
  -not -path "*/services/data-acquisition/data/models/*" \
  -not -path "$current_dir/scripts/final_git_fix.sh" \
  -exec cp --parents {} "$new_repo_dir" \;

# Copy the .gitignore file
cp "$current_dir/.gitignore" "$new_repo_dir/"

# Stage all files
git add .

# Copy over the git commit history message only
echo "Creating new commit with all files..."
latest_commit_msg=$(cd "$current_dir" && git log -1 --pretty=%B)
git commit -m "$latest_commit_msg"

echo "Clean repository created at: $new_repo_dir"
echo ""
echo "To complete the process:"
echo "1. cd $new_repo_dir"
echo "2. Verify the repository content: git status"
echo "3. Double-check that large files are gone: du -sh ."
echo "4. Push to GitHub: git push origin $new_branch --force"
echo "5. On GitHub, make $new_branch the default branch"
echo ""
echo "If everything looks good, you can replace your original repo with this clean one:"
echo "1. cd $current_dir/.."
echo "2. mv $current_dir ${current_dir}_backup"
echo "3. mv $new_repo_dir $current_dir"
echo ""
echo "WARNING: This is a drastic approach that creates a completely new repo."
echo "History and commit messages beyond the latest commit will be lost."