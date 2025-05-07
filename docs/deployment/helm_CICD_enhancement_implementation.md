# Sentimark: Enhanced Helm Deployment Process for AKS

This document describes the improved Helm deployment process implemented for the Sentimark sentiment analysis platform. It covers the architectural improvements, deployment strategies, and best practices for reliable deployments in private AKS environments.

## Overview of Improvements

The enhanced deployment process addresses several critical challenges:

1. **Secure Private AKS Deployments**: Enables deployments to private AKS clusters with no public IP exposure
2. **Robust Base64 Handling**: Fixes encoding/decoding issues when transferring Helm charts
3. **Comprehensive Error Handling**: Provides detailed error reporting and automatic recovery
4. **Deployment Verification**: Built-in verification steps to ensure successful service deployment
5. **Spot Instance Support**: Optimized deployment for cost-effective Azure spot instances
6. **Detailed Logging**: Structured logging for auditing and troubleshooting

## Architectural Improvements

### Two-Phase Deployment Approach

The deployment now follows a two-phase approach:

1. **Infrastructure Deployment (Terraform)**: 
   - Provisions Azure resources including AKS clusters, storage, and networking
   - Configures node pools including specialized spot instance pools for optimized workloads
   - Sets up necessary IAM permissions and security controls

2. **Application Deployment (Helm via CI/CD)**:
   - Deploys containerized services using Helm charts
   - Handles service configuration and dependencies
   - Supports rolling updates and zero-downtime deployments

### Enhanced Helm Deployment Script

The `helm_deploy_fixed.sh` script provides:

- Reliable deployment to private AKS clusters using `az aks command invoke`
- Proper chunking and handling of large base64-encoded Helm charts
- Multiple deployment methods (direct Helm or pod-based Helm for compatibility)
- Progressive verification of deployment success
- Detailed logging and diagnostics

### Integration with CI/CD Pipeline

The deployment process integrates with the existing GitHub Actions workflow:

- Comprehensive testing across multiple dimensions (unit tests, integration tests)
- Security scanning for dependencies and container images
- Optimized Docker builds with caching
- Post-deployment verification to validate system functionality

## Key Components

### Secure Chart Transfer

The improved process securely transfers Helm charts to private AKS clusters by:

1. Properly encoding chart packages using base64
2. Chunking large files to avoid command line limitations
3. Verifying integrity after transfer
4. Using kubectl cp for file transfer when available

### Deployment Methods

Two deployment methods are supported based on environment capabilities:

1. **Direct Helm Execution**: Used when Helm is available in the AKS command environment
   - More efficient and simpler execution
   - Preferred method when available

2. **Pod-based Helm Execution**: Fallback method for constrained environments
   - Creates a temporary pod with Helm installed
   - Transfers and executes chart within the pod
   - Automatically cleans up after deployment

### Verification and Rollback

The deployment includes verification steps:

- Checks deployed pods and services
- Verifies Helm release status
- Captures detailed logs for auditing
- Provides automatic cleanup on failures
- Documents rollback commands for manual recovery

## Implementation Best Practices

### Spot Instance Considerations

When deploying to spot instance node pools:

1. Use appropriate tolerations and node selectors in Helm values
2. Set resource requests and limits appropriate for spot instance types
3. Implement retry logic for spot instance preemption
4. Use PodDistruptionBudgets for critical services

### Security Best Practices

The implementation follows security best practices:

1. No secrets in Helm values files or command line arguments
2. Uses Azure-managed identities where possible
3. Implements proper RBAC within Kubernetes
4. Maintains isolation between namespaces

### Monitoring and Alerting

Deployment results are captured in:

1. Structured JSON logs for automated processing
2. Terminal output for operator visibility
3. Integration with Azure Monitor for metrics and alerts
4. Kubernetes event logging for detailed diagnostics

## Deployment Workflow

A typical deployment follows these steps:

1. **Environment Setup**:
   ```bash
   cd environments/sit && ./setup.sh
   ```

2. **Terraform Infrastructure Deployment**:
   ```bash
   cd infrastructure/terraform/azure && ./run-terraform.sh
   ```

3. **Application Deployment using Helm**:
   ```bash
   cd environments/sit
   ./helm_deploy_fixed.sh --release-name sentimark --namespace sit
   ```

4. **Verification**:
   ```bash
   ./verify_deployment.sh
   ```

## Troubleshooting Guide

### Common Issues and Resolutions

| Issue | Solution |
|-------|----------|
| Base64 decoding failures | Ensure no line breaks in base64 output; check for CRLF vs LF issues |
| AKS command permission errors | Verify Azure user has proper RBAC permissions on the AKS cluster |
| Chart package too large | Reduce chart size by excluding unnecessary files or use repository-based charts |
| Pod creation failures | Check node resource availability and pod security policies |
| Timeout during deployment | Increase timeout parameter or check resource constraints |

### Diagnostic Commands

For deployment issues, use these diagnostic commands:

```bash
# Check pod status
az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command "kubectl get pods -n sit"

# View pod logs
az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command "kubectl logs <pod-name> -n sit"

# Check Helm release status
az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command "helm list -n sit"

# Get detailed Helm release information
az aks command invoke -g sentimark-sit-rg -n sentimark-sit-aks --command "helm get all sentimark -n sit"
```

## Future Enhancements

Planned improvements to the deployment process:

1. **Canary Deployments**: Implementing progressive traffic shifting for safer rollouts
2. **A/B Testing**: Supporting parallel deployments for feature comparison
3. **Automated Rollbacks**: Based on real-time monitoring metrics
4. **GitOps Integration**: Using tools like Flux or ArgoCD for declarative deployments
5. **Chart Repository**: Moving from file-based transfers to Helm repository hosting

## Deprecated Scripts

The following scripts are now deprecated and should not be used:

- `~/real_senti/environments/sit/helm_deploy.sh` (superseded by `helm_deploy_fixed.sh`)
- `~/real_senti/environments/sit/deploy_services.sh` (functionality integrated into CI/CD pipeline)

## Conclusion

The enhanced Helm deployment process provides a reliable, secure, and maintainable method for deploying the Sentimark sentiment analysis platform to Azure Kubernetes Service. By following the documented workflow and best practices, teams can achieve consistent deployments with minimal manual intervention.

For questions or issues, refer to the troubleshooting guide or contact the DevOps team.