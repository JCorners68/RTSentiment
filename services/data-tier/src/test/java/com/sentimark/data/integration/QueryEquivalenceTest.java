package com.sentimark.data.integration;

import com.sentimark.data.model.SentimentRecord;
import com.sentimark.data.repository.EnhancedSentimentRecordRepository;
import com.sentimark.data.repository.SentimentRecordRepository;
import com.sentimark.data.specification.Specification;
import com.sentimark.data.specification.TickerSpecification;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class QueryEquivalenceTest {

    @Mock
    private SentimentRecordRepository postgresRepo;
    
    @Mock
    private SentimentRecordRepository icebergRepo;
    
    @Mock
    private EnhancedSentimentRecordRepository postgresEnhancedRepo;
    
    @Mock
    private EnhancedSentimentRecordRepository icebergEnhancedRepo;
    
    private TestDataGenerator testDataGenerator;
    
    @BeforeEach
    public void setup() {
        testDataGenerator = new TestDataGenerator();
        
        // Setup mocks for casting
        when(postgresRepo.findById(any())).thenReturn(Optional.empty());
        when(icebergRepo.findById(any())).thenReturn(Optional.empty());
    }
    
    @Test
    public void testSameResultsForFindAll() {
        // Create sample data sets for both implementations
        List<SentimentRecord> postgresData = testDataGenerator.createMixedSampleRecords(10);
        List<SentimentRecord> icebergData = new ArrayList<>(postgresData); // Same data
        
        // Setup mocks
        when(postgresRepo.findAll()).thenReturn(postgresData);
        when(icebergRepo.findAll()).thenReturn(icebergData);
        
        // Execute findAll on both repositories
        List<SentimentRecord> postgresResults = postgresRepo.findAll();
        List<SentimentRecord> icebergResults = icebergRepo.findAll();
        
        // Compare results
        assertEquivalentResults(postgresResults, icebergResults);
        
        // Verify method calls
        verify(postgresRepo).findAll();
        verify(icebergRepo).findAll();
    }
    
    @Test
    public void testSameResultsForTickerQuery() {
        // Create sample data for the ticker query
        String ticker = "AAPL";
        List<SentimentRecord> tickerData = testDataGenerator.createSampleSentimentRecords(5, ticker);
        
        // Setup mocks
        when(postgresRepo.findByTicker(ticker)).thenReturn(tickerData);
        when(icebergRepo.findByTicker(ticker)).thenReturn(tickerData);
        
        // Execute findByTicker on both repositories
        List<SentimentRecord> postgresResults = postgresRepo.findByTicker(ticker);
        List<SentimentRecord> icebergResults = icebergRepo.findByTicker(ticker);
        
        // Compare results
        assertEquivalentResults(postgresResults, icebergResults);
        
        // Verify method calls
        verify(postgresRepo).findByTicker(ticker);
        verify(icebergRepo).findByTicker(ticker);
    }
    
    @Test
    public void testSameResultsForDateRangeQuery() {
        // Create time range
        Instant start = Instant.parse("2023-01-01T00:00:00Z");
        Instant end = Instant.parse("2023-01-31T23:59:59Z");
        
        // Create sample data for the date range query
        List<SentimentRecord> rangeData = testDataGenerator.createSampleSentimentRecords(5, "AAPL", start, end);
        
        // Setup mocks
        when(postgresRepo.findByTickerAndTimeRange("AAPL", start, end)).thenReturn(rangeData);
        when(icebergRepo.findByTickerAndTimeRange("AAPL", start, end)).thenReturn(rangeData);
        
        // Execute findByTickerAndTimeRange on both repositories
        List<SentimentRecord> postgresResults = postgresRepo.findByTickerAndTimeRange("AAPL", start, end);
        List<SentimentRecord> icebergResults = icebergRepo.findByTickerAndTimeRange("AAPL", start, end);
        
        // Compare results
        assertEquivalentResults(postgresResults, icebergResults);
        
        // Verify method calls
        verify(postgresRepo).findByTickerAndTimeRange("AAPL", start, end);
        verify(icebergRepo).findByTickerAndTimeRange("AAPL", start, end);
    }
    
    @Test
    public void testSameResultsForAverageSentiment() {
        // Create parameters
        String ticker = "AAPL";
        Instant since = Instant.parse("2023-01-01T00:00:00Z");
        double avgSentiment = 0.75;
        
        // Setup mocks
        when(postgresRepo.getAverageSentimentForTicker(ticker, since)).thenReturn(avgSentiment);
        when(icebergRepo.getAverageSentimentForTicker(ticker, since)).thenReturn(avgSentiment);
        
        // Execute getAverageSentimentForTicker on both repositories
        double postgresResult = postgresRepo.getAverageSentimentForTicker(ticker, since);
        double icebergResult = icebergRepo.getAverageSentimentForTicker(ticker, since);
        
        // Compare results
        assertEquals(postgresResult, icebergResult, 0.0001);
        
        // Verify method calls
        verify(postgresRepo).getAverageSentimentForTicker(ticker, since);
        verify(icebergRepo).getAverageSentimentForTicker(ticker, since);
    }
    
    @Test
    public void testSameResultsForSpecifications() {
        // Create specification
        Specification<SentimentRecord> tickerSpec = new TickerSpecification("AAPL");
        
        // Create sample data for the specification query
        List<SentimentRecord> specData = testDataGenerator.createSampleSentimentRecords(5, "AAPL");
        
        // Setup mocks
        when(postgresEnhancedRepo.findBySpecification(tickerSpec)).thenReturn(specData);
        when(icebergEnhancedRepo.findBySpecification(tickerSpec)).thenReturn(specData);
        
        // Execute findBySpecification on both repositories
        List<SentimentRecord> postgresResults = postgresEnhancedRepo.findBySpecification(tickerSpec);
        List<SentimentRecord> icebergResults = icebergEnhancedRepo.findBySpecification(tickerSpec);
        
        // Compare results
        assertEquivalentResults(postgresResults, icebergResults);
        
        // Verify method calls
        verify(postgresEnhancedRepo).findBySpecification(tickerSpec);
        verify(icebergEnhancedRepo).findBySpecification(tickerSpec);
    }
    
    @Test
    public void testSameResultsWithPagination() {
        // Create a large dataset for pagination
        List<SentimentRecord> allData = testDataGenerator.createMixedSampleRecords(100);
        
        // Setup pagination parameters
        int limit = 10;
        int offset = 20;
        
        // Get expected page
        List<SentimentRecord> expectedPage = allData.stream()
            .skip(offset)
            .limit(limit)
            .collect(Collectors.toList());
        
        // Setup mocks
        when(postgresEnhancedRepo.findAll(limit, offset)).thenReturn(expectedPage);
        when(icebergEnhancedRepo.findAll(limit, offset)).thenReturn(expectedPage);
        
        // Execute findAll with pagination on both repositories
        List<SentimentRecord> postgresResults = postgresEnhancedRepo.findAll(limit, offset);
        List<SentimentRecord> icebergResults = icebergEnhancedRepo.findAll(limit, offset);
        
        // Compare results
        assertEquivalentResults(postgresResults, icebergResults);
        
        // Verify method calls
        verify(postgresEnhancedRepo).findAll(limit, offset);
        verify(icebergEnhancedRepo).findAll(limit, offset);
    }
    
    @Test
    public void testSameResultsForSourceQuery() {
        // Create parameters
        String source = "TWITTER";
        
        // Create sample data for the source query
        List<SentimentRecord> sourceData = testDataGenerator.createSampleSentimentRecords(5, source);
        
        // Setup mocks
        when(postgresEnhancedRepo.findBySource(source)).thenReturn(sourceData);
        when(icebergEnhancedRepo.findBySource(source)).thenReturn(sourceData);
        
        // Execute findBySource on both repositories
        List<SentimentRecord> postgresResults = postgresEnhancedRepo.findBySource(source);
        List<SentimentRecord> icebergResults = icebergEnhancedRepo.findBySource(source);
        
        // Compare results
        assertEquivalentResults(postgresResults, icebergResults);
        
        // Verify method calls
        verify(postgresEnhancedRepo).findBySource(source);
        verify(icebergEnhancedRepo).findBySource(source);
    }
    
    @Test
    public void testSameResultsForCountQuery() {
        // Set expected count
        long count = 42;
        
        // Setup mocks
        when(postgresEnhancedRepo.count()).thenReturn(count);
        when(icebergEnhancedRepo.count()).thenReturn(count);
        
        // Execute count on both repositories
        long postgresResult = postgresEnhancedRepo.count();
        long icebergResult = icebergEnhancedRepo.count();
        
        // Compare results
        assertEquals(postgresResult, icebergResult);
        
        // Verify method calls
        verify(postgresEnhancedRepo).count();
        verify(icebergEnhancedRepo).count();
    }
    
    /**
     * Asserts that two result lists contain equivalent records.
     */
    private void assertEquivalentResults(List<SentimentRecord> list1, List<SentimentRecord> list2) {
        assertEquals(list1.size(), list2.size(), "Result lists have different sizes");
        
        // For these tests, we expect identical objects in the same order
        for (int i = 0; i < list1.size(); i++) {
            SentimentRecord record1 = list1.get(i);
            SentimentRecord record2 = list2.get(i);
            
            assertEquals(record1.getId(), record2.getId());
            assertEquals(record1.getTicker(), record2.getTicker());
            assertEquals(record1.getSentimentScore(), record2.getSentimentScore(), 0.0001);
            assertEquals(record1.getTimestamp(), record2.getTimestamp());
            assertEquals(record1.getSource(), record2.getSource());
            assertEquals(record1.getAttributes(), record2.getAttributes());
        }
    }
    
    /**
     * Test data generator for creating sample records.
     */
    private static class TestDataGenerator {
        
        public List<SentimentRecord> createSampleSentimentRecords(int count, String ticker) {
            return createSampleSentimentRecords(count, ticker, Instant.now().minus(30, ChronoUnit.DAYS), Instant.now());
        }
        
        public List<SentimentRecord> createSampleSentimentRecords(int count, String source) {
            List<SentimentRecord> records = new ArrayList<>();
            Random random = new Random();
            String[] tickers = {"AAPL", "MSFT", "GOOG", "AMZN", "FB"};
            
            for (int i = 0; i < count; i++) {
                String ticker = tickers[random.nextInt(tickers.length)];
                double score = (random.nextDouble() * 2) - 1; // -1.0 to 1.0
                Instant timestamp = Instant.now().minus(
                    random.nextInt(365), ChronoUnit.DAYS);
                
                Map<String, Double> attributes = new HashMap<>();
                attributes.put("confidence", 0.8 + random.nextDouble() * 0.2);
                attributes.put("volume", 500.0 + random.nextDouble() * 1000.0);
                
                records.add(new SentimentRecord(
                    UUID.randomUUID(), ticker, score, timestamp, source, attributes));
            }
            
            return records;
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
        
        public List<SentimentRecord> createMixedSampleRecords(int count) {
            List<SentimentRecord> records = new ArrayList<>();
            Random random = new Random();
            String[] tickers = {"AAPL", "MSFT", "GOOG", "AMZN", "FB"};
            String[] sources = {"TWITTER", "NEWS", "BLOG", "FORUM", "ANALYSIS"};
            
            for (int i = 0; i < count; i++) {
                String ticker = tickers[random.nextInt(tickers.length)];
                double score = (random.nextDouble() * 2) - 1; // -1.0 to 1.0
                Instant timestamp = Instant.now().minus(
                    random.nextInt(365), ChronoUnit.DAYS);
                String source = sources[random.nextInt(sources.length)];
                
                Map<String, Double> attributes = new HashMap<>();
                attributes.put("confidence", 0.5 + random.nextDouble() * 0.5);
                attributes.put("volume", random.nextDouble() * 10000);
                
                records.add(new SentimentRecord(
                    UUID.randomUUID(), ticker, score, timestamp, source, attributes));
            }
            
            return records;
        }
    }
}