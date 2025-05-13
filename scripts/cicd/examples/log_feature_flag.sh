#!/bin/bash
# Example script for logging feature flag changes

# Source the logging environment
source "$(dirname "$0")/../../config/logging/logging_env.sh" 2>/dev/null || true

# Source the logging client library
source "$(dirname "$0")/../lib/logging_client.sh"

# Example feature flag change
log_feature_flag_change \
  "sit" \
  "USE_ICEBERG_STORAGE" \
  "false" \
  "true" \
  "DevOps Team" \
  "Enabling Iceberg storage for production readiness testing"

echo "Feature flag change logged successfully"
