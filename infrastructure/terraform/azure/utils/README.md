# Terraform Utilities for State Locking and Management

This directory contains utilities for monitoring, managing, and coordinating Terraform operations with a focus on state locking and concurrency management.

## Overview

Terraform uses state locking to prevent concurrent operations that could corrupt the state file. These utilities help monitor, detect, manage, and coordinate locks to prevent issues with stale locks, improve visibility into the locking system, and prevent conflicts when multiple developers or pipelines are working with the same environments.

## Utilities

### 1. `tf_distributed_lock.sh`

A comprehensive distributed locking system for Terraform operations that works alongside Terraform's built-in state locking.

**Features:**
- Prevents concurrent Terraform operations on the same environment
- Uses Azure Blob Storage for distributed lock coordination
- Provides lock expiration and automatic stale lock detection
- Supports multiple operation types (plan, apply, destroy)
- Includes detailed status reporting and monitoring capabilities
- Works alongside Terraform's built-in state locking for additional safety

**Usage:**
```bash
# Acquire a lock for running plan in SIT environment
./tf_distributed_lock.sh -e sit -o plan acquire

# Check status of locks for an environment
./tf_distributed_lock.sh -e sit status

# List all active locks
./tf_distributed_lock.sh list

# Watch locks in real-time (updates every 5 seconds)
./tf_distributed_lock.sh watch

# Release a lock
./tf_distributed_lock.sh -e sit -o plan release

# Force release a lock (admin only)
./tf_distributed_lock.sh -e sit -o plan -f release
```

### 2. `tf_run_with_lock.sh`

A wrapper script that integrates distributed locking with normal Terraform operations.

**Features:**
- Automatically acquires appropriate locks before running Terraform
- Releases locks when operations complete (even if they fail)
- Supports all standard Terraform operations
- Provides environment auto-detection
- Includes timeout configuration for long-running operations

**Usage:**
```bash
# Run plan with automatic locking
./tf_run_with_lock.sh -e sit plan

# Run apply with longer lock timeout
./tf_run_with_lock.sh -e prod -t 7200 apply -auto-approve

# Skip locking (use with caution)
./tf_run_with_lock.sh -e dev -s plan -var-file=dev.tfvars
```

### 3. `tf_lock_monitor.sh`

A comprehensive utility for monitoring Terraform state locks in Azure Storage.

**Features:**
- Detects locks across all environments (SIT, UAT, PROD)
- Reports detailed information about lock owners and creation times
- Supports continuous monitoring mode with configurable intervals
- Can send notifications via email, webhooks, Microsoft Teams, and Slack
- Has the ability to automatically fix stale locks in non-production environments
- Generates detailed reports for troubleshooting
- Supports both Azure CLI and REST API methods

**Usage:**
```bash
# Check all environments for locks
./tf_lock_monitor.sh

# Check only production environment
./tf_lock_monitor.sh prod

# Monitor locks every 5 minutes and send email notifications
./tf_lock_monitor.sh --monitor --interval 300 --notify --email devops@example.com

# Get detailed information about locks in UAT
./tf_lock_monitor.sh --detailed uat

# Fix stale locks older than 2 hours in SIT environment
./tf_lock_monitor.sh --fix --critical 120 sit
```

### 2. `tf_lock_notify.sh`

A simplified script for checking locks and sending notifications. Designed to be run from cron jobs or CI/CD pipelines.

**Features:**
- Configurable notification thresholds
- Multiple notification methods (email, Teams, Slack)
- JSON configuration file support
- Customizable notification levels

**Usage:**
```bash
# Use configuration file
./tf_lock_notify.sh --config notify_config.json

# Send critical notifications to Teams
./tf_lock_notify.sh --level critical --teams-webhook https://webhook.url --critical 60
```

## Installation

### Setting up as a system service:

1. Edit the `tf-lock-monitor.service` file to configure your notification settings
2. Install the service:
   ```bash
   sudo cp tf-lock-monitor.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable tf-lock-monitor
   sudo systemctl start tf-lock-monitor
   ```
3. Check service status:
   ```bash
   sudo systemctl status tf-lock-monitor
   ```

### Setting up as a cron job:

Add this to your crontab (`crontab -e`):
```
# Check for stale locks every hour
0 * * * * /path/to/tf_lock_notify.sh --config /path/to/notify_config.json >> /var/log/tf_lock_monitor.log 2>&1
```

## Configuration

### `notify_config.json`

This file contains configuration for the notification system:

```json
{
  "warning_threshold": 30,
  "critical_threshold": 120,
  "email_recipients": "devops@example.com,alerts@example.com",
  "teams_webhook": "https://outlook.office.com/webhook/example",
  "slack_webhook": "https://hooks.slack.com/services/example",
  "notification_level": "warning"
}
```

## Integration with Terraform Scripts

The lock monitoring utilities can be integrated with your existing Terraform workflows:

1. **Pre-execution check**: Run `tf_lock_monitor.sh` before Terraform operations to check for existing locks
2. **Post-execution verification**: Ensure locks are properly released after operations complete
3. **Automated monitoring**: Set up the service or cron job for continuous monitoring
4. **CI/CD integration**: Add lock checks to your CI/CD pipelines

## Troubleshooting

### Common Issues:

1. **Authentication failures**: Ensure you're logged in with `az login` when running manually
2. **Permission issues**: The service principal needs read access to the storage account
3. **Webhook failures**: Verify webhook URLs are correct and accessible
4. **Email delivery issues**: Check your server can send emails or configure SMTP settings

## Best Practices

1. Use the monitoring service in production environments to detect stale locks
2. Set up notifications to alert teams of lock issues before they become critical
3. Only use the `--fix` option in non-production environments or with extreme caution
4. Review lock reports regularly to identify patterns or problematic workflows
5. Include this tool in your DevOps onboarding documentation

## Examples

### Example 1: Checking for locks before deployments

```bash
#!/bin/bash
# Check for locks before deploying
if ./utils/tf_lock_monitor.sh prod | grep -q "CRITICAL"; then
  echo "Critical locks detected! Aborting deployment."
  exit 1
fi

# Proceed with deployment
terraform apply -auto-approve
```

### Example 2: Integrating with CI/CD

```yaml
- name: Check for Terraform locks
  run: |
    ./utils/tf_lock_notify.sh --level warning --teams-webhook ${{ secrets.TEAMS_WEBHOOK }}
    if [ $? -ne 0 ]; then
      echo "::warning::Stale locks detected, check notification for details"
    fi
```

## License

See the main project license file.