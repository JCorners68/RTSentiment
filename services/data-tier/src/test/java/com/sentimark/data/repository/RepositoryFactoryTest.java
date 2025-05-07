package com.sentimark.data.repository;

import com.sentimark.data.config.FeatureDecisions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.context.ApplicationContext;

import static org.junit.jupiter.api.Assertions.assertSame;
import static org.mockito.Mockito.when;

public class RepositoryFactoryTest {

    @Mock
    private FeatureDecisions featureDecisions;

    @Mock
    private ApplicationContext applicationContext;

    @Mock
    private SentimentRecordRepository postgresSentimentRepo;

    @Mock
    private SentimentRecordRepository icebergSentimentRepo;

    private RepositoryFactory repositoryFactory;

    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
        
        when(applicationContext.getBean("postgresSentimentRecordRepository", SentimentRecordRepository.class))
            .thenReturn(postgresSentimentRepo);
        
        repositoryFactory = new RepositoryFactory(featureDecisions, applicationContext);
        
        // Manually register repositories for testing
        repositoryFactory.registerRepository(
            SentimentRecordRepository.class,
            postgresSentimentRepo,
            icebergSentimentRepo
        );
    }

    @Test
    public void shouldUsePostgresRepositoryByDefault() {
        // Given
        when(featureDecisions.useIcebergBackend()).thenReturn(false);

        // When
        SentimentRecordRepository repo = repositoryFactory.getRepository(SentimentRecordRepository.class);

        // Then
        assertSame(postgresSentimentRepo, repo);
    }

    @Test
    public void shouldUseIcebergRepositoryWhenEnabled() {
        // Given
        when(featureDecisions.useIcebergBackend()).thenReturn(true);

        // When
        SentimentRecordRepository repo = repositoryFactory.getRepository(SentimentRecordRepository.class);

        // Then
        assertSame(icebergSentimentRepo, repo);
    }

    @Test
    public void shouldFallbackToPostgresWhenIcebergEnabledButNotAvailable() {
        // Given
        when(featureDecisions.useIcebergBackend()).thenReturn(true);
        
        // Create a new factory with only postgres implementations
        RepositoryFactory factoryWithoutIceberg = new RepositoryFactory(featureDecisions, applicationContext);
        factoryWithoutIceberg.registerRepository(
            SentimentRecordRepository.class,
            postgresSentimentRepo,
            null // No Iceberg implementation
        );

        // When
        SentimentRecordRepository repo = factoryWithoutIceberg.getRepository(SentimentRecordRepository.class);

        // Then
        assertSame(postgresSentimentRepo, repo);
    }
}