# RT Sentiment Analysis - UAT Environment

This document outlines the requirements, configuration, and procedures for the User Acceptance Testing (UAT) environment hosted in Azure.

## Azure Requirements

### Required Information

To successfully deploy and promote to the UAT environment, the following Azure information is required:

1. **Authentication Credentials**:
   - Service Principal with Contributor permissions
   - Application (client) ID
   - Client Secret
   - Tenant ID: `1ced8c49-a03c-439c-9ff1-0c23f5128720`
   - Subscription ID: `644936a7-e58a-4ccb-a882-0005f213f5bd`

2. **Azure Resources**:
   - Resource Group: `rt-sentiment-uat`
   - Region: `US West`
   - AKS Cluster: `rt-sentiment-aks`
   - Container Registry: `rtsentiregistry`
   - Storage Account: `rtsentistorage`

3. **Proximity Placement Group (PPG)**:
   - Name: `rt-sentiment-ppg`
   - Region: `US West`
   - Purpose: Ensure low latency by co-locating resources

## Step 1: Obtaining Required Azure Information

### Subscription Information

1. **Get Subscription ID**:
   - Open the Azure Portal (https://portal.azure.com)
   - Navigate to "Subscriptions" in the top search bar
   - Select your subscription
   - Copy the Subscription ID from the Overview page
   
   ```bash
   # Alternative: Get via Azure CLI
   az account show --query id -o tsv
   ```

2. **Get Tenant ID**:
   - In the Azure Portal, navigate to "Azure Active Directory"
   - In the Overview page, copy the "Tenant ID"
   
   ```bash
   # Alternative: Get via Azure CLI
   az account show --query tenantId -o tsv
   # Our tenant ID: 1ced8c49-a03c-439c-9ff1-0c23f5128720
   ```

### Creating a Service Principal

1. **Create a Service Principal with Contributor role**:
   ```bash
   # Using our subscription ID and tenant ID
   az ad sp create-for-rbac --name "rt-sentiment-uat-sp" --role contributor \
     --scopes /subscriptions/644936a7-e58a-4ccb-a882-0005f213f5bd \
     --tenant 1ced8c49-a03c-439c-9ff1-0c23f5128720 \
     --sdk-auth
   ```

2. **Save the output JSON**:
   The command will output JSON similar to:
   ```json
   {
     "clientId": "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX",
     "clientSecret": "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
     "subscriptionId": "644936a7-e58a-4ccb-a882-0005f213f5bd",
     "tenantId": "1ced8c49-a03c-439c-9ff1-0c23f5128720",
     "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
     "resourceManagerEndpointUrl": "https://management.azure.com/",
     "activeDirectoryGraphResourceId": "https://graph.windows.net/",
     "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
     "galleryEndpointUrl": "https://gallery.azure.com/",
     "managementEndpointUrl": "https://management.core.windows.net/"
   }
   ```

3. **Extract required credentials**:
   - `clientId` is your Application (client) ID
   - `clientSecret` is your Client Secret
   - `tenantId` is your Tenant ID
   - `subscriptionId` is your Subscription ID

4. **Store the entire JSON as a GitHub Secret**:
   - Go to your GitHub repository
   - Navigate to Settings > Secrets and variables > Actions
   - Create a new repository secret named `AZURE_CREDENTIALS`
   - Paste the entire JSON output as the value

### Checking Resource Quota and Permissions

1. **Verify subscription quota for US West region**:
   ```bash
   az vm list-usage --location westus --query "[?contains(name.value, 'standardDSv3Family')]"
   ```

2. **Ensure you have sufficient permissions**:
   ```bash
   # Verify your current permissions
   az role assignment list --assignee <your-email> --subscription 644936a7-e58a-4ccb-a882-0005f213f5bd --tenant 1ced8c49-a03c-439c-9ff1-0c23f5128720
   ```

3. **Check if you can create Proximity Placement Groups**:
   ```bash
   # Test if you can create a PPG
   az group create --name test-rg --location westus --subscription 644936a7-e58a-4ccb-a882-0005f213f5bd
   az ppg create --name test-ppg --resource-group test-rg --location westus --type Standard --subscription 644936a7-e58a-4ccb-a882-0005f213f5bd
   
   # Clean up the test resource if successful
   az group delete --name test-rg --yes --subscription 644936a7-e58a-4ccb-a882-0005f213f5bd
   ```

## API Access Management

### Service Principal Setup

1. Create a Service Principal:
   ```bash
   az ad sp create-for-rbac --name "rt-sentiment-uat-sp" --role contributor --scopes /subscriptions/{subscription-id}/resourceGroups/rt-sentiment-uat
   ```

2. The output will provide:
   ```json
   {
     "appId": "YOUR_CLIENT_ID",
     "displayName": "rt-sentiment-uat-sp",
     "password": "YOUR_CLIENT_SECRET",
     "tenant": "YOUR_TENANT_ID"
   }
   ```

3. Store these credentials securely in GitHub repository secrets:
   - `AZURE_CLIENT_ID`: Service Principal App ID
   - `AZURE_CLIENT_SECRET`: Service Principal Password
   - `AZURE_TENANT_ID`: Azure AD Tenant ID
   - `AZURE_SUBSCRIPTION_ID`: Azure Subscription ID

### GitHub Actions Integration

The Service Principal credentials will be used by GitHub Actions workflow (`sit_to_uat.yml`) to authenticate with Azure and deploy resources.

Configure in GitHub repository:
1. Go to Settings > Secrets and variables > Actions
2. Add the required secrets:
   - `AZURE_CREDENTIALS`: JSON containing all credentials
   ```json
   {
     "clientId": "YOUR_CLIENT_ID",
     "clientSecret": "YOUR_CLIENT_SECRET",
     "subscriptionId": "YOUR_SUBSCRIPTION_ID",
     "tenantId": "YOUR_TENANT_ID"
   }
   ```

## Proximity Placement Group (PPG) Configuration

PPGs are used to minimize network latency between Azure resources by placing them in close physical proximity within a data center.

### Benefits for RT Sentiment Analysis:
- Reduced latency between services
- Improved performance for real-time sentiment processing
- Enhanced user experience for web and mobile clients

### Setup Instructions:
1. The PPG is created as part of the Terraform configuration
2. All relevant resources (VMs, AKS Nodes) are configured to use this PPG
3. Latency-sensitive components are prioritized within the PPG

## Deployment Process

### Prerequisites
1. Azure CLI installed and configured
2. Terraform v1.0+ installed
3. Service Principal credentials available
4. Docker installed (for local image building/testing)

### Manual Deployment Steps

1. Authenticate to Azure:
   ```bash
   az login --service-principal -u $CLIENT_ID -p $CLIENT_SECRET --tenant $TENANT_ID
   ```

2. Run the UAT deployment script:
   ```bash
   cd /home/jonat/real_senti/rt-sentiment/environments/uat
   ./setup.sh
   ```

3. Verify the deployment:
   ```bash
   cd /home/jonat/real_senti/rt-sentiment/environments/uat/tests
   pytest
   ```

### Automated Deployment (GitHub Actions)

The GitHub Actions workflow automatically:
1. Builds and tests services in SIT environment
2. Builds and pushes Docker images to GitHub Container Registry
3. Deploys to UAT environment in Azure
4. Runs verification tests

To trigger:
1. Go to the Actions tab in the GitHub repository
2. Select the "Promote from SIT to UAT" workflow
3. Click "Run workflow"
4. Enter the version to promote (default: latest)
5. Click "Run workflow"

## Verification & Monitoring

### Verification
- All services should have health check endpoints
- UAT verification tests will confirm functionality
- API endpoints should be accessible

### Monitoring
- Azure Monitor is configured for all resources
- Log Analytics workspace collects logs from all services
- Alerts are configured for critical service metrics

## Troubleshooting

### Common Issues

1. **Service Principal Authentication Failure**:
   - Check credential validity and permissions
   - Ensure the service principal has contributor access

2. **Container Registry Access Issues**:
   - Verify AKS has AcrPull role assigned
   - Check image names and tags

3. **PPG Resource Limitations**:
   - PPGs have resource type and quantity limitations
   - If deployment fails, may need to split resources across multiple PPGs

4. **Network Connectivity Issues**:
   - Check network security groups
   - Verify service endpoints are properly configured

## Support

For issues with the UAT environment, contact the infrastructure team at infrastructure@example.com.