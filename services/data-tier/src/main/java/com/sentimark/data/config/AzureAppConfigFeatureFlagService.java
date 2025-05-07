package com.sentimark.data.config;

import com.azure.data.appconfiguration.ConfigurationClient;
import com.azure.data.appconfiguration.ConfigurationClientBuilder;
import com.azure.data.appconfiguration.models.ConfigurationSetting;
import com.azure.identity.ClientSecretCredential;
import com.azure.identity.ClientSecretCredentialBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * Azure App Configuration implementation of the FeatureFlagService.
 * Used in production to manage feature flags centrally.
 */
@Component
@Profile("production")
public class AzureAppConfigFeatureFlagService implements FeatureFlagService, MutableFeatureFlagService {
    private final ConfigurationClient client;
    private final Logger logger = LoggerFactory.getLogger(AzureAppConfigFeatureFlagService.class);
    private final Map<String, Boolean> featureCache = new ConcurrentHashMap<>();
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
    private final String label;

    /**
     * Creates a new AzureAppConfigFeatureFlagService using service principal authentication.
     *
     * @param endpoint Azure App Configuration endpoint URL
     * @param tenantId Azure tenant ID
     * @param clientId Azure client ID
     * @param clientSecret Azure client secret
     * @param label (Optional) Label to filter configurations by
     */
    @Autowired
    public AzureAppConfigFeatureFlagService(
            @Value("${azure.appconfig.endpoint}") String endpoint,
            @Value("${azure.tenant-id}") String tenantId,
            @Value("${azure.client-id}") String clientId,
            @Value("${azure.client-secret}") String clientSecret,
            @Value("${azure.appconfig.label:production}") String label) {
        
        this.label = label;
        
        // Create Azure credential
        ClientSecretCredential credential = new ClientSecretCredentialBuilder()
            .tenantId(tenantId)
            .clientId(clientId)
            .clientSecret(clientSecret)
            .build();
            
        // Build App Configuration client
        client = new ConfigurationClientBuilder()
            .credential(credential)
            .endpoint(endpoint)
            .buildClient();
            
        logger.info("Azure App Configuration feature flag service initialized with label: {}", label);
        
        // Initialize cache
        refreshCache();
        
        // Schedule periodic refresh (every 5 minutes)
        scheduler.scheduleAtFixedRate(this::refreshCache, 5, 5, TimeUnit.MINUTES);
    }
    
    /**
     * Creates a new AzureAppConfigFeatureFlagService using connection string authentication.
     *
     * @param connectionString Azure App Configuration connection string
     * @param label (Optional) Label to filter configurations by
     */
    @Autowired
    public AzureAppConfigFeatureFlagService(
            @Value("${azure.appconfig.connection-string}") String connectionString,
            @Value("${azure.appconfig.label:production}") String label) {
        
        this.label = label;
        
        // Build App Configuration client using connection string
        client = new ConfigurationClientBuilder()
            .connectionString(connectionString)
            .buildClient();
            
        logger.info("Azure App Configuration feature flag service initialized with connection string and label: {}", label);
        
        // Initialize cache
        refreshCache();
        
        // Schedule periodic refresh (every 5 minutes)
        scheduler.scheduleAtFixedRate(this::refreshCache, 5, 5, TimeUnit.MINUTES);
    }
    
    /**
     * Refreshes the local cache of feature flags from Azure App Configuration.
     */
    private synchronized void refreshCache() {
        try {
            logger.debug("Refreshing feature flag cache from Azure App Configuration");
            
            client.listConfigurationSettings(
                    setting -> setting.getLabelFilter().equals(label) &&
                              setting.getKeyFilter().startsWith("feature."))
                .forEach(setting -> {
                    String featureName = setting.getKey().substring("feature.".length());
                    boolean enabled = Boolean.parseBoolean(setting.getValue());
                    
                    // Check if value changed before logging
                    Boolean previousValue = featureCache.get(featureName);
                    if (previousValue == null || previousValue != enabled) {
                        logger.info("Feature flag updated: {} = {}", featureName, enabled);
                    }
                    
                    featureCache.put(featureName, enabled);
                });
                
            logger.debug("Feature flag cache refresh completed, {} flags loaded", featureCache.size());
        } catch (Exception e) {
            logger.error("Error refreshing feature flags from Azure App Configuration: {}", e.getMessage(), e);
        }
    }

    @Override
    public boolean isEnabled(String featureName) {
        return featureCache.getOrDefault(featureName, false);
    }

    @Override
    public boolean isEnabled(String featureName, Map<String, Object> context) {
        // Simple implementation ignores context
        // In a real implementation, you could add targeting rules based on context
        return isEnabled(featureName);
    }
    
    @Override
    public void enableFeature(String featureName) {
        setFeatureState(featureName, true);
    }
    
    @Override
    public void disableFeature(String featureName) {
        setFeatureState(featureName, false);
    }
    
    /**
     * Sets the state of a feature flag in Azure App Configuration.
     *
     * @param featureName The feature flag name
     * @param enabled The new state
     */
    private void setFeatureState(String featureName, boolean enabled) {
        try {
            logger.info("Setting feature flag {} to {}", featureName, enabled);
            
            client.setConfigurationSetting(
                    "feature." + featureName,
                    label,
                    Boolean.toString(enabled));
                    
            // Update local cache immediately
            featureCache.put(featureName, enabled);
            
            logger.info("Successfully updated feature flag {} to {}", featureName, enabled);
        } catch (Exception e) {
            logger.error("Error updating feature flag {} to {}: {}", 
                    featureName, enabled, e.getMessage(), e);
            throw new RuntimeException("Failed to update feature flag", e);
        }
    }
    
    /**
     * Shutdown hook to clean up resources.
     */
    public void shutdown() {
        scheduler.shutdown();
    }
}