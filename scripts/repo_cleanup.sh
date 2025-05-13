#!/bin/bash
set -e

echo "=== Repository Cleanup Script ==="
echo "This script will clean up secrets and consolidate your Git repository"

# 1. Update .gitignore to exclude secrets and temporary files
cat << 'EOF' > /home/jonat/real_senti/.gitignore
# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
dist/
build/
*.egg-info/

# Virtual environments
venv/
env/
ENV/
.env/
.venv/
azure_venv/

# Terraform
.terraform/
.terraform.lock.hcl
*.tfstate
*.tfstate.*
*.tfvars
override.tf
override.tf.json
*_override.tf
*_override.tf.json
terraform.log

# Credentials and secrets
.env
*.key
*.pem
*.pfx
*.p12
credentials*
*token*
*secret*
*password*
.aws/
.azure/

# Jupyter Notebook
.ipynb_checkpoints/

# IDE specific files
.idea/
.vscode/
*.swp
*.swo

# Data and ML model files
*.h5
*.pkl
*.bin
*.onnx
*.pt
services/data-acquisition/data/models/

# Temp directories
to_delete/
temp*/
*/temp/

# Local configuration
.claude/settings.local.json

# Logs
logs/
*.log

# OS specific
.DS_Store
.Trash
Thumbs.db
EOF

# 2. Clean up large files and secrets
echo "Cleaning up large files and sensitive data..."
find . -name "*.pem" -o -name "*.key" -o -name "credentials*" -o -name "*secret*" -o -name "*password*" -o -name "*token*" | grep -v "example\|placeholder" > secrets_to_remove.txt

if [ -s secrets_to_remove.txt ]; then
  echo "Found potential secrets in the following files:"
  cat secrets_to_remove.txt
  echo "Please review these files and remove sensitive data manually."
  echo "After cleaning, you can use 'git filter-repo' to purge them from history."
else
  echo "No obvious secret files found."
fi

# 3. Clean remote URL of tokens
git remote -v | grep -q "ghp_" && {
  echo "Removing token from remote URL..."
  git remote set-url origin https://github.com/JCorners68/RTSentiment.git
}

# 4. Create a clean branch based on your preferred state
echo "Which branch would you like to use as the base for a clean branch? (default: data_tier_clean_purged)"
read branch_name
branch_name=${branch_name:-data_tier_clean_purged}

echo "Creating a new clean branch 'clean_main' based on $branch_name..."
git checkout $branch_name
git checkout -b clean_main

# 5. Instructions for final cleanup
cat << 'EOF'

=== NEXT STEPS ===

1. Review the secrets_to_remove.txt file and clean any sensitive data

2. To permanently remove sensitive data from Git history, install git-filter-repo:
   pip install git-filter-repo

3. Then run this command to remove files with sensitive data:
   git filter-repo --path-glob "*token*" --path-glob "*secret*" --path-glob "*password*" --path-glob "credentials*" --invert-paths

4. Force push your clean branch:
   git push -f origin clean_main:main

5. Delete unnecessary branches:
   git branch -D data_tier data_tier_clean reorganized_code_branch sync_main_to_data_tier temp_main terraform-azure-setup terraform-azure-setup-temp terraform-uat-setup update_architecture_docs

6. Push only the clean branches:
   git push origin clean_main:main

WARNING: Force pushing will overwrite history on the remote. Make sure you have a backup of your code.
EOF

echo "Script completed!"