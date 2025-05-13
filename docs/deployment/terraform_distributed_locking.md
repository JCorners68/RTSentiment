# Terraform Distributed Locking System

## Overview

The Terraform Distributed Locking System is a critical enhancement to our Terraform pipeline that prevents concurrent operations on the same environment. This document details the design, implementation, and usage guidelines for this system.

## Problem Statement

Terraform's built-in state locking helps prevent state corruption during a single operation, but it has several limitations:

1. It only locks during the actual operation, not before or after
2. It doesn't prevent multiple users from starting different operations on the same environment
3. It doesn't provide visibility into who is currently working on an environment
4. Its lock detection and resolution mechanisms are limited

Our distributed locking system addresses these issues by providing environment-level coordination across all Terraform users and pipelines.

## Solution Architecture

The solution uses Azure Blob Storage as a distributed coordination mechanism. Each environment+operation combination gets a dedicated lock file with metadata about the lock owner, creation time, and expiration.

### Components

1. **tf_distributed_lock.sh**: Core implementation of the distributed locking mechanism
2. **tf_run_with_lock.sh**: Wrapper script that integrates locking with Terraform operations
3. **tf_shared_utils.sh**: Common utility functions shared across the scripts

### Lock Storage

Locks are stored in the Azure Storage account used for Terraform state, in a dedicated `terraform-locks` container. Each lock is a blob with a name pattern of `{environment}_{operation}.lock` (e.g., `prod_apply.lock`).

### Lock Metadata

Each lock blob contains JSON metadata with:

- **environment**: The environment being locked (dev, sit, uat, prod)
- **operation**: The Terraform operation being performed (plan, apply, destroy, custom)
- **acquired_by**: Identity of the user/process that acquired the lock
- **acquired_at**: ISO8601 timestamp when the lock was acquired
- **expires_at**: ISO8601 timestamp when the lock will automatically expire
- **timeout_seconds**: The lock timeout in seconds
- **hostname**: The computer where the lock was acquired
- **pid**: Process ID of the lock acquirer

## Implementation Details

### Acquiring a Lock

1. Generate lock metadata with user identity and timestamps
2. Attempt to upload the lock blob with an if-none-match condition
3. If upload succeeds, lock is acquired
4. If upload fails because lock exists, check if it's expired
5. If expired, force-release and retry; otherwise, fail with lock details

### Releasing a Lock

1. Verify the lock exists
2. Check lock ownership (unless force release is specified)
3. Delete the lock blob

### Lock Monitoring

1. List blobs in the locks container
2. For each lock, fetch and parse its metadata
3. Calculate expiration status
4. Display sorted, formatted lock information

### Integration with Terraform

1. Detect environment and operation
2. Acquire appropriate lock
3. Run Terraform command
4. Release lock (using a trap to ensure release even on failure)

## Security Considerations

1. **Authorization**: Users must have appropriate Azure Storage permissions to acquire/release locks
2. **Force Release**: Only administrators should use the force option to release others' locks
3. **Timeouts**: Locks automatically expire to prevent permanent locking
4. **Audit Trail**: Lock metadata includes user identity for accountability

## Usage Guidelines

### Basic Usage

For most users, the recommended approach is to use the wrapper script:

```bash
# Run plan with automatic locking
./utils/tf_run_with_lock.sh -e sit plan

# Run apply with automatic locking
./utils/tf_run_with_lock.sh -e prod apply -auto-approve
```

### Lock Management

For more advanced lock management:

```bash
# Check lock status
./utils/tf_distributed_lock.sh -e prod status

# Watch all locks in real-time
./utils/tf_distributed_lock.sh watch

# Force release a lock (administrators only)
./utils/tf_distributed_lock.sh -e prod -o apply -f release
```

### CI/CD Integration

For CI/CD pipelines, use longer timeouts to accommodate extended operations:

```bash
# In a pipeline script
./utils/tf_run_with_lock.sh -e prod -t 7200 apply -auto-approve
```

## Best Practices

1. **Always use locking for production environments**
2. **Set appropriate timeouts** for long-running operations
3. **Check lock status before starting work** on an environment
4. **Communicate with your team** when you acquire locks for extended periods
5. **Never use --skip-locking** in production environments
6. **Only force-release locks** when you've confirmed the owner is no longer working
7. **Review lock history periodically** to identify patterns and optimize workflows

## Troubleshooting

### Common Issues

1. **Cannot acquire lock**: Someone else is working on the environment
   - Solution: Check who has the lock and coordinate with them

2. **Lock persists after operation**: Previous run might have crashed
   - Solution: Check if the process is still running; if not, force-release the lock

3. **Cannot release lock**: Might not be the lock owner
   - Solution: Only administrators should force-release others' locks

4. **Azure authentication issues**: 
   - Solution: Run `az login` to authenticate with Azure

## Monitoring and Maintenance

1. **Regular checks**: Run the monitor periodically to detect stale locks
2. **Cleanup job**: Consider a scheduled job to detect and notify about long-running locks
3. **Audit reports**: Generate reports of lock usage to optimize team workflows

## Future Enhancements

1. **Web dashboard**: Create a web interface for lock visibility
2. **Reservation system**: Allow "booking" environments in advance
3. **Active Directory integration**: Enhance authentication and authorization
4. **Notification system**: Send alerts for long-running locks
5. **Analytics**: Collect usage patterns to optimize infrastructure

## Conclusion

The distributed locking system significantly enhances our Terraform pipeline's reliability, especially in multi-user and CI/CD environments. By preventing concurrent operations, providing visibility, and adding additional safety mechanisms, we reduce the risk of state corruption and infrastructure conflicts.