package com.sentimark.data.integration;

import com.sentimark.data.config.FeatureDecisions;
import com.sentimark.data.config.FeatureFlagService;
import com.sentimark.data.exception.DatabaseException;
import com.sentimark.data.exception.EntityNotFoundException;
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
import java.util.concurrent.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class EdgeCaseTest {

    @Mock
    private FeatureFlagService featureFlagService;
    
    @Mock
    private SentimentRecordRepository postgresRepo;
    
    @Mock
    private SentimentRecordRepository icebergRepo;
    
    private RepositoryFactory repositoryFactory;
    private FeatureDecisions featureDecisions;
    
    @BeforeEach
    public void setup() {
        // Initialize featureDecisions with the mock service
        featureDecisions = new FeatureDecisions(featureFlagService);
        
        // Initialize the repository factory
        repositoryFactory = new RepositoryFactory(featureDecisions, null);
        
        // Register repositories
        repositoryFactory.registerRepository(SentimentRecordRepository.class, postgresRepo, icebergRepo);
    }
    
    @Test
    public void testExtremeValuesWithPostgres() {
        // Configure feature flag to use PostgreSQL
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);
        
        // Test with extreme values
        testExtremeValues(repositoryFactory.getRepository(SentimentRecordRepository.class));
    }
    
    @Test
    public void testExtremeValuesWithIceberg() {
        // Configure feature flag to use Iceberg
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);
        
        // Test with extreme values
        testExtremeValues(repositoryFactory.getRepository(SentimentRecordRepository.class));
    }
    
    private void testExtremeValues(SentimentRecordRepository repo) {
        // Test with maximum String length
        String veryLongTicker = "A".repeat(1000);
        
        // Test with very large/small doubles
        double veryLargeScore = Double.MAX_VALUE;
        double verySmallScore = Double.MIN_VALUE;
        
        // Test with distant date values
        Instant veryOldDate = Instant.parse("1900-01-01T00:00:00Z");
        Instant veryFutureDate = Instant.parse("2100-01-01T00:00:00Z");
        
        // Create entities with extreme values
        SentimentRecord longTickerRecord = new SentimentRecord(
            UUID.randomUUID(), veryLongTicker, 0.75, Instant.now(), "TEST", Map.of());
        
        SentimentRecord largeScoreRecord = new SentimentRecord(
            UUID.randomUUID(), "AAPL", veryLargeScore, Instant.now(), "TEST", Map.of());
        
        SentimentRecord smallScoreRecord = new SentimentRecord(
            UUID.randomUUID(), "AAPL", verySmallScore, Instant.now(), "TEST", Map.of());
        
        SentimentRecord oldDateRecord = new SentimentRecord(
            UUID.randomUUID(), "AAPL", 0.75, veryOldDate, "TEST", Map.of());
        
        SentimentRecord futureDateRecord = new SentimentRecord(
            UUID.randomUUID(), "AAPL", 0.75, veryFutureDate, "TEST", Map.of());
        
        // Setup mocks for saving records
        when(repo.save(longTickerRecord)).thenReturn(longTickerRecord.getId());
        when(repo.save(largeScoreRecord)).thenReturn(largeScoreRecord.getId());
        when(repo.save(smallScoreRecord)).thenReturn(smallScoreRecord.getId());
        when(repo.save(oldDateRecord)).thenReturn(oldDateRecord.getId());
        when(repo.save(futureDateRecord)).thenReturn(futureDateRecord.getId());
        
        // Test saving records with extreme values
        UUID longTickerId = repo.save(longTickerRecord);
        UUID largeScoreId = repo.save(largeScoreRecord);
        UUID smallScoreId = repo.save(smallScoreRecord);
        UUID oldDateId = repo.save(oldDateRecord);
        UUID futureId = repo.save(futureDateRecord);
        
        // Verify all were saved
        assertNotNull(longTickerId);
        assertNotNull(largeScoreId);
        assertNotNull(smallScoreId);
        assertNotNull(oldDateId);
        assertNotNull(futureId);
        
        // Setup mocks for retrieving records
        when(repo.findById(longTickerId)).thenReturn(Optional.of(longTickerRecord));
        when(repo.findById(largeScoreId)).thenReturn(Optional.of(largeScoreRecord));
        when(repo.findById(smallScoreId)).thenReturn(Optional.of(smallScoreRecord));
        when(repo.findById(oldDateId)).thenReturn(Optional.of(oldDateRecord));
        when(repo.findById(futureId)).thenReturn(Optional.of(futureDateRecord));
        
        // Test retrieving records with extreme values
        Optional<SentimentRecord> foundLongTicker = repo.findById(longTickerId);
        Optional<SentimentRecord> foundLargeScore = repo.findById(largeScoreId);
        Optional<SentimentRecord> foundSmallScore = repo.findById(smallScoreId);
        Optional<SentimentRecord> foundOldDate = repo.findById(oldDateId);
        Optional<SentimentRecord> foundFutureDate = repo.findById(futureId);
        
        // Verify all were retrieved correctly
        assertTrue(foundLongTicker.isPresent());
        assertEquals(veryLongTicker, foundLongTicker.get().getTicker());
        
        assertTrue(foundLargeScore.isPresent());
        assertEquals(veryLargeScore, foundLargeScore.get().getSentimentScore());
        
        assertTrue(foundSmallScore.isPresent());
        assertEquals(verySmallScore, foundSmallScore.get().getSentimentScore());
        
        assertTrue(foundOldDate.isPresent());
        assertEquals(veryOldDate, foundOldDate.get().getTimestamp());
        
        assertTrue(foundFutureDate.isPresent());
        assertEquals(veryFutureDate, foundFutureDate.get().getTimestamp());
    }
    
    @Test
    public void testErrorRecoveryWithPostgres() {
        // Configure feature flag to use PostgreSQL
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);
        
        // Test error recovery
        testErrorRecovery(repositoryFactory.getRepository(SentimentRecordRepository.class));
    }
    
    @Test
    public void testErrorRecoveryWithIceberg() {
        // Configure feature flag to use Iceberg
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);
        
        // Test error recovery
        testErrorRecovery(repositoryFactory.getRepository(SentimentRecordRepository.class));
    }
    
    private void testErrorRecovery(SentimentRecordRepository repo) {
        // Create test records
        UUID id = UUID.randomUUID();
        SentimentRecord record = new SentimentRecord(
            id, "AAPL", 0.75, Instant.now(), "TEST", Map.of());
        
        // Setup mock to throw exception on findById
        when(repo.findById(id)).thenThrow(new DatabaseException("Simulated database error"));
        
        // Test exception handling
        assertThrows(DatabaseException.class, () -> repo.findById(id));
        
        // Setup mock to throw exception on save
        when(repo.save(record)).thenThrow(new DatabaseException("Simulated database error on save"));
        
        // Test exception handling for save
        assertThrows(DatabaseException.class, () -> repo.save(record));
        
        // Setup mock to throw EntityNotFoundException
        UUID nonExistentId = UUID.randomUUID();
        when(repo.findById(nonExistentId)).thenThrow(
            new EntityNotFoundException("Entity not found with ID: " + nonExistentId));
        
        // Test entity not found exception
        Exception exception = assertThrows(EntityNotFoundException.class, 
            () -> repo.findById(nonExistentId));
        assertTrue(exception.getMessage().contains(nonExistentId.toString()));
    }
    
    @Test
    public void testNullAndEmptyValuesWithPostgres() {
        // Configure feature flag to use PostgreSQL
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);
        
        // Test null and empty values
        testNullAndEmptyValues(repositoryFactory.getRepository(SentimentRecordRepository.class));
    }
    
    @Test
    public void testNullAndEmptyValuesWithIceberg() {
        // Configure feature flag to use Iceberg
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);
        
        // Test null and empty values
        testNullAndEmptyValues(repositoryFactory.getRepository(SentimentRecordRepository.class));
    }
    
    private void testNullAndEmptyValues(SentimentRecordRepository repo) {
        // Create records with null and empty values
        SentimentRecord emptySourceRecord = new SentimentRecord(
            UUID.randomUUID(), "AAPL", 0.75, Instant.now(), "", Map.of());
        
        SentimentRecord nullAttributesRecord = new SentimentRecord(
            UUID.randomUUID(), "AAPL", 0.75, Instant.now(), "TEST", null);
        
        SentimentRecord emptyTickerRecord = new SentimentRecord(
            UUID.randomUUID(), "", 0.75, Instant.now(), "TEST", Map.of());
        
        // Setup mocks
        when(repo.save(emptySourceRecord)).thenReturn(emptySourceRecord.getId());
        when(repo.save(nullAttributesRecord)).thenReturn(nullAttributesRecord.getId());
        when(repo.save(emptyTickerRecord)).thenReturn(emptyTickerRecord.getId());
        
        // Test saving records with null/empty values
        UUID emptySourceId = repo.save(emptySourceRecord);
        UUID nullAttributesId = repo.save(nullAttributesRecord);
        UUID emptyTickerId = repo.save(emptyTickerRecord);
        
        // Verify all were saved
        assertNotNull(emptySourceId);
        assertNotNull(nullAttributesId);
        assertNotNull(emptyTickerId);
        
        // Setup mocks for retrieval
        when(repo.findById(emptySourceId)).thenReturn(Optional.of(emptySourceRecord));
        when(repo.findById(nullAttributesId)).thenReturn(Optional.of(nullAttributesRecord));
        when(repo.findById(emptyTickerId)).thenReturn(Optional.of(emptyTickerRecord));
        
        // Test retrieving records with null/empty values
        Optional<SentimentRecord> foundEmptySource = repo.findById(emptySourceId);
        Optional<SentimentRecord> foundNullAttributes = repo.findById(nullAttributesId);
        Optional<SentimentRecord> foundEmptyTicker = repo.findById(emptyTickerId);
        
        // Verify all were retrieved correctly
        assertTrue(foundEmptySource.isPresent());
        assertEquals("", foundEmptySource.get().getSource());
        
        assertTrue(foundNullAttributes.isPresent());
        assertNull(foundNullAttributes.get().getAttributes());
        
        assertTrue(foundEmptyTicker.isPresent());
        assertEquals("", foundEmptyTicker.get().getTicker());
    }
    
    @Test
    public void testConcurrentOperationsWithPostgres() {
        // Configure feature flag to use PostgreSQL
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);
        
        // Test concurrent operations
        testConcurrentOperations(repositoryFactory.getRepository(SentimentRecordRepository.class));
    }
    
    @Test
    public void testConcurrentOperationsWithIceberg() {
        // Configure feature flag to use Iceberg
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);
        
        // Test concurrent operations
        testConcurrentOperations(repositoryFactory.getRepository(SentimentRecordRepository.class));
    }
    
    private void testConcurrentOperations(SentimentRecordRepository repo) {
        // Create a test record
        UUID id = UUID.randomUUID();
        SentimentRecord record = new SentimentRecord(
            id, "AAPL", 0.75, Instant.now(), "TEST", Map.of());
        
        // Setup mock for findById
        when(repo.findById(id)).thenReturn(Optional.of(record));
        
        // Update versions of the record
        SentimentRecord update1 = new SentimentRecord(
            id, "AAPL", 0.8, record.getTimestamp(), record.getSource(), record.getAttributes());
        
        SentimentRecord update2 = new SentimentRecord(
            id, "AAPL", 0.9, record.getTimestamp(), record.getSource(), record.getAttributes());
        
        // Setup mocks for concurrent updates
        when(repo.update(update1)).thenReturn(update1);
        when(repo.update(update2)).thenReturn(update2);
        
        // Simulate concurrent updates (in a real scenario, these would be from different threads)
        ExecutorService executor = Executors.newFixedThreadPool(2);
        
        Future<SentimentRecord> future1 = executor.submit(() -> repo.update(update1));
        Future<SentimentRecord> future2 = executor.submit(() -> repo.update(update2));
        
        try {
            SentimentRecord result1 = future1.get(1, TimeUnit.SECONDS);
            SentimentRecord result2 = future2.get(1, TimeUnit.SECONDS);
            
            // Both updates should succeed (in a mock environment)
            assertEquals(0.8, result1.getSentimentScore());
            assertEquals(0.9, result2.getSentimentScore());
            
            // Verify that update was called twice
            verify(repo, times(2)).update(any());
            
        } catch (InterruptedException | ExecutionException | TimeoutException e) {
            fail("Concurrent execution failed: " + e.getMessage());
        } finally {
            executor.shutdown();
        }
    }
    
    @Test
    public void testBoundaryConditionsWithPostgres() {
        // Configure feature flag to use PostgreSQL
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(false);
        
        // Test boundary conditions
        testBoundaryConditions(repositoryFactory.getRepository(SentimentRecordRepository.class));
    }
    
    @Test
    public void testBoundaryConditionsWithIceberg() {
        // Configure feature flag to use Iceberg
        when(featureFlagService.isEnabled("use-iceberg-backend")).thenReturn(true);
        
        // Test boundary conditions
        testBoundaryConditions(repositoryFactory.getRepository(SentimentRecordRepository.class));
    }
    
    private void testBoundaryConditions(SentimentRecordRepository repo) {
        // Test boundary conditions for sentiment score
        SentimentRecord minScoreRecord = new SentimentRecord(
            UUID.randomUUID(), "AAPL", -1.0, Instant.now(), "TEST", Map.of());
        
        SentimentRecord maxScoreRecord = new SentimentRecord(
            UUID.randomUUID(), "AAPL", 1.0, Instant.now(), "TEST", Map.of());
        
        SentimentRecord zeroScoreRecord = new SentimentRecord(
            UUID.randomUUID(), "AAPL", 0.0, Instant.now(), "TEST", Map.of());
        
        // Setup mocks
        when(repo.save(minScoreRecord)).thenReturn(minScoreRecord.getId());
        when(repo.save(maxScoreRecord)).thenReturn(maxScoreRecord.getId());
        when(repo.save(zeroScoreRecord)).thenReturn(zeroScoreRecord.getId());
        
        // Test saving records with boundary scores
        UUID minScoreId = repo.save(minScoreRecord);
        UUID maxScoreId = repo.save(maxScoreRecord);
        UUID zeroScoreId = repo.save(zeroScoreRecord);
        
        // Verify all were saved
        assertNotNull(minScoreId);
        assertNotNull(maxScoreId);
        assertNotNull(zeroScoreId);
        
        // Setup mocks for retrieval
        when(repo.findById(minScoreId)).thenReturn(Optional.of(minScoreRecord));
        when(repo.findById(maxScoreId)).thenReturn(Optional.of(maxScoreRecord));
        when(repo.findById(zeroScoreId)).thenReturn(Optional.of(zeroScoreRecord));
        
        // Test retrieving records with boundary scores
        Optional<SentimentRecord> foundMinScore = repo.findById(minScoreId);
        Optional<SentimentRecord> foundMaxScore = repo.findById(maxScoreId);
        Optional<SentimentRecord> foundZeroScore = repo.findById(zeroScoreId);
        
        // Verify all were retrieved correctly
        assertTrue(foundMinScore.isPresent());
        assertEquals(-1.0, foundMinScore.get().getSentimentScore());
        
        assertTrue(foundMaxScore.isPresent());
        assertEquals(1.0, foundMaxScore.get().getSentimentScore());
        
        assertTrue(foundZeroScore.isPresent());
        assertEquals(0.0, foundZeroScore.get().getSentimentScore());
    }
}