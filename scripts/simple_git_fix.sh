#!/bin/bash
set -e

echo "=== Simple Git Repository Fix ==="

# 1. Create a new branch based on main that ignores tracked sensitive files
git checkout -b fresh_start

# 2. Update .gitignore to exclude sensitive files
cat << 'EOF' >> /home/jonat/real_senti/.gitignore

# Additional ignores for sensitive files
*.tfstate
*.tfstate.backup
terraform.tfvars
*.tfbackend
storage_connection.txt
kubeconfig
*.key
*.pem
config/storage_connection.txt
infrastructure/terraform/azure/.terraform/
infrastructure/terraform/azure/.terraform.lock.hcl
EOF

# 3. Reset the repository state to make changes take effect
git rm -r --cached .
git add .
git commit -m "Reset repository with updated .gitignore"

# 4. Fix remote URL
git remote set-url origin https://github.com/JCorners68/RTSentiment.git

# 5. Display instructions
cat << 'EOF'

=== NEXT STEPS ===

Your repository has been reset with a proper .gitignore to prevent sensitive files.

To continue working:

1. Verify that sensitive files are no longer tracked:
   git status

2. Push this clean branch to a new repository:
   git push -u origin fresh_start

3. On GitHub, create a new clean repository and use this as your new main

4. If you want to clean up disk space:
   git gc --aggressive --prune=now

NOTE: The history still contains sensitive data but new commits won't add more.
For a complete cleanup, you'd need to create a new repository and copy just the
code (without .git directory).

EOF