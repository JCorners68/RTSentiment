package com.sentimark.data.config;

/**
 * Extension of the FeatureFlagService that allows for modifying feature flag states.
 * This is particularly useful for rollback scenarios and administrative control.
 */
public interface MutableFeatureFlagService extends FeatureFlagService {
    
    /**
     * Enables a feature flag.
     *
     * @param featureName The name of the feature to enable
     */
    void enableFeature(String featureName);
    
    /**
     * Disables a feature flag.
     *
     * @param featureName The name of the feature to disable
     */
    void disableFeature(String featureName);
}