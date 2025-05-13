#!/bin/bash
set -e

echo "=== Repository Finalization Script ==="

# 1. Ensure we're on the clean_main branch
if [[ $(git branch --show-current) != "clean_main" ]]; then
  git checkout clean_main
fi

# 2. Update .gitignore with all patterns from to_do_password.md
cat << 'EOF' >> /home/jonat/real_senti/.gitignore

# Additional ignores from to_do_password.md
*.tfstate
*.tfstate.backup
terraform.tfvars
*.tfbackend
storage_connection.txt
kubeconfig
*.key
*.pem
config/storage_connection.txt
.terraform/
.terraform.lock.hcl
EOF

# 3. Remove currently tracked files that match the ignore patterns
git rm -r --cached "*.tfstate" "*.tfstate.backup" "terraform.tfvars" "*.tfbackend" "*.key" "*.pem" 2>/dev/null || true
git rm -r --cached infrastructure/terraform/azure/.terraform/ 2>/dev/null || true
git rm -r --cached infrastructure/terraform/azure/.terraform.lock.hcl 2>/dev/null || true
git rm -r --cached environments/sit/config/storage_connection.txt 2>/dev/null || true

# 4. Add and commit changes
git add .gitignore
git commit -m "Update .gitignore to exclude sensitive files"

# 5. Clean untracked files (optional - commented out for safety)
# echo "The following files will be removed:"
# git clean -n -d
# read -p "Remove these files? (y/n) " answer
# if [[ $answer == "y" ]]; then
#   git clean -f -d
# fi

echo "==== Next Steps ===="
echo "1. Review changes with: git status"
echo "2. Push to your repository with: git push origin clean_main:main -f"
echo "3. Set main as default branch in GitHub repository settings"
echo "4. Delete other branches locally with: git branch -D branch_name"
echo "5. Delete remote branches with: git push origin --delete branch_name"