# Sentimark CI/CD Improvement Plan

## Overview

This document outlines a comprehensive plan to improve the CI/CD process for the Sentimark project, addressing all high-priority issues identified in the Kanban board. The goal is to create a smooth, reliable deployment pipeline that allows for efficient development workflow.

## Key Areas for Improvement

1. **Helm Chart Security and Validation**
   - Fix securityContext issues in YAML structure
   - Create schema validation for preventative quality control

2. **Terraform State Management and Pipeline Efficiency**
   - Implement proper state locking with DynamoDB
   - Resolve S3 backend conflicts
   - Fix timeout and concurrency issues

3. **GitHub Actions Workflow Enhancements**
   - Improve secret management
   - Enhance error handling and recovery
   - Optimize pipeline performance

4. **Test Framework Implementation**
   - Set up comprehensive testing framework
   - Integrate tests with CI pipeline
   - Ensure proper test coverage

## Implementation Plan

### Phase 1: Foundation and Analysis (Days 1-2)

1. **Audit Current State**
   - Analyze all Helm chart templates for security issues
   - Review Terraform state configuration
   - Examine GitHub Actions workflows
   - Assess current testing approach

2. **Design Solutions**
   - Document required changes for each component
   - Create architecture diagrams for improved workflows
   - Define success criteria for each improvement

### Phase 2: Security and Validation (Days 3-5)

1. **Fix Helm Chart securityContext Issues**
   ```bash
   # Task: Move securityContext from pod-level to container-level
   
   # 1. Identify affected templates
   grep -r "securityContext" infrastructure/helm/sentimark-services/templates/
   
   # 2. Apply fixes to each template
   # Example: edit api-deployment.yaml, auth-deployment.yaml, etc.
   
   # 3. Create schema validation script
   cat > scripts/validate_helm_schema.sh << 'EOF'
   #!/bin/bash
   # Validate Helm chart against Kubernetes schema
   set -e
   
   CHART_DIR=$1
   if [ -z "$CHART_DIR" ]; then
     echo "Usage: $0 <chart-directory>"
     exit 1
   fi
   
   echo "Validating Helm chart in $CHART_DIR..."
   helm lint "$CHART_DIR"
   
   # Use kubeval for schema validation
   echo "Validating against Kubernetes schema..."
   helm template "$CHART_DIR" | kubeval --strict
   
   # Use kubesec for security scanning
   echo "Running security scan..."
   helm template "$CHART_DIR" | kubesec scan -
   EOF
   
   chmod +x scripts/validate_helm_schema.sh
   ```

2. **Create Helm Pre-Deployment Validation**
   - Integrate schema validation into deployment script
   - Add automated security scanning
   - Implement validation report generation

### Phase 3: State Management (Days 6-8)

1. **Implement Terraform State Locking Fix**
   ```bash
   # 1. Configure DynamoDB for state locking
   cat > infrastructure/terraform/azure/modules/state-locking/main.tf << 'EOF'
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
   
   # 2. Update backend configuration
   cat > infrastructure/terraform/azure/templates/backends/sit.tfbackend.template << 'EOF'
   bucket               = "sentimark-terraform-state"
   key                  = "sit/terraform.tfstate"
   region               = "us-west-2"
   dynamodb_table       = "sentimark-terraform-locks"
   encrypt              = true
   EOF
   ```

2. **Create Terraform Pipeline Fixes**
   - Implement timeout adjustments
   - Add concurrency controls
   - Create better error recovery

### Phase 4: GitHub Actions Improvements (Days 9-11)

1. **Set Up GitHub Actions Pipeline Improvements**
   ```yaml
   # Example workflow improvement
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
           uses: ./.github/actions/setup-env
           with:
             setupCache: true
         
         - name: Validate Helm Charts
           run: |
             ./scripts/validate_helm_schema.sh infrastructure/helm/sentimark-services
           continue-on-error: false
   
     build:
       name: Build
       needs: validate
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         
         # Secret management using OIDC for cloud providers
         - name: Configure AWS credentials
           uses: aws-actions/configure-aws-credentials@v2
           with:
             role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
             aws-region: us-west-2
         
         # Improved error handling with retries
         - name: Build and push images
           uses: ./.github/actions/build-push
           with:
             retry-attempts: 3
             timeout-minutes: 20
   ```

2. **Implement Secret Management Integration**
   - Use OIDC federation where possible
   - Implement rotation for GitHub secrets
   - Create secure credential provider

### Phase 5: Testing Framework (Days 12-14)

1. **Set up Unit and Integration Tests**
   ```bash
   # 1. Create pytest configuration
   cat > services/data-acquisition/pytest.ini << 'EOF'
   [pytest]
   testpaths = tests
   python_files = test_*.py
   python_classes = Test*
   python_functions = test_*
   markers =
     unit: unit tests
     integration: integration tests
     performance: performance tests
   EOF
   
   # 2. Set up Docker Compose for integration tests
   cat > services/data-acquisition/tests/docker-compose.test.yml << 'EOF'
   version: '3.8'
   
   services:
     data-acquisition:
       build:
         context: ../
         dockerfile: Dockerfile
       environment:
         - TESTING=true
       depends_on:
         - mock-api
     
     mock-api:
       image: mockserver/mockserver:latest
       ports:
         - "1080:1080"
       environment:
         - MOCKSERVER_INITIALIZATION_JSON_PATH=/config/mockserver.json
       volumes:
         - ./mocks:/config
   EOF
   
   # 3. Create test runner script
   cat > scripts/run_tests.sh << 'EOF'
   #!/bin/bash
   set -e
   
   COMPONENT=$1
   TEST_TYPE=$2
   
   if [ -z "$COMPONENT" ]; then
     echo "Usage: $0 <component> [unit|integration|all]"
     exit 1
   fi
   
   cd services/$COMPONENT
   
   case "$TEST_TYPE" in
     unit)
       pytest tests/unit -v -m unit
       ;;
     integration)
       docker-compose -f tests/docker-compose.test.yml up -d
       pytest tests/integration -v -m integration
       docker-compose -f tests/docker-compose.test.yml down
       ;;
     all|"")
       pytest tests -v
       ;;
     *)
       echo "Unknown test type: $TEST_TYPE"
       exit 1
       ;;
   esac
   EOF
   
   chmod +x scripts/run_tests.sh
   ```

2. **Integrate Tests with CI Pipeline**
   - Add testing stage to GitHub Actions
   - Implement test result reporting
   - Create code coverage visualization

### Phase 6: Integration and Verification (Days 15-16)

1. **Combine All Improvements**
   - Merge all components into unified pipeline
   - Create comprehensive deployment process
   - Implement monitoring and verification

2. **Documentation and Training**
   - Create detailed documentation for all changes
   - Update project READMEs
   - Document troubleshooting procedures

## Success Criteria

- **Security**: All Helm charts pass security scanning with no HIGH or CRITICAL issues
- **Reliability**: Zero deployment failures due to infrastructure issues
- **Efficiency**: 30% reduction in total pipeline execution time
- **Quality**: 90%+ test coverage for critical components
- **Usability**: Clear error messages and recovery procedures

## Implementation Timeline

```
Week 1: Phases 1-2 (Foundation, Security, Validation)
Week 2: Phases 3-4 (State Management, GitHub Actions)
Week 3: Phases 5-6 (Testing, Integration, Documentation)
```

## Priority Order for Implementation

1. Fix Helm Chart securityContext Issues (SENTI-1746817183)
2. Implement Terraform State Locking Fix (SENTI-1746817193)
3. Set Up GitHub Actions Pipeline Improvements (SENTI-1746817195)
4. Create Helm Schema Validation Script (SENTI-1746817184)
5. Set up Unit and Integration Tests (SENTI-1746811668)

## Monitoring and Maintenance

- Implement daily automated test runs
- Create weekly security scanning
- Set up automated dependency updates
- Establish monthly review process for pipeline performance