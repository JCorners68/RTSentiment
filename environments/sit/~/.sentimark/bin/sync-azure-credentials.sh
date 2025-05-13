#!/bin/bash
# Purpose: Syncs credentials from Azure Key Vault to local password store

set -euo pipefail

# Ensure we're logged in to Azure
if ! az account show &>/dev/null; then
    echo "Not logged in to Azure. Initiating login..."
    az login
fi

echo "Fetching credentials from Azure Key Vault..."

# Array of credential names to sync
credential_names=(
    "AZURE-CLIENT-ID"
    "AZURE-CLIENT-SECRET"
    "AZURE-SUBSCRIPTION-ID"
    "AZURE-TENANT-ID"
)

# Vault name
vault_name="sentimark-credentials"

# Check if vault exists, if not create it
if ! az keyvault show --name "$vault_name" &>/dev/null; then
    echo "Key Vault '$vault_name' not found. Creating it..."
    
    # Create resource group if it doesn't exist
    rg_name="sentimark-security-rg"
    if ! az group show --name "$rg_name" &>/dev/null; then
        echo "Creating resource group '$rg_name'..."
        az group create --name "$rg_name" --location eastus
    fi
    
    # Create Key Vault with purge protection
    echo "Creating Key Vault..."
    az keyvault create \
      --name "$vault_name" \
      --resource-group "$rg_name" \
      --location eastus \
      --enable-purge-protection true \
      --retention-days 90
      
    echo "Key Vault created successfully!"
    
    # Add initial dummy values for credentials if they don't exist
    # In a real scenario, you would securely collect these from the user
    for cred_name in "${credential_names[@]}"; do
        if ! az keyvault secret show --vault-name "$vault_name" --name "$cred_name" &>/dev/null; then
            echo "Creating placeholder for $cred_name..."
            az keyvault secret set --vault-name "$vault_name" --name "$cred_name" --value "placeholder-value"
        fi
    done
    
    echo "Please update these placeholder values with real credentials using the Azure portal or CLI before using them."
    echo "Example: az keyvault secret set --vault-name \"$vault_name\" --name \"AZURE-CLIENT-ID\" --value \"your-client-id\""
fi

# Ensure pass is installed and properly set up
if ! command -v pass &>/dev/null; then
    echo "pass is not installed. Installing..."
    
    # Check for package manager and install pass
    if command -v apt-get &>/dev/null; then
        sudo apt-get update
        sudo apt-get install -y pass gnupg2
    elif command -v yum &>/dev/null; then
        sudo yum install -y pass gnupg2
    elif command -v brew &>/dev/null; then
        brew install pass gnupg2
    else
        echo "Error: Could not install pass. Please install it manually."
        exit 1
    fi
fi

# Check if pass is initialized
if ! pass show &>/dev/null; then
    echo "Initializing pass password store..."
    
    # Check if a GPG key exists
    gpg_key=$(gpg --list-secret-keys --keyid-format LONG | grep sec | head -n 1 | awk '{print $2}' | cut -d'/' -f2)
    
    if [ -z "$gpg_key" ]; then
        echo "No GPG key found. Generating a new one..."
        echo "Please follow the prompts to generate a GPG key."
        echo "Recommended settings:"
        echo "- Kind: RSA and RSA"
        echo "- Size: 4096"
        echo "- Expiration: 0 (does not expire)"
        echo "- Name: Sentimark Azure Credentials"
        
        # Generate a GPG key interactively
        gpg --full-generate-key
        
        # Get the newly created key
        gpg_key=$(gpg --list-secret-keys --keyid-format LONG | grep sec | head -n 1 | awk '{print $2}' | cut -d'/' -f2)
    fi
    
    # Initialize pass with the GPG key
    pass init "$gpg_key"
    echo "Pass initialized with GPG key: $gpg_key"
fi

# Create the sentimark/azure directory structure in pass
pass show sentimark &>/dev/null || pass insert -m sentimark/dummy >/dev/null <<< "dummy value"
pass rm -f sentimark/dummy &>/dev/null || true

# Sync each credential
for cred_name in "${credential_names[@]}"; do
    echo "Syncing $cred_name..."
    
    # Fetch secret from Key Vault
    secret_value=$(az keyvault secret show --vault-name "$vault_name" --name "$cred_name" --query value -o tsv)
    
    if [ -z "$secret_value" ]; then
        echo "Error: Could not retrieve $cred_name from Key Vault"
        exit 1
    fi
    
    # Store in pass
    echo "$secret_value" | pass insert -f "sentimark/azure/$cred_name"
done

echo "Credentials successfully synced to local password store."
echo "To view credentials: pass show sentimark/azure/AZURE-CLIENT-ID"