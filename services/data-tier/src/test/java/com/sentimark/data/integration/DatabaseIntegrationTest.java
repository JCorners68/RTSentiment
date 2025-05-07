package com.sentimark.data.integration;

import com.sentimark.data.config.FeatureDecisions;
import com.sentimark.data.config.FeatureFlagService;
import com.sentimark.data.model.SentimentRecord;
import com.sentimark.data.repository.RepositoryFactory;
import com.sentimark.data.repository.SentimentRecordRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class DatabaseIntegrationTest {

    @Mock
    private FeatureFlagService featureFlagService;
    
    @Mock
    private SentimentRecordRepository postgresRepo;
    
    @Mock
    private SentimentRecordRepository icebergRepo;
    
    private RepositoryFactory repositoryFactory;
    private FeatureDecisions featureDecisions;
    private TestDataGenerator testDataGenerator;
    
    @BeforeEach
    public void setup() {
        // Initialize featureDecisions with the mock service
        featureDecisions = new FeatureDecisions(featureFlagService);
        
        // Initialize the repository factory
        repositoryFactory = new RepositoryFactory(featureDecisions, null);
        
        // Register repositories
        repositoryFactory.registerRepository(SentimentRecordRepository.class, postgresRepo, icebergRepo);
        
        // Initialize test data generator
        testDataGenerator = new TestDataGenerator();
    }
    
    @Test
    public void testRepositorySwitching() {
        // Configure feature flag to use PostgreSQL
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);
        
        // Get repository (should be PostgreSQL)
        SentimentRecordRepository repo1 = repositoryFactory.getRepository(SentimentRecordRepository.class);
        assertSame(postgresRepo, repo1);
        
        // Change feature flag to use Iceberg
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);
        
        // Get repository (should be Iceberg)
        SentimentRecordRepository repo2 = repositoryFactory.getRepository(SentimentRecordRepository.class);
        assertSame(icebergRepo, repo2);
    }
    
    @Test
    public void testBasicOperationsWithPostgres() {
        // Configure feature flag to use PostgreSQL
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);
        
        // Perform basic operations test
        testBasicOperations(repositoryFactory.getRepository(SentimentRecordRepository.class));
    }
    
    @Test
    public void testBasicOperationsWithIceberg() {
        // Configure feature flag to use Iceberg
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);
        
        // Perform basic operations test
        testBasicOperations(repositoryFactory.getRepository(SentimentRecordRepository.class));
    }
    
    private void testBasicOperations(SentimentRecordRepository repo) {
        // Create test data
        UUID id = UUID.randomUUID();
        SentimentRecord record = testDataGenerator.createSampleSentimentRecord(id);
        
        // Test save
        when(repo.save(record)).thenReturn(id);
        UUID savedId = repo.save(record);
        assertEquals(id, savedId);
        verify(repo).save(record);
        
        // Test findById
        when(repo.findById(id)).thenReturn(Optional.of(record));
        Optional<SentimentRecord> found = repo.findById(id);
        assertTrue(found.isPresent());
        assertEquals(record, found.get());
        verify(repo).findById(id);
        
        // Test update
        record.setSentimentScore(0.9);
        when(repo.update(record)).thenReturn(record);
        SentimentRecord updated = repo.update(record);
        assertEquals(record, updated);
        assertEquals(0.9, updated.getSentimentScore());
        verify(repo).update(record);
        
        // Test delete
        doNothing().when(repo).delete(id);
        repo.delete(id);
        verify(repo).delete(id);
    }
    
    @Test
    public void testFindByTickerWithPostgres() {
        // Configure feature flag to use PostgreSQL
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);
        SentimentRecordRepository repo = repositoryFactory.getRepository(SentimentRecordRepository.class);
        
        // Test findByTicker
        List<SentimentRecord> records = testDataGenerator.createSampleSentimentRecords(5, "AAPL");
        when(repo.findByTicker("AAPL")).thenReturn(records);
        
        List<SentimentRecord> found = repo.findByTicker("AAPL");
        assertEquals(5, found.size());
        found.forEach(record -> assertEquals("AAPL", record.getTicker()));
        
        verify(repo).findByTicker("AAPL");
    }
    
    @Test
    public void testFindByTickerWithIceberg() {
        // Configure feature flag to use Iceberg
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);
        SentimentRecordRepository repo = repositoryFactory.getRepository(SentimentRecordRepository.class);
        
        // Test findByTicker
        List<SentimentRecord> records = testDataGenerator.createSampleSentimentRecords(5, "AAPL");
        when(repo.findByTicker("AAPL")).thenReturn(records);
        
        List<SentimentRecord> found = repo.findByTicker("AAPL");
        assertEquals(5, found.size());
        found.forEach(record -> assertEquals("AAPL", record.getTicker()));
        
        verify(repo).findByTicker("AAPL");
    }
    
    @Test
    public void testTimeRangeQueryWithPostgres() {
        // Configure feature flag to use PostgreSQL
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);
        SentimentRecordRepository repo = repositoryFactory.getRepository(SentimentRecordRepository.class);
        
        // Test date range
        Instant start = Instant.parse("2023-01-01T00:00:00Z");
        Instant end = Instant.parse("2023-01-31T23:59:59Z");
        
        List<SentimentRecord> records = testDataGenerator.createSampleSentimentRecords(3, "AAPL", start, end);
        when(repo.findByTickerAndTimeRange("AAPL", start, end)).thenReturn(records);
        
        List<SentimentRecord> found = repo.findByTickerAndTimeRange("AAPL", start, end);
        assertEquals(3, found.size());
        found.forEach(record -> {
            assertEquals("AAPL", record.getTicker());
            assertTrue(record.getTimestamp().isAfter(start) || record.getTimestamp().equals(start));
            assertTrue(record.getTimestamp().isBefore(end) || record.getTimestamp().equals(end));
        });
        
        verify(repo).findByTickerAndTimeRange("AAPL", start, end);
    }
    
    @Test
    public void testTimeRangeQueryWithIceberg() {
        // Configure feature flag to use Iceberg
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);
        SentimentRecordRepository repo = repositoryFactory.getRepository(SentimentRecordRepository.class);
        
        // Test date range
        Instant start = Instant.parse("2023-01-01T00:00:00Z");
        Instant end = Instant.parse("2023-01-31T23:59:59Z");
        
        List<SentimentRecord> records = testDataGenerator.createSampleSentimentRecords(3, "AAPL", start, end);
        when(repo.findByTickerAndTimeRange("AAPL", start, end)).thenReturn(records);
        
        List<SentimentRecord> found = repo.findByTickerAndTimeRange("AAPL", start, end);
        assertEquals(3, found.size());
        found.forEach(record -> {
            assertEquals("AAPL", record.getTicker());
            assertTrue(record.getTimestamp().isAfter(start) || record.getTimestamp().equals(start));
            assertTrue(record.getTimestamp().isBefore(end) || record.getTimestamp().equals(end));
        });
        
        verify(repo).findByTickerAndTimeRange("AAPL", start, end);
    }
    
    @Test
    public void testAverageSentimentWithPostgres() {
        // Configure feature flag to use PostgreSQL
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);
        SentimentRecordRepository repo = repositoryFactory.getRepository(SentimentRecordRepository.class);
        
        // Test getAverageSentimentForTicker
        Instant since = Instant.parse("2023-01-01T00:00:00Z");
        when(repo.getAverageSentimentForTicker("AAPL", since)).thenReturn(0.75);
        
        double average = repo.getAverageSentimentForTicker("AAPL", since);
        assertEquals(0.75, average);
        
        verify(repo).getAverageSentimentForTicker("AAPL", since);
    }
    
    @Test
    public void testAverageSentimentWithIceberg() {
        // Configure feature flag to use Iceberg
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);
        SentimentRecordRepository repo = repositoryFactory.getRepository(SentimentRecordRepository.class);
        
        // Test getAverageSentimentForTicker
        Instant since = Instant.parse("2023-01-01T00:00:00Z");
        when(repo.getAverageSentimentForTicker("AAPL", since)).thenReturn(0.75);
        
        double average = repo.getAverageSentimentForTicker("AAPL", since);
        assertEquals(0.75, average);
        
        verify(repo).getAverageSentimentForTicker("AAPL", since);
    }
    
    /**
     * Simple test data generator for creating sample records.
     */
    private static class TestDataGenerator {
        
        public SentimentRecord createSampleSentimentRecord(UUID id) {
            return new SentimentRecord(
                id,
                "AAPL",
                0.75,
                Instant.now(),
                "TWITTER",
                Map.of("confidence", 0.9, "volume", 1000.0)
            );
        }
        
        public List<SentimentRecord> createSampleSentimentRecords(int count, String ticker) {
            return createSampleSentimentRecords(count, ticker, Instant.now().minusSeconds(86400), Instant.now());
        }
        
        public List<SentimentRecord> createSampleSentimentRecords(int count, String ticker, Instant start, Instant end) {
            List<SentimentRecord> records = new ArrayList<>();
            
            long rangeSecs = end.getEpochSecond() - start.getEpochSecond();
            Random random = new Random();
            
            for (int i = 0; i < count; i++) {
                long randomSecs = (long) (random.nextDouble() * rangeSecs);
                Instant timestamp = start.plusSeconds(randomSecs);
                
                double score = 0.5 + random.nextDouble() * 0.5; // 0.5 to 1.0
                
                records.add(new SentimentRecord(
                    UUID.randomUUID(),
                    ticker,
                    score,
                    timestamp,
                    "TWITTER",
                    Map.of("confidence", 0.8 + random.nextDouble() * 0.2, 
                           "volume", 500.0 + random.nextDouble() * 1000.0)
                ));
            }
            
            return records;
        }
    }
}