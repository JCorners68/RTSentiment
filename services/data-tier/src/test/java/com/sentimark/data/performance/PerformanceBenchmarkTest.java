package com.sentimark.data.performance;

import com.sentimark.data.config.FeatureDecisions;
import com.sentimark.data.config.FeatureFlagService;
import com.sentimark.data.model.SentimentRecord;
import com.sentimark.data.repository.EnhancedSentimentRecordRepository;
import com.sentimark.data.repository.RepositoryFactory;
import com.sentimark.data.repository.SentimentRecordRepository;
import com.sentimark.data.specification.TickerSpecification;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.function.Supplier;
import java.util.stream.Collectors;

import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
public class PerformanceBenchmarkTest {

    @Mock
    private FeatureFlagService featureFlagService;
    
    @Mock
    private SentimentRecordRepository postgresRepo;
    
    @Mock
    private SentimentRecordRepository icebergRepo;
    
    @Mock
    private EnhancedSentimentRecordRepository postgresEnhancedRepo;
    
    @Mock
    private EnhancedSentimentRecordRepository icebergEnhancedRepo;
    
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
        
        // Setup enhanced repository casting
        when(postgresRepo.findById(any())).thenReturn(Optional.empty());
        when(icebergRepo.findById(any())).thenReturn(Optional.empty());
        
        // Initialize test data generator
        testDataGenerator = new TestDataGenerator();
    }
    
    @Test
    public void benchmarkFindAll() {
        // Prepare test data
        List<SentimentRecord> records = testDataGenerator.createMixedSampleRecords(1000);
        
        // Setup mocks
        when(postgresRepo.findAll()).thenReturn(records);
        when(icebergRepo.findAll()).thenReturn(records);
        
        // Run benchmarks
        runBenchmark("FindAll-PostgreSQL", () -> postgresRepo.findAll(), 100);
        runBenchmark("FindAll-Iceberg", () -> icebergRepo.findAll(), 100);
    }
    
    @Test
    public void benchmarkFindByTicker() {
        // Prepare test data
        List<SentimentRecord> appleRecords = testDataGenerator.createSampleSentimentRecords(100, "AAPL");
        
        // Setup mocks
        when(postgresRepo.findByTicker("AAPL")).thenReturn(appleRecords);
        when(icebergRepo.findByTicker("AAPL")).thenReturn(appleRecords);
        
        // Run benchmarks
        runBenchmark("FindByTicker-PostgreSQL", () -> postgresRepo.findByTicker("AAPL"), 100);
        runBenchmark("FindByTicker-Iceberg", () -> icebergRepo.findByTicker("AAPL"), 100);
    }
    
    @Test
    public void benchmarkFindByTickerAndTimeRange() {
        // Prepare test data
        Instant start = Instant.parse("2023-01-01T00:00:00Z");
        Instant end = Instant.parse("2023-01-31T23:59:59Z");
        List<SentimentRecord> rangeRecords = testDataGenerator.createSampleSentimentRecords(50, "AAPL", start, end);
        
        // Setup mocks
        when(postgresRepo.findByTickerAndTimeRange("AAPL", start, end)).thenReturn(rangeRecords);
        when(icebergRepo.findByTickerAndTimeRange("AAPL", start, end)).thenReturn(rangeRecords);
        
        // Run benchmarks
        runBenchmark("FindByTickerAndTimeRange-PostgreSQL", 
            () -> postgresRepo.findByTickerAndTimeRange("AAPL", start, end), 100);
        runBenchmark("FindByTickerAndTimeRange-Iceberg", 
            () -> icebergRepo.findByTickerAndTimeRange("AAPL", start, end), 100);
    }
    
    @Test
    public void benchmarkFindBySpecification() {
        // Prepare test data
        List<SentimentRecord> appleRecords = testDataGenerator.createSampleSentimentRecords(100, "AAPL");
        TickerSpecification spec = new TickerSpecification("AAPL");
        
        // Setup mocks
        when(postgresEnhancedRepo.findBySpecification(spec)).thenReturn(appleRecords);
        when(icebergEnhancedRepo.findBySpecification(spec)).thenReturn(appleRecords);
        
        // Run benchmarks
        runBenchmark("FindBySpecification-PostgreSQL", 
            () -> postgresEnhancedRepo.findBySpecification(spec), 100);
        runBenchmark("FindBySpecification-Iceberg", 
            () -> icebergEnhancedRepo.findBySpecification(spec), 100);
    }
    
    @Test
    public void benchmarkPagination() {
        // Prepare test data
        int limit = 20;
        int offset = 40;
        List<SentimentRecord> pageRecords = testDataGenerator.createMixedSampleRecords(20);
        
        // Setup mocks
        when(postgresEnhancedRepo.findAll(limit, offset)).thenReturn(pageRecords);
        when(icebergEnhancedRepo.findAll(limit, offset)).thenReturn(pageRecords);
        
        // Run benchmarks
        runBenchmark("Pagination-PostgreSQL", 
            () -> postgresEnhancedRepo.findAll(limit, offset), 100);
        runBenchmark("Pagination-Iceberg", 
            () -> icebergEnhancedRepo.findAll(limit, offset), 100);
    }
    
    @Test
    public void benchmarkGetAverageSentiment() {
        // Prepare test data
        Instant since = Instant.parse("2023-01-01T00:00:00Z");
        
        // Setup mocks
        when(postgresRepo.getAverageSentimentForTicker("AAPL", since)).thenReturn(0.75);
        when(icebergRepo.getAverageSentimentForTicker("AAPL", since)).thenReturn(0.75);
        
        // Run benchmarks
        runBenchmark("GetAverageSentiment-PostgreSQL", 
            () -> postgresRepo.getAverageSentimentForTicker("AAPL", since), 100);
        runBenchmark("GetAverageSentiment-Iceberg", 
            () -> icebergRepo.getAverageSentimentForTicker("AAPL", since), 100);
    }
    
    /**
     * Runs a benchmark test and prints the results.
     *
     * @param name The name of the benchmark
     * @param operation The operation to benchmark
     * @param iterations The number of iterations to run
     * @param <T> The return type of the operation
     */
    private <T> void runBenchmark(String name, Supplier<T> operation, int iterations) {
        // Warmup
        for (int i = 0; i < 10; i++) {
            operation.get();
        }
        
        // Measure performance
        List<Long> executionTimes = new ArrayList<>();
        
        for (int i = 0; i < iterations; i++) {
            long startTime = System.nanoTime();
            operation.get();
            long endTime = System.nanoTime();
            
            executionTimes.add(endTime - startTime);
        }
        
        // Calculate statistics
        PerformanceResult result = new PerformanceResult(executionTimes);
        
        // Print results
        System.out.println("Benchmark: " + name);
        System.out.println("  Average execution time: " + result.getAverageTimeMs() + " ms");
        System.out.println("  Min execution time: " + result.getMinTimeMs() + " ms");
        System.out.println("  Max execution time: " + result.getMaxTimeMs() + " ms");
        System.out.println("  Median execution time: " + result.getMedianTimeMs() + " ms");
        System.out.println();
    }
    
    /**
     * Represents the results of a performance benchmark.
     */
    private static class PerformanceResult {
        private final List<Long> executionTimesNs;
        
        public PerformanceResult(List<Long> executionTimesNs) {
            this.executionTimesNs = executionTimesNs;
        }
        
        public double getAverageTimeMs() {
            return executionTimesNs.stream()
                   .mapToLong(Long::longValue)
                   .average()
                   .orElse(0) / 1_000_000.0;
        }
        
        public double getMinTimeMs() {
            return executionTimesNs.stream()
                   .mapToLong(Long::longValue)
                   .min()
                   .orElse(0) / 1_000_000.0;
        }
        
        public double getMaxTimeMs() {
            return executionTimesNs.stream()
                   .mapToLong(Long::longValue)
                   .max()
                   .orElse(0) / 1_000_000.0;
        }
        
        public double getMedianTimeMs() {
            List<Long> sorted = new ArrayList<>(executionTimesNs);
            Collections.sort(sorted);
            return sorted.get(sorted.size() / 2) / 1_000_000.0;
        }
    }
    
    /**
     * Test data generator for creating sample records.
     */
    private static class TestDataGenerator {
        
        public List<SentimentRecord> createSampleSentimentRecords(int count, String ticker) {
            return createSampleSentimentRecords(count, ticker, Instant.now().minus(30, ChronoUnit.DAYS), Instant.now());
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