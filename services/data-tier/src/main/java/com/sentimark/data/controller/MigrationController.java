package com.sentimark.data.controller;

import com.sentimark.data.migration.DataMigrationService;
import com.sentimark.data.migration.MigrationResult;
import com.sentimark.data.migration.ValidationSummary;
import com.sentimark.data.repository.MarketEventRepository;
import com.sentimark.data.repository.Repository;
import com.sentimark.data.repository.SentimentRecordRepository;
import com.sentimark.data.repository.iceberg.IcebergMarketEventRepository;
import com.sentimark.data.repository.iceberg.IcebergSentimentRecordRepository;
import com.sentimark.data.repository.postgres.PostgresMarketEventRepository;
import com.sentimark.data.repository.postgres.PostgresSentimentRecordRepository;
import com.sentimark.data.service.RollbackService;
import io.micrometer.core.annotation.Timed;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;

/**
 * REST controller for managing data migration between PostgreSQL and Iceberg.
 * This provides endpoints for initiating, monitoring, and validating migrations.
 */
@RestController
@RequestMapping("/api/v1/migration")
public class MigrationController {
    private final Logger logger = LoggerFactory.getLogger(MigrationController.class);
    private final DataMigrationService migrationService;
    private final RollbackService rollbackService;
    
    private final PostgresSentimentRecordRepository postgresSentimentRepo;
    private final IcebergSentimentRecordRepository icebergSentimentRepo;
    
    private final PostgresMarketEventRepository postgresMarketEventRepo;
    private final IcebergMarketEventRepository icebergMarketEventRepo;
    
    // Track ongoing migrations
    private final Map<String, CompletableFuture<MigrationResult>> activeMigrations = new HashMap<>();
    
    /**
     * Creates a new MigrationController.
     */
    @Autowired
    public MigrationController(
            DataMigrationService migrationService,
            RollbackService rollbackService,
            @Qualifier("postgresSentimentRecordRepository") PostgresSentimentRecordRepository postgresSentimentRepo,
            @Qualifier("icebergSentimentRecordRepository") IcebergSentimentRecordRepository icebergSentimentRepo,
            @Qualifier("postgresMarketEventRepository") PostgresMarketEventRepository postgresMarketEventRepo,
            @Qualifier("icebergMarketEventRepository") IcebergMarketEventRepository icebergMarketEventRepo) {
        this.migrationService = migrationService;
        this.rollbackService = rollbackService;
        this.postgresSentimentRepo = postgresSentimentRepo;
        this.icebergSentimentRepo = icebergSentimentRepo;
        this.postgresMarketEventRepo = postgresMarketEventRepo;
        this.icebergMarketEventRepo = icebergMarketEventRepo;
    }
    
    /**
     * Starts migration of SentimentRecord entities from PostgreSQL to Iceberg.
     *
     * @return the migration job ID
     */
    @PostMapping("/sentiment-records/postgres-to-iceberg")
    @Timed(value = "migration.sentiment.postgres_to_iceberg", description = "Time taken to migrate sentiment records from PostgreSQL to Iceberg")
    public ResponseEntity<Map<String, String>> migrateSentimentRecords() {
        logger.info("Starting sentiment records migration from PostgreSQL to Iceberg");
        
        String jobId = UUID.randomUUID().toString();
        
        // Start migration in background
        CompletableFuture<MigrationResult> future = CompletableFuture.supplyAsync(() -> 
            migrationService.migrateRepository(
                "postgres-sentiment",
                "iceberg-sentiment",
                postgresSentimentRepo,
                icebergSentimentRepo,
                new SentimentRecordValidator()
            )
        );
        
        // Store reference to the migration job
        activeMigrations.put(jobId, future);
        
        // Return job ID to client
        Map<String, String> response = new HashMap<>();
        response.put("jobId", jobId);
        response.put("status", "started");
        response.put("entityType", "sentimentRecord");
        response.put("source", "postgres");
        response.put("target", "iceberg");
        
        return ResponseEntity.accepted().body(response);
    }
    
    /**
     * Starts migration of MarketEvent entities from PostgreSQL to Iceberg.
     *
     * @return the migration job ID
     */
    @PostMapping("/market-events/postgres-to-iceberg")
    @Timed(value = "migration.market_events.postgres_to_iceberg", description = "Time taken to migrate market events from PostgreSQL to Iceberg")
    public ResponseEntity<Map<String, String>> migrateMarketEvents() {
        logger.info("Starting market events migration from PostgreSQL to Iceberg");
        
        String jobId = UUID.randomUUID().toString();
        
        // Start migration in background
        CompletableFuture<MigrationResult> future = CompletableFuture.supplyAsync(() -> 
            migrationService.migrateRepository(
                "postgres-market-events",
                "iceberg-market-events",
                postgresMarketEventRepo,
                icebergMarketEventRepo,
                new MarketEventValidator()
            )
        );
        
        // Store reference to the migration job
        activeMigrations.put(jobId, future);
        
        // Return job ID to client
        Map<String, String> response = new HashMap<>();
        response.put("jobId", jobId);
        response.put("status", "started");
        response.put("entityType", "marketEvent");
        response.put("source", "postgres");
        response.put("target", "iceberg");
        
        return ResponseEntity.accepted().body(response);
    }
    
    /**
     * Gets the status of a migration job.
     *
     * @param jobId the migration job ID
     * @return the job status
     */
    @GetMapping("/status/{jobId}")
    public ResponseEntity<?> getMigrationStatus(@PathVariable String jobId) {
        logger.info("Getting status for migration job: {}", jobId);
        
        CompletableFuture<MigrationResult> future = activeMigrations.get(jobId);
        
        if (future == null) {
            return ResponseEntity.notFound().build();
        }
        
        if (future.isDone()) {
            try {
                MigrationResult result = future.get();
                
                // Remove completed job from active migrations
                activeMigrations.remove(jobId);
                
                return ResponseEntity.ok(result);
            } catch (Exception e) {
                logger.error("Error getting migration result: {}", e.getMessage(), e);
                
                Map<String, String> response = new HashMap<>();
                response.put("jobId", jobId);
                response.put("status", "failed");
                response.put("error", e.getMessage());
                
                return ResponseEntity.internalServerError().body(response);
            }
        } else {
            Map<String, String> response = new HashMap<>();
            response.put("jobId", jobId);
            response.put("status", "in_progress");
            
            return ResponseEntity.ok(response);
        }
    }
    
    /**
     * Validates SentimentRecord entities between PostgreSQL and Iceberg.
     *
     * @return validation summary
     */
    @GetMapping("/validate/sentiment-records")
    @Timed(value = "validation.sentiment_records", description = "Time taken to validate sentiment records between PostgreSQL and Iceberg")
    public ResponseEntity<ValidationSummary> validateSentimentRecords() {
        logger.info("Validating sentiment records between PostgreSQL and Iceberg");
        
        ValidationSummary summary = migrationService.validateRepositories(
            "postgres-sentiment",
            "iceberg-sentiment",
            postgresSentimentRepo,
            icebergSentimentRepo,
            new SentimentRecordValidator()
        );
        
        return ResponseEntity.ok(summary);
    }
    
    /**
     * Validates MarketEvent entities between PostgreSQL and Iceberg.
     *
     * @return validation summary
     */
    @GetMapping("/validate/market-events")
    @Timed(value = "validation.market_events", description = "Time taken to validate market events between PostgreSQL and Iceberg")
    public ResponseEntity<ValidationSummary> validateMarketEvents() {
        logger.info("Validating market events between PostgreSQL and Iceberg");
        
        ValidationSummary summary = migrationService.validateRepositories(
            "postgres-market-events",
            "iceberg-market-events",
            postgresMarketEventRepo,
            icebergMarketEventRepo,
            new MarketEventValidator()
        );
        
        return ResponseEntity.ok(summary);
    }
    
    /**
     * Executes rollback to PostgreSQL.
     *
     * @param request the rollback request
     * @return success response
     */
    @PostMapping("/rollback")
    @Timed(value = "rollback.to_postgres", description = "Time taken to roll back to PostgreSQL")
    public ResponseEntity<Map<String, String>> rollbackToPostgres(@RequestBody RollbackRequest request) {
        logger.warn("Rollback to PostgreSQL requested. Reason: {}", request.getReason());
        
        rollbackService.rollbackToPostgres(request.getReason());
        
        Map<String, String> response = new HashMap<>();
        response.put("status", "success");
        response.put("message", "Rolled back to PostgreSQL");
        
        return ResponseEntity.ok(response);
    }
    
    /**
     * Rollback request DTO.
     */
    public static class RollbackRequest {
        private String reason;
        
        public String getReason() {
            return reason;
        }
        
        public void setReason(String reason) {
            this.reason = reason;
        }
    }
    
    /**
     * SentimentRecord validator implementation.
     */
    private static class SentimentRecordValidator implements com.sentimark.data.migration.MigrationValidator<com.sentimark.data.model.SentimentRecord> {
        @Override
        public com.sentimark.data.migration.ValidationResult validate(
                com.sentimark.data.model.SentimentRecord source, 
                com.sentimark.data.model.SentimentRecord target) {
            
            com.sentimark.data.migration.ValidationResult result = 
                new com.sentimark.data.migration.ValidationResult(source.getId().toString());
            
            // Compare all relevant fields
            if (!source.getTicker().equals(target.getTicker())) {
                result.addIssue("Ticker mismatch: " + source.getTicker() + " vs " + target.getTicker());
            }
            
            if (Math.abs(source.getSentimentScore() - target.getSentimentScore()) > 0.000001) {
                result.addIssue("Sentiment score mismatch: " + source.getSentimentScore() + " vs " + target.getSentimentScore());
            }
            
            if (!source.getTimestamp().equals(target.getTimestamp())) {
                result.addIssue("Timestamp mismatch: " + source.getTimestamp() + " vs " + target.getTimestamp());
            }
            
            if (!source.getSource().equals(target.getSource())) {
                result.addIssue("Source mismatch: " + source.getSource() + " vs " + target.getSource());
            }
            
            // Compare attributes map (if present)
            if (source.getAttributes() != null && target.getAttributes() != null) {
                if (source.getAttributes().size() != target.getAttributes().size()) {
                    result.addIssue("Attributes size mismatch: " + source.getAttributes().size() + 
                                    " vs " + target.getAttributes().size());
                } else {
                    for (Map.Entry<String, Double> entry : source.getAttributes().entrySet()) {
                        Double targetValue = target.getAttributes().get(entry.getKey());
                        
                        if (targetValue == null) {
                            result.addIssue("Missing attribute in target: " + entry.getKey());
                        } else if (Math.abs(entry.getValue() - targetValue) > 0.000001) {
                            result.addIssue("Attribute value mismatch for " + entry.getKey() + ": " + 
                                            entry.getValue() + " vs " + targetValue);
                        }
                    }
                }
            } else if (source.getAttributes() != null || target.getAttributes() != null) {
                result.addIssue("Attributes presence mismatch: one is null, the other is not");
            }
            
            return result;
        }
        
        @Override
        public Object getEntityId(com.sentimark.data.model.SentimentRecord entity) {
            return entity.getId();
        }
    }
    
    /**
     * MarketEvent validator implementation.
     */
    private static class MarketEventValidator implements com.sentimark.data.migration.MigrationValidator<com.sentimark.data.model.MarketEvent> {
        @Override
        public com.sentimark.data.migration.ValidationResult validate(
                com.sentimark.data.model.MarketEvent source, 
                com.sentimark.data.model.MarketEvent target) {
            
            com.sentimark.data.migration.ValidationResult result = 
                new com.sentimark.data.migration.ValidationResult(source.getId().toString());
            
            // Compare all relevant fields
            if (!source.getHeadline().equals(target.getHeadline())) {
                result.addIssue("Headline mismatch: " + source.getHeadline() + " vs " + target.getHeadline());
            }
            
            // Compare tickers list
            if (source.getTickers().size() != target.getTickers().size()) {
                result.addIssue("Tickers size mismatch: " + source.getTickers().size() + 
                                " vs " + target.getTickers().size());
            } else {
                for (String ticker : source.getTickers()) {
                    if (!target.getTickers().contains(ticker)) {
                        result.addIssue("Missing ticker in target: " + ticker);
                    }
                }
            }
            
            // Compare content (if present)
            if (source.getContent() != null && target.getContent() != null) {
                if (!source.getContent().equals(target.getContent())) {
                    result.addIssue("Content mismatch");
                }
            } else if (source.getContent() != null || target.getContent() != null) {
                result.addIssue("Content presence mismatch: one is null, the other is not");
            }
            
            if (!source.getPublishedAt().equals(target.getPublishedAt())) {
                result.addIssue("Published date mismatch: " + source.getPublishedAt() + 
                                " vs " + target.getPublishedAt());
            }
            
            if (!source.getSource().equals(target.getSource())) {
                result.addIssue("Source mismatch: " + source.getSource() + " vs " + target.getSource());
            }
            
            if (Math.abs(source.getCredibilityScore() - target.getCredibilityScore()) > 0.000001) {
                result.addIssue("Credibility score mismatch: " + source.getCredibilityScore() + 
                                " vs " + target.getCredibilityScore());
            }
            
            return result;
        }
        
        @Override
        public Object getEntityId(com.sentimark.data.model.MarketEvent entity) {
            return entity.getId();
        }
    }
}