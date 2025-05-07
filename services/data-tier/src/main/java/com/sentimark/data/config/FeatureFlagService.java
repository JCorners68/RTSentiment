package com.sentimark.data.config;

import java.util.Map;

/**
 * Service for checking whether features are enabled.
 */
public interface FeatureFlagService {
    
    /**
     * Check if a feature is enabled.
     *
     * @param featureName the name of the feature
     * @return true if the feature is enabled, false otherwise
     */
    boolean isEnabled(String featureName);
    
    /**
     * Check if a feature is enabled, with context-specific information.
     *
     * @param featureName the name of the feature
     * @param context additional context information
     * @return true if the feature is enabled, false otherwise
     */
    boolean isEnabled(String featureName, Map<String, Object> context);
}