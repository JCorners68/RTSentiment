package com.sentimark.data.migration;

import com.sentimark.data.repository.Repository;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executor;
import java.util.concurrent.Executors;
import java.util.stream.Collectors;

/**
 * Service responsible for migrating data between PostgreSQL and Iceberg.
 * This handles the batch migration of historical data as part of Phase 5.
 */
@Service
public class DataMigrationService {
    private final Logger logger = LoggerFactory.getLogger(DataMigrationService.class);
    private final MeterRegistry meterRegistry;
    private final int batchSize;
    private final int parallelThreads;
    private final boolean validationEnabled;
    private final Executor executor;
    
    /**
     * Creates a new DataMigrationService.
     *
     * @param meterRegistry The meter registry for monitoring
     * @param batchSize The batch size for migration
     * @param parallelThreads Number of parallel threads for migration
     * @param validationEnabled Whether to validate migrated data
     */
    @Autowired
    public DataMigrationService(
            MeterRegistry meterRegistry,
            @Value("${migration.batch-size:100}") int batchSize,
            @Value("${migration.parallel-threads:4}") int parallelThreads,
            @Value("${migration.validation-enabled:true}") boolean validationEnabled) {
        this.meterRegistry = meterRegistry;
        this.batchSize = batchSize;
        this.parallelThreads = parallelThreads;
        this.validationEnabled = validationEnabled;
        this.executor = Executors.newFixedThreadPool(parallelThreads);
        
        logger.info("Data migration service initialized with batch size: {}, parallel threads: {}, validation: {}",
                batchSize, parallelThreads, validationEnabled);
    }
    
    /**
     * Migrates data from source repository to target repository.
     *
     * @param <T> Entity type
     * @param <ID> Entity ID type
     * @param sourceName Source repository name (for metrics)
     * @param targetName Target repository name (for metrics)
     * @param sourceRepo Source repository
     * @param targetRepo Target repository
     * @param validator Optional validator for data validation
     * @return Migration result with statistics
     */
    public <T, ID> MigrationResult migrateRepository(
            String sourceName,
            String targetName,
            Repository<T, ID> sourceRepo,
            Repository<T, ID> targetRepo,
            MigrationValidator<T> validator) {
        
        Timer.Sample timer = Timer.start(meterRegistry);
        MigrationResult result = new MigrationResult();
        
        try {
            logger.info("Starting migration from {} to {}", sourceName, targetName);
            
            // Get all entities from source repository
            List<T> allEntities = sourceRepo.findAll();
            result.setTotalRecords(allEntities.size());
            
            logger.info("Found {} records to migrate", allEntities.size());
            
            // Process in batches
            List<CompletableFuture<BatchResult<T>>> futures = new ArrayList<>();
            
            for (int i = 0; i < allEntities.size(); i += batchSize) {
                int end = Math.min(i + batchSize, allEntities.size());
                List<T> batch = allEntities.subList(i, end);
                
                int batchNumber = (i / batchSize) + 1;
                
                // Process batch asynchronously
                CompletableFuture<BatchResult<T>> future = CompletableFuture.supplyAsync(
                        () -> processBatch(batch, batchNumber, targetRepo, validator),
                        executor);
                
                futures.add(future);
            }
            
            // Wait for all batches to complete
            CompletableFuture.allOf(futures.toArray(new CompletableFuture[0])).join();
            
            // Collect results
            for (CompletableFuture<BatchResult<T>> future : futures) {
                BatchResult<T> batchResult = future.get();
                result.incrementSuccessCount(batchResult.getSuccessCount());
                result.incrementFailureCount(batchResult.getFailureCount());
                
                if (validationEnabled) {
                    result.addValidationIssues(batchResult.getValidationIssues());
                }
                
                result.addFailures(batchResult.getFailures());
            }
            
            result.setSuccess(true);
            
            // Record final metrics
            timer.stop(meterRegistry.timer("data.migration.duration", 
                "source", sourceName,
                "target", targetName,
                "success", String.valueOf(result.isSuccess())));
                
            meterRegistry.counter("data.migration.records.total", 
                "source", sourceName,
                "target", targetName)
                .increment(result.getTotalRecords());
                
            meterRegistry.counter("data.migration.records.success", 
                "source", sourceName,
                "target", targetName)
                .increment(result.getSuccessCount());
                
            meterRegistry.counter("data.migration.records.failure", 
                "source", sourceName,
                "target", targetName)
                .increment(result.getFailureCount());
            
            if (validationEnabled) {
                meterRegistry.counter("data.migration.records.validation_issues", 
                    "source", sourceName,
                    "target", targetName)
                    .increment(result.getValidationIssues().size());
            }
            
            logger.info("Migration completed: total={}, success={}, failures={}, validation_issues={}",
                    result.getTotalRecords(), result.getSuccessCount(), 
                    result.getFailureCount(), result.getValidationIssues().size());
                    
        } catch (Exception e) {
            logger.error("Migration failed: {}", e.getMessage(), e);
            result.setSuccess(false);
            result.setErrorMessage(e.getMessage());
            
            // Record failure metrics
            timer.stop(meterRegistry.timer("data.migration.duration", 
                "source", sourceName,
                "target", targetName,
                "success", "false"));
        }
        
        return result;
    }
    
    /**
     * Processes a batch of entities.
     *
     * @param <T> Entity type
     * @param batch The batch of entities to process
     * @param batchNumber The batch number (for logging)
     * @param targetRepo The target repository
     * @param validator Optional validator for data validation
     * @return Batch result with statistics
     */
    private <T, ID> BatchResult<T> processBatch(
            List<T> batch, 
            int batchNumber,
            Repository<T, ID> targetRepo,
            MigrationValidator<T> validator) {
        
        BatchResult<T> result = new BatchResult<>();
        
        logger.info("Processing batch #{} with {} records", batchNumber, batch.size());
        
        for (T entity : batch) {
            try {
                // Save to target repository
                targetRepo.save(entity);
                result.incrementSuccessCount();
                
                // Validate if validator is provided and validation is enabled
                if (validationEnabled && validator != null) {
                    ValidationResult validation = validator.validate(entity, entity);
                    if (!validation.isValid()) {
                        result.addValidationIssue(validation);
                    }
                }
            } catch (Exception e) {
                logger.error("Error migrating entity in batch #{}: {}", batchNumber, e.getMessage());
                result.incrementFailureCount();
                result.addFailure(entity, e);
            }
        }
        
        logger.info("Completed batch #{}: success={}, failures={}, validation_issues={}",
                batchNumber, result.getSuccessCount(), result.getFailureCount(), 
                validationEnabled ? result.getValidationIssues().size() : "N/A");
                
        return result;
    }
    
    /**
     * Validates all data between two repositories.
     *
     * @param <T> Entity type
     * @param <ID> Entity ID type
     * @param sourceName Source repository name (for metrics)
     * @param targetName Target repository name (for metrics)
     * @param sourceRepo Source repository
     * @param targetRepo Target repository
     * @param validator Validator for data validation
     * @return Validation result with statistics
     */
    public <T, ID> ValidationSummary validateRepositories(
            String sourceName,
            String targetName,
            Repository<T, ID> sourceRepo,
            Repository<T, ID> targetRepo,
            MigrationValidator<T> validator) {
        
        Timer.Sample timer = Timer.start(meterRegistry);
        ValidationSummary summary = new ValidationSummary();
        
        try {
            logger.info("Starting validation between {} and {}", sourceName, targetName);
            
            // Get all entities from source and target
            List<T> sourceEntities = sourceRepo.findAll();
            List<T> targetEntities = targetRepo.findAll();
            
            // Extract IDs using the validator's getEntityId method
            Map<String, T> sourceMap = sourceEntities.stream()
                    .collect(Collectors.toMap(
                            e -> validator.getEntityId(e).toString(),
                            e -> e));
                            
            Map<String, T> targetMap = targetEntities.stream()
                    .collect(Collectors.toMap(
                            e -> validator.getEntityId(e).toString(),
                            e -> e,
                            (e1, e2) -> e1)); // In case of duplicates, keep first
            
            // Count statistics
            summary.setSourceCount(sourceEntities.size());
            summary.setTargetCount(targetEntities.size());
            
            // Find missing in target
            List<String> missingInTarget = sourceMap.keySet().stream()
                    .filter(id -> !targetMap.containsKey(id))
                    .collect(Collectors.toList());
            
            summary.setMissingInTarget(missingInTarget.size());
            
            // Find missing in source (extras in target)
            List<String> missingInSource = targetMap.keySet().stream()
                    .filter(id -> !sourceMap.containsKey(id))
                    .collect(Collectors.toList());
                    
            summary.setMissingInSource(missingInSource.size());
            
            // Validate entities that exist in both
            List<ValidationResult> issues = new ArrayList<>();
            
            for (String id : sourceMap.keySet()) {
                if (targetMap.containsKey(id)) {
                    T sourceEntity = sourceMap.get(id);
                    T targetEntity = targetMap.get(id);
                    
                    ValidationResult result = validator.validate(sourceEntity, targetEntity);
                    if (!result.isValid()) {
                        issues.add(result);
                    }
                }
            }
            
            summary.setDifferenceCount(issues.size());
            summary.setValidationIssues(issues);
            
            // Calculate success percentage
            int commonCount = sourceMap.size() - missingInTarget.size();
            int validCount = commonCount - issues.size();
            
            if (commonCount > 0) {
                summary.setSuccessPercentage((double) validCount / commonCount * 100);
            } else {
                summary.setSuccessPercentage(0);
            }
            
            // Record metrics
            timer.stop(meterRegistry.timer("data.validation.duration", 
                "source", sourceName,
                "target", targetName));
                
            meterRegistry.gauge("data.validation.missing_in_target", 
                summary.getMissingInTarget());
                
            meterRegistry.gauge("data.validation.missing_in_source", 
                summary.getMissingInSource());
                
            meterRegistry.gauge("data.validation.differences", 
                summary.getDifferenceCount());
                
            meterRegistry.gauge("data.validation.success_percentage", 
                summary.getSuccessPercentage());
            
            logger.info("Validation completed: source={}, target={}, missing_in_target={}, " +
                         "missing_in_source={}, differences={}, success_percentage={}%",
                    summary.getSourceCount(), summary.getTargetCount(),
                    summary.getMissingInTarget(), summary.getMissingInSource(),
                    summary.getDifferenceCount(), String.format("%.2f", summary.getSuccessPercentage()));
                    
        } catch (Exception e) {
            logger.error("Validation failed: {}", e.getMessage(), e);
            summary.setErrorMessage(e.getMessage());
            
            // Record failure metrics
            timer.stop(meterRegistry.timer("data.validation.duration", 
                "source", sourceName,
                "target", targetName,
                "status", "failed"));
        }
        
        return summary;
    }
    
    /**
     * Container for batch processing results.
     */
    private static class BatchResult<T> {
        private int successCount = 0;
        private int failureCount = 0;
        private final List<ValidationResult> validationIssues = new ArrayList<>();
        private final Map<T, Exception> failures = new HashMap<>();
        
        public void incrementSuccessCount() {
            successCount++;
        }
        
        public void incrementFailureCount() {
            failureCount++;
        }
        
        public void addValidationIssue(ValidationResult issue) {
            validationIssues.add(issue);
        }
        
        public void addFailure(T entity, Exception exception) {
            failures.put(entity, exception);
        }
        
        public int getSuccessCount() {
            return successCount;
        }
        
        public int getFailureCount() {
            return failureCount;
        }
        
        public List<ValidationResult> getValidationIssues() {
            return validationIssues;
        }
        
        public Map<T, Exception> getFailures() {
            return failures;
        }
    }
}