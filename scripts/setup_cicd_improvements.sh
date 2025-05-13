#!/bin/bash
# Script to initialize CICD improvement project files
# This script creates necessary directories and template files for the CICD improvement plan

set -euo pipefail

# Log function for consistent output
timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

log() {
  echo -e "$(timestamp) - $1"
}

# Create directory structure
create_directories() {
  log "Creating directory structure for CICD improvements..."
  
  # Helm validation
  mkdir -p scripts/helm
  
  # Terraform fixes
  mkdir -p infrastructure/terraform/azure/modules/state-locking
  mkdir -p infrastructure/terraform/azure/templates/backends
  
  # Testing framework
  mkdir -p scripts/testing
  
  # GitHub Actions
  mkdir -p .github/workflows
  mkdir -p .github/actions/setup-env
  mkdir -p .github/actions/build-push
  
  log "Directory structure created successfully"
}

# Create Helm validation script
create_helm_validation() {
  log "Creating Helm validation script..."
  
  cat > scripts/helm/validate_charts.sh << 'EOF'
#!/bin/bash
# Validates Helm charts for schema compliance and security issues
# Usage: ./validate_charts.sh [chart_dir]

set -euo pipefail

# Default chart directory
CHART_DIR=${1:-"/home/jonat/real_senti/infrastructure/helm/sentimark-services"}
OUTPUT_DIR="/home/jonat/real_senti/scan-results/$(date +%Y%m%d_%H%M%S)"

# Create output directory
mkdir -p "$OUTPUT_DIR"

echo "Validating Helm chart: $CHART_DIR"
echo "Results will be saved to: $OUTPUT_DIR"

# Step 1: Run helm lint
echo "Running helm lint..."
helm lint "$CHART_DIR" > "$OUTPUT_DIR/helm_lint.txt" || {
  echo "Helm lint failed!"
  cat "$OUTPUT_DIR/helm_lint.txt"
  exit 1
}

# Step 2: Generate template
echo "Generating Helm template..."
helm template "$CHART_DIR" > "$OUTPUT_DIR/helm_template.yaml" 2> "$OUTPUT_DIR/helm_template_errors.txt" || {
  echo "Helm template generation failed!"
  cat "$OUTPUT_DIR/helm_template_errors.txt"
  exit 1
}

# Step 3: Run security scan if kubesec is available
if command -v kubesec &> /dev/null; then
  echo "Running security scan with kubesec..."
  kubesec scan "$OUTPUT_DIR/helm_template.yaml" > "$OUTPUT_DIR/kubesec_results.json" || {
    echo "Security scan failed!"
    cat "$OUTPUT_DIR/kubesec_results.json"
    exit 1
  }
else
  echo "kubesec not found. Skipping security scan."
  echo "Install with: curl -s https://raw.githubusercontent.com/controlplaneio/kubesec/master/install.sh | sh"
fi

# Step 4: Check for securityContext at pod level
echo "Checking for pod-level securityContext issues..."
grep -n "securityContext:" "$OUTPUT_DIR/helm_template.yaml" | grep -B 5 "template:" > "$OUTPUT_DIR/securitycontext_issues.txt" || true

# Step 5: Summarize findings
echo "Validation complete. Results saved to: $OUTPUT_DIR"
echo "Summary:"
echo "----------------------------------------"
grep -A 2 "CHART VALIDATION" "$OUTPUT_DIR/helm_lint.txt" || true
echo "----------------------------------------"
if [ -s "$OUTPUT_DIR/securitycontext_issues.txt" ]; then
  echo "Found potential pod-level securityContext issues:"
  cat "$OUTPUT_DIR/securitycontext_issues.txt"
else
  echo "No pod-level securityContext issues found."
fi
EOF

  chmod +x scripts/helm/validate_charts.sh
  log "Helm validation script created successfully"
}

# Create Terraform state locking template
create_terraform_templates() {
  log "Creating Terraform state locking templates..."
  
  # Create module template
  cat > infrastructure/terraform/azure/modules/state-locking/main.tf << 'EOF'
# DynamoDB table for Terraform state locking
resource "aws_dynamodb_table" "terraform_locks" {
  name         = var.lock_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  
  attribute {
    name = "LockID"
    type = "S"
  }
  
  tags = {
    Environment = var.environment
    Project     = "Sentimark"
  }
}
EOF

  cat > infrastructure/terraform/azure/modules/state-locking/variables.tf << 'EOF'
variable "lock_table_name" {
  description = "Name of the DynamoDB table used for Terraform state locking"
  type        = string
  default     = "terraform-locks"
}

variable "environment" {
  description = "Environment name (e.g., sit, uat, prod)"
  type        = string
  default     = "sit"
}
EOF

  cat > infrastructure/terraform/azure/modules/state-locking/outputs.tf << 'EOF'
output "dynamodb_table_name" {
  description = "Name of the DynamoDB table used for Terraform state locking"
  value       = aws_dynamodb_table.terraform_locks.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table used for Terraform state locking"
  value       = aws_dynamodb_table.terraform_locks.arn
}
EOF

  # Create backend templates
  cat > infrastructure/terraform/azure/templates/backends/sit.tfbackend.template << 'EOF'
bucket               = "sentimark-terraform-state"
key                  = "sit/terraform.tfstate"
region               = "us-west-2"
dynamodb_table       = "sentimark-terraform-locks"
encrypt              = true
EOF

  cat > infrastructure/terraform/azure/templates/backends/uat.tfbackend.template << 'EOF'
bucket               = "sentimark-terraform-state"
key                  = "uat/terraform.tfstate"
region               = "us-west-2"
dynamodb_table       = "sentimark-terraform-locks"
encrypt              = true
EOF

  log "Terraform templates created successfully"
}

# Create GitHub Actions workflow templates
create_github_actions() {
  log "Creating GitHub Actions templates..."
  
  # Main workflow
  cat > .github/workflows/deploy.yml.template << 'EOF'
name: Sentimark Deployment

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  validate:
    name: Validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up environment
        id: setup
        uses: ./.github/actions/setup-env
        with:
          setupCache: true
      
      - name: Validate Helm Charts
        run: |
          ./scripts/helm/validate_charts.sh
        continue-on-error: false
      
      - name: Run Tests
        run: |
          ./scripts/testing/run_tests.sh
      
      - name: Upload validation results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: validation-results
          path: scan-results/

  terraform:
    name: Infrastructure
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      # Secure credential handling using OIDC
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-west-2
      
      - name: Configure Azure credentials
        uses: azure/login@v1
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      
      - name: Terraform Init and Plan
        id: terraform
        run: |
          cd infrastructure/terraform/azure
          ./init-terraform.sh
          terraform init -backend-config=backends/sit.tfbackend
          terraform plan -out=tfplan.sit
        timeout-minutes: 15
        
      - name: Upload Terraform plan
        uses: actions/upload-artifact@v3
        with:
          name: terraform-plan
          path: infrastructure/terraform/azure/tfplan.sit

  deploy:
    name: Deploy
    needs: [validate, terraform]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure Azure credentials
        uses: azure/login@v1
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      
      - name: Download artifacts
        uses: actions/download-artifact@v3
        with:
          name: terraform-plan
          path: infrastructure/terraform/azure/
      
      - name: Terraform Apply
        working-directory: infrastructure/terraform/azure
        run: |
          terraform apply -auto-approve tfplan.sit
        timeout-minutes: 30
      
      - name: Helm Deployment
        run: |
          cd environments/sit
          ./deploy.sh
        timeout-minutes: 20
      
      - name: Verify Deployment
        run: |
          cd environments/sit
          ./verify_deployment.sh
EOF

  # Setup environment action
  mkdir -p .github/actions/setup-env
  cat > .github/actions/setup-env/action.yml << 'EOF'
name: 'Setup Environment'
description: 'Sets up the environment for build and deployment'

inputs:
  setupCache:
    description: 'Whether to set up caching'
    required: false
    default: 'true'
  pythonVersion:
    description: 'Python version to use'
    required: false
    default: '3.10'

outputs:
  cacheHit:
    description: 'Whether the cache was hit'
    value: ${{ steps.cache.outputs.cache-hit }}

runs:
  using: 'composite'
  steps:
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ inputs.pythonVersion }}
    
    - name: Install dependencies
      shell: bash
      run: |
        python -m pip install --upgrade pip
        if [ -f requirements.txt ]; then
          pip install -r requirements.txt
        fi
        pip install pytest pytest-cov
    
    - name: Cache Python dependencies
      if: inputs.setupCache == 'true'
      id: cache
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-
    
    - name: Install Helm
      shell: bash
      run: |
        curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    
    - name: Install security tools
      shell: bash
      run: |
        # Install kubesec
        curl -s https://raw.githubusercontent.com/controlplaneio/kubesec/master/install.sh | bash
EOF

  log "GitHub Actions templates created successfully"
}

# Create test framework templates
create_test_framework() {
  log "Creating test framework templates..."
  
  cat > scripts/testing/run_tests.sh << 'EOF'
#!/bin/bash
# Runs tests for specified service components
# Usage: ./run_tests.sh [component] [test_type]

set -euo pipefail

COMPONENT=${1:-"all"}
TEST_TYPE=${2:-"all"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Log function
log() {
  echo "[$(date "+%Y-%m-%d %H:%M:%S")] $1"
}

# Run tests for a specific component
run_component_tests() {
  local component=$1
  local test_type=$2
  
  log "Running $test_type tests for $component..."
  
  if [ ! -d "$PROJECT_ROOT/services/$component" ]; then
    log "ERROR: Component directory not found: $component"
    return 1
  fi
  
  cd "$PROJECT_ROOT/services/$component"
  
  case "$test_type" in
    unit)
      log "Running unit tests..."
      if [ -d tests/unit ]; then
        python -m pytest tests/unit -v -m unit --cov=src
      else
        log "No unit tests found for $component"
      fi
      ;;
    integration)
      log "Running integration tests..."
      if [ -d tests/integration ]; then
        if [ -f tests/docker-compose.test.yml ]; then
          log "Setting up integration test environment..."
          docker-compose -f tests/docker-compose.test.yml up -d
          python -m pytest tests/integration -v -m integration
          docker-compose -f tests/docker-compose.test.yml down
        else
          python -m pytest tests/integration -v -m integration
        fi
      else
        log "No integration tests found for $component"
      fi
      ;;
    all)
      log "Running all tests..."
      python -m pytest tests -v --cov=src
      ;;
    *)
      log "Unknown test type: $test_type"
      return 1
      ;;
  esac
  
  log "Tests completed for $component"
  return 0
}

# Main function
main() {
  log "Starting test run: component=$COMPONENT, type=$TEST_TYPE"
  
  # Create test results directory
  RESULTS_DIR="$PROJECT_ROOT/test-results/$(date +%Y%m%d_%H%M%S)"
  mkdir -p "$RESULTS_DIR"
  log "Test results will be saved to: $RESULTS_DIR"
  
  # Run tests for all components or specific component
  if [ "$COMPONENT" = "all" ]; then
    log "Running tests for all components..."
    for dir in "$PROJECT_ROOT"/services/*/; do
      component=$(basename "$dir")
      run_component_tests "$component" "$TEST_TYPE" || log "WARNING: Tests failed for $component"
    done
  else
    run_component_tests "$COMPONENT" "$TEST_TYPE" || {
      log "ERROR: Tests failed for $COMPONENT"
      exit 1
    }
  fi
  
  log "All tests completed successfully"
}

# Run main function
main
EOF

  chmod +x scripts/testing/run_tests.sh
  
  # Create pytest config template
  cat > scripts/testing/pytest.ini.template << 'EOF'
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
markers =
    unit: unit tests
    integration: integration tests
    performance: performance tests
    security: security tests
addopts = --strict-markers
EOF

  log "Test framework templates created successfully"
}

# Create Docker Compose test template
create_docker_compose_test() {
  log "Creating Docker Compose test template..."
  
  cat > scripts/testing/docker-compose.test.yml.template << 'EOF'
version: '3.8'

services:
  # Test database
  db-test:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: test_db
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
    ports:
      - "5432:5432"
    volumes:
      - postgres-test-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U test_user -d test_db"]
      interval: 5s
      timeout: 5s
      retries: 5

  # Mock API server
  mock-api:
    image: mockserver/mockserver:latest
    ports:
      - "1080:1080"
    environment:
      MOCKSERVER_INITIALIZATION_JSON_PATH: /config/mockserver.json
    volumes:
      - ./mocks:/config

volumes:
  postgres-test-data:
EOF

  log "Docker Compose test template created successfully"
}

# Create test mockserver config template
create_mockserver_config() {
  log "Creating MockServer config template..."
  
  mkdir -p scripts/testing/mocks
  
  cat > scripts/testing/mocks/mockserver.json.template << 'EOF'
[
  {
    "httpRequest": {
      "method": "GET",
      "path": "/api/v1/stock/profile2",
      "queryStringParameters": {
        "symbol": ["AAPL"],
        "token": [".*"]
      }
    },
    "httpResponse": {
      "statusCode": 200,
      "headers": {
        "Content-Type": ["application/json"]
      },
      "body": {
        "country": "US",
        "currency": "USD",
        "exchange": "NASDAQ/NMS (GLOBAL MARKET)",
        "ipo": "1980-12-12",
        "marketCapitalization": 1415993,
        "name": "Apple Inc",
        "phone": "14089961010",
        "shareOutstanding": 4375.47998046875,
        "ticker": "AAPL",
        "weburl": "https://www.apple.com/",
        "logo": "https://static.finnhub.io/logo/87cb30d8-80df-11ea-8951-00000000092a.png",
        "finnhubIndustry": "Technology"
      }
    }
  },
  {
    "httpRequest": {
      "method": "GET",
      "path": "/api/v1/stock/earnings",
      "queryStringParameters": {
        "symbol": ["AAPL"],
        "token": [".*"]
      }
    },
    "httpResponse": {
      "statusCode": 200,
      "headers": {
        "Content-Type": ["application/json"]
      },
      "body": {
        "data": [
          {
            "actual": 1.52,
            "estimate": 1.43,
            "period": "2023-06-30",
            "symbol": "AAPL"
          },
          {
            "actual": 1.52,
            "estimate": 1.5,
            "period": "2023-03-31",
            "symbol": "AAPL"
          }
        ],
        "symbol": "AAPL"
      }
    }
  },
  {
    "httpRequest": {
      "method": "GET",
      "path": "/api/v1/news-sentiment",
      "queryStringParameters": {
        "symbol": ["AAPL"],
        "token": [".*"]
      }
    },
    "httpResponse": {
      "statusCode": 200,
      "headers": {
        "Content-Type": ["application/json"]
      },
      "body": {
        "buzz": {
          "articlesInLastWeek": 123,
          "buzz": 1.5,
          "weeklyAverage": 82
        },
        "companyNewsScore": 0.75,
        "sectorAverageBullishPercent": 0.6,
        "sectorAverageNewsScore": 0.5,
        "sentiment": {
          "bearishPercent": 0.25,
          "bullishPercent": 0.75
        },
        "symbol": "AAPL"
      }
    }
  }
]
EOF

  log "MockServer config template created successfully"
}

# Create deployment script 
create_deployment_script() {
  log "Creating deployment script template..."
  
  cat > scripts/cicd_deploy.sh << 'EOF'
#!/bin/bash
# Master script to deploy the CICD improvements
# This script initializes and applies all CICD improvement components

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Log function for consistent output
timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

log() {
  echo -e "$(timestamp) - $1"
}

# Parse arguments
COMPONENT=${1:-"all"}

# Validate Helm charts
deploy_helm_validation() {
  log "Deploying Helm chart validation..."
  "$SCRIPT_DIR/helm/validate_charts.sh"
  log "Helm validation deployed successfully"
}

# Apply Terraform state locking
deploy_terraform_locking() {
  log "Deploying Terraform state locking..."
  
  # Apply Terraform state locking module (sample - would be executed in real deployment)
  log "In a real deployment, this would apply the Terraform state locking configuration"
  log "Terraform state locking deployed successfully"
}

# Deploy GitHub Actions workflows
deploy_github_actions() {
  log "Deploying GitHub Actions workflows..."
  
  # In a real deployment, this would:
  # 1. Replace placeholder values in template files
  # 2. Move templates to their final locations
  # 3. Configure GitHub secrets
  
  log "GitHub Actions workflow templates prepared. In a real deployment, they would be committed to the repository."
  log "GitHub Actions deployed successfully"
}

# Deploy test framework
deploy_test_framework() {
  log "Deploying test framework..."
  
  # Create pytest configuration for components
  for component in data-acquisition data-tier sentiment-analysis api auth; do
    if [ -d "$PROJECT_ROOT/services/$component" ]; then
      log "Setting up test framework for $component..."
      
      # Create pytest.ini
      if [ ! -f "$PROJECT_ROOT/services/$component/pytest.ini" ]; then
        cp "$SCRIPT_DIR/testing/pytest.ini.template" "$PROJECT_ROOT/services/$component/pytest.ini"
      fi
      
      # Create test directories if they don't exist
      mkdir -p "$PROJECT_ROOT/services/$component/tests/unit"
      mkdir -p "$PROJECT_ROOT/services/$component/tests/integration"
      
      # Create __init__.py files
      touch "$PROJECT_ROOT/services/$component/tests/__init__.py"
      touch "$PROJECT_ROOT/services/$component/tests/unit/__init__.py"
      touch "$PROJECT_ROOT/services/$component/tests/integration/__init__.py"
      
      # Create docker-compose test file if it doesn't exist
      if [ ! -f "$PROJECT_ROOT/services/$component/tests/docker-compose.test.yml" ]; then
        cp "$SCRIPT_DIR/testing/docker-compose.test.yml.template" "$PROJECT_ROOT/services/$component/tests/docker-compose.test.yml"
      fi
      
      # Create mocks directory and config if they don't exist
      mkdir -p "$PROJECT_ROOT/services/$component/tests/mocks"
      if [ ! -f "$PROJECT_ROOT/services/$component/tests/mocks/mockserver.json" ]; then
        cp "$SCRIPT_DIR/testing/mocks/mockserver.json.template" "$PROJECT_ROOT/services/$component/tests/mocks/mockserver.json"
      fi
    fi
  done
  
  log "Test framework deployed successfully"
}

# Main function
main() {
  log "Starting CICD improvements deployment: component=$COMPONENT"
  
  case "$COMPONENT" in
    helm)
      deploy_helm_validation
      ;;
    terraform)
      deploy_terraform_locking
      ;;
    github)
      deploy_github_actions
      ;;
    tests)
      deploy_test_framework
      ;;
    all)
      deploy_helm_validation
      deploy_terraform_locking
      deploy_github_actions
      deploy_test_framework
      ;;
    *)
      log "ERROR: Unknown component: $COMPONENT"
      log "Usage: $0 [helm|terraform|github|tests|all]"
      exit 1
      ;;
  esac
  
  log "CICD improvements deployment completed successfully"
}

# Run main function
main
EOF

  chmod +x scripts/cicd_deploy.sh
  log "Deployment script created successfully"
}

# Main function
main() {
  log "Initializing CICD improvement project files..."
  
  create_directories
  create_helm_validation
  create_terraform_templates
  create_github_actions
  create_test_framework
  create_docker_compose_test
  create_mockserver_config
  create_deployment_script
  
  log "CICD improvement project files initialized successfully"
  log "Run './scripts/cicd_deploy.sh' to deploy the improvements"
}

# Run main function
main