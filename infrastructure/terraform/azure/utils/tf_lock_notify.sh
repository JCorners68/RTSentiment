#!/bin/bash
# Terraform State Lock Notification Script
#
# This script checks for state locks and sends notifications
# It's designed to be run from cron or CI/CD pipelines

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK_MONITOR="$SCRIPT_DIR/tf_lock_monitor.sh"
CONFIG_FILE="$SCRIPT_DIR/notify_config.json"

# Default values
WARNING_THRESHOLD=30
CRITICAL_THRESHOLD=120
EMAIL_RECIPIENTS=""
TEAMS_WEBHOOK=""
SLACK_WEBHOOK=""
NOTIFICATION_LEVEL="warning"  # warning|critical|all

# Function to show usage
usage() {
  cat << EOF
Terraform Lock Notification Script

USAGE:
  $(basename "$0") [OPTIONS]

OPTIONS:
  -h, --help                   Show this help message
  -c, --config FILE            Configuration file path (default: ./notify_config.json)
  -w, --warning MINUTES        Warning threshold in minutes (default: $WARNING_THRESHOLD)
  -x, --critical MINUTES       Critical threshold in minutes (default: $CRITICAL_THRESHOLD)
  -e, --email ADDRESSES        Comma-separated list of email recipients
  -t, --teams-webhook URL      Microsoft Teams webhook URL
  -s, --slack-webhook URL      Slack webhook URL
  -l, --level LEVEL            Notification level: warning, critical, all (default: warning)
  -o, --output FILE            Output results to a file
  -v, --verbose                Enable verbose output

EXAMPLES:
  # Use configuration file
  $(basename "$0") --config /path/to/config.json

  # Send critical notifications to Teams
  $(basename "$0") --level critical --teams-webhook https://webhook.url --critical 60
EOF
  exit 0
}

# Function to load configuration
load_config() {
  local config_file="$1"
  
  if [ ! -f "$config_file" ]; then
    return 1
  fi
  
  # Load values from JSON configuration
  WARNING_THRESHOLD=$(jq -r '.warning_threshold // empty' "$config_file" || echo "$WARNING_THRESHOLD")
  CRITICAL_THRESHOLD=$(jq -r '.critical_threshold // empty' "$config_file" || echo "$CRITICAL_THRESHOLD")
  EMAIL_RECIPIENTS=$(jq -r '.email_recipients // empty' "$config_file" || echo "$EMAIL_RECIPIENTS")
  TEAMS_WEBHOOK=$(jq -r '.teams_webhook // empty' "$config_file" || echo "$TEAMS_WEBHOOK")
  SLACK_WEBHOOK=$(jq -r '.slack_webhook // empty' "$config_file" || echo "$SLACK_WEBHOOK")
  NOTIFICATION_LEVEL=$(jq -r '.notification_level // empty' "$config_file" || echo "$NOTIFICATION_LEVEL")
  
  return 0
}

# Parse arguments
parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)
        usage
        ;;
      -c|--config)
        CONFIG_FILE="$2"
        shift 2
        ;;
      -w|--warning)
        WARNING_THRESHOLD="$2"
        shift 2
        ;;
      -x|--critical)
        CRITICAL_THRESHOLD="$2"
        shift 2
        ;;
      -e|--email)
        EMAIL_RECIPIENTS="$2"
        shift 2
        ;;
      -t|--teams-webhook)
        TEAMS_WEBHOOK="$2"
        shift 2
        ;;
      -s|--slack-webhook)
        SLACK_WEBHOOK="$2"
        shift 2
        ;;
      -l|--level)
        NOTIFICATION_LEVEL="$2"
        shift 2
        ;;
      -o|--output)
        OUTPUT_FILE="$2"
        shift 2
        ;;
      -v|--verbose)
        set -x
        shift
        ;;
      *)
        echo "Unknown option: $1"
        usage
        ;;
    esac
  done
}

# Main function
main() {
  parse_args "$@"
  
  # Try to load configuration file
  if ! load_config "$CONFIG_FILE"; then
    echo "Configuration file not found: $CONFIG_FILE"
    echo "Using command line parameters or defaults"
  fi
  
  # Validate notification level
  if [[ ! "$NOTIFICATION_LEVEL" =~ ^(warning|critical|all)$ ]]; then
    echo "Invalid notification level: $NOTIFICATION_LEVEL"
    echo "Must be one of: warning, critical, all"
    exit 1
  fi
  
  # Build command for lock monitor
  cmd="$LOCK_MONITOR --warning $WARNING_THRESHOLD --critical $CRITICAL_THRESHOLD"
  
  # Add notification options
  if [ -n "$EMAIL_RECIPIENTS" ]; then
    cmd="$cmd --email $EMAIL_RECIPIENTS"
  fi
  
  if [ -n "$TEAMS_WEBHOOK" ]; then
    cmd="$cmd --teams-webhook $TEAMS_WEBHOOK"
  fi
  
  if [ -n "$SLACK_WEBHOOK" ]; then
    cmd="$cmd --slack-webhook $SLACK_WEBHOOK"
  fi
  
  # Determine which locks to check based on notification level
  case "$NOTIFICATION_LEVEL" in
    "warning")
      # Only check warning and critical locks
      cmd="$cmd --notify"
      ;;
    "critical")
      # Only check critical locks
      cmd="$cmd --notify --warning $CRITICAL_THRESHOLD"
      ;;
    "all")
      # Check all locks
      cmd="$cmd --notify --all-files"
      ;;
  esac
  
  # Add output file if specified
  if [ -n "$OUTPUT_FILE" ]; then
    cmd="$cmd --detailed > $OUTPUT_FILE"
  else
    cmd="$cmd --detailed"
  fi
  
  # Execute the command
  echo "Executing: $cmd"
  eval "$cmd"
}

# Run main function
main "$@"