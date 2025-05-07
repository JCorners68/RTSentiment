#!/bin/bash

# RT Sentiment Analysis - SIT Environment Setup Script
# This script sets up the System Integration Testing (SIT) environment.

# Display a message at the start
echo "Setting up RT Sentiment Analysis SIT environment..."

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Create the necessary directories if they don't exist
mkdir -p ${SCRIPT_DIR}/config
mkdir -p ${SCRIPT_DIR}/tests
mkdir -p ${SCRIPT_DIR}/logs

# Ensure the latest version of pip
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Create a Python virtual environment
if [ ! -d "${SCRIPT_DIR}/venv" ]; then
    echo "Creating Python virtual environment..."
    python -m venv ${SCRIPT_DIR}/venv
fi

# Activate the virtual environment
source ${SCRIPT_DIR}/venv/bin/activate

# Install required Python packages
echo "Installing required Python packages..."
pip install pytest requests azure-identity azure-mgmt-resource azure-mgmt-containerservice azure-mgmt-storage

# Check deployment method
echo "Checking available deployment methods..."

DEPLOY_METHOD="unknown"

# Check if Docker is running correctly
if command -v docker &> /dev/null && docker ps &> /dev/null; then
    echo "Docker is available and running."
    DEPLOY_METHOD="docker"
# Check if Azure CLI is installed
elif command -v az &> /dev/null; then
    echo "Azure CLI is available."
    DEPLOY_METHOD="azure_cli"
# Check for Python with Azure SDK
elif command -v python &> /dev/null; then
    echo "Python with Azure SDK will be used."
    DEPLOY_METHOD="python_sdk"
else
    echo "No deployment method available. Please install Docker, Azure CLI, or Python."
    exit 1
fi

# Ask if the user wants to deploy to Azure
echo ""
echo "Would you like to deploy the SIT environment to Azure? (y/n)"
read -p "This will create resources in Azure that may incur costs: " DEPLOY_AZURE

if [[ "$DEPLOY_AZURE" == "y" || "$DEPLOY_AZURE" == "Y" ]]; then
    echo "Deploying to Azure..."
    
    if [ "$DEPLOY_METHOD" == "docker" ]; then
        echo "Using Docker with Terraform method..."
        chmod +x ${SCRIPT_DIR}/deploy_azure_sit.sh
        ${SCRIPT_DIR}/deploy_azure_sit.sh
    elif [ "$DEPLOY_METHOD" == "azure_cli" ]; then
        echo "Using Azure CLI method..."
        chmod +x ${SCRIPT_DIR}/deploy_azure_sit.sh
        ${SCRIPT_DIR}/deploy_azure_sit.sh
    else
        echo "Using Python SDK method..."
        chmod +x ${SCRIPT_DIR}/deploy_azure_sit.sh
        ${SCRIPT_DIR}/deploy_azure_sit.sh
    fi
else
    echo "Skipping Azure deployment."
    
    # Check if local Docker deployment is required
    echo ""
    echo "Would you like to deploy the services locally using Docker? (y/n)"
    read -p "This will use Docker Compose to set up local services: " DEPLOY_LOCAL
    
    if [[ "$DEPLOY_LOCAL" == "y" || "$DEPLOY_LOCAL" == "Y" ]]; then
        echo "Deploying services locally..."
        
        # Navigate to the infrastructure directory to build and start the services
        cd ${SCRIPT_DIR}/../../infrastructure
        
        # Build the services
        echo "Building services..."
        docker-compose build
        
        # Start the services
        echo "Starting services..."
        docker-compose up -d
        
        # Wait for services to be ready
        echo "Waiting for services to be ready..."
        sleep 10
        
        # Verify service health
        echo "Verifying service health..."
        docker-compose ps
        
        echo "Local services deployed successfully."
        echo "Data Acquisition Service is available at: http://localhost:8002"
        echo "Use 'docker-compose down' in the infrastructure directory to stop the services."
    else
        echo "Skipping local deployment."
    fi
fi

# Run verification tests
echo ""
echo "Would you like to run the environment verification tests? (y/n)"
read -p "This will check if the environment is set up correctly: " RUN_TESTS

if [[ "$RUN_TESTS" == "y" || "$RUN_TESTS" == "Y" ]]; then
    echo "Running environment verification tests..."
    
    if [ -f "${SCRIPT_DIR}/tests/run_verification.py" ]; then
        python ${SCRIPT_DIR}/tests/run_verification.py
    else
        cd ${SCRIPT_DIR}/tests && pytest -xvs test_environment.py
    fi
else
    echo "Skipping tests."
fi

# Create an alias for easy deployment
if [[ "$DEPLOY_AZURE" == "y" || "$DEPLOY_AZURE" == "Y" ]]; then
    echo ""
    echo "Would you like to create an alias for easy SIT deployment? (y/n)"
    read -p "This will add a 'sit-deploy' alias to your .bashrc file: " ADD_ALIAS
    
    if [[ "$ADD_ALIAS" == "y" || "$ADD_ALIAS" == "Y" ]]; then
        cat > ${SCRIPT_DIR}/sit-deploy-alias.sh << EOF
#!/bin/bash
# SIT deployment alias
alias sit-deploy='cd ${SCRIPT_DIR} && ./deploy_azure_sit.sh'
alias sit-verify='cd ${SCRIPT_DIR} && ./verify_deployment.sh'
alias sit-clean='cd ${SCRIPT_DIR} && ./cleanup_azure_sit.sh'
EOF
        
        chmod +x ${SCRIPT_DIR}/sit-deploy-alias.sh
        
        echo "# RT Sentiment Analysis SIT deployment aliases" >> ~/.bashrc
        echo "source ${SCRIPT_DIR}/sit-deploy-alias.sh" >> ~/.bashrc
        
        echo "Aliases added to your .bashrc file."
        echo "Run 'source ~/.bashrc' to load them in your current session."
        echo "You can now use:"
        echo "  - 'sit-deploy' to deploy the SIT environment"
        echo "  - 'sit-verify' to verify the deployment"
        echo "  - 'sit-clean' to clean up the SIT environment"
    fi
fi

# Deactivate the virtual environment
deactivate

# Display success message
echo ""
echo "SIT environment setup complete."
if [[ "$DEPLOY_AZURE" == "y" || "$DEPLOY_AZURE" == "Y" ]]; then
    echo "SIT environment has been deployed to Azure in the 'sentimark-sit-rg' resource group."
    echo ""
    echo "To verify the deployment manually:"
    echo "  ${SCRIPT_DIR}/verify_deployment.sh"
    echo ""
    echo "To clean up the Azure resources when done:"
    echo "  ${SCRIPT_DIR}/cleanup_azure_sit.sh"
fi