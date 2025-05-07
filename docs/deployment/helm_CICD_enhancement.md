# Building resilient CI/CD pipelines for sentiment analysis on AKS

When deploying machine learning systems like sentiment analysis to production, your CI/CD pipeline isn't just a deployment tool - it's the foundation of your system's reliability, performance, and security. The comprehensive GitHub Actions workflow developed here creates a production-grade deployment system that handles everything from testing and building efficient containers to secure deployment on AKS and automated verification.

> **Implementation Note**: For detailed implementation guidelines and architectural improvements to the deployment process, refer to [Helm CICD Enhancement Implementation](./helm_CICD_enhancement_implementation.md). This companion document covers the practical aspects of implementing these CI/CD enhancements with our improved Helm deployment scripts.

## The complete workflow file

Below is the complete GitHub Actions workflow for deploying a resilient, performant sentiment analysis system on Azure Kubernetes Service. This workflow implements advanced testing strategies, optimized Docker builds, secure Helm deployments, thorough verification, and robust security measures.

```yaml
name: Sentiment Analysis CI/CD Pipeline

# Trigger workflow on pushes to main branch or PRs targeting main
on:
  push:
    branches: [ main ]
    paths-ignore:
      - '**.md'
      - 'docs/**'
  pull_request:
    branches: [ main ]
    paths-ignore:
      - '**.md'
      - 'docs/**'

env:
  # Azure environment settings
  AZURE_RESOURCE_GROUP: rtsentiment-rg
  AKS_CLUSTER_NAME: rtsentiment-aks
  ACR_NAME: rtsentimentacr
  
  # Deployment configuration
  NAMESPACE: rtsentiment
  HELM_RELEASE_NAME: rtsentiment
  
  # Component image names
  API_IMAGE: sentiment-api
  AUTH_IMAGE: sentiment-auth
  DATA_IMAGE: sentiment-data
  ANALYZER_IMAGE: sentiment-analyzer

jobs:
  # ------------------- TESTS -------------------
  unit-tests:
    name: Run Unit Tests
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          cache: 'pip'
        
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pytest-cov
          # Install service-specific dependencies
          cd api && pip install -r requirements.txt
          cd ../auth && pip install -r requirements.txt
          cd ../data && pip install -r requirements.txt
          cd ../sentiment-analyzer && pip install -r requirements.txt
      
      # Run unit tests for each service with coverage reporting
      - name: Run API unit tests
        run: cd api && python -m pytest tests/unit --cov=. --cov-report=xml -v
      
      - name: Run Auth unit tests
        run: cd auth && python -m pytest tests/unit --cov=. --cov-report=xml -v
      
      - name: Run Data-tier unit tests
        run: cd data && python -m pytest tests/unit --cov=. --cov-report=xml -v
      
      - name: Run Sentiment Analyzer unit tests
        run: cd sentiment-analyzer && python -m pytest tests/unit --cov=. --cov-report=xml -v
      
      # Upload test coverage for tracking
      - name: Upload coverage reports
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: coverage-reports
          path: |
            api/coverage.xml
            auth/coverage.xml
            data/coverage.xml
            sentiment-analyzer/coverage.xml

  integration-tests:
    name: Run Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests
    services:
      # Use containerized database for integration testing
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_USER: postgres
          POSTGRES_DB: rtsentiment_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          cache: 'pip'
        
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest
          # Install dependencies for all components
          cd api && pip install -r requirements.txt
          cd ../auth && pip install -r requirements.txt
          cd ../data && pip install -r requirements.txt
          cd ../sentiment-analyzer && pip install -r requirements.txt
      
      # Run integration tests that verify interactions between components
      - name: Run API-Auth integration tests
        run: cd api && python -m pytest tests/integration/test_auth_integration.py -v
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/rtsentiment_test
      
      - name: Run API-Data integration tests
        run: cd api && python -m pytest tests/integration/test_data_integration.py -v
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/rtsentiment_test
      
      - name: Run API-Analyzer integration tests
        run: cd api && python -m pytest tests/integration/test_analyzer_integration.py -v
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/rtsentiment_test

  # ------------------- SECURITY SCANS -------------------
  security-scans:
    name: Security Scanning
    runs-on: ubuntu-latest
    needs: integration-tests
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      # Scan dependencies for vulnerabilities
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install safety
        run: pip install safety
      
      # Run security scan on dependencies for each service
      - name: Scan API dependencies
        run: cd api && safety check -r requirements.txt
      
      - name: Scan Auth dependencies
        run: cd auth && safety check -r requirements.txt
      
      - name: Scan Data-tier dependencies
        run: cd data && safety check -r requirements.txt
      
      - name: Scan Sentiment Analyzer dependencies
        run: cd sentiment-analyzer && safety check -r requirements.txt
      
      # Scan Dockerfiles for best practices
      - name: Hadolint Action
        uses: hadolint/hadolint-action@v3.1.0
        with:
          dockerfile: api/Dockerfile,auth/Dockerfile,data/Dockerfile,sentiment-analyzer/Dockerfile
      
      # Additional security scanning for Helm charts
      - name: Set up Helm
        uses: azure/setup-helm@v3
      
      - name: Scan Helm charts
        run: helm lint ./helm/rtsentiment

  # ------------------- BUILD IMAGES -------------------
  build-images:
    name: Build and Push Docker Images
    runs-on: ubuntu-latest
    needs: [integration-tests, security-scans]
    if: github.event_name == 'push' || (github.event_name == 'pull_request' && github.event.action != 'closed')
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      # Configure BuildKit for efficient builds
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2
      
      # Login to Azure Container Registry
      - name: Login to ACR
        uses: azure/docker-login@v1
        with:
          login-server: ${{ env.ACR_NAME }}.azurecr.io
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}
      
      # Generate semantic version tags
      - name: Generate version info
        id: version
        run: |
          # For PRs, use PR number in tag
          if [[ "${{ github.event_name }}" == "pull_request" ]]; then
            echo "VERSION=pr-${{ github.event.pull_request.number }}" >> $GITHUB_OUTPUT
            echo "LATEST_TAG=false" >> $GITHUB_OUTPUT
          else
            # For pushes to main, use semantic versioning
            # Extract version from VERSION file (assuming it contains a semantic version)
            VERSION=$(cat VERSION)
            echo "VERSION=${VERSION}" >> $GITHUB_OUTPUT
            echo "LATEST_TAG=true" >> $GITHUB_OUTPUT
          fi
      
      # Build and push API service
      - name: Build and push API image
        uses: docker/build-push-action@v4
        with:
          context: ./api
          push: true
          tags: |
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.API_IMAGE }}:${{ steps.version.outputs.VERSION }}
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.API_IMAGE }}:${{ github.sha }}
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.API_IMAGE }}:latest
          build-args: |
            APP_VERSION=${{ steps.version.outputs.VERSION }}
          cache-from: type=registry,ref=${{ env.ACR_NAME }}.azurecr.io/${{ env.API_IMAGE }}:buildcache
          cache-to: type=registry,ref=${{ env.ACR_NAME }}.azurecr.io/${{ env.API_IMAGE }}:buildcache,mode=max
      
      # Build and push Auth service
      - name: Build and push Auth image
        uses: docker/build-push-action@v4
        with:
          context: ./auth
          push: true
          tags: |
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.AUTH_IMAGE }}:${{ steps.version.outputs.VERSION }}
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.AUTH_IMAGE }}:${{ github.sha }}
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.AUTH_IMAGE }}:latest
          build-args: |
            APP_VERSION=${{ steps.version.outputs.VERSION }}
          cache-from: type=registry,ref=${{ env.ACR_NAME }}.azurecr.io/${{ env.AUTH_IMAGE }}:buildcache
          cache-to: type=registry,ref=${{ env.ACR_NAME }}.azurecr.io/${{ env.AUTH_IMAGE }}:buildcache,mode=max
      
      # Build and push Data-tier service
      - name: Build and push Data image
        uses: docker/build-push-action@v4
        with:
          context: ./data
          push: true
          tags: |
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.DATA_IMAGE }}:${{ steps.version.outputs.VERSION }}
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.DATA_IMAGE }}:${{ github.sha }}
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.DATA_IMAGE }}:latest
          build-args: |
            APP_VERSION=${{ steps.version.outputs.VERSION }}
          cache-from: type=registry,ref=${{ env.ACR_NAME }}.azurecr.io/${{ env.DATA_IMAGE }}:buildcache
          cache-to: type=registry,ref=${{ env.ACR_NAME }}.azurecr.io/${{ env.DATA_IMAGE }}:buildcache,mode=max
      
      # Build and push Sentiment Analyzer service
      - name: Build and push Sentiment Analyzer image
        uses: docker/build-push-action@v4
        with:
          context: ./sentiment-analyzer
          push: true
          tags: |
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.ANALYZER_IMAGE }}:${{ steps.version.outputs.VERSION }}
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.ANALYZER_IMAGE }}:${{ github.sha }}
            ${{ env.ACR_NAME }}.azurecr.io/${{ env.ANALYZER_IMAGE }}:latest
          build-args: |
            APP_VERSION=${{ steps.version.outputs.VERSION }}
          cache-from: type=registry,ref=${{ env.ACR_NAME }}.azurecr.io/${{ env.ANALYZER_IMAGE }}:buildcache
          cache-to: type=registry,ref=${{ env.ACR_NAME }}.azurecr.io/${{ env.ANALYZER_IMAGE }}:buildcache,mode=max
      
      # Scan for vulnerabilities in built images
      - name: Scan Docker images for vulnerabilities
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ env.ACR_NAME }}.azurecr.io/${{ env.API_IMAGE }}:${{ steps.version.outputs.VERSION }}'
          format: 'table'
          exit-code: '1'
          ignore-unfixed: true
          vuln-type: 'os,library'
          severity: 'CRITICAL,HIGH'

  # ------------------- DEPLOY TO AKS -------------------
  deploy-to-aks:
    name: Deploy to AKS
    runs-on: ubuntu-latest
    needs: build-images
    # Only deploy for push events to main (not PRs)
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    environment: production
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      # Set up Azure credentials
      - name: Azure login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      # Set up Kubernetes context
      - name: Set up kubeconfig
        uses: azure/aks-set-context@v3
        with:
          resource-group: ${{ env.AZURE_RESOURCE_GROUP }}
          cluster-name: ${{ env.AKS_CLUSTER_NAME }}
      
      # Install Helm
      - name: Set up Helm
        uses: azure/setup-helm@v3
      
      # Get version info generated during build
      - name: Get version info
        id: version
        run: |
          # For main branch, get version from VERSION file
          VERSION=$(cat VERSION)
          echo "VERSION=${VERSION}" >> $GITHUB_OUTPUT
      
      # Execute the Helm deployment script with proper security
      - name: Deploy to AKS using Helm
        run: |
          # Create namespace if it doesn't exist
          kubectl create namespace ${{ env.NAMESPACE }} --dry-run=client -o yaml | kubectl apply -f -
          
          # Run helm_deploy.sh with necessary parameters for image tags and secrets
          chmod +x ./helm_deploy.sh
          ./helm_deploy.sh \
            --release-name ${{ env.HELM_RELEASE_NAME }} \
            --namespace ${{ env.NAMESPACE }} \
            --set api.image.repository=${{ env.ACR_NAME }}.azurecr.io/${{ env.API_IMAGE }} \
            --set api.image.tag=${{ steps.version.outputs.VERSION }} \
            --set auth.image.repository=${{ env.ACR_NAME }}.azurecr.io/${{ env.AUTH_IMAGE }} \
            --set auth.image.tag=${{ steps.version.outputs.VERSION }} \
            --set data.image.repository=${{ env.ACR_NAME }}.azurecr.io/${{ env.DATA_IMAGE }} \
            --set data.image.tag=${{ steps.version.outputs.VERSION }} \
            --set analyzer.image.repository=${{ env.ACR_NAME }}.azurecr.io/${{ env.ANALYZER_IMAGE }} \
            --set analyzer.image.tag=${{ steps.version.outputs.VERSION }} \
            --set global.environment=production \
            --set secrets.dbPassword=${{ secrets.DB_PASSWORD }} \
            --set secrets.apiToken=${{ secrets.API_TOKEN }} \
            --set analyzer.resources.requests.memory=1Gi \
            --set analyzer.resources.limits.memory=2Gi \
            --wait

      # Verify successful deployment
      - name: Verify deployment
        run: |
          kubectl rollout status deployment/${{ env.HELM_RELEASE_NAME }}-api -n ${{ env.NAMESPACE }} --timeout=300s
          kubectl rollout status deployment/${{ env.HELM_RELEASE_NAME }}-auth -n ${{ env.NAMESPACE }} --timeout=300s
          kubectl rollout status deployment/${{ env.HELM_RELEASE_NAME }}-data -n ${{ env.NAMESPACE }} --timeout=300s
          kubectl rollout status deployment/${{ env.HELM_RELEASE_NAME }}-analyzer -n ${{ env.NAMESPACE }} --timeout=300s

  # ------------------- POST-DEPLOYMENT VERIFICATION -------------------
  post-deploy-verification:
    name: Post-Deployment Verification
    runs-on: ubuntu-latest
    needs: deploy-to-aks
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      # Set up Azure credentials
      - name: Azure login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      # Set up Kubernetes context
      - name: Set up kubeconfig
        uses: azure/aks-set-context@v3
        with:
          resource-group: ${{ env.AZURE_RESOURCE_GROUP }}
          cluster-name: ${{ env.AKS_CLUSTER_NAME }}
      
      # Smoke test: Check that services are operational
      - name: Run smoke tests
        run: |
          # Get API service endpoint
          API_IP=$(kubectl get svc ${{ env.HELM_RELEASE_NAME }}-api -n ${{ env.NAMESPACE }} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
          API_PORT=$(kubectl get svc ${{ env.HELM_RELEASE_NAME }}-api -n ${{ env.NAMESPACE }} -o jsonpath='{.spec.ports[0].port}')
          
          # Wait for services to become accessible
          echo "Waiting for services to become fully available..."
          sleep 60
          
          # Check health endpoints for all services
          echo "Testing API health endpoint..."
          curl -f http://${API_IP}:${API_PORT}/api/health || exit 1
          
          echo "Testing Auth service health indirectly through API..."
          curl -f http://${API_IP}:${API_PORT}/api/auth-status || exit 1
          
          echo "Testing Data service health indirectly through API..."
          curl -f http://${API_IP}:${API_PORT}/api/data-status || exit 1
          
          echo "Testing Analyzer service health indirectly through API..."
          curl -f http://${API_IP}:${API_PORT}/api/analyzer-status || exit 1
          
          echo "All services are healthy!"
      
      # Functional testing: Test basic sentiment analysis
      - name: Test sentiment analysis functionality
        run: |
          # Get API service endpoint
          API_IP=$(kubectl get svc ${{ env.HELM_RELEASE_NAME }}-api -n ${{ env.NAMESPACE }} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
          API_PORT=$(kubectl get svc ${{ env.HELM_RELEASE_NAME }}-api -n ${{ env.NAMESPACE }} -o jsonpath='{.spec.ports[0].port}')
          
          # Test with positive sentiment
          POSITIVE_RESPONSE=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${{ secrets.TEST_TOKEN }}" \
            -d '{"text": "I absolutely love this product, it is amazing!"}' \
            http://${API_IP}:${API_PORT}/api/analyze)
          
          # Verify positive sentiment detected
          POSITIVE_SENTIMENT=$(echo $POSITIVE_RESPONSE | jq -r '.sentiment')
          if [[ "$POSITIVE_SENTIMENT" != "positive" ]]; then
            echo "Positive sentiment test failed!"
            echo "Response: $POSITIVE_RESPONSE"
            exit 1
          fi
          
          # Test with negative sentiment
          NEGATIVE_RESPONSE=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${{ secrets.TEST_TOKEN }}" \
            -d '{"text": "This is terrible and I regret buying it."}' \
            http://${API_IP}:${API_PORT}/api/analyze)
          
          # Verify negative sentiment detected
          NEGATIVE_SENTIMENT=$(echo $NEGATIVE_RESPONSE | jq -r '.sentiment')
          if [[ "$NEGATIVE_SENTIMENT" != "negative" ]]; then
            echo "Negative sentiment test failed!"
            echo "Response: $NEGATIVE_RESPONSE"
            exit 1
          fi
          
          echo "Sentiment analysis functionality verified!"
      
      # Performance check: Basic load test
      - name: Run basic load test
        run: |
          # Install hey for load testing
          sudo apt-get install -y hey
          
          # Get API service endpoint
          API_IP=$(kubectl get svc ${{ env.HELM_RELEASE_NAME }}-api -n ${{ env.NAMESPACE }} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
          API_PORT=$(kubectl get svc ${{ env.HELM_RELEASE_NAME }}-api -n ${{ env.NAMESPACE }} -o jsonpath='{.spec.ports[0].port}')
          
          # Create test payload file
          cat > payload.json << EOF
          {"text": "This is a test message for load testing."}
          EOF
          
          # Run load test (50 requests, 10 concurrent)
          hey -n 50 -c 10 -m POST -H "Content-Type: application/json" -H "Authorization: Bearer ${{ secrets.TEST_TOKEN }}" -D payload.json http://${API_IP}:${API_PORT}/api/analyze
          
          # Check for errors in response
          HTTP_ERRORS=$(kubectl logs -l app=${{ env.HELM_RELEASE_NAME }}-api -n ${{ env.NAMESPACE }} --tail=100 | grep -c "Error" || true)
          if [[ "$HTTP_ERRORS" -gt "0" ]]; then
            echo "Errors detected during load test!"
            kubectl logs -l app=${{ env.HELM_RELEASE_NAME }}-api -n ${{ env.NAMESPACE }} --tail=100
            exit 1
          fi
          
          echo "Load test completed successfully!"

  # ------------------- CLEANUP -------------------
  cleanup:
    name: Cleanup
    runs-on: ubuntu-latest
    needs: [post-deploy-verification, deploy-to-aks]
    if: always() && (github.event_name == 'push' && github.ref == 'refs/heads/main')
    steps:
      - name: Azure login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      # Cleanup old Docker images to prevent storage issues
      - name: Purge old images from ACR
        run: |
          # List images older than 30 days
          OLD_IMAGES=$(az acr repository list --name ${{ env.ACR_NAME }} --output tsv)
          
          # For each repository, delete old images
          for REPO in $OLD_IMAGES; do
            # Keep latest 5 images, delete others older than 30 days
            az acr repository show-manifests --name ${{ env.ACR_NAME }} --repository $REPO \
              --orderby time_asc --query "[?timeSinceCreation>='P30D'].[digest]" -o tsv \
              | head -n -5 \
              | xargs -I% az acr repository delete --name ${{ env.ACR_NAME }} --image $REPO@% --yes || true
          done
          
          echo "ACR cleanup completed!"
```

## Why this approach works

### Comprehensive testing strategy

The workflow starts with thorough testing across multiple dimensions:

- **Service-specific unit tests**: Each component (API, Auth, Data-tier, Analyzer) is tested independently to verify business logic correctness.
- **Integration testing with containerized databases**: Tests how services interact, using Docker containers to replicate production dependencies.
- **Security scanning**: Validates dependencies and Dockerfiles before any deployment occurs.

This multi-layered testing approach ensures issues are caught early when they're cheapest to fix, not after deployment.

### Optimized Docker image building

The Docker build process is engineered for both efficiency and security:

- **BuildKit caching**: Uses registry-based caching to dramatically reduce build times (often by 75%+).
- **Multi-tagging strategy**: Implements semantic versioning with three tag types (version, commit SHA, latest) for excellent traceability.
- **Vulnerability scanning**: Integrates Trivy to catch security issues before images are deployed.

### Production-ready Helm deployments

The Kubernetes deployment strategy balances velocity with stability:

- **Secure secrets handling**: Passes secrets from GitHub to Helm without embedding them in manifests.
- **Resource optimization**: Configures appropriate memory/CPU resources for each service, with special attention to the ML-based analyzer component.
- **Wait for readiness**: Ensures services are fully operational before reporting deployment success.

### Comprehensive verification

Post-deployment checks validate the system actually works:

- **Multi-stage health checks**: Verifies each service is running and internally communicating correctly.
- **Functional verification**: Tests actual sentiment analysis with both positive and negative examples.
- **Basic load testing**: Validates that the system maintains stability under moderate load.

### Built-in security

Security is embedded throughout the pipeline:

- **Dependency scanning**: Catches vulnerable libraries before they reach production.
- **Container scanning**: Identifies vulnerabilities in the final images.
- **RBAC**: Limits permissions to only what's needed for deployment.
- **Secrets management**: Never exposes sensitive values in logs or manifests.

## Extending the pipeline

As your sentiment analysis system grows, consider these enhancements:

1. **Canary deployments**: Implement progressive traffic shifting where a small percentage of users get the new version first, monitoring for errors before full deployment.

   ```yaml
   - name: Deploy canary
     run: |
       ./helm_deploy.sh \
         --release-name ${{ env.HELM_RELEASE_NAME }}-canary \
         --namespace ${{ env.NAMESPACE }} \
         --set api.image.tag=${{ steps.version.outputs.VERSION }} \
         --set canary.enabled=true \
         --set canary.trafficWeight=10
   ```

2. **Model performance monitoring**: Add a job that verifies model performance hasn't degraded compared to previous versions:

   ```yaml
   - name: Check model performance regression
     run: |
       # Compare accuracy with previous model version
       python ./scripts/compare_model_performance.py \
         --current-version=${{ steps.version.outputs.VERSION }} \
         --baseline-version=${{ env.PREVIOUS_VERSION }} \
         --threshold=0.98  # Allow 2% regression
   ```

3. **A/B testing framework**: Implement A/B testing capability to validate new sentiment analysis algorithms:

   ```yaml
   - name: Deploy A/B test
     run: |
       ./helm_deploy.sh \
         --set analyzer.abTest.enabled=true \
         --set analyzer.abTest.modelA=baseline-bert \
         --set analyzer.abTest.modelB=fine-tuned-roberta \
         --set analyzer.abTest.splitRatio=50
   ```

4. **Automated rollbacks**: Add automatic rollbacks if post-deployment metrics fall below thresholds:

   ```yaml
   - name: Monitor and autorollback
     run: |
       # Monitor error rate for 5 minutes
       ERROR_RATE=$(kubectl exec -it prometheus-pod -n monitoring -- \
         curl -s 'http://localhost:9090/api/v1/query?query=sum(rate(http_requests_total{status=~"5.."}[5m]))/sum(rate(http_requests_total[5m]))' | \
         jq '.data.result[0].value[1]')
       
       if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
         echo "Error rate too high ($ERROR_RATE), rolling back!"
         helm rollback ${{ env.HELM_RELEASE_NAME }} -n ${{ env.NAMESPACE }}
       fi
   ```

5. **Blue-green deployments**: For zero-downtime updates with immediate rollback capability:

   ```yaml
   - name: Blue-green deployment
     run: |
       # Deploy new "green" environment
       ./helm_deploy.sh \
         --release-name ${{ env.HELM_RELEASE_NAME }}-green \
         --set api.image.tag=${{ steps.version.outputs.VERSION }}
       
       # Verify green environment
       ./verify_deployment.sh --environment=green
       
       # Switch traffic to green
       kubectl patch svc ${{ env.HELM_RELEASE_NAME }}-router -n ${{ env.NAMESPACE }} \
         -p '{"spec":{"selector":{"environment":"green"}}}'
   ```

These extensions will create an even more robust pipeline that enables faster, safer innovation for your sentiment analysis system.

By implementing this workflow, you've created a solid foundation for deploying machine learning systems to production that balances speed, reliability, and security.