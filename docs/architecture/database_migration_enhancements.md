# Database Migration Enhancement Plan

This document outlines specific enhancements to the existing PostgreSQL to Iceberg migration plan to improve reliability, performance, and integration with other systems.

## 1. CI/CD Integration Enhancements

The current migration plan lacks tight integration with CI/CD pipelines, which would provide automated testing, verification, and deployment. The following enhancements address this gap:

### 1.1 Automated Migration Testing Pipeline

**Problem:** The migration verification is primarily manual, requiring team members to run CLI tools themselves.

**Solution:** Create a dedicated CI/CD pipeline that automatically tests the migration process:

```yaml
# .github/workflows/migration-test.yml
name: Test Database Migration

on:
  push:
    branches: [ data_tier ]
    paths:
      - 'services/data-tier/**'
      - 'scripts/migration/**'
  pull_request:
    branches: [ main ]
    paths:
      - 'services/data-tier/**'
      - 'scripts/migration/**'
  workflow_dispatch:
    inputs:
      entity:
        description: 'Entity to test migration for'
        required: false
        default: ''
      test_size:
        description: 'Test size (small, medium, large)'
        required: false
        default: 'medium'

jobs:
  test-migration:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_USER: postgres
          POSTGRES_DB: test_migration
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up JDK 11
        uses: actions/setup-java@v2
        with:
          java-version: '11'
          distribution: 'adopt'
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r services/data-tier/requirements.txt
          pip install -r scripts/migration/requirements.txt
      
      - name: Set up test database
        run: |
          ./scripts/migration/setup_test_db.sh --size ${{ github.event.inputs.test_size || 'medium' }}
      
      - name: Run migration tests
        run: |
          if [ -n "${{ github.event.inputs.entity }}" ]; then
            ./scripts/migration/test_migration.sh --entity=${{ github.event.inputs.entity }} --verify --report
          else
            ./scripts/migration/test_migration.sh --verify --report
          fi
      
      - name: Upload test results
        uses: actions/upload-artifact@v2
        with:
          name: migration-test-results
          path: |
            build/reports/migration/
            build/reports/verification/
```

### 1.2 Schema Drift Detection

**Problem:** The current plan doesn't automatically detect when schema drift occurs between environments.

**Solution:** Implement a schema drift detector that runs daily in CI/CD:

```python
#!/usr/bin/env python3
# /scripts/migration/schema_drift_detector.py

import argparse
import json
import sys
from database_connectors import connect_postgres, connect_iceberg

def get_schema_signature(connection, entity_name):
    """Get a hash of the schema structure for comparison"""
    # Implementation specific to connection type
    pass

def compare_schemas(env1, env2, entity_list=None):
    """Compare schemas between two environments"""
    pg_conn_env1 = connect_postgres(env1)
    pg_conn_env2 = connect_postgres(env2)
    
    if not entity_list:
        # Get all entities from schema registry
        entity_list = get_all_entities()
    
    results = []
    for entity in entity_list:
        schema1 = get_schema_signature(pg_conn_env1, entity)
        schema2 = get_schema_signature(pg_conn_env2, entity)
        
        if schema1 != schema2:
            results.append({
                "entity": entity,
                "status": "DRIFT_DETECTED",
                "details": get_schema_differences(schema1, schema2)
            })
        else:
            results.append({
                "entity": entity,
                "status": "MATCH"
            })
    
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Detect schema drift between environments")
    parser.add_argument("--env1", required=True, help="First environment to compare")
    parser.add_argument("--env2", required=True, help="Second environment to compare") 
    parser.add_argument("--entities", help="Comma-separated list of entities to check")
    parser.add_argument("--output", default="json", choices=["json", "text", "html"], help="Output format")
    
    args = parser.parse_args()
    
    entity_list = args.entities.split(",") if args.entities else None
    results = compare_schemas(args.env1, args.env2, entity_list)
    
    drift_detected = any(r["status"] == "DRIFT_DETECTED" for r in results)
    
    if args.output == "json":
        print(json.dumps(results, indent=2))
    elif args.output == "text":
        for r in results:
            print(f"{r['entity']}: {r['status']}")
            if r["status"] == "DRIFT_DETECTED":
                for diff in r.get("details", []):
                    print(f"  - {diff}")
    
    sys.exit(1 if drift_detected else 0)
```

### 1.3 Migration Pipeline Metrics Collection

**Problem:** The current plan lacks centralized collection of migration metrics across environments.

**Solution:** Add metrics collection to CI/CD pipeline:

```yaml
# End of migration-test.yml job
- name: Collect migration metrics
  run: |
    ./scripts/migration/collect_metrics.sh --publish
    
- name: Update migration dashboard
  run: |
    ./scripts/migration/update_dashboard.py
    
- name: Publish migration reports to documentation site
  if: github.event_name == 'workflow_dispatch'
  run: |
    ./scripts/migration/publish_reports.sh
```

## 2. Performance Optimization Enhancements

The current migration approach may encounter performance bottlenecks with very large datasets. The following enhancements address these concerns:

### 2.1 Parallel Entity Migration Framework

**Problem:** The current approach processes entities sequentially or with limited parallelism that doesn't optimize for data characteristics.

**Solution:** Implement an adaptive parallelism framework:

```java
// services/data-tier/src/main/java/com/sentimark/migration/AdaptiveParallelMigrator.java
package com.sentimark.migration;

import java.util.List;
import java.util.concurrent.*;
import java.util.stream.Collectors;

public class AdaptiveParallelMigrator {
    private final ExecutorService executorService;
    private final SchemaRegistry schemaRegistry;
    private final RepositoryFactory repositoryFactory;
    private final MigrationProgressTracker progressTracker;
    private final MigrationValidator validator;
    
    // Number of available CPU cores for computation
    private final int availableCores = Runtime.getRuntime().availableProcessors();
    
    // Maximum memory to use for migration (in MB)
    private final long maxMemoryMB;
    
    public AdaptiveParallelMigrator(
            SchemaRegistry schemaRegistry,
            RepositoryFactory repositoryFactory,
            MigrationProgressTracker progressTracker,
            MigrationValidator validator,
            long maxMemoryMB) {
        this.schemaRegistry = schemaRegistry;
        this.repositoryFactory = repositoryFactory;
        this.progressTracker = progressTracker;
        this.validator = validator;
        this.maxMemoryMB = maxMemoryMB;
        this.executorService = Executors.newWorkStealingPool(availableCores);
    }
    
    public MigrationReport migrateAllEntities() {
        MigrationReport report = new MigrationReport();
        
        // Get all entities to migrate
        List<String> allEntities = schemaRegistry.getAllRegisteredEntities();
        
        // Classify entities by size and complexity
        Map<MigrationComplexity, List<String>> entityGroups = classifyEntities(allEntities);
        
        // Migrate small entities in parallel 
        List<CompletableFuture<MigrationResult>> smallEntityFutures = 
            entityGroups.get(MigrationComplexity.SMALL).stream()
                .map(entity -> CompletableFuture.supplyAsync(
                    () -> migrateEntity(entity), executorService))
                .collect(Collectors.toList());
        
        // Wait for small entities to complete
        CompletableFuture.allOf(smallEntityFutures.toArray(new CompletableFuture[0])).join();
        
        // Add results to report
        smallEntityFutures.forEach(future -> {
            try {
                MigrationResult result = future.get();
                report.addResult(result.getEntityName(), result);
            } catch (Exception e) {
                report.addFailure(e.getMessage(), e);
            }
        });
        
        // Migrate medium entities with some parallelism (but less than small)
        int mediumParallelism = Math.max(1, availableCores / 2);
        ExecutorService mediumExecutor = Executors.newFixedThreadPool(mediumParallelism);
        
        // ... similar pattern for medium entities
        
        // Migrate large entities sequentially with optimized batch size
        for (String entity : entityGroups.get(MigrationComplexity.LARGE)) {
            try {
                long estimatedSize = estimateEntityDataSize(entity);
                int optimalBatchSize = calculateOptimalBatchSize(estimatedSize);
                
                MigrationResult result = migrateEntity(entity, optimalBatchSize);
                report.addResult(entity, result);
            } catch (Exception e) {
                report.addFailure(entity, e);
            }
        }
        
        return report;
    }
    
    // Helper methods for entity classification, size estimation, etc.
    private Map<MigrationComplexity, List<String>> classifyEntities(List<String> entities) {
        // Implementation to classify entities as SMALL, MEDIUM, or LARGE based on:
        // 1. Number of records
        // 2. Schema complexity
        // 3. Data size estimates
        // ...
    }
    
    private long estimateEntityDataSize(String entityName) {
        // Implementation to estimate the data size for an entity
        // ...
    }
    
    private int calculateOptimalBatchSize(long estimatedSizeBytes) {
        // Implementation to calculate optimal batch size based on:
        // 1. Available memory
        // 2. Estimated record size
        // 3. System resources
        // ...
    }
    
    private enum MigrationComplexity {
        SMALL, MEDIUM, LARGE
    }
}
```

### 2.2 Incremental Migration Support

**Problem:** The current plan assumes a complete one-time migration, which may be impractical for very large tables.

**Solution:** Add support for incremental migration based on time windows:

```java
// services/data-tier/src/main/java/com/sentimark/migration/IncrementalMigrationService.java
package com.sentimark.migration;

import java.time.Instant;
import java.time.Duration;
import java.util.List;

public class IncrementalMigrationService {
    private final RepositoryFactory repositoryFactory;
    private final MigrationProgressTracker progressTracker;
    private final MigrationCheckpointManager checkpointManager;
    
    public IncrementalMigrationService(
            RepositoryFactory repositoryFactory,
            MigrationProgressTracker progressTracker,
            MigrationCheckpointManager checkpointManager) {
        this.repositoryFactory = repositoryFactory;
        this.progressTracker = progressTracker;
        this.checkpointManager = checkpointManager;
    }
    
    public <T> MigrationResult migrateIncrementally(
            String entityName,
            String timeWindowField,
            Duration timeWindowSize,
            int maxBatchSize) {
        
        MigrationResult result = new MigrationResult(entityName);
        progressTracker.startMigration(entityName);
        
        try {
            // Get source and target repositories
            Repository<T> sourceRepo = repositoryFactory.getPostgresRepository(entityName);
            Repository<T> targetRepo = repositoryFactory.getIcebergRepository(entityName);
            
            // Get latest checkpoint from previous runs
            MigrationCheckpoint checkpoint = checkpointManager.getLatestCheckpoint(entityName);
            Instant startTime = checkpoint != null ? 
                checkpoint.getLastMigratedTimestamp() : Instant.EPOCH;
            
            // Calculate end time for this run
            Instant endTime = startTime.plus(timeWindowSize);
            if (endTime.isAfter(Instant.now())) {
                endTime = Instant.now();
            }
            
            // Get records in the time window
            List<T> recordsToMigrate = sourceRepo.findByTimeWindow(
                timeWindowField, startTime, endTime, maxBatchSize);
            
            int migratedCount = 0;
            for (T entity : recordsToMigrate) {
                try {
                    targetRepo.save(entity);
                    migratedCount++;
                    
                    // Update checkpoint every 100 records
                    if (migratedCount % 100 == 0) {
                        Object id = getEntityId(entity);
                        Instant timestamp = getFieldValue(entity, timeWindowField);
                        checkpointManager.updateCheckpoint(entityName, id.toString(), timestamp);
                    }
                } catch (Exception e) {
                    result.addError(new MigrationError(
                        getEntityId(entity).toString(), 
                        "Failed to migrate: " + e.getMessage()));
                }
            }
            
            // Update final checkpoint
            if (!recordsToMigrate.isEmpty()) {
                T lastEntity = recordsToMigrate.get(recordsToMigrate.size() - 1);
                Instant timestamp = getFieldValue(lastEntity, timeWindowField);
                checkpointManager.updateCheckpoint(entityName, 
                    getEntityId(lastEntity).toString(), timestamp);
            }
            
            // Determine if more records exist after this batch
            boolean hasMoreRecords = sourceRepo.existsAfterTimestamp(
                timeWindowField, endTime);
            
            result.setCompleted(!hasMoreRecords);
            result.addMigratedRecords(migratedCount);
            result.setTimeWindow(startTime, endTime);
            
            if (!hasMoreRecords) {
                progressTracker.finishMigration(entityName);
            }
            
        } catch (Exception e) {
            progressTracker.failMigration(entityName, e);
            result.setCompleted(false);
            result.setFailureReason(e.getMessage());
            throw e;
        }
        
        return result;
    }
    
    // Helper methods
    private Object getEntityId(Object entity) {
        // Implementation to extract ID using reflection
        // ...
    }
    
    private <T> Instant getFieldValue(T entity, String fieldName) {
        // Implementation to get timestamp field using reflection
        // ...
    }
}
```

### 2.3 Batch Size Auto-Tuning

**Problem:** Fixed batch sizes don't account for entity complexity and system resources.

**Solution:** Implement a batch size auto-tuner:

```java
// services/data-tier/src/main/java/com/sentimark/migration/BatchSizeAutoTuner.java
package com.sentimark.migration;

import java.util.concurrent.ConcurrentHashMap;
import java.util.Map;

public class BatchSizeAutoTuner {
    private final Map<String, BatchSizeStats> entityStats = new ConcurrentHashMap<>();
    private final int minBatchSize = 10;
    private final int maxBatchSize = 10000;
    
    /**
     * Get the optimal batch size for an entity based on historical performance
     */
    public int getOptimalBatchSize(String entityName, int defaultBatchSize) {
        BatchSizeStats stats = entityStats.getOrDefault(entityName, 
            new BatchSizeStats(defaultBatchSize));
        
        return stats.getCurrentOptimalBatchSize();
    }
    
    /**
     * Update statistics after a batch is processed
     */
    public void recordBatchPerformance(
            String entityName, 
            int batchSize, 
            long processTimeMs, 
            long memoryUsedBytes,
            int errorCount) {
        
        BatchSizeStats stats = entityStats.computeIfAbsent(entityName, 
            k -> new BatchSizeStats(batchSize));
        
        // Record this batch performance
        stats.recordBatch(batchSize, processTimeMs, memoryUsedBytes, errorCount);
        
        // Adjust batch size based on performance
        if (errorCount > 0 && errorCount > stats.getAverageErrorRate() * 1.5) {
            // Too many errors, reduce batch size
            stats.adjustBatchSize(-0.2);
        } else if (memoryUsedBytes > Runtime.getRuntime().maxMemory() * 0.8) {
            // Close to memory limit, reduce batch size
            stats.adjustBatchSize(-0.3);
        } else if (processTimeMs > 30000) {
            // Batch taking too long, reduce size
            stats.adjustBatchSize(-0.1);
        } else if (errorCount == 0 && processTimeMs < 5000 && 
                memoryUsedBytes < Runtime.getRuntime().maxMemory() * 0.5) {
            // Good performance, try increasing batch size
            stats.adjustBatchSize(0.1);
        }
    }
    
    /**
     * Class to track batch size performance for an entity
     */
    private class BatchSizeStats {
        private int currentBatchSize;
        private double averageProcessTimeMs = 0;
        private double averageMemoryUsedBytes = 0;
        private double averageErrorRate = 0;
        private int batchesProcessed = 0;
        
        public BatchSizeStats(int initialBatchSize) {
            this.currentBatchSize = initialBatchSize;
        }
        
        public void recordBatch(int batchSize, long processTimeMs, 
                long memoryUsedBytes, int errorCount) {
            
            // Update moving averages
            double errorRate = errorCount / (double) batchSize;
            
            if (batchesProcessed == 0) {
                averageProcessTimeMs = processTimeMs;
                averageMemoryUsedBytes = memoryUsedBytes;
                averageErrorRate = errorRate;
            } else {
                double weight = 0.7; // Weight for new values vs historical
                averageProcessTimeMs = averageProcessTimeMs * (1 - weight) + 
                    processTimeMs * weight;
                averageMemoryUsedBytes = averageMemoryUsedBytes * (1 - weight) + 
                    memoryUsedBytes * weight;
                averageErrorRate = averageErrorRate * (1 - weight) + 
                    errorRate * weight;
            }
            
            batchesProcessed++;
        }
        
        public void adjustBatchSize(double factor) {
            int adjustment = (int) (currentBatchSize * factor);
            currentBatchSize = Math.max(minBatchSize, 
                Math.min(maxBatchSize, currentBatchSize + adjustment));
        }
        
        public int getCurrentOptimalBatchSize() {
            return currentBatchSize;
        }
        
        public double getAverageErrorRate() {
            return averageErrorRate;
        }
    }
}
```

## 3. Disaster Recovery Enhancements

The current migration plan lacks comprehensive disaster recovery mechanisms. The following enhancements address this gap:

### 3.1 Point-in-Time Recovery Script

**Problem:** The current plan doesn't provide a way to restore to a specific point in time during migration.

**Solution:** Implement a comprehensive point-in-time recovery script:

```bash
#!/bin/bash
# scripts/migration/recovery/pit_recovery.sh

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Required parameters
ENTITY=""
TIMESTAMP=""
RECOVERY_MODE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --entity=*)
      ENTITY="${1#*=}"
      shift
      ;;
    --timestamp=*)
      TIMESTAMP="${1#*=}"
      shift
      ;;
    --mode=*)
      RECOVERY_MODE="${1#*=}"
      shift
      ;;
    --snapshot=*)
      SNAPSHOT_ID="${1#*=}"
      shift
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --entity=NAME        Entity to recover"
      echo "  --timestamp=TIMESTAMP  Point-in-time for recovery (ISO format)"
      echo "  --mode=MODE          Recovery mode (iceberg_to_postgres, postgres_to_iceberg, iceberg_snapshot)"
      echo "  --snapshot=ID        Iceberg snapshot ID (only for iceberg_snapshot mode)"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Validate arguments
if [[ -z "$ENTITY" ]]; then
  echo -e "${RED}ERROR: Entity is required.${NC}"
  exit 1
fi

if [[ -z "$RECOVERY_MODE" ]]; then
  echo -e "${RED}ERROR: Recovery mode is required.${NC}"
  exit 1
fi

if [[ "$RECOVERY_MODE" == "iceberg_snapshot" && -z "$SNAPSHOT_ID" ]]; then
  echo -e "${RED}ERROR: Snapshot ID is required for iceberg_snapshot mode.${NC}"
  exit 1
fi

if [[ "$RECOVERY_MODE" != "iceberg_snapshot" && -z "$TIMESTAMP" ]]; then
  echo -e "${RED}ERROR: Timestamp is required for this recovery mode.${NC}"
  exit 1
fi

echo -e "${YELLOW}==============================================${NC}"
echo -e "${YELLOW}      Point-in-Time Recovery Tool            ${NC}"
echo -e "${YELLOW}==============================================${NC}"
echo "Entity: $ENTITY"
echo "Recovery Mode: $RECOVERY_MODE"

case $RECOVERY_MODE in
  iceberg_to_postgres)
    echo "Target Timestamp: $TIMESTAMP"
    echo -e "\n${YELLOW}Recovering PostgreSQL data from Iceberg at point-in-time${NC}"
    
    # Find Iceberg snapshot closest to timestamp
    echo "Finding closest Iceberg snapshot to timestamp..."
    SNAPSHOT_INFO=$(java -cp ./build/libs/migration-tools.jar \
      com.sentimark.migration.tools.IcebergTools \
      --action=find-snapshot-at-time \
      --entity=$ENTITY \
      --timestamp="$TIMESTAMP")
    
    SNAPSHOT_ID=$(echo "$SNAPSHOT_INFO" | grep "Snapshot ID:" | awk '{print $3}')
    SNAPSHOT_TIME=$(echo "$SNAPSHOT_INFO" | grep "Timestamp:" | awk '{print $2}')
    
    echo "Found snapshot $SNAPSHOT_ID from $SNAPSHOT_TIME"
    
    # Backup current PostgreSQL data
    echo "Backing up current PostgreSQL data..."
    pg_dump -t "$ENTITY" > "./backup/${ENTITY}_before_recovery_$(date +%Y%m%d%H%M%S).sql"
    
    # Restore data from Iceberg snapshot to PostgreSQL
    echo "Restoring data from Iceberg snapshot to PostgreSQL..."
    java -cp ./build/libs/migration-tools.jar \
      com.sentimark.migration.tools.SnapshotRestoreTool \
      --source=iceberg \
      --target=postgres \
      --entity=$ENTITY \
      --snapshot-id=$SNAPSHOT_ID
    
    echo -e "${GREEN}Recovery completed!${NC}"
    ;;
    
  postgres_to_iceberg)
    echo "Target Timestamp: $TIMESTAMP"
    echo -e "\n${YELLOW}Recovering Iceberg data from PostgreSQL at point-in-time${NC}"
    
    # Get PostgreSQL backup closest to timestamp
    echo "Finding closest PostgreSQL backup to timestamp..."
    BACKUP_FILE=$(./scripts/migration/recovery/find_closest_backup.sh --entity=$ENTITY --timestamp="$TIMESTAMP")
    
    echo "Found backup: $BACKUP_FILE"
    
    # Restore PostgreSQL data to a temporary table
    echo "Restoring PostgreSQL backup to temporary table..."
    psql -c "CREATE TABLE ${ENTITY}_recovery AS SELECT * FROM $ENTITY WHERE 1=0;"
    pg_restore -t "$ENTITY" -a --data-only "$BACKUP_FILE" | sed "s/$ENTITY/${ENTITY}_recovery/g" | psql
    
    # Migrate data from temporary table to Iceberg
    echo "Migrating data from temporary PostgreSQL table to Iceberg..."
    java -cp ./build/libs/migration-tools.jar \
      com.sentimark.migration.tools.TemporaryTableMigrator \
      --source=postgres \
      --source-table=${ENTITY}_recovery \
      --target=iceberg \
      --target-table=$ENTITY \
      --replace
    
    # Clean up temporary table
    echo "Cleaning up temporary table..."
    psql -c "DROP TABLE ${ENTITY}_recovery;"
    
    echo -e "${GREEN}Recovery completed!${NC}"
    ;;
    
  iceberg_snapshot)
    echo "Target Snapshot ID: $SNAPSHOT_ID"
    echo -e "\n${YELLOW}Recovering Iceberg data from specific snapshot${NC}"
    
    # Validate snapshot exists
    echo "Validating snapshot exists..."
    SNAPSHOT_EXISTS=$(java -cp ./build/libs/migration-tools.jar \
      com.sentimark.migration.tools.IcebergTools \
      --action=check-snapshot \
      --entity=$ENTITY \
      --snapshot-id=$SNAPSHOT_ID)
    
    if [[ "$SNAPSHOT_EXISTS" != "Snapshot exists" ]]; then
      echo -e "${RED}ERROR: Snapshot does not exist!${NC}"
      exit 1
    fi
    
    # Restore from snapshot
    echo "Restoring Iceberg table from snapshot..."
    java -cp ./build/libs/migration-tools.jar \
      com.sentimark.migration.tools.IcebergTools \
      --action=rollback-to-snapshot \
      --entity=$ENTITY \
      --snapshot-id=$SNAPSHOT_ID
    
    echo -e "${GREEN}Recovery completed!${NC}"
    ;;
    
  *)
    echo -e "${RED}ERROR: Unknown recovery mode: $RECOVERY_MODE${NC}"
    exit 1
    ;;
esac
```

### 3.2 Transaction Log and Audit Trail

**Problem:** The current plan doesn't maintain a comprehensive audit trail for all migration operations.

**Solution:** Implement a transaction log system for migration operations:

```java
// services/data-tier/src/main/java/com/sentimark/migration/MigrationTransactionLogger.java
package com.sentimark.migration;

import java.time.Instant;
import java.util.UUID;
import javax.sql.DataSource;
import org.springframework.jdbc.core.JdbcTemplate;
import com.fasterxml.jackson.databind.ObjectMapper;

public class MigrationTransactionLogger {
    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;
    
    public MigrationTransactionLogger(DataSource dataSource) {
        this.jdbcTemplate = new JdbcTemplate(dataSource);
        this.objectMapper = new ObjectMapper();
        
        // Ensure log table exists
        initializeLogTable();
    }
    
    private void initializeLogTable() {
        jdbcTemplate.execute(
            "CREATE TABLE IF NOT EXISTS migration_transaction_log (" +
            "  id VARCHAR(36) PRIMARY KEY, " +
            "  timestamp TIMESTAMP NOT NULL, " +
            "  entity_name VARCHAR(255) NOT NULL, " +
            "  operation VARCHAR(50) NOT NULL, " +
            "  source_system VARCHAR(50) NOT NULL, " +
            "  target_system VARCHAR(50) NOT NULL, " +
            "  user_id VARCHAR(255), " +
            "  record_count INTEGER, " +
            "  batch_id VARCHAR(36), " +
            "  status VARCHAR(20) NOT NULL, " +
            "  error_message TEXT, " +
            "  metadata JSONB" +
            ")");
    }
    
    public String logMigrationStart(
            String entityName, 
            String operation, 
            String sourceSystem,
            String targetSystem,
            String userId,
            int expectedRecordCount) {
        
        String transactionId = UUID.randomUUID().toString();
        String batchId = UUID.randomUUID().toString();
        
        jdbcTemplate.update(
            "INSERT INTO migration_transaction_log " +
            "(id, timestamp, entity_name, operation, source_system, target_system, " +
            " user_id, record_count, batch_id, status, metadata) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)",
            transactionId,
            Instant.now(),
            entityName,
            operation,
            sourceSystem,
            targetSystem,
            userId,
            expectedRecordCount,
            batchId,
            "STARTED",
            "{ \"start_time\": \"" + Instant.now() + "\" }"
        );
        
        return batchId;
    }
    
    public void logMigrationComplete(
            String batchId,
            int actualRecordCount,
            Map<String, Object> additionalMetadata) {
        
        try {
            String metadataJson = objectMapper.writeValueAsString(additionalMetadata);
            
            jdbcTemplate.update(
                "UPDATE migration_transaction_log " +
                "SET status = ?, record_count = ?, metadata = ?::jsonb, " +
                "timestamp = ? " +
                "WHERE batch_id = ? AND status = 'STARTED'",
                "COMPLETED",
                actualRecordCount,
                metadataJson,
                Instant.now(),
                batchId
            );
        } catch (Exception e) {
            logError("Error updating transaction log", e);
        }
    }
    
    public void logMigrationError(
            String batchId,
            String errorMessage,
            Exception exception) {
        
        try {
            Map<String, Object> metadata = new HashMap<>();
            metadata.put("error_time", Instant.now().toString());
            if (exception != null) {
                metadata.put("exception_type", exception.getClass().getName());
                metadata.put("stack_trace", getStackTraceAsString(exception));
            }
            
            String metadataJson = objectMapper.writeValueAsString(metadata);
            
            jdbcTemplate.update(
                "UPDATE migration_transaction_log " +
                "SET status = ?, error_message = ?, metadata = ?::jsonb, " +
                "timestamp = ? " +
                "WHERE batch_id = ? AND status = 'STARTED'",
                "FAILED",
                errorMessage,
                metadataJson,
                Instant.now(),
                batchId
            );
        } catch (Exception e) {
            logError("Error updating transaction log", e);
        }
    }
    
    // Helper methods for logging operations...
}
```

### 3.3 Automated Recovery Testing

**Problem:** Recovery procedures are defined but not regularly tested.

**Solution:** Add automated recovery testing to CI/CD:

```yaml
# .github/workflows/migration-recovery-test.yml
name: Test Migration Recovery Procedures

on:
  schedule:
    # Run weekly
    - cron: '0 2 * * 0'
  workflow_dispatch:
    inputs:
      recovery_scenario:
        description: 'Recovery scenario to test'
        required: false
        default: 'all'
        type: choice
        options:
          - 'all'
          - 'snapshot_rollback'
          - 'point_in_time'
          - 'partial_failure'

jobs:
  test-recovery:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_USER: postgres
          POSTGRES_DB: test_recovery
        ports:
          - 5432:5432
        
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up JDK 11
        uses: actions/setup-java@v2
        with:
          java-version: '11'
          distribution: 'adopt'
      
      - name: Set up test environment
        run: |
          ./scripts/migration/recovery/setup_test_recovery.sh
      
      - name: Run recovery tests
        run: |
          SCENARIOS="${{ github.event.inputs.recovery_scenario || 'all' }}"
          
          if [[ "$SCENARIOS" == "all" || "$SCENARIOS" == "snapshot_rollback" ]]; then
            echo "Testing snapshot rollback recovery..."
            ./scripts/migration/recovery/test_scenario.sh --scenario=snapshot_rollback
          fi
          
          if [[ "$SCENARIOS" == "all" || "$SCENARIOS" == "point_in_time" ]]; then
            echo "Testing point-in-time recovery..."
            ./scripts/migration/recovery/test_scenario.sh --scenario=point_in_time
          fi
          
          if [[ "$SCENARIOS" == "all" || "$SCENARIOS" == "partial_failure" ]]; then
            echo "Testing recovery from partial migration failure..."
            ./scripts/migration/recovery/test_scenario.sh --scenario=partial_failure
          fi
      
      - name: Generate recovery test report
        run: |
          ./scripts/migration/recovery/generate_report.sh
      
      - name: Upload recovery test results
        uses: actions/upload-artifact@v2
        with:
          name: recovery-test-results
          path: build/reports/recovery/
```

## 4. Monitoring and Alerting Enhancements

The current plan includes some monitoring but lacks comprehensive alerting and integrations. The following enhancements address this gap:

### 4.1 Prometheus Metrics Integration

**Problem:** The migration tools lack integration with standard monitoring systems.

**Solution:** Add Prometheus metrics for all migration operations:

```java
// services/data-tier/src/main/java/com/sentimark/migration/monitoring/MigrationMetrics.java
package com.sentimark.migration.monitoring;

import io.micrometer.core.instrument.*;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

public class MigrationMetrics {
    private final MeterRegistry registry;
    
    // Metrics for tracking migration processes
    private final Map<String, Counter> recordsMigratedCounters = new ConcurrentHashMap<>();
    private final Map<String, Counter> migrationErrorCounters = new ConcurrentHashMap<>();
    private final Map<String, Timer> migrationTimers = new ConcurrentHashMap<>();
    private final Map<String, Gauge> migrationProgressGauges = new ConcurrentHashMap<>();
    
    public MigrationMetrics(MeterRegistry registry) {
        this.registry = registry;
    }
    
    public void recordMigratedRecords(String entity, int count) {
        Counter counter = recordsMigratedCounters.computeIfAbsent(
            entity,
            e -> Counter.builder("migration.records.migrated")
                .tag("entity", e)
                .description("Number of records migrated")
                .register(registry)
        );
        
        counter.increment(count);
    }
    
    public void recordMigrationError(String entity, String errorType) {
        String metricName = entity + "." + errorType;
        Counter counter = migrationErrorCounters.computeIfAbsent(
            metricName,
            e -> Counter.builder("migration.errors")
                .tag("entity", entity)
                .tag("error_type", errorType)
                .description("Number of migration errors")
                .register(registry)
        );
        
        counter.increment();
    }
    
    public Timer.Sample startMigrationTimer(String entity, String operation) {
        return Timer.start(registry);
    }
    
    public void stopMigrationTimer(Timer.Sample sample, String entity, String operation) {
        Timer timer = migrationTimers.computeIfAbsent(
            entity + "." + operation,
            k -> Timer.builder("migration.duration")
                .tag("entity", entity)
                .tag("operation", operation)
                .description("Migration operation duration")
                .register(registry)
        );
        
        sample.stop(timer);
    }
    
    public void updateMigrationProgress(String entity, double percentComplete) {
        String metricName = entity + ".progress";
        if (!migrationProgressGauges.containsKey(metricName)) {
            // Create a custom gauge implementation to track progress
            AtomicDouble progressValue = new AtomicDouble(percentComplete);
            Gauge gauge = Gauge.builder("migration.progress", progressValue::get)
                .tag("entity", entity)
                .description("Migration progress percentage")
                .register(registry);
            
            migrationProgressGauges.put(metricName, gauge);
        } else {
            // Update the existing gauge value
            ((AtomicDouble)migrationProgressGauges.get(metricName).value()).set(percentComplete);
        }
    }
}
```

### 4.2 Real-Time Alerting System

**Problem:** No real-time alerting for migration failures or anomalies.

**Solution:** Implement an alerting system with multiple notification channels:

```java
// services/data-tier/src/main/java/com/sentimark/migration/monitoring/MigrationAlertingService.java
package com.sentimark.migration.monitoring;

import java.time.Instant;
import java.util.EnumSet;
import java.util.Map;

@Service
public class MigrationAlertingService {
    private final NotificationService notificationService;
    private final AlertThresholds alertThresholds;
    private final Map<String, EntityAlertStatus> entityAlertStatus = new ConcurrentHashMap<>();
    
    public MigrationAlertingService(
            NotificationService notificationService,
            AlertThresholds alertThresholds) {
        this.notificationService = notificationService;
        this.alertThresholds = alertThresholds;
    }
    
    public void checkAndAlertMigrationStatus(
            String entity, 
            int totalRecords,
            int migratedRecords, 
            int errorCount,
            double migrationRate,
            double timeRemainingMinutes) {
        
        EntityAlertStatus status = entityAlertStatus.computeIfAbsent(entity,
            e -> new EntityAlertStatus());
        
        EnumSet<AlertType> triggeredAlerts = EnumSet.noneOf(AlertType.class);
        
        // Check for stalled migration
        if (migrationRate < alertThresholds.getStalledRateThreshold() &&
            status.getLastProgress() == migratedRecords &&
            status.getLastProgressTimestamp().isBefore(
                Instant.now().minusSeconds(
                    alertThresholds.getStalledTimeThresholdSeconds()))) {
            
            if (!status.hasAlertBeenSent(AlertType.STALLED)) {
                triggeredAlerts.add(AlertType.STALLED);
                status.markAlertSent(AlertType.STALLED);
            }
        } else {
            status.resetAlert(AlertType.STALLED);
        }
        
        // Check for high error rate
        double errorRate = (double) errorCount / Math.max(1, migratedRecords);
        if (errorRate > alertThresholds.getErrorRateThreshold() && 
            migratedRecords > 100) { // Ignore initial errors
            
            if (!status.hasAlertBeenSent(AlertType.HIGH_ERROR_RATE)) {
                triggeredAlerts.add(AlertType.HIGH_ERROR_RATE);
                status.markAlertSent(AlertType.HIGH_ERROR_RATE);
            }
        } else {
            status.resetAlert(AlertType.HIGH_ERROR_RATE);
        }
        
        // Check for slow migration rate (comparing to historical baseline)
        double expectedRate = alertThresholds.getExpectedMigrationRate(entity);
        if (migrationRate < expectedRate * 0.5 && migratedRecords > 1000) {
            if (!status.hasAlertBeenSent(AlertType.SLOW_MIGRATION)) {
                triggeredAlerts.add(AlertType.SLOW_MIGRATION);
                status.markAlertSent(AlertType.SLOW_MIGRATION);
            }
        } else {
            status.resetAlert(AlertType.SLOW_MIGRATION);
        }
        
        // Update status for next check
        status.setLastProgress(migratedRecords);
        status.setLastProgressTimestamp(Instant.now());
        
        // Send alerts for triggered conditions
        if (!triggeredAlerts.isEmpty()) {
            sendAlerts(entity, triggeredAlerts, Map.of(
                "totalRecords", totalRecords,
                "migratedRecords", migratedRecords,
                "errorCount", errorCount,
                "migrationRate", migrationRate,
                "timeRemainingMinutes", timeRemainingMinutes,
                "percentComplete", (migratedRecords * 100.0) / totalRecords
            ));
        }
    }
    
    private void sendAlerts(
            String entity, 
            EnumSet<AlertType> alertTypes,
            Map<String, Object> metrics) {
        
        StringBuilder alertMessage = new StringBuilder();
        alertMessage.append("⚠️ Migration Alert for ").append(entity).append(":\n\n");
        
        for (AlertType alertType : alertTypes) {
            alertMessage.append("- ").append(alertType.getDescription()).append("\n");
        }
        
        alertMessage.append("\nCurrent Metrics:\n");
        alertMessage.append("- Progress: ")
            .append(metrics.get("migratedRecords")).append("/")
            .append(metrics.get("totalRecords"))
            .append(" (").append(String.format("%.2f", metrics.get("percentComplete")))
            .append("%)\n");
        alertMessage.append("- Migration Rate: ")
            .append(String.format("%.2f", metrics.get("migrationRate")))
            .append(" records/second\n");
        alertMessage.append("- Error Count: ")
            .append(metrics.get("errorCount")).append("\n");
        alertMessage.append("- Estimated Time Remaining: ")
            .append(String.format("%.2f", metrics.get("timeRemainingMinutes")))
            .append(" minutes\n");
        
        // Send notification to all configured channels
        notificationService.sendAlert(
            "Migration Alert: " + String.join(", ", 
                alertTypes.stream().map(AlertType::name).toList()),
            alertMessage.toString(),
            NotificationPriority.HIGH
        );
    }
    
    public enum AlertType {
        STALLED("Migration appears to be stalled"),
        HIGH_ERROR_RATE("High error rate detected"),
        SLOW_MIGRATION("Migration is slower than expected"),
        VERIFICATION_FAILED("Data verification failed"),
        RESOURCE_EXHAUSTION("System resources are exhausted");
        
        private final String description;
        
        AlertType(String description) {
            this.description = description;
        }
        
        public String getDescription() {
            return description;
        }
    }
    
    // Helper classes
    private static class EntityAlertStatus {
        private final Map<AlertType, Instant> lastAlertSent = new ConcurrentHashMap<>();
        private int lastProgress = 0;
        private Instant lastProgressTimestamp = Instant.now();
        
        public int getLastProgress() {
            return lastProgress;
        }
        
        public void setLastProgress(int lastProgress) {
            this.lastProgress = lastProgress;
        }
        
        public Instant getLastProgressTimestamp() {
            return lastProgressTimestamp;
        }
        
        public void setLastProgressTimestamp(Instant lastProgressTimestamp) {
            this.lastProgressTimestamp = lastProgressTimestamp;
        }
        
        public boolean hasAlertBeenSent(AlertType alertType) {
            return lastAlertSent.containsKey(alertType) && 
                lastAlertSent.get(alertType).isAfter(
                    Instant.now().minusSeconds(1800)); // 30 min cooldown
        }
        
        public void markAlertSent(AlertType alertType) {
            lastAlertSent.put(alertType, Instant.now());
        }
        
        public void resetAlert(AlertType alertType) {
            lastAlertSent.remove(alertType);
        }
    }
}
```

### 4.3 Integration with External Monitoring Systems

**Problem:** Migration monitoring is isolated from the overall system monitoring.

**Solution:** Add integration with external monitoring systems:

```yaml
# /infrastructure/monitoring/grafana-dashboards/migration-dashboard.json
{
  "annotations": {...},
  "editable": true,
  "gnetId": null,
  "graphTooltip": 0,
  "id": 15,
  "links": [],
  "panels": [
    {
      "datasource": "Prometheus",
      "fieldConfig": {
        "defaults": {
          "color": {
            "mode": "thresholds"
          },
          "mappings": [],
          "thresholds": {
            "mode": "absolute",
            "steps": [
              {
                "color": "red",
                "value": null
              },
              {
                "color": "orange",
                "value": 50
              },
              {
                "color": "green",
                "value": 90
              }
            ]
          },
          "unit": "percent"
        },
        "overrides": []
      },
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 0,
        "y": 0
      },
      "id": 2,
      "options": {
        "orientation": "auto",
        "reduceOptions": {
          "calcs": [
            "lastNotNull"
          ],
          "fields": "",
          "values": false
        },
        "showThresholdLabels": false,
        "showThresholdMarkers": true,
        "text": {}
      },
      "pluginVersion": "7.5.7",
      "targets": [
        {
          "expr": "migration_progress{entity=~\"$entity\"}",
          "interval": "",
          "legendFormat": "{{entity}}",
          "refId": "A"
        }
      ],
      "title": "Migration Progress",
      "type": "gauge"
    },
    {
      "aliasColors": {},
      "bars": false,
      "dashLength": 10,
      "dashes": false,
      "datasource": "Prometheus",
      "fieldConfig": {
        "defaults": {},
        "overrides": []
      },
      "fill": 1,
      "fillGradient": 0,
      "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 0
      },
      "hiddenSeries": false,
      "id": 4,
      "legend": {
        "avg": false,
        "current": false,
        "max": false,
        "min": false,
        "show": true,
        "total": false,
        "values": false
      },
      "lines": true,
      "linewidth": 1,
      "nullPointMode": "null",
      "options": {
        "alertThreshold": true
      },
      "percentage": false,
      "pluginVersion": "7.5.7",
      "pointradius": 2,
      "points": false,
      "renderer": "flot",
      "seriesOverrides": [],
      "spaceLength": 10,
      "stack": false,
      "steppedLine": false,
      "targets": [
        {
          "expr": "rate(migration_records_migrated{entity=~\"$entity\"}[1m])",
          "interval": "",
          "legendFormat": "{{entity}}",
          "refId": "A"
        }
      ],
      "thresholds": [],
      "timeFrom": null,
      "timeRegions": [],
      "timeShift": null,
      "title": "Migration Rate (records/sec)",
      "tooltip": {
        "shared": true,
        "sort": 0,
        "value_type": "individual"
      },
      "type": "graph",
      "xaxis": {
        "buckets": null,
        "mode": "time",
        "name": null,
        "show": true,
        "values": []
      },
      "yaxes": [
        {
          "format": "short",
          "label": null,
          "logBase": 1,
          "max": null,
          "min": null,
          "show": true
        },
        {
          "format": "short",
          "label": null,
          "logBase": 1,
          "max": null,
          "min": null,
          "show": true
        }
      ],
      "yaxis": {
        "align": false,
        "alignLevel": null
      }
    },
    {
      "datasource": null,
      "fieldConfig": {},
      "gridPos": {},
      "id": 6,
      "title": "Migration Errors",
      "type": "timeseries",
      "targets": [
        {
          "expr": "sum(migration_errors{entity=~\"$entity\"}) by (entity, error_type)",
          "legendFormat": "{{entity}} - {{error_type}}"
        }
      ]
    },
    {
      "datasource": null,
      "fieldConfig": {},
      "gridPos": {},
      "id": 8,
      "title": "Migration Duration",
      "type": "timeseries",
      "targets": [
        {
          "expr": "histogram_quantile(0.95, sum(rate(migration_duration_seconds_bucket{entity=~\"$entity\"}[5m])) by (le, entity, operation))",
          "legendFormat": "{{entity}} - {{operation}} (p95)"
        }
      ]
    }
  ],
  "refresh": "5s",
  "schemaVersion": 27,
  "style": "dark",
  "tags": [
    "migration",
    "database",
    "iceberg"
  ],
  "templating": {
    "list": [
      {
        "allValue": null,
        "current": {
          "selected": false,
          "text": "All",
          "value": "$__all"
        },
        "datasource": "Prometheus",
        "definition": "label_values(migration_progress, entity)",
        "description": null,
        "error": null,
        "hide": 0,
        "includeAll": true,
        "label": "Entity",
        "multi": false,
        "name": "entity",
        "options": [],
        "query": {
          "query": "label_values(migration_progress, entity)",
          "refId": "StandardVariableQuery"
        },
        "refresh": 1,
        "regex": "",
        "skipUrlSync": false,
        "sort": 0,
        "type": "query"
      }
    ]
  },
  "time": {
    "from": "now-6h",
    "to": "now"
  },
  "timepicker": {},
  "timezone": "",
  "title": "Database Migration Dashboard",
  "uid": "db-migration",
  "version": 1
}
```

## 5. Edge Case Handling

The current migration plan may not account for all edge cases. The following enhancements address specific edge cases that could cause problems during migration:

### 5.1 Large Object Handling

**Problem:** The migration doesn't handle large binary objects (BLOBs) efficiently.

**Solution:** Add specialized handling for large objects:

```java
// services/data-tier/src/main/java/com/sentimark/migration/handlers/LargeObjectMigrationHandler.java
package com.sentimark.migration.handlers;

import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Blob;
import java.util.Map;
import java.util.UUID;

@Component
@MigrationHandler(supportedTypes = {"BLOB", "BYTEA"})
public class LargeObjectMigrationHandler implements SpecializedMigrationHandler {
    private final Path tempDir;
    private final LargeObjectStorageService objectStorageService;
    
    public LargeObjectMigrationHandler(
            @Value("${migration.temp-dir}") String tempDirPath,
            LargeObjectStorageService objectStorageService) {
        this.tempDir = Path.of(tempDirPath);
        this.objectStorageService = objectStorageService;
        
        // Ensure temp directory exists
        try {
            Files.createDirectories(tempDir);
        } catch (Exception e) {
            throw new RuntimeException("Could not create temp directory", e);
        }
    }
    
    @Override
    public Object handleSourceValue(Object sourceValue, Map<String, Object> metadata) {
        if (sourceValue == null) {
            return null;
        }
        
        try {
            InputStream contentStream;
            
            if (sourceValue instanceof Blob) {
                Blob blob = (Blob) sourceValue;
                contentStream = blob.getBinaryStream();
            } else if (sourceValue instanceof byte[]) {
                contentStream = new ByteArrayInputStream((byte[]) sourceValue);
            } else {
                throw new UnsupportedOperationException(
                    "Unsupported large object type: " + sourceValue.getClass().getName());
            }
            
            // For very large objects, use temporary file as intermediate storage
            if (getSize(sourceValue) > 10 * 1024 * 1024) { // > 10MB
                String objectId = UUID.randomUUID().toString();
                Path tempFile = tempDir.resolve(objectId);
                
                Files.copy(contentStream, tempFile);
                
                // Store in object storage and keep the reference
                String storageId = objectStorageService.storeObject(
                    Files.newInputStream(tempFile), 
                    metadata.getOrDefault("contentType", "application/octet-stream").toString());
                
                // Clean up temp file
                Files.delete(tempFile);
                
                // Return storage ID that will be stored in the database
                return storageId;
            } else {
                // For smaller objects, use direct migration
                return convertToTargetType(contentStream, metadata);
            }
        } catch (Exception e) {
            throw new MigrationException("Failed to handle large object", e);
        }
    }
    
    private long getSize(Object value) throws Exception {
        if (value instanceof Blob) {
            return ((Blob) value).length();
        } else if (value instanceof byte[]) {
            return ((byte[]) value).length;
        }
        return -1;
    }
    
    private Object convertToTargetType(InputStream stream, Map<String, Object> metadata) 
            throws Exception {
        // Implementation depends on target system (Iceberg)
        // For Iceberg, convert to bytes for storage in binary column
        return stream.readAllBytes();
    }
}
```

### 5.2 Handling Schema Evolution During Migration

**Problem:** The migration doesn't handle schema changes during the migration process.

**Solution:** Add a schema evolution detection and handling mechanism:

```java
// services/data-tier/src/main/java/com/sentimark/migration/SchemaEvolutionHandler.java
package com.sentimark.migration;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.apache.iceberg.Schema;
import org.apache.iceberg.types.Types.NestedField;

@Component
public class SchemaEvolutionHandler {
    private final SchemaRegistry schemaRegistry;
    private final Map<String, Integer> schemaVersions = new ConcurrentHashMap<>();
    private final SchemaCompatibilityChecker compatibilityChecker;
    
    public SchemaEvolutionHandler(
            SchemaRegistry schemaRegistry,
            SchemaCompatibilityChecker compatibilityChecker) {
        this.schemaRegistry = schemaRegistry;
        this.compatibilityChecker = compatibilityChecker;
    }
    
    /**
     * Check if a schema has changed and handle the evolution if needed
     */
    public SchemaEvolutionResult handleSchemaEvolution(
            String entityName, 
            Schema currentSchema) {
        
        Schema registeredSchema = schemaRegistry.getSchema(entityName);
        
        if (registeredSchema == null) {
            // First time seeing this schema
            schemaRegistry.registerSchema(entityName, currentSchema);
            schemaVersions.put(entityName, 1);
            return new SchemaEvolutionResult(entityName, 1, false, null);
        }
        
        SchemaCompatibility compatibility = 
            compatibilityChecker.checkCompatibility(registeredSchema, currentSchema);
        
        if (compatibility.isCompatible()) {
            // No evolution needed
            return new SchemaEvolutionResult(
                entityName, 
                schemaVersions.get(entityName),
                false,
                null);
        }
        
        // Handle schema evolution
        if (compatibility.isSafeEvolution()) {
            // Can be handled automatically
            Schema evolvedSchema = evolveSchema(
                registeredSchema, 
                currentSchema, 
                compatibility.getChanges());
            
            // Update registry with evolved schema
            schemaRegistry.registerSchema(entityName, evolvedSchema);
            
            // Increment version
            int newVersion = schemaVersions.get(entityName) + 1;
            schemaVersions.put(entityName, newVersion);
            
            return new SchemaEvolutionResult(
                entityName,
                newVersion,
                true,
                evolvedSchema);
        } else {
            // Unsafe evolution that requires manual intervention
            throw new UnsafeSchemaEvolutionException(
                "Unsafe schema evolution detected for " + entityName + ": " +
                compatibility.getIncompatibleChanges());
        }
    }
    
    /**
     * Evolve a schema based on detected changes
     */
    private Schema evolveSchema(
            Schema oldSchema, 
            Schema newSchema,
            List<SchemaChange> changes) {
        
        // Start with the old schema
        List<NestedField> fields = new ArrayList<>(oldSchema.columns());
        
        // Apply each change
        for (SchemaChange change : changes) {
            switch (change.getType()) {
                case ADD_OPTIONAL_FIELD:
                    // Find field in new schema and add it
                    NestedField newField = newSchema.findField(change.getFieldName());
                    fields.add(newField);
                    break;
                    
                case RELAX_NULLABILITY:
                    // Find field and make it optional
                    for (int i = 0; i < fields.size(); i++) {
                        NestedField field = fields.get(i);
                        if (field.name().equals(change.getFieldName())) {
                            fields.set(i, field.asOptional());
                            break;
                        }
                    }
                    break;
                    
                // Handle other safe changes
                // ...
            }
        }
        
        return new Schema(fields);
    }
    
    /**
     * Result class for schema evolution operations
     */
    @Getter
    public static class SchemaEvolutionResult {
        private final String entityName;
        private final int schemaVersion;
        private final boolean evolved;
        private final Schema evolvedSchema;
        
        // Constructor and getters...
    }
}
```

### 5.3 Circular Dependency Resolution

**Problem:** The migration doesn't handle circular references between entities.

**Solution:** Add a circular dependency detector and resolver:

```java
// services/data-tier/src/main/java/com/sentimark/migration/CircularDependencyResolver.java
package com.sentimark.migration;

import java.util.*;
import java.util.stream.Collectors;

@Component
public class CircularDependencyResolver {
    private final SchemaRegistry schemaRegistry;
    private final DataSource postgresDataSource;
    
    public CircularDependencyResolver(
            SchemaRegistry schemaRegistry,
            DataSource postgresDataSource) {
        this.schemaRegistry = schemaRegistry;
        this.postgresDataSource = postgresDataSource;
    }
    
    /**
     * Analyze database and detect entity dependencies
     */
    public DependencyGraph buildDependencyGraph() {
        try (Connection conn = postgresDataSource.getConnection()) {
            DependencyGraph graph = new DependencyGraph();
            
            // Get all entities
            Set<String> allEntities = schemaRegistry.getAllRegisteredEntities();
            
            // For each entity, find its foreign key dependencies
            for (String entity : allEntities) {
                graph.addNode(entity);
                
                // Query foreign key constraints
                try (PreparedStatement stmt = conn.prepareStatement(
                        "SELECT ccu.table_name AS foreign_table " +
                        "FROM information_schema.table_constraints AS tc " +
                        "JOIN information_schema.key_column_usage AS kcu " +
                        "  ON tc.constraint_name = kcu.constraint_name " +
                        "  AND tc.table_schema = kcu.table_schema " +
                        "JOIN information_schema.constraint_column_usage AS ccu " +
                        "  ON ccu.constraint_name = tc.constraint_name " +
                        "  AND ccu.table_schema = tc.table_schema " +
                        "WHERE tc.constraint_type = 'FOREIGN KEY' " +
                        "  AND tc.table_name = ?")) {
                    
                    stmt.setString(1, entity);
                    
                    try (ResultSet rs = stmt.executeQuery()) {
                        while (rs.next()) {
                            String dependsOn = rs.getString("foreign_table");
                            if (allEntities.contains(dependsOn)) {
                                graph.addDependency(entity, dependsOn);
                            }
                        }
                    }
                }
            }
            
            return graph;
        } catch (SQLException e) {
            throw new MigrationException("Failed to build dependency graph", e);
        }
    }
    
    /**
     * Given a dependency graph, determine the optimal migration order
     */
    public List<EntityBatch> determineOptimalMigrationOrder() {
        DependencyGraph graph = buildDependencyGraph();
        
        // Detect cycles in the graph
        Set<Set<String>> cycles = graph.findCycles();
        
        // Convert graph to DAG by collapsing cycles
        DependencyGraph dag = graph.collapseIntoCyclicDAG();
        
        // Determine migration batches using topological sort
        List<Set<String>> batches = dag.topologicalSort();
        
        // Expand collapsed nodes back into their constituent entities
        List<EntityBatch> migrationBatches = new ArrayList<>();
        
        for (Set<String> batch : batches) {
            EntityBatch entityBatch = new EntityBatch();
            
            for (String node : batch) {
                if (node.startsWith("CYCLE_")) {
                    // This is a collapsed cycle, find which cycle it corresponds to
                    String cycleId = node.substring(6);
                    Set<String> cycleEntities = findCycleById(cycles, cycleId);
                    
                    // Create a circular batch with the cycle entities
                    entityBatch.addCircularBatch(cycleEntities);
                } else {
                    // Regular entity
                    entityBatch.addEntity(node);
                }
            }
            
            migrationBatches.add(entityBatch);
        }
        
        return migrationBatches;
    }
    
    // Helper classes
    
    /**
     * Graph representing entity dependencies
     */
    public static class DependencyGraph {
        private final Map<String, Set<String>> outgoingEdges = new HashMap<>();
        private final Map<String, Set<String>> incomingEdges = new HashMap<>();
        
        public void addNode(String node) {
            outgoingEdges.putIfAbsent(node, new HashSet<>());
            incomingEdges.putIfAbsent(node, new HashSet<>());
        }
        
        public void addDependency(String from, String to) {
            addNode(from);
            addNode(to);
            outgoingEdges.get(from).add(to);
            incomingEdges.get(to).add(from);
        }
        
        // Implementation of cycle detection algorithms
        public Set<Set<String>> findCycles() {
            // Tarjan's strongly connected components algorithm
            // ...
            return cycles;
        }
        
        // Implementation of graph collapsing
        public DependencyGraph collapseIntoCyclicDAG() {
            // ...
            return dag;
        }
        
        // Implementation of topological sort
        public List<Set<String>> topologicalSort() {
            // ...
            return sorted;
        }
    }
    
    /**
     * Represents a batch of entities to migrate together
     */
    public static class EntityBatch {
        private final Set<String> regularEntities = new HashSet<>();
        private final List<Set<String>> circularBatches = new ArrayList<>();
        
        public void addEntity(String entity) {
            regularEntities.add(entity);
        }
        
        public void addCircularBatch(Set<String> entities) {
            circularBatches.add(entities);
        }
        
        public Set<String> getRegularEntities() {
            return regularEntities;
        }
        
        public List<Set<String>> getCircularBatches() {
            return circularBatches;
        }
        
        public boolean hasCircularDependencies() {
            return !circularBatches.isEmpty();
        }
    }
}
```

## Implementation Plan

To implement these enhancements, we will follow this structured approach:

1. **Phase 1: Infrastructure and Tooling Enhancements (Weeks 1-2)**
   - Set up CI/CD pipelines for migration testing
   - Implement schema drift detection
   - Add Prometheus metrics endpoints
   - Create Grafana dashboards

2. **Phase 2: Performance Optimizations (Weeks 3-4)**
   - Implement adaptive parallel migration framework
   - Add incremental migration support
   - Implement batch size auto-tuning
   - Add performance benchmarking tests

3. **Phase 3: Disaster Recovery and Monitoring (Weeks 5-6)**
   - Implement transaction logging
   - Create point-in-time recovery scripts
   - Set up alerting integrations
   - Add automated recovery testing

4. **Phase 4: Edge Case Handling (Weeks 7-8)**
   - Implement large object handling
   - Add schema evolution detection
   - Implement circular dependency resolution
   - Add comprehensive edge case tests

Each phase will be delivered with full documentation, testing, and demonstration of the new capabilities.