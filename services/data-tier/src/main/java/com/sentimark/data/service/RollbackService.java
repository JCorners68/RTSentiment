package com.sentimark.data.service;

import com.sentimark.data.config.FeatureDecisions;
import com.sentimark.data.config.MutableFeatureFlagService;
import com.sentimark.data.exception.RollbackException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Service;

import java.util.HashSet;
import java.util.Set;

/**
 * Service responsible for executing rollback procedures in case of issues with the Iceberg implementation.
 * This provides a safety mechanism to quickly revert to PostgreSQL in production.
 */
@Service
public class RollbackService {
    private final MutableFeatureFlagService featureFlagService;
    private final FeatureDecisions featureDecisions;
    private final Logger logger = LoggerFactory.getLogger(RollbackService.class);
    private final Set<String> icebergFeatures;
    
    /**
     * Creates a new RollbackService.
     *
     * @param featureFlagService The mutable feature flag service
     * @param featureDecisions Feature decision component
     */
    @Autowired
    public RollbackService(
            @Qualifier("azureAppConfigFeatureFlagService") MutableFeatureFlagService featureFlagService,
            FeatureDecisions featureDecisions) {
        this.featureFlagService = featureFlagService;
        this.featureDecisions = featureDecisions;
        
        // Initialize the set of Iceberg-related features
        this.icebergFeatures = new HashSet<>();
        icebergFeatures.add("use-iceberg-backend");
        icebergFeatures.add("use-iceberg-optimizations");
        icebergFeatures.add("use-iceberg-partitioning");
        icebergFeatures.add("use-iceberg-time-travel");
    }
    
    /**
     * Rolls back to PostgreSQL by disabling all Iceberg-related features.
     * This is an emergency procedure and should be used with caution.
     *
     * @param reason The reason for the rollback
     * @throws RollbackException If rollback fails
     */
    public void rollbackToPostgres(String reason) {
        logger.warn("EMERGENCY ROLLBACK TO POSTGRESQL INITIATED. Reason: {}", reason);
        
        try {
            // Check if we're actually using Iceberg
            if (!featureDecisions.useIcebergBackend()) {
                logger.info("Rollback not needed: Iceberg backend is not currently active");
                return;
            }
            
            // Disable all Iceberg features
            for (String feature : icebergFeatures) {
                logger.info("Disabling feature: {}", feature);
                featureFlagService.disableFeature(feature);
            }
            
            logger.info("Rollback to PostgreSQL completed successfully");
            
            // Send alert notification
            sendRollbackNotification(reason);
        } catch (Exception e) {
            String errorMessage = "Failed to complete rollback to PostgreSQL: " + e.getMessage();
            logger.error(errorMessage, e);
            throw new RollbackException(errorMessage, e);
        }
    }
    
    /**
     * Checks if the system is in a rollback state.
     *
     * @return true if the system is rolled back to PostgreSQL, false otherwise
     */
    public boolean isRolledBack() {
        return !featureDecisions.useIcebergBackend();
    }
    
    /**
     * Sends a notification about the rollback for monitoring.
     *
     * @param reason The reason for the rollback
     */
    private void sendRollbackNotification(String reason) {
        // In a real implementation, this would send alerts via monitoring systems
        logger.warn("ROLLBACK ALERT: Database backend rolled back to PostgreSQL. Reason: {}", reason);
    }
}