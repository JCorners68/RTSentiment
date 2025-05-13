#!/bin/bash
# Script to set up Azure Storage for Terraform state with locking
# This creates the necessary Azure resources for remote state storage
# Enhanced with testing and verification capabilities

set -e

# Set colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="sit"
LOCATION="eastus"
PREFIX="sentimark"
TEST_MODE=false
VERIFY_ONLY=false
SKIP_ROLE_ASSIGNMENT=false

# Function to display usage information
show_usage() {
  echo "Usage: $0 [OPTIONS]"
  echo "Create Azure Storage Account for Terraform state management with locking"
  echo
  echo "Options:"
  echo "  -e, --environment ENV     Environment name: sit, uat, prod (default: sit)"
  echo "  -l, --location LOCATION   Azure region (default: eastus)"
  echo "  -p, --prefix PREFIX       Resource prefix (default: sentimark)"
  echo "  -t, --test                Test mode - verify permissions without creating resources"
  echo "  -v, --verify-only         Only verify the backend, don't create resources"
  echo "  -s, --skip-role           Skip service principal role assignments"
  echo "  -h, --help                Show this help message"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -e|--environment)
      ENVIRONMENT="$2"
      shift 2
      ;;
    -l|--location)
      LOCATION="$2"
      shift 2
      ;;
    -p|--prefix)
      PREFIX="$2"
      shift 2
      ;;
    -t|--test)
      TEST_MODE=true
      shift
      ;;
    -v|--verify-only)
      VERIFY_ONLY=true
      shift
      ;;
    -s|--skip-role)
      SKIP_ROLE_ASSIGNMENT=true
      shift
      ;;
    -h|--help)
      show_usage
      exit 0
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      show_usage
      exit 1
      ;;
  esac
done

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(sit|uat|prod)$ ]]; then
  echo -e "${RED}Error: Environment must be sit, uat, or prod${NC}"
  exit 1
fi

# Generate names
RESOURCE_GROUP_NAME="${PREFIX}-${ENVIRONMENT}-rg"
STORAGE_ACCOUNT_NAME="${PREFIX}${ENVIRONMENT}terraform"
CONTAINER_NAME="tfstate"

echo -e "${BLUE}Setting up Terraform state storage for ${ENVIRONMENT} environment${NC}"
echo "  Resource Group: ${RESOURCE_GROUP_NAME}"
echo "  Storage Account: ${STORAGE_ACCOUNT_NAME}"
echo "  Container: ${CONTAINER_NAME}"

# Check if logged in to Azure
echo -e "${BLUE}Checking Azure CLI login...${NC}"
if ! az account show &>/dev/null; then
  echo -e "${RED}Not logged in to Azure. Please run 'az login' first.${NC}"
  exit 1
fi

# Get current subscription info for display
SUBSCRIPTION_NAME=$(az account show --query name -o tsv)
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
echo -e "${GREEN}Using subscription: ${SUBSCRIPTION_NAME} (${SUBSCRIPTION_ID})${NC}"

# Check if we're running with a service principal
CLIENT_ID=$(az account show --query user.name -o tsv | grep -E '^[0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}$' || echo "")
if [ -n "$CLIENT_ID" ]; then
  echo -e "${BLUE}Detected use of service principal for authentication${NC}"
  IS_SERVICE_PRINCIPAL=true
else
  echo -e "${BLUE}Using user authentication${NC}"
  IS_SERVICE_PRINCIPAL=false
fi

# Function to verify service principal permissions
verify_permissions() {
  echo -e "${BLUE}Verifying service principal permissions...${NC}"

  # Check Resource Group permission
  echo -ne "  Resource Group Contributor... "
  if az group show --name "$RESOURCE_GROUP_NAME" &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
  else
    echo -e "${YELLOW}⚠ (Will attempt to create)${NC}"
  fi

  # Check Storage Account permission
  if [ -n "$STORAGE_ACCOUNT_NAME" ]; then
    echo -ne "  Storage Account Contributor... "
    if az storage account show --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" &>/dev/null; then
      echo -e "${GREEN}✓${NC}"

      # Check Blob Data Contributor permission
      echo -ne "  Storage Blob Data Contributor... "
      if az storage container exists --name "$CONTAINER_NAME" --account-name "$STORAGE_ACCOUNT_NAME" --auth-mode login &>/dev/null; then
        echo -e "${GREEN}✓${NC}"
      else
        echo -e "${YELLOW}⚠ (May need to assign role)${NC}"
      fi
    else
      echo -e "${YELLOW}⚠ (Will attempt to create)${NC}"
    fi
  fi
}

# If in test mode, just verify permissions and exit
if [ "$TEST_MODE" = true ]; then
  echo -e "${YELLOW}Running in TEST MODE - no resources will be created${NC}"
  verify_permissions

  # Create backend config file only in test mode
  mkdir -p backends
  BACKEND_FILE="backends/${ENVIRONMENT}.tfbackend"

  echo -e "${BLUE}Creating backend configuration file: $BACKEND_FILE${NC}"
  cat > "$BACKEND_FILE" << EOF
resource_group_name  = "${RESOURCE_GROUP_NAME}"
storage_account_name = "${STORAGE_ACCOUNT_NAME}"
container_name       = "${CONTAINER_NAME}"
key                  = "${ENVIRONMENT}.terraform.tfstate"
use_azuread_auth     = true
EOF

  echo -e "${GREEN}Backend configuration file created successfully!${NC}"
  echo -e "${YELLOW}Test completed. Run without --test to create resources.${NC}"
  exit 0
fi

# If verify only, check if resources exist without creating them
if [ "$VERIFY_ONLY" = true ]; then
  echo -e "${YELLOW}Running in VERIFY-ONLY mode - checking existing resources${NC}"
  verify_permissions

  # Check resource group
  echo -ne "${BLUE}Checking if resource group exists... ${NC}"
  if az group show --name "$RESOURCE_GROUP_NAME" &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
  else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}Resource group $RESOURCE_GROUP_NAME does not exist!${NC}"
    exit 1
  fi

  # Check storage account
  echo -ne "${BLUE}Checking if storage account exists... ${NC}"
  if az storage account show --name "$STORAGE_ACCOUNT_NAME" --resource-group "$RESOURCE_GROUP_NAME" &>/dev/null; then
    echo -e "${GREEN}✓${NC}"
  else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}Storage account $STORAGE_ACCOUNT_NAME does not exist!${NC}"
    exit 1
  fi

  # Check container
  echo -ne "${BLUE}Checking if container exists... ${NC}"
  if az storage container exists --name "$CONTAINER_NAME" --account-name "$STORAGE_ACCOUNT_NAME" --auth-mode login --query exists -o tsv | grep -q "true"; then
    echo -e "${GREEN}✓${NC}"
  else
    echo -e "${RED}✗${NC}"
    echo -e "${RED}Container $CONTAINER_NAME does not exist!${NC}"
    exit 1
  fi

  echo -e "${GREEN}Verification completed successfully! All required resources exist.${NC}"
  exit 0
fi

# Create resource group if it doesn't exist
echo -e "${BLUE}Creating resource group if it doesn't exist...${NC}"
if ! az group show --name "${RESOURCE_GROUP_NAME}" &>/dev/null; then
  az group create --name "${RESOURCE_GROUP_NAME}" --location "${LOCATION}" --output none
  if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to create resource group ${RESOURCE_GROUP_NAME}!${NC}"
    echo -e "${YELLOW}This may be due to insufficient permissions. Check that you have Contributor role.${NC}"
    exit 1
  fi
  echo -e "${GREEN}Resource group created successfully!${NC}"
else
  echo -e "${GREEN}Resource group already exists.${NC}"
fi

# Create storage account if it doesn't exist
echo -e "${BLUE}Creating storage account if it doesn't exist...${NC}"
if ! az storage account show --name "${STORAGE_ACCOUNT_NAME}" --resource-group "${RESOURCE_GROUP_NAME}" &>/dev/null; then
  if ! az storage account create \
    --name "${STORAGE_ACCOUNT_NAME}" \
    --resource-group "${RESOURCE_GROUP_NAME}" \
    --location "${LOCATION}" \
    --sku "Standard_LRS" \
    --kind "StorageV2" \
    --https-only true \
    --allow-blob-public-access false \
    --tags "environment=${ENVIRONMENT}" "usage=terraform-state" \
    --output none; then

    echo -e "${RED}Failed to create storage account ${STORAGE_ACCOUNT_NAME}!${NC}"
    echo -e "${YELLOW}This may be due to insufficient permissions or a naming conflict.${NC}"
    echo -e "${YELLOW}Storage account names must be globally unique and only use lowercase letters and numbers.${NC}"
    exit 1
  fi
  echo -e "${GREEN}Storage account created successfully!${NC}"
else
  echo -e "${GREEN}Storage account already exists.${NC}"
fi

# Enable versioning for data protection
echo -e "${BLUE}Enabling blob versioning...${NC}"
if ! az storage account blob-service-properties update \
  --account-name "${STORAGE_ACCOUNT_NAME}" \
  --resource-group "${RESOURCE_GROUP_NAME}" \
  --enable-versioning true \
  --output none; then

  echo -e "${YELLOW}Warning: Could not enable blob versioning. This is recommended but not required.${NC}"
fi

# Add resource lock to prevent accidental deletion
echo -e "${BLUE}Adding resource lock to prevent accidental deletion...${NC}"
if ! az lock create --name "terraform-state-lock" --resource-group "${RESOURCE_GROUP_NAME}" \
  --resource-name "${STORAGE_ACCOUNT_NAME}" --resource-type "Microsoft.Storage/storageAccounts" \
  --lock-type CanNotDelete --notes "Protect Terraform state storage" &>/dev/null; then

  echo -e "${YELLOW}Warning: Could not create resource lock. This is recommended but not required.${NC}"
  echo -e "${YELLOW}Resource locks require Owner role on the subscription.${NC}"
fi

# Create container if it doesn't exist
echo -e "${BLUE}Creating container if it doesn't exist...${NC}"
if ! az storage container exists --name "${CONTAINER_NAME}" --account-name "${STORAGE_ACCOUNT_NAME}" --auth-mode login --query exists -o tsv | grep -q "true"; then
  if ! az storage container create \
    --name "${CONTAINER_NAME}" \
    --account-name "${STORAGE_ACCOUNT_NAME}" \
    --resource-group "${RESOURCE_GROUP_NAME}" \
    --auth-mode login \
    --output none; then

    echo -e "${RED}Failed to create container ${CONTAINER_NAME}!${NC}"
    echo -e "${YELLOW}This may be due to insufficient blob data permissions.${NC}"
    exit 1
  fi
  echo -e "${GREEN}Container created successfully!${NC}"
else
  echo -e "${GREEN}Container already exists.${NC}"
fi

# Assign role if this is a service principal and role assignments are not skipped
if [ "$IS_SERVICE_PRINCIPAL" = true ] && [ "$SKIP_ROLE_ASSIGNMENT" = false ]; then
  echo -e "${BLUE}Checking service principal role assignments...${NC}"

  # Get service principal object ID
  OBJECT_ID=$(az ad sp show --id "$CLIENT_ID" --query id -o tsv 2>/dev/null || echo "")

  if [ -n "$OBJECT_ID" ]; then
    echo -e "${BLUE}Assigning Storage Blob Data Contributor role to service principal...${NC}"

    # Check if role already assigned
    ROLE_ASSIGNED=$(az role assignment list --assignee "$OBJECT_ID" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT_NAME" --query "[?roleDefinitionName=='Storage Blob Data Contributor'].id" -o tsv)

    if [ -z "$ROLE_ASSIGNED" ]; then
      if ! az role assignment create --assignee-object-id "$OBJECT_ID" --assignee-principal-type ServicePrincipal \
        --role "Storage Blob Data Contributor" \
        --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT_NAME" \
        --output none; then

        echo -e "${YELLOW}Warning: Could not assign Storage Blob Data Contributor role.${NC}"
        echo -e "${YELLOW}This is required for state locking. Ensure you have Owner role to assign permissions.${NC}"
      else
        echo -e "${GREEN}Role assignment created successfully!${NC}"
      fi
    else
      echo -e "${GREEN}Role already assigned.${NC}"
    fi
  else
    echo -e "${YELLOW}Could not retrieve service principal details for role assignment.${NC}"
    echo -e "${YELLOW}Please manually assign Storage Blob Data Contributor role to the service principal.${NC}"
  fi
fi

# Create/update backend config file
mkdir -p backends
BACKEND_FILE="backends/${ENVIRONMENT}.tfbackend"

echo -e "${BLUE}Creating backend configuration file: $BACKEND_FILE${NC}"
cat > "$BACKEND_FILE" << EOF
resource_group_name  = "${RESOURCE_GROUP_NAME}"
storage_account_name = "${STORAGE_ACCOUNT_NAME}"
container_name       = "${CONTAINER_NAME}"
key                  = "${ENVIRONMENT}.terraform.tfstate"
use_azuread_auth     = true
EOF

echo -e "${GREEN}Backend storage configuration completed!${NC}"
echo -e "${BLUE}To initialize Terraform with this backend, run:${NC}"
echo "  ./run-terraform.sh init -backend-config=${BACKEND_FILE}"
echo

# Create documentation of required permissions
if [ "$IS_SERVICE_PRINCIPAL" = true ]; then
  PERMISSIONS_DOC="service_principal_permissions.md"
  echo -e "${BLUE}Creating service principal permissions documentation: $PERMISSIONS_DOC${NC}"

  cat > "$PERMISSIONS_DOC" << EOF
# Required Service Principal Permissions

The following permissions are required for the service principal used in Terraform CI/CD pipelines:

## Subscription Level Permissions

- **Contributor** - To create and manage all Azure resources

## Storage Account Specific Permissions

- **Storage Blob Data Contributor** - For Terraform state locking and management
  - Scope: /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT_NAME

## Resource Group Permissions

- **Contributor** - To manage resources within the resource group
  - Scope: /subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP_NAME

## Role Assignment Permissions (Only needed for initial setup)

- **Owner** or **User Access Administrator** - To assign the Storage Blob Data Contributor role
  - This is only needed for initial setup or when creating new storage accounts

## How to Assign These Permissions

\`\`\`bash
# Assign Contributor role at subscription level
az role assignment create --assignee "<service-principal-id>" --role "Contributor" --scope "/subscriptions/$SUBSCRIPTION_ID"

# Assign Storage Blob Data Contributor role for the storage account
az role assignment create --assignee "<service-principal-id>" --role "Storage Blob Data Contributor" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.Storage/storageAccounts/$STORAGE_ACCOUNT_NAME"
\`\`\`

Replace \`<service-principal-id>\` with your service principal's Client ID or Object ID.
EOF

  echo -e "${GREEN}Documentation created successfully!${NC}"
fi

# Perform test initialization to verify state access
echo -e "${BLUE}Testing backend configuration with a dry run...${NC}"
if ! terraform init -backend-config="$BACKEND_FILE" -backend=true -reconfigure -backend-config="key=${ENVIRONMENT}.terraform.tfstate.test" -backend-config="use_azuread_auth=true" &>/dev/null; then
  echo -e "${YELLOW}Warning: Initial backend configuration test failed.${NC}"
  echo -e "${YELLOW}This may be due to insufficient permissions or configuration issues.${NC}"
  echo -e "${YELLOW}See detailed error by running: terraform init -backend-config=\"$BACKEND_FILE\"${NC}"
else
  echo -e "${GREEN}Backend configuration test successful!${NC}"
fi

echo -e "${GREEN}For CI/CD pipelines, ensure service principal has Storage Blob Data Contributor role on the storage account.${NC}"