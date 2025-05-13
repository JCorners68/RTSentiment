# Sentimark CICD Implementation Plan

## Overview

This implementation plan addresses two critical issues in the Sentimark CI/CD infrastructure:

1. **Helm Chart securityContext Issues**: The current Helm charts have securityContext defined at the pod level, but Kubernetes best practices recommend defining it at the container level.

2. **CICD Logging Integration**: Our Phase 5 implementation requires comprehensive logging for deployment events, feature flag changes, data migrations, and rollbacks.

This document provides a structured approach to implement both fixes, with detailed verification steps and rollback procedures.

## 1. Helm Chart securityContext Fix

### Issue Description

The current Helm charts define securityContext at the pod level, which is causing issues with security scanning tools and doesn't follow Kubernetes best practices. The securityContext settings should be moved to the container level for better security and compatibility.

### Implementation Steps

1. **Backup Current Templates**
   - The `securitycontext_fix.sh` script automatically creates backups of all templates before modification
   - Backups are stored in `/home/jonat/real_senti/infrastructure/helm/sentimark-services/templates_backup_YYYYMMDD_HHMMSS/`

2. **Fix Regular Expression**
   - The script has been fixed to properly handle the regex pattern for identifying and commenting out pod-level securityContext
   - The corrected pattern is now working properly

3. **Move securityContext to Container Level**
   - The script identifies and extracts the securityContext block from pod-level
   - It then inserts the block at the container level with proper indentation

4. **Verification**
   - The script includes a verification step that checks each template for:
     - Proper removal of pod-level securityContext
     - Proper insertion of container-level securityContext
   - Any files that fail verification are flagged for manual review

### Verification Steps

After running the script, perform these verification steps:

```bash
# Run Helm lint to validate syntax
helm lint /home/jonat/real_senti/infrastructure/helm/sentimark-services

# Generate template and check for securityContext placement
helm template /home/jonat/real_senti/infrastructure/helm/sentimark-services > /tmp/helm_template.yaml
grep -A 10 -B 2 "securityContext:" /tmp/helm_template.yaml

# Run security scan on the template
curl -s https://raw.githubusercontent.com/controlplaneio/kubesec/master/install.sh | sh
kubesec scan /tmp/helm_template.yaml > /tmp/security_scan.json
cat /tmp/security_scan.json | jq '.[] | .scoring.advise[] | select(.selector | contains("securityContext"))'
```

### Rollback Procedure

If issues are detected, you can easily roll back using the backups:

```bash
# Find the backup directory
ls -la /home/jonat/real_senti/infrastructure/helm/sentimark-services/templates_backup_*

# Restore from backup
cp /home/jonat/real_senti/infrastructure/helm/sentimark-services/templates_backup_YYYYMMDD_HHMMSS/* \
   /home/jonat/real_senti/infrastructure/helm/sentimark-services/templates/
```

## 2. CICD Logging Integration

### Implementation Overview

The CICD logging integration implements a comprehensive logging framework that connects to Azure Monitor/Log Analytics and provides specialized logging for:

1. Feature flag changes
2. Data migration processes
3. Iceberg operations
4. Rollback events

### Implementation Steps

1. **Azure Resource Creation**
   - The script creates or uses existing Azure Log Analytics workspace and Application Insights resources
   - These resources provide the centralized storage and querying capabilities for logs

2. **Custom Log Tables**
   - Creates templates for custom log tables in Azure Log Analytics:
     - `SentimarkFeatureFlagChanges_CL`
     - `SentimarkDataMigration_CL`
     - `SentimarkIcebergOperations_CL`
     - `SentimarkRollbackEvents_CL`

3. **Client Libraries**
   - Creates both bash and Java client libraries for logging events
   - The bash library supports shell scripts and CI/CD processes
   - The Java library integrates with the data tier service

4. **Integration Hooks**
   - Implements several integration hooks into existing services:
     - `FeatureFlagChangeListener`: For tracking feature flag changes
     - `LoggingMigrationDecorator`: For tracking data migrations
     - `IcebergOperationListener`: For tracking Iceberg operations
     - `LoggingRollbackDecorator`: For tracking rollback events

5. **Configuration**
   - Creates environment configuration for bash scripts
   - Creates Spring Boot configuration for Java components

6. **Example Scripts**
   - Provides example scripts for testing and demonstration
   - Includes a CLI tool for viewing logs from Azure Log Analytics

7. **Documentation**
   - Creates comprehensive documentation in the specified location according to CLAUDE.md preferences
   - Includes implementation guides and troubleshooting procedures

### Verification Steps

After running the script, perform these verification steps:

```bash
# Verify Azure resources
az monitor log-analytics workspace show \
  --resource-group sentimark-sit-rg \
  --workspace-name sentimark-logs

az monitor app-insights component show \
  --resource-group sentimark-sit-rg \
  --app sentimark-appinsights

# Test logging with example scripts
source /home/jonat/real_senti/config/logging/logging_env.sh
/home/jonat/real_senti/scripts/cicd/examples/log_feature_flag.sh

# View the logs
/home/jonat/real_senti/scripts/cicd/view_logs.sh
```

### Integration with Data Tier Service

To complete the integration with the data tier service:

```bash
# Build the data tier service with the new components
cd /home/jonat/real_senti/services/data-tier
mvn clean package

# Deploy the service
# (Use existing deployment procedures)
```

### Rollback Procedure

If issues are detected, you can disable the logging components without removing them:

```bash
# For bash components, just don't source the environment file
# For Java components, disable in application.properties:
echo "azure.application-insights.enabled=false" >> \
  /home/jonat/real_senti/services/data-tier/src/main/resources/application.properties
```

## Implementation Schedule

### Day 1: Preparation and Testing

1. Review and finalize the implementation plan
2. Test the `securitycontext_fix.sh` script in a test environment
3. Test the `cicd_logging.sh` script in a test environment

### Day 2: Implementation

1. Run the `securitycontext_fix.sh` script
2. Verify the Helm chart fixes
3. Run the `cicd_logging.sh` script
4. Verify the CICD logging integration

### Day 3: Integration and Documentation

1. Integrate the CICD logging with the data tier service
2. Verify end-to-end logging functionality
3. Finalize documentation
4. Conduct knowledge transfer session

## Success Criteria

### Helm Chart securityContext Fix

- All pod-level securityContext settings are moved to container level
- Helm lint passes without errors
- Security scanning tools don't report securityContext-related issues
- Deployments using the updated charts work correctly

### CICD Logging Integration

- All Azure resources are created and accessible
- Custom log tables are created in Log Analytics
- Example scripts successfully send logs to Azure
- Log Analytics queries show the logged events
- Documentation is complete and accurate

## Conclusion

This implementation plan provides a structured approach to fixing the Helm chart securityContext issues and implementing CICD logging integration. By following this plan, we will improve our deployment security posture and enhance our monitoring capabilities for Phase 5 of the Sentimark project.

The scripts provided (`securitycontext_fix.sh` and `cicd_logging.sh`) implement all the necessary components, and the verification steps ensure that the implementations are correct and functioning as expected.

Both implementations follow the organization's standards as specified in CLAUDE.md, with proper error handling, logging, documentation, and rollback procedures.