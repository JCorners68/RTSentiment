#!/bin/bash
# Purpose: Loads Azure credentials from pass into environment variables

set -euo pipefail

# Check if pass store exists
if ! pass show sentimark/azure/AZURE-CLIENT-ID &>/dev/null; then
    echo "Azure credentials not found in password store. Run sync-azure-credentials.sh first."
    exit 1
fi

# Load credentials from pass
export TF_VAR_client_id=$(pass show sentimark/azure/AZURE-CLIENT-ID)
export TF_VAR_client_secret=$(pass show sentimark/azure/AZURE-CLIENT-SECRET)
export TF_VAR_subscription_id=$(pass show sentimark/azure/AZURE-SUBSCRIPTION-ID)
export TF_VAR_tenant_id=$(pass show sentimark/azure/AZURE-TENANT-ID)

# Export backend configuration variables
export ARM_CLIENT_ID=$TF_VAR_client_id
export ARM_CLIENT_SECRET=$TF_VAR_client_secret
export ARM_SUBSCRIPTION_ID=$TF_VAR_subscription_id
export ARM_TENANT_ID=$TF_VAR_tenant_id

# Verify exports were successful
if [ -z "$TF_VAR_client_id" ] || [ -z "$ARM_CLIENT_ID" ]; then
    echo "Error: Failed to load credentials"
    exit 1
fi

echo "Azure credentials loaded successfully!"
echo "Variables exported: TF_VAR_* and ARM_*"