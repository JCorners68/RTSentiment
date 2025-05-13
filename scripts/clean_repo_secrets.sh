#!/bin/bash
# Script to remove sensitive files from the clean repository
# Run this in the /tmp/clean_repo directory

echo "Removing sensitive files from the clean repository..."

# Create a strong .gitignore
cat >> .gitignore << 'EOL'
# Sensitive files that should not be tracked
*.tfstate
*.tfstate.backup
terraform.tfvars
*.tfbackend
storage_connection.txt
kubeconfig
*.key
*.pem
.env
.env.*
config/storage_connection.txt
credentials.json
*secret*
*password*
*credential*
*connection*
environments/sit/config/storage_connection.txt
environments/*/config/*connection*.txt
EOL

# Remove sensitive files
echo "Removing Terraform state files and credentials..."
find . -name "*.tfstate" -o -name "*.tfstate.backup" -exec git rm --cached {} \; 2>/dev/null

# Remove specific files mentioned in GitHub errors
files_to_remove=(
  "home/jonat/real_senti/environments/sit/config/storage_connection.txt"
  "home/jonat/real_senti/infrastructure/terraform/azure/terraform.tfstate"
  "home/jonat/real_senti/infrastructure/terraform/azure/terraform.tfstate.backup"
  "home/jonat/real_senti/infrastructure/terraform/azure/backends/sit.tfbackend"
)

for file in "${files_to_remove[@]}"; do
  if [ -f "$file" ]; then
    echo "Removing $file from git tracking..."
    git rm --cached "$file" 2>/dev/null || true
    # Replace with placeholder
    mkdir -p "$(dirname "$file")"
    echo "[CREDENTIALS REMOVED FOR SECURITY]" > "$file"
  fi
done

# Redact sensitive info in files
if [ -f "home/jonat/real_senti/infrastructure/terraform/azure/providers.tf" ]; then
  echo "Redacting providers.tf..."
  sed -i 's/\(client_id *=\) *"[^"]*"/\1 "[REDACTED]"/g' "home/jonat/real_senti/infrastructure/terraform/azure/providers.tf"
  sed -i 's/\(client_secret *=\) *"[^"]*"/\1 "[REDACTED]"/g' "home/jonat/real_senti/infrastructure/terraform/azure/providers.tf"
  sed -i 's/\(tenant_id *=\) *"[^"]*"/\1 "[REDACTED]"/g' "home/jonat/real_senti/infrastructure/terraform/azure/providers.tf"
  sed -i 's/\(subscription_id *=\) *"[^"]*"/\1 "[REDACTED]"/g' "home/jonat/real_senti/infrastructure/terraform/azure/providers.tf"
fi

if [ -f "home/jonat/real_senti/environments/sit/DEPLOYMENT_INSTRUCTIONS.md" ]; then
  echo "Redacting DEPLOYMENT_INSTRUCTIONS.md..."
  sed -i 's/\(CLIENT_ID=\)"[^"]*"/\1"[REDACTED]"/g' "home/jonat/real_senti/environments/sit/DEPLOYMENT_INSTRUCTIONS.md"
  sed -i 's/\(CLIENT_SECRET=\)"[^"]*"/\1"[REDACTED]"/g' "home/jonat/real_senti/environments/sit/DEPLOYMENT_INSTRUCTIONS.md"
  sed -i 's/\(TENANT_ID=\)"[^"]*"/\1"[REDACTED]"/g' "home/jonat/real_senti/environments/sit/DEPLOYMENT_INSTRUCTIONS.md"
  sed -i 's/\(SUBSCRIPTION_ID=\)"[^"]*"/\1"[REDACTED]"/g' "home/jonat/real_senti/environments/sit/DEPLOYMENT_INSTRUCTIONS.md"
fi

if [ -f "home/jonat/real_senti/environments/sit/continue_deploy.sh" ]; then
  echo "Redacting continue_deploy.sh..."
  sed -i 's/\(export SIT_CLIENT_ID=\)"[^"]*"/\1"[REDACTED]"/g' "home/jonat/real_senti/environments/sit/continue_deploy.sh"
  sed -i 's/\(export SIT_CLIENT_SECRET=\)"[^"]*"/\1"[REDACTED]"/g' "home/jonat/real_senti/environments/sit/continue_deploy.sh"
  sed -i 's/\(export SIT_TENANT_ID=\)"[^"]*"/\1"[REDACTED]"/g' "home/jonat/real_senti/environments/sit/continue_deploy.sh"
  sed -i 's/\(export SIT_SUBSCRIPTION_ID=\)"[^"]*"/\1"[REDACTED]"/g' "home/jonat/real_senti/environments/sit/continue_deploy.sh"
fi

# Commit changes
git add .gitignore
git add -A
git commit -m "Remove sensitive credentials for security"

echo "Done cleaning sensitive files from repository."
echo "You can now try pushing to GitHub again."
echo "git push origin data_tier_clean_purged_final --force"