#!/bin/bash
# Test script for CICD logging

set -e

# Create required directories
mkdir -p /home/jonat/real_senti/config/logging
mkdir -p /home/jonat/real_senti/scripts/cicd/templates
mkdir -p /home/jonat/real_senti/scripts/cicd/lib
mkdir -p /home/jonat/real_senti/scripts/cicd/examples

# Log function for consistent output
timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

log() {
  echo -e "$(timestamp) - $1"
}

# Create custom log tables
create_custom_log_tables() {
  log "Creating custom log table templates..."
  
  mkdir -p "/home/jonat/real_senti/scripts/cicd/templates"
  
  # Feature Flag Changes Log Table
  cat > "/home/jonat/real_senti/scripts/cicd/templates/feature_flag_logs.json" << 'EOF'
{
  "tables": [
    {
      "name": "SentimarkFeatureFlagChanges_CL",
      "columns": [
        {
          "name": "TimeGenerated",
          "type": "datetime"
        },
        {
          "name": "Environment",
          "type": "string"
        },
        {
          "name": "FeatureName",
          "type": "string"
        },
        {
          "name": "OldValue",
          "type": "string"
        },
        {
          "name": "NewValue",
          "type": "string"
        },
        {
          "name": "ChangedBy",
          "type": "string"
        },
        {
          "name": "ChangeReason",
          "type": "string"
        }
      ]
    }
  ]
}
EOF

  # Data Migration Log Table
  cat > "/home/jonat/real_senti/scripts/cicd/templates/data_migration_logs.json" << 'EOF'
{
  "tables": [
    {
      "name": "SentimarkDataMigration_CL",
      "columns": [
        {
          "name": "TimeGenerated",
          "type": "datetime"
        },
        {
          "name": "Environment",
          "type": "string"
        },
        {
          "name": "MigrationType",
          "type": "string"
        },
        {
          "name": "SourceSystem",
          "type": "string"
        },
        {
          "name": "TargetSystem",
          "type": "string"
        },
        {
          "name": "RecordsProcessed",
          "type": "int"
        },
        {
          "name": "RecordsSucceeded",
          "type": "int"
        },
        {
          "name": "RecordsFailed",
          "type": "int"
        },
        {
          "name": "DurationSeconds",
          "type": "real"
        },
        {
          "name": "ErrorMessage",
          "type": "string"
        },
        {
          "name": "Status",
          "type": "string"
        }
      ]
    }
  ]
}
EOF

  log "Custom log table templates created successfully"
  return 0
}

# Function to create logging client library
create_logging_client() {
  log "Creating logging client library..."
  
  # Create directory for client library
  mkdir -p "/home/jonat/real_senti/scripts/cicd/lib"
  
  # Create bash logging client
  cat > "/home/jonat/real_senti/scripts/cicd/lib/logging_client.sh" << 'EOF'
#!/bin/bash
# Sentimark CICD Logging Client Library
# This library provides functions for logging to Azure Log Analytics

# Check if required environment variables are set
check_logging_env() {
  if [ -z "${INSTRUMENTATION_KEY:-}" ]; then
    echo "WARNING: INSTRUMENTATION_KEY environment variable not set, using test mode"
    export INSTRUMENTATION_KEY="test-key"
  fi
  
  if [ -z "${WORKSPACE_ID:-}" ]; then
    echo "WARNING: WORKSPACE_ID environment variable not set, using test mode"
    export WORKSPACE_ID="test-workspace"
  fi
  
  if [ -z "${WORKSPACE_KEY:-}" ]; then
    echo "WARNING: WORKSPACE_KEY environment variable not set, using test mode"
    export WORKSPACE_KEY="test-key"
  fi
  
  return 0
}

# Function to send logs to Log Analytics
send_log() {
  local log_type=$1
  local json_payload=$2
  
  # Check if required environment variables are set
  check_logging_env
  
  # Add timestamp if not present
  if ! echo "$json_payload" | grep -q "TimeGenerated"; then
    # Create a temporary file with the properly formatted JSON
    local temp_file=$(mktemp)
    echo "$json_payload" | jq '. + {"TimeGenerated": "'"$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")"'"}' > "$temp_file" 2>/dev/null || echo "$json_payload" > "$temp_file"
    json_payload=$(cat "$temp_file")
    rm -f "$temp_file"
  fi
  
  # In test mode, just print the log
  echo "SIMULATED LOG:"
  echo "Log type: $log_type"
  echo "Payload: $json_payload"
  
  return 0
}

# Log feature flag changes
log_feature_flag_change() {
  local environment=$1
  local feature_name=$2
  local old_value=$3
  local new_value=$4
  local changed_by=$5
  local change_reason=$6
  
  local json_payload='{
    "Environment": "'"$environment"'",
    "FeatureName": "'"$feature_name"'",
    "OldValue": "'"$old_value"'",
    "NewValue": "'"$new_value"'",
    "ChangedBy": "'"$changed_by"'",
    "ChangeReason": "'"$change_reason"'"
  }'
  
  send_log "SentimarkFeatureFlagChanges" "$json_payload"
  return $?
}

# Log data migration events
log_data_migration() {
  local environment=$1
  local migration_type=$2
  local source_system=$3
  local target_system=$4
  local records_processed=$5
  local records_succeeded=$6
  local records_failed=$7
  local duration_seconds=$8
  local status=$9
  local error_message=${10:-""}
  
  local json_payload='{
    "Environment": "'"$environment"'",
    "MigrationType": "'"$migration_type"'",
    "SourceSystem": "'"$source_system"'",
    "TargetSystem": "'"$target_system"'",
    "RecordsProcessed": '"$records_processed"',
    "RecordsSucceeded": '"$records_succeeded"',
    "RecordsFailed": '"$records_failed"',
    "DurationSeconds": '"$duration_seconds"',
    "Status": "'"$status"'",
    "ErrorMessage": "'"$error_message"'"
  }'
  
  send_log "SentimarkDataMigration" "$json_payload"
  return $?
}

# Log Iceberg operations
log_iceberg_operation() {
  local environment=$1
  local operation_type=$2
  local table_name=$3
  local schema_version=$4
  local partition_key=$5
  local records_affected=$6
  local snapshot_id=$7
  local transaction_id=$8
  local status=$9
  local error_message=${10:-""}
  
  local json_payload='{
    "Environment": "'"$environment"'",
    "OperationType": "'"$operation_type"'",
    "TableName": "'"$table_name"'",
    "SchemaVersion": "'"$schema_version"'",
    "PartitionKey": "'"$partition_key"'",
    "RecordsAffected": '"$records_affected"',
    "SnapshotId": "'"$snapshot_id"'",
    "TransactionId": "'"$transaction_id"'",
    "Status": "'"$status"'",
    "ErrorMessage": "'"$error_message"'"
  }'
  
  send_log "SentimarkIcebergOperations" "$json_payload"
  return $?
}

# Log rollback events
log_rollback_event() {
  local environment=$1
  local system_component=$2
  local rollback_type=$3
  local triggered_by=$4
  local rollback_reason=$5
  local from_version=$6
  local to_version=$7
  local duration=$8
  local status=$9
  local affected_components=${10}
  local error_message=${11:-""}
  
  local json_payload='{
    "Environment": "'"$environment"'",
    "SystemComponent": "'"$system_component"'",
    "RollbackType": "'"$rollback_type"'",
    "TriggeredBy": "'"$triggered_by"'",
    "RollbackReason": "'"$rollback_reason"'",
    "FromVersion": "'"$from_version"'",
    "ToVersion": "'"$to_version"'",
    "Duration": '"$duration"',
    "Status": "'"$status"'",
    "AffectedComponents": "'"$affected_components"'",
    "ErrorMessage": "'"$error_message"'"
  }'
  
  send_log "SentimarkRollbackEvents" "$json_payload"
  return $?
}
EOF

  # Make the client library executable
  chmod +x "/home/jonat/real_senti/scripts/cicd/lib/logging_client.sh"

  log "Logging client library created successfully"
  return 0
}

# Function to create example/test scripts
create_example_scripts() {
  log "Creating example/test scripts..."
  
  # Create directory for examples
  mkdir -p "/home/jonat/real_senti/scripts/cicd/examples"
  
  # Create example for feature flag logging
  cat > "/home/jonat/real_senti/scripts/cicd/examples/log_feature_flag.sh" << 'EOF'
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
EOF

  chmod +x "/home/jonat/real_senti/scripts/cicd/examples/log_feature_flag.sh"
  
  log "Example/test scripts created successfully"
  return 0
}

# Create service configuration
create_service_config() {
  log "Creating service configuration files..."
  
  # Create required directories
  mkdir -p "/home/jonat/real_senti/config/logging"
  
  # Create bash environment config
  cat > "/home/jonat/real_senti/config/logging/logging_env.sh" << 'EOF'
#!/bin/bash
# Sentimark CICD Logging Environment Configuration

# Azure Workspace Configuration - Test values used if real values not available
export WORKSPACE_ID="${WORKSPACE_ID:-test-workspace-id}"
export WORKSPACE_KEY="${WORKSPACE_KEY:-test-workspace-key}"

# Application Insights Configuration  
export INSTRUMENTATION_KEY="${INSTRUMENTATION_KEY:-test-instrumentation-key}"

# Common environment settings
export SENTIMARK_ENVIRONMENT="sit"
EOF

  chmod +x "/home/jonat/real_senti/config/logging/logging_env.sh"
  
  log "Service configuration files created successfully"
  return 0
}

# Main function
main() {
  log "Starting CICD logging setup (TEST MODE)..."
  
  # Create custom log tables
  create_custom_log_tables || {
    log "ERROR: Failed to create custom log tables"
    exit 1
  }
  
  # Create logging client library
  create_logging_client || {
    log "ERROR: Failed to create logging client library"
    exit 1
  }
  
  # Create service configuration
  create_service_config || {
    log "ERROR: Failed to create service configuration"
    exit 1
  }
  
  # Create example scripts
  create_example_scripts || {
    log "ERROR: Failed to create example scripts"
    exit 1
  }
  
  log "CICD logging setup completed successfully!"
  log "Test the logging system with: /home/jonat/real_senti/scripts/cicd/examples/log_feature_flag.sh"
  
  return 0
}

# Run main function
main "$@"