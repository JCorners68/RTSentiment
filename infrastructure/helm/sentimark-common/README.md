# Sentimark Common Helm Chart

This is a library chart that provides common templates and configurations for Sentimark services.

## Usage

This chart is meant to be used as a dependency in other charts. It provides common templates and helper functions.

To use this chart as a dependency, add the following to your Chart.yaml:

```yaml
dependencies:
  - name: sentimark-common
    version: 0.1.0
    repository: "file://../sentimark-common"
    condition: sentimark-common.enabled
    tags:
      - sentimark-common
```

## Templates

The following helper templates are provided:

- `sentimark-common.fullname`: Creates a fully qualified app name
- `sentimark-common.labels`: Provides common labels
- `sentimark-common.securityContext`: Common security context settings
- `sentimark-common.spotTolerations`: Common spot instance tolerations

## Configuration

See values.yaml for configuration options.