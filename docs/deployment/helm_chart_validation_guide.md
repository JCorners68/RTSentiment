# Helm Chart Validation Guide

This guide provides comprehensive instructions for validating Helm charts before deployment to ensure both syntax correctness and Kubernetes compatibility.

## Validation Levels

Helm chart validation should occur at multiple levels to ensure complete correctness:

1. **Syntax Validation** - Check basic YAML syntax and template structure
2. **Template Rendering** - Verify template rendering with values
3. **Kubernetes Schema Validation** - Validate against Kubernetes API schema
4. **Security Review** - Check for security best practices
5. **Deployment Testing** - Verify in a non-production environment

## Validation Tools

### 1. Built-in Validation Tools

#### Helm Lint

Basic syntax checker for Helm charts.

```bash
# Run from chart directory
helm lint .

# With specific values
helm lint . -f values.yaml -f values-test.yaml
```

Limitations:
- Only checks basic syntax and structure
- Doesn't validate against Kubernetes schema
- Doesn't catch all template rendering issues

#### Helm Template

Renders templates with values but doesn't deploy.

```bash
# Render templates
helm template my-release . > rendered.yaml

# With specific values
helm template my-release . -f values.yaml -f values-test.yaml > rendered.yaml
```

Limitations:
- Doesn't validate against Kubernetes schema
- May not catch all runtime issues

#### Kubectl Apply Dry Run

Validates rendered templates against Kubernetes schema.

```bash
# Client-side validation
kubectl apply --dry-run=client -f rendered.yaml

# Server-side validation (more thorough)
kubectl apply --dry-run=server -f rendered.yaml
```

Limitations:
- Server-side requires cluster access
- Doesn't catch all runtime issues

### 2. Our Custom Validation Script

We've created a comprehensive validation script that combines all these approaches:

```bash
/home/jonat/real_senti/scripts/validate_helm_charts.sh
```

This script:
1. Runs `helm lint` to check syntax
2. Renders templates with `helm template`
3. Validates with `kubectl apply --dry-run`
4. Checks security with kubesec (if available)
5. Verifies securityContext placement
6. Checks indentation consistency
7. Generates a validation report

## Validation Before Deployment

### Required Steps

Before deploying to any environment, ensure you've completed:

1. Run the validation script
   ```bash
   ./scripts/validate_helm_charts.sh
   ```

2. Review the validation report
   ```bash
   cat scan-results/[timestamp]/validation_report.md
   ```

3. Fix any identified issues

4. Test deployment in a non-production environment
   ```bash
   # Deploy to test namespace
   helm upgrade --install --namespace test-namespace \
     --create-namespace test-release \
     ./infrastructure/helm/sentimark-services \
     -f values-test.yaml
   ```

5. Verify all resources are running correctly
   ```bash
   kubectl get all -n test-namespace
   ```

### CI/CD Pipeline Integration

Add these validation steps to your CI/CD pipeline:

```yaml
# Example CI/CD pipeline step
validate-helm:
  stage: validate
  script:
    - ./scripts/validate_helm_charts.sh
    - if grep -q "ERROR" scan-results/$(ls -t scan-results | head -n1)/*; then exit 1; fi
  artifacts:
    paths:
      - scan-results/
```

## Common Issues and Solutions

### 1. SecurityContext Placement

**Issue**: Properties in wrong location (pod vs. container level)

**Solution**: 
- `fsGroup` belongs at pod level only
- Most other security settings belong at container level
- Use our `fix_securitycontext.sh` script

### 2. Indentation Problems

**Issue**: Inconsistent indentation causing YAML parsing errors

**Solution**:
- List items should be properly indented
- All resources should be separated with `---`
- Use our `fix_helm_syntax.sh` script

### 3. Template Variable Issues

**Issue**: Referencing non-existent variables

**Solution**:
- Verify all template variables exist in values.yaml
- Provide sensible defaults where possible
- Add proper conditionals for optional values

## Indentation Standards

Follow these indentation standards for Kubernetes YAML:

```yaml
# Top level fields
apiVersion: v1
kind: ConfigMap
metadata:
  name: example
  labels:
    app: example
data:
  key: value

# Lists under fields (2 space indent + 2 spaces for item)
spec:
  containers:
  - name: container-1
    image: image:tag
    # Fields under list items (4 space indent)
    env:
    - name: ENV_VAR
      value: "value"
    # Deeper nesting
    securityContext:
      capabilities:
        drop:
        - ALL
```

## Reference

- [Kubernetes YAML Style Guide](https://kubernetes.io/docs/contribute/style/style-guide/#yaml-formatting)
- [Helm Best Practices](https://helm.sh/docs/chart_best_practices/)
- [Kubernetes securityContext](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)