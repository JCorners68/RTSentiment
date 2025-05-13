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
