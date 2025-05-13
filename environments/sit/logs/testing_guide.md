# Testing Guide for Sentimark SIT Deployment

## 1. Basic Deployment Test

To test the basic deployment functionality:

```bash
cd /home/jonat/real_senti/environments/sit
./deploy.sh
```

This will:
- Fix line endings in the scripts
- Create values override file for spot instances
- Deploy Helm charts to the AKS cluster

## 2. Verify Kubernetes Resources

Check the deployed resources in the Kubernetes cluster:

```bash
# Check Helm releases
az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command "helm list -n sit"

# Check running pods
az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command "kubectl get pods -n sit"

# Check services
az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command "kubectl get services -n sit"
```

## 3. Test Secure Credential Management

To test the secure credential management system:

```bash
# 1. Ensure pass is initialized
gpg --list-keys
pass ls

# 2. Set up test credentials
echo "test-client-id" | pass insert -f "sentimark/azure/AZURE-CLIENT-ID"
echo "test-client-secret" | pass insert -f "sentimark/azure/AZURE-CLIENT-SECRET"
echo "test-subscription-id" | pass insert -f "sentimark/azure/AZURE-SUBSCRIPTION-ID"
echo "test-tenant-id" | pass insert -f "sentimark/azure/AZURE-TENANT-ID"

# 3. Test loading credentials as environment variables
source ~/.sentimark/bin/load-terraform-env.sh
echo $TF_VAR_client_id
echo $ARM_CLIENT_ID

# 4. Test creating Terraform files from templates
cd /home/jonat/real_senti/infrastructure/terraform/azure
./init-terraform.sh
ls -la providers.tf backends/
```

## 4. Test CRLF Line Ending Fix

To specifically test the line ending fix functionality:

```bash
# 1. Create a test script with Windows-style CRLF line endings
cat > /tmp/test_crlf.sh << 'EOF'
#!/bin/bash
echo "This is a test script with CRLF line endings"
EOF

# 2. Convert Unix LF to Windows CRLF
sed -i 's/$/\r/' /tmp/test_crlf.sh
chmod +x /tmp/test_crlf.sh

# 3. Try to run the script (might fail due to CRLF)
/tmp/test_crlf.sh

# 4. Fix the script with our CRLF removal technique
tr -d '\r' < /tmp/test_crlf.sh > /tmp/test_crlf_fixed.sh
chmod +x /tmp/test_crlf_fixed.sh

# 5. Run the fixed script (should work correctly)
/tmp/test_crlf_fixed.sh
```

## 5. Test Spot Instance Configuration Override

To test the spot instance configuration handling:

```bash
# 1. Create a specific override for a test deployment
cat > /tmp/test-values-override.yaml << EOF
# Test override to specifically configure spot instances
dataAcquisition:
  useSpotInstances: true
  nodeSelector:
    "kubernetes.azure.com/scalesetpriority": "spot"
  tolerations:
  - key: "kubernetes.azure.com/scalesetpriority"
    operator: "Equal"
    value: "spot"
    effect: "NoSchedule"

dataMigration:
  useSpotInstances: false
  nodeSelector: {}
  tolerations: []
EOF

# 2. Run the deployment with this specific values override
cd /home/jonat/real_senti/environments/sit
./helm_deploy_fixed.sh --release-name test-spot --namespace sit-test \
  --chart-dir /home/jonat/real_senti/infrastructure/helm/sentimark-services \
  --values-file /tmp/test-values-override.yaml
```

## 6. Test Script Error Handling

To test the error handling in the deployment script:

```bash
# 1. Test with invalid chart directory
cd /home/jonat/real_senti/environments/sit
./helm_deploy_fixed.sh --release-name test-error --namespace sit-test \
  --chart-dir /nonexistent/chart/path

# 2. Test with invalid values file
./helm_deploy_fixed.sh --release-name test-error --namespace sit-test \
  --chart-dir /home/jonat/real_senti/infrastructure/helm/sentimark-services \
  --values-file /nonexistent/values.yaml
```

## 7. Full End-to-End Testing

For a complete end-to-end test including the Terraform infrastructure:

```bash
# 1. Set up credentials (assuming they're already in Azure Key Vault)
~/.sentimark/bin/sync-azure-credentials.sh

# 2. Initialize Terraform configuration
cd /home/jonat/real_senti/infrastructure/terraform/azure
./init-terraform.sh

# 3. Apply Terraform configuration for SIT environment
source ~/.sentimark/bin/load-terraform-env.sh
terraform init -backend-config=backends/sit.tfbackend
terraform plan -out=tfplan.sit
terraform apply tfplan.sit

# 4. Deploy services to the newly created infrastructure
cd /home/jonat/real_senti/environments/sit
./deploy.sh
```

## 8. Verify Logging

Check that the deployment logs are properly created:

```bash
# Check the most recent deployment log
ls -la /home/jonat/real_senti/environments/sit/logs/deployment_*.json | tail -1
cat $(ls -la /home/jonat/real_senti/environments/sit/logs/deployment_*.json | tail -1 | awk '{print $9}')

# Check verification logs
ls -la /home/jonat/real_senti/environments/sit/logs/verification_*.json | tail -1
cat $(ls -la /home/jonat/real_senti/environments/sit/logs/verification_*.json | tail -1 | awk '{print $9}')
```

## 9. Cleanup After Testing

To clean up after testing:

```bash
# Remove test releases
az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command "helm uninstall test-spot -n sit-test"

# Remove test namespace
az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command "kubectl delete namespace sit-test"

# Clean up test credentials (if created)
pass rm sentimark/azure/AZURE-CLIENT-ID
pass rm sentimark/azure/AZURE-CLIENT-SECRET
pass rm sentimark/azure/AZURE-SUBSCRIPTION-ID
pass rm sentimark/azure/AZURE-TENANT-ID
```