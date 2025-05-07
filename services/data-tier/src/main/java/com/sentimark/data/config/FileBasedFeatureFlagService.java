package com.sentimark.data.config;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.io.FileInputStream;
import java.io.IOException;
import java.util.Map;
import java.util.Properties;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Implementation of FeatureFlagService that loads feature flags from a properties file.
 */
@Component
public class FileBasedFeatureFlagService implements FeatureFlagService {
    
    private static final Logger logger = LoggerFactory.getLogger(FileBasedFeatureFlagService.class);
    
    private final Map<String, Boolean> features = new ConcurrentHashMap<>();
    
    @Value("${features.config.path}")
    private String configPath;
    
    @PostConstruct
    public void init() {
        try {
            Properties props = new Properties();
            props.load(new FileInputStream(configPath));
            
            for (String key : props.stringPropertyNames()) {
                if (key.startsWith("feature.")) {
                    String featureName = key.substring("feature.".length());
                    boolean enabled = Boolean.parseBoolean(props.getProperty(key));
                    features.put(featureName, enabled);
                    logger.info("Feature flag loaded: {} = {}", featureName, enabled);
                }
            }
        } catch (IOException e) {
            logger.warn("Could not load feature flags from {}: {}", configPath, e.getMessage());
        }
    }
    
    @Override
    public boolean isEnabled(String featureName) {
        return features.getOrDefault(featureName, false);
    }
    
    @Override
    public boolean isEnabled(String featureName, Map<String, Object> context) {
        // Simple implementation ignores context for now
        return isEnabled(featureName);
    }
}