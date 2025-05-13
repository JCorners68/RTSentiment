#!/bin/bash
# Purpose: Initializes Terraform configuration files from templates and credentials

set -euo pipefail

# Source environment variables
if ! source ~/.sentimark/bin/load-terraform-env.sh; then
    echo "Failed to load environment variables. Exiting."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Initializing Terraform configuration files..."

# Create providers.tf from template
if [ -f "templates/providers.tf.template" ]; then
    cp "templates/providers.tf.template" "providers.tf"
    echo "Created providers.tf"
else
    echo "Warning: providers.tf.template not found"
fi

# Create backend configuration files
for ENV in sit uat; do
    if [ -f "templates/backends/${ENV}.tfbackend.template" ]; then
        mkdir -p "backends"
        cp "templates/backends/${ENV}.tfbackend.template" "backends/${ENV}.tfbackend"
        echo "Created backends/${ENV}.tfbackend"
    else
        echo "Warning: backends/${ENV}.tfbackend.template not found"
    fi
done

# Create .terraform-init-timestamp to track when files were last generated
date > .terraform-init-timestamp

echo "Terraform initialization complete!"
echo "You can now run Terraform commands with the secure credentials."