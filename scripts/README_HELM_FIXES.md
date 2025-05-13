# Helm Chart Fix Scripts

This directory contains scripts to fix and maintain Kubernetes Helm chart templates for the Sentimark project.

## Scripts

### 1. `fix_securitycontext.sh`

A script to fix securityContext fields in Kubernetes Helm charts by moving them from pod-level to container-level as per best practices.

#### Usage

```bash
# Fix all deployment files in the templates directory
./fix_securitycontext.sh

# Fix specific files
./fix_securitycontext.sh /path/to/file1.yaml /path/to/file2.yaml

# Display help
./fix_securitycontext.sh --help
```

#### Features

- Automatically detects pod-level and container-level securityContext sections
- Comments out pod-level securityContext while preserving fsGroup information
- Adds properly indented container-level securityContext with all required fields
- Handles capabilities and their indentation correctly
- Creates backups before making any changes
- Provides detailed logging of all operations

#### Example

```yaml
# Before
spec:
  # Pod-level (incorrect)
  securityContext:
    fsGroup: 1000
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    allowPrivilegeEscalation: false
    capabilities:
      drop:
      - ALL
    readOnlyRootFilesystem: true

# After
spec:
  # Pod-level (correct)
  # securityContext:
  #   fsGroup: 1000
  
  containers:
  - name: app
    # Container-level (correct)
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      runAsGroup: 1000
      allowPrivilegeEscalation: false
      capabilities:
        drop:
        - ALL
      readOnlyRootFilesystem: true
```

### 2. `fix_helm_syntax.sh`

A script to fix common YAML syntax issues in Helm chart templates.

#### Usage

```bash
# Fix all YAML files in the templates directory
./fix_helm_syntax.sh

# Fix specific files
./fix_helm_syntax.sh /path/to/file1.yaml /path/to/file2.yaml

# Display help
./fix_helm_syntax.sh --help
```

#### Features

- Fixes resource separators (changes `- --` to `---`)
- Corrects indentation for list items in various contexts:
  - Environment variables (`env:`)
  - Container ports (`ports:`)
  - Capabilities (`capabilities:`)
  - Ingress hosts and rules
- Creates backups before making any changes
- Includes verification with `helm lint` after fixes are applied

#### Example

```yaml
# Before (Incorrect)
        env:
        {{- range .Values.api.env }}
            -  name: {{ .name }}
          {{- if .value }}
          value: {{ .value | quote }}
          {{- end }}
        {{- end }}
            - --
apiVersion: v1

# After (Correct)
        env:
        {{- range .Values.api.env }}
        - name: {{ .name }}
          {{- if .value }}
          value: {{ .value | quote }}
          {{- end }}
        {{- end }}
---
apiVersion: v1
```

## Best Practices for Helm Charts

### Security Context Configuration

- **Pod-level securityContext**: Use only for settings that apply to all containers:
  - `fsGroup` (for volume permissions)

- **Container-level securityContext**: Use for per-container security policies:
  - `runAsNonRoot`
  - `runAsUser`
  - `runAsGroup`
  - `allowPrivilegeEscalation`
  - `capabilities` (drop)
  - `readOnlyRootFilesystem`

### YAML Formatting

- Use consistent indentation (2 spaces recommended)
- Use proper YAML document separators (`---`) between resources
- Ensure proper list item indentation with consistent spacing
- Follow Helm's recommended templating practices

## Verification

Always verify your Helm templates with:

```bash
helm lint /path/to/chart
```

## References

- [Kubernetes Security Context Documentation](https://kubernetes.io/docs/tasks/configure-pod-container/security-context/)
- [Helm Best Practices](https://helm.sh/docs/chart_best_practices/)
- [Kubernetes YAML Style Guide](https://kubernetes.io/docs/contribute/style/style-guide/#yaml-formatting)