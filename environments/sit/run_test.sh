#!/bin/bash
# Quick test script for Sentimark SIT deployment

set -e

# Define colors for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}===== Sentimark SIT Deployment Test =====${NC}"
echo "This script will test the key components of the deployment system."

# Test 1: CRLF to LF conversion
echo -e "\n${YELLOW}Test 1: Testing CRLF line ending fix${NC}"
echo "Creating test script with CRLF line endings..."

# Create test script with CRLF line endings
cat > /tmp/test_crlf.sh << 'EOF'
#!/bin/bash
echo "Test script executed successfully!"
EOF

# Convert LF to CRLF
sed -i 's/$/\r/' /tmp/test_crlf.sh
chmod +x /tmp/test_crlf.sh

echo "Attempting to run script with CRLF line endings (may fail)..."
/tmp/test_crlf.sh 2>/tmp/crlf_error.log || true

if [ -s /tmp/crlf_error.log ]; then
    echo -e "${YELLOW}Script with CRLF endings produced errors as expected${NC}"
else
    echo -e "${YELLOW}Script with CRLF ran without errors (unexpected)${NC}"
fi

echo "Fixing line endings with our conversion method..."
tr -d '\r' < /tmp/test_crlf.sh > /tmp/test_crlf_fixed.sh
chmod +x /tmp/test_crlf_fixed.sh

echo "Running fixed script..."
/tmp/test_crlf_fixed.sh
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ CRLF line ending fix works correctly${NC}"
else
    echo -e "${RED}✗ CRLF line ending fix failed${NC}"
fi

# Test 2: Values override detection
echo -e "\n${YELLOW}Test 2: Testing values override detection${NC}"
echo "Creating test values override file..."

# Create test values override
mkdir -p /tmp/test-deploy
cat > /tmp/test-deploy/values-override.yaml << EOF
# Test values override
dataAcquisition:
  useSpotInstances: false
  nodeSelector: {}
  tolerations: []
EOF

echo "Testing values override detection in deploy.sh..."
SCRIPT_DIR="$(dirname "$0")"
grep -q "VALUES_FILE_OVERRIDE" "$SCRIPT_DIR/helm_deploy_fixed.sh"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Values override detection present in helm_deploy_fixed.sh${NC}"
else
    echo -e "${RED}✗ Values override detection not found in helm_deploy_fixed.sh${NC}"
fi

grep -q "VALUES_FILE=\"\$VALUES_FILE_OVERRIDE\"" "$SCRIPT_DIR/helm_deploy_fixed.sh"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Values override properly applied in helm_deploy_fixed.sh${NC}"
else
    echo -e "${RED}✗ Values override not properly applied in helm_deploy_fixed.sh${NC}"
fi

# Test 3: Secure credential management
echo -e "\n${YELLOW}Test 3: Testing secure credential management${NC}"

# Check if pass is installed
if ! command -v pass &> /dev/null; then
    echo -e "${YELLOW}pass is not installed, skipping credential management test${NC}"
else
    echo "Testing credential management scripts..."
    
    if [ -f ~/.sentimark/bin/load-terraform-env.sh ]; then
        echo -e "${GREEN}✓ load-terraform-env.sh exists${NC}"
    else
        echo -e "${RED}✗ load-terraform-env.sh not found${NC}"
    fi
    
    if [ -f ~/.sentimark/bin/sync-azure-credentials.sh ]; then
        echo -e "${GREEN}✓ sync-azure-credentials.sh exists${NC}"
    else
        echo -e "${RED}✗ sync-azure-credentials.sh not found${NC}"
    fi
    
    if [ -f /home/jonat/real_senti/infrastructure/terraform/azure/init-terraform.sh ]; then
        echo -e "${GREEN}✓ init-terraform.sh exists${NC}"
    else
        echo -e "${RED}✗ init-terraform.sh not found${NC}"
    fi
fi

# Test 4: Check for log directory
echo -e "\n${YELLOW}Test 4: Testing logging system${NC}"
if [ -d "$SCRIPT_DIR/logs" ]; then
    echo -e "${GREEN}✓ Logs directory exists${NC}"
    
    # Count deployment logs
    DEPLOY_LOGS=$(ls -1 "$SCRIPT_DIR/logs"/deployment_*.json 2>/dev/null | wc -l)
    echo "Found $DEPLOY_LOGS deployment log files"
    
    if [ $DEPLOY_LOGS -gt 0 ]; then
        echo -e "${GREEN}✓ Deployment logs are being created${NC}"
        LATEST_LOG=$(ls -1t "$SCRIPT_DIR/logs"/deployment_*.json | head -1)
        echo "Latest deployment log: $LATEST_LOG"
        
        # Check if log contains status field
        grep -q "\"status\":" "$LATEST_LOG"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Deployment logs have the correct format${NC}"
        else
            echo -e "${RED}✗ Deployment logs may not have the correct format${NC}"
        fi
    else
        echo -e "${YELLOW}No deployment logs found${NC}"
    fi
else
    echo -e "${RED}✗ Logs directory does not exist${NC}"
fi

# Test 5: Check for all script requirements
echo -e "\n${YELLOW}Test 5: Testing required tools${NC}"

for cmd in az jq helm; do
    if command -v $cmd &> /dev/null; then
        echo -e "${GREEN}✓ $cmd is installed${NC}"
    else
        echo -e "${YELLOW}✗ $cmd is not installed${NC}"
    fi
done

# Clean up
echo -e "\n${YELLOW}Cleaning up test files...${NC}"
rm -f /tmp/test_crlf.sh /tmp/test_crlf_fixed.sh /tmp/crlf_error.log
rm -rf /tmp/test-deploy

echo -e "\n${GREEN}===== Test Summary =====${NC}"
echo "The deployment system components have been tested."
echo "For a full deployment test, run the following command:"
echo "  cd $(dirname "$0") && ./deploy.sh"
echo ""
echo "For cluster verification after deployment, run:"
echo "  az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command \"helm list -n sit\""
echo "  az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command \"kubectl get pods -n sit\""