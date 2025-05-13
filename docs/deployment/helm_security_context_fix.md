# Helm Chart Security Context Implementation

## Overview

This document outlines the implementation of Kubernetes security contexts in the Helm charts for Sentimark Services. We've followed Kubernetes security best practices to ensure proper pod and container security settings.

## Security Context Implementation

Security contexts in Kubernetes define privilege and access control settings for pods and containers. They are critical for maintaining a secure deployment posture.

### Key Changes Implemented

1. **Container-level Security Context**:
   - All security settings are primarily set at the container level
   - These include:
     - `runAsNonRoot: true` - Prevents containers from running as root
     - `runAsUser` and `runAsGroup` - Specify the UID/GID to run the container processes
     - `allowPrivilegeEscalation: false` - Prevents container processes from gaining more privileges than its parent
     - `capabilities.drop: ["ALL"]` - Removes all Linux capabilities
     - `readOnlyRootFilesystem` - Controls whether the container has a read-only root filesystem

2. **Pod-level Security Context**:
   - `fsGroup` - Remains at pod level when volumes are used
   - This is necessary because fsGroup is a pod-level setting that controls file permissions for mounted volumes
   - Only applied to deployments that use volumes

## Justification

The changes align with Kubernetes security best practices:

1. **Least Privilege Principle**: Containers run with minimal permissions required
2. **Defense in Depth**: Multiple layers of security controls
3. **Volume Permission Management**: Using fsGroup at pod level when needed for volumes

## Implementation Scripts

The following scripts have been created to manage security contexts:

1. `clean_securitycontext.sh`: Cleans up commented security context settings for consistency
2. `fix_fsgroup.sh`: Properly configures fsGroup at pod level when volumes are present
3. `validate_securitycontext.sh`: Validates security context settings across all deployments

## Verification

To verify the security context settings:

```bash
# Run the validation script
./scripts/validate_securitycontext.sh

# Check the Helm chart syntax
cd infrastructure/helm/sentimark-services
helm lint .

# Validate template rendering
helm template .
```

## Security Considerations

These security context settings should be maintained in all future updates to the Helm charts. When adding new services or modifying existing ones, ensure proper security contexts are applied following these guidelines:

1. Container-specific security settings should be at container level
2. fsGroup should be at pod level only when volumes are used
3. Non-root UIDs should be used (e.g., UID 1000)
4. Privilege escalation should be disabled
5. Unnecessary capabilities should be dropped

## Further Improvements

Future security enhancements may include:

1. Implementing Security Context Constraint profiles
2. Adding Pod Security Policy templates
3. Integrating with OPA/Gatekeeper for policy enforcement