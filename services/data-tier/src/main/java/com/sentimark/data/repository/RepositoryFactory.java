package com.sentimark.data.repository;

import com.sentimark.data.config.FeatureDecisions;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.ApplicationContext;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;
import java.util.HashMap;
import java.util.Map;

/**
 * Factory for creating repository instances based on feature flags.
 */
@Component
public class RepositoryFactory {
    
    private static final Logger logger = LoggerFactory.getLogger(RepositoryFactory.class);
    
    private final Map<Class<?>, Object> postgresRepositories = new HashMap<>();
    private final Map<Class<?>, Object> icebergRepositories = new HashMap<>();
    private final FeatureDecisions featureDecisions;
    private final ApplicationContext applicationContext;
    
    @Autowired
    public RepositoryFactory(FeatureDecisions featureDecisions, ApplicationContext applicationContext) {
        this.featureDecisions = featureDecisions;
        this.applicationContext = applicationContext;
    }
    
    @PostConstruct
    public void init() {
        // Register SentimentRecordRepository implementations
        try {
            SentimentRecordRepository postgresImpl = applicationContext.getBean(
                "postgresSentimentRecordRepository", 
                SentimentRecordRepository.class
            );
            
            // Try to get Iceberg implementation if available
            SentimentRecordRepository icebergImpl = null;
            try {
                icebergImpl = applicationContext.getBean(
                    "icebergSentimentRecordRepository",
                    SentimentRecordRepository.class
                );
                logger.info("Found Iceberg implementation for SentimentRecordRepository");
            } catch (Exception e) {
                logger.debug("Iceberg implementation for SentimentRecordRepository not available");
            }
            
            registerRepository(
                SentimentRecordRepository.class,
                postgresImpl,
                icebergImpl
            );
            logger.info("Registered PostgreSQL implementation for SentimentRecordRepository");
        } catch (Exception e) {
            logger.error("Error registering SentimentRecordRepository", e);
        }
        
        // Register MarketEventRepository implementations
        try {
            MarketEventRepository postgresImpl = applicationContext.getBean(
                "postgresMarketEventRepository", 
                MarketEventRepository.class
            );
            
            // Try to get Iceberg implementation if available
            MarketEventRepository icebergImpl = null;
            try {
                icebergImpl = applicationContext.getBean(
                    "icebergMarketEventRepository",
                    MarketEventRepository.class
                );
                logger.info("Found Iceberg implementation for MarketEventRepository");
            } catch (Exception e) {
                logger.debug("Iceberg implementation for MarketEventRepository not available");
            }
            
            registerRepository(
                MarketEventRepository.class,
                postgresImpl,
                icebergImpl
            );
            logger.info("Registered PostgreSQL implementation for MarketEventRepository");
        } catch (Exception e) {
            logger.error("Error registering MarketEventRepository", e);
        }
    }
    
    /**
     * Register repository implementations.
     *
     * @param repositoryInterface the repository interface
     * @param postgresImplementation the PostgreSQL implementation
     * @param icebergImplementation the Iceberg implementation
     * @param <T> the repository type
     */
    public <T> void registerRepository(
            Class<T> repositoryInterface,
            T postgresImplementation,
            T icebergImplementation) {
        if (postgresImplementation != null) {
            postgresRepositories.put(repositoryInterface, postgresImplementation);
        }
        if (icebergImplementation != null) {
            icebergRepositories.put(repositoryInterface, icebergImplementation);
        }
    }
    
    /**
     * Get the appropriate repository implementation based on feature flags.
     *
     * @param repositoryInterface the repository interface
     * @param <T> the repository type
     * @return the repository implementation
     */
    @SuppressWarnings("unchecked")
    public <T> T getRepository(Class<T> repositoryInterface) {
        if (featureDecisions.useIcebergBackend() && icebergRepositories.containsKey(repositoryInterface)) {
            logger.debug("Using Iceberg implementation for {}", repositoryInterface.getSimpleName());
            return (T) icebergRepositories.get(repositoryInterface);
        } else {
            logger.debug("Using PostgreSQL implementation for {}", repositoryInterface.getSimpleName());
            return (T) postgresRepositories.get(repositoryInterface);
        }
    }
}