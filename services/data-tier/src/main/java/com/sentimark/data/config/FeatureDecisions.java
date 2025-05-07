package com.sentimark.data.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * Component for making decisions based on feature flags.
 */
@Component
public class FeatureDecisions {
    
    private final FeatureFlagService featureFlagService;
    
    @Autowired
    public FeatureDecisions(FeatureFlagService featureFlagService) {
        this.featureFlagService = featureFlagService;
    }
    
    /**
     * Check if the Iceberg backend should be used.
     *
     * @return true if the Iceberg backend should be used, false otherwise
     */
    public boolean useIcebergBackend() {
        return featureFlagService.isEnabled("use-iceberg-backend");
    }
    
    /**
     * Check if Iceberg-specific optimizations should be used.
     * This will only return true if the Iceberg backend is also enabled.
     *
     * @return true if Iceberg optimizations should be used, false otherwise
     */
    public boolean useIcebergOptimizations() {
        return useIcebergBackend() && featureFlagService.isEnabled("use-iceberg-optimizations");
    }
    
    /**
     * Check if Iceberg partitioning should be used.
     * This will only return true if the Iceberg backend is also enabled.
     *
     * @return true if Iceberg partitioning should be used, false otherwise
     */
    public boolean useIcebergPartitioning() {
        return useIcebergBackend() && featureFlagService.isEnabled("use-iceberg-partitioning");
    }
}