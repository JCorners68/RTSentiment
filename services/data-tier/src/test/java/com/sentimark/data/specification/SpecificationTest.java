package com.sentimark.data.specification;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.time.Instant;
import java.util.Map;

import org.junit.jupiter.api.Test;

import com.sentimark.data.model.SentimentRecord;

public class SpecificationTest {

    @Test
    public void testTickerSpecification() {
        // Given
        String tickerSymbol = "AAPL";
        Specification<SentimentRecord> tickerSpec = new TickerSpecification(tickerSymbol);
        
        // When
        String sqlClause = tickerSpec.toSqlClause();
        Map<String, Object> params = tickerSpec.getParameters();
        
        // Then
        assertEquals("ticker = :ticker", sqlClause);
        assertEquals(1, params.size());
        assertEquals(tickerSymbol, params.get("ticker"));
        
        // Test with a matching entity
        SentimentRecord matchingRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.now(), "TWITTER"
        );
        assertTrue(tickerSpec.isSatisfiedBy(matchingRecord));
        
        // Test with a non-matching entity
        SentimentRecord nonMatchingRecord = new SentimentRecord(
            null, "MSFT", 0.75, Instant.now(), "TWITTER"
        );
        assertFalse(tickerSpec.isSatisfiedBy(nonMatchingRecord));
    }
    
    @Test
    public void testDateRangeSpecification() {
        // Given
        Instant start = Instant.parse("2023-01-01T00:00:00Z");
        Instant end = Instant.parse("2023-01-31T23:59:59Z");
        Specification<SentimentRecord> dateRangeSpec = new DateRangeSpecification(start, end);
        
        // When
        String sqlClause = dateRangeSpec.toSqlClause();
        Map<String, Object> params = dateRangeSpec.getParameters();
        
        // Then
        assertEquals("timestamp >= :startDate AND timestamp <= :endDate", sqlClause);
        assertEquals(2, params.size());
        assertEquals(start, params.get("startDate"));
        assertEquals(end, params.get("endDate"));
        
        // Test with entity in range
        SentimentRecord inRangeRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.parse("2023-01-15T12:00:00Z"), "TWITTER"
        );
        assertTrue(dateRangeSpec.isSatisfiedBy(inRangeRecord));
        
        // Test with entity before range
        SentimentRecord beforeRangeRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.parse("2022-12-31T23:59:59Z"), "TWITTER"
        );
        assertFalse(dateRangeSpec.isSatisfiedBy(beforeRangeRecord));
        
        // Test with entity after range
        SentimentRecord afterRangeRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.parse("2023-02-01T00:00:00Z"), "TWITTER"
        );
        assertFalse(dateRangeSpec.isSatisfiedBy(afterRangeRecord));
    }
    
    @Test
    public void testAndSpecification() {
        // Given
        String tickerSymbol = "AAPL";
        Instant start = Instant.parse("2023-01-01T00:00:00Z");
        Instant end = Instant.parse("2023-01-31T23:59:59Z");
        
        Specification<SentimentRecord> tickerSpec = new TickerSpecification(tickerSymbol);
        Specification<SentimentRecord> dateRangeSpec = new DateRangeSpecification(start, end);
        
        Specification<SentimentRecord> combinedSpec = new AndSpecification<>(tickerSpec, dateRangeSpec);
        
        // When
        String sqlClause = combinedSpec.toSqlClause();
        Map<String, Object> params = combinedSpec.getParameters();
        
        // Then
        assertEquals("(ticker = :ticker) AND (timestamp >= :startDate AND timestamp <= :endDate)", sqlClause);
        assertEquals(3, params.size());
        assertEquals(tickerSymbol, params.get("ticker"));
        assertEquals(start, params.get("startDate"));
        assertEquals(end, params.get("endDate"));
        
        // Test with matching entity
        SentimentRecord matchingRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.parse("2023-01-15T12:00:00Z"), "TWITTER"
        );
        assertTrue(combinedSpec.isSatisfiedBy(matchingRecord));
        
        // Test with non-matching ticker
        SentimentRecord wrongTickerRecord = new SentimentRecord(
            null, "MSFT", 0.75, Instant.parse("2023-01-15T12:00:00Z"), "TWITTER"
        );
        assertFalse(combinedSpec.isSatisfiedBy(wrongTickerRecord));
        
        // Test with non-matching date
        SentimentRecord wrongDateRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.parse("2023-02-15T12:00:00Z"), "TWITTER"
        );
        assertFalse(combinedSpec.isSatisfiedBy(wrongDateRecord));
    }
    
    @Test
    public void testOrSpecification() {
        // Given
        Specification<SentimentRecord> appleSpec = new TickerSpecification("AAPL");
        Specification<SentimentRecord> microsoftSpec = new TickerSpecification("MSFT");
        
        Specification<SentimentRecord> combinedSpec = new OrSpecification<>(appleSpec, microsoftSpec);
        
        // When
        String sqlClause = combinedSpec.toSqlClause();
        Map<String, Object> params = combinedSpec.getParameters();
        
        // Then
        assertEquals("(ticker = :ticker) OR (ticker = :ticker2)", sqlClause);
        assertEquals(2, params.size());
        
        // Test with matching AAPL entity
        SentimentRecord appleRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.now(), "TWITTER"
        );
        assertTrue(combinedSpec.isSatisfiedBy(appleRecord));
        
        // Test with matching MSFT entity
        SentimentRecord microsoftRecord = new SentimentRecord(
            null, "MSFT", 0.75, Instant.now(), "TWITTER"
        );
        assertTrue(combinedSpec.isSatisfiedBy(microsoftRecord));
        
        // Test with non-matching entity
        SentimentRecord googleRecord = new SentimentRecord(
            null, "GOOGL", 0.75, Instant.now(), "TWITTER"
        );
        assertFalse(combinedSpec.isSatisfiedBy(googleRecord));
    }
    
    @Test
    public void testNotSpecification() {
        // Given
        Specification<SentimentRecord> appleSpec = new TickerSpecification("AAPL");
        Specification<SentimentRecord> notAppleSpec = new NotSpecification<>(appleSpec);
        
        // When
        String sqlClause = notAppleSpec.toSqlClause();
        Map<String, Object> params = notAppleSpec.getParameters();
        
        // Then
        assertEquals("NOT (ticker = :ticker)", sqlClause);
        assertEquals(1, params.size());
        
        // Test with non-matching entity (which should match the NOT spec)
        SentimentRecord microsoftRecord = new SentimentRecord(
            null, "MSFT", 0.75, Instant.now(), "TWITTER"
        );
        assertTrue(notAppleSpec.isSatisfiedBy(microsoftRecord));
        
        // Test with matching entity (which should not match the NOT spec)
        SentimentRecord appleRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.now(), "TWITTER"
        );
        assertFalse(notAppleSpec.isSatisfiedBy(appleRecord));
    }
    
    @Test
    public void testSentimentScoreRangeSpecification() {
        // Given
        double minScore = 0.5;
        double maxScore = 0.8;
        Specification<SentimentRecord> sentimentSpec = 
            new SentimentScoreRangeSpecification(minScore, maxScore);
        
        // When
        String sqlClause = sentimentSpec.toSqlClause();
        Map<String, Object> params = sentimentSpec.getParameters();
        
        // Then
        assertEquals("sentiment_score >= :minScore AND sentiment_score <= :maxScore", sqlClause);
        assertEquals(2, params.size());
        assertEquals(minScore, params.get("minScore"));
        assertEquals(maxScore, params.get("maxScore"));
        
        // Test with in-range entity
        SentimentRecord inRangeRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.now(), "TWITTER"
        );
        assertTrue(sentimentSpec.isSatisfiedBy(inRangeRecord));
        
        // Test with below-range entity
        SentimentRecord belowRangeRecord = new SentimentRecord(
            null, "AAPL", 0.4, Instant.now(), "TWITTER"
        );
        assertFalse(sentimentSpec.isSatisfiedBy(belowRangeRecord));
        
        // Test with above-range entity
        SentimentRecord aboveRangeRecord = new SentimentRecord(
            null, "AAPL", 0.9, Instant.now(), "TWITTER"
        );
        assertFalse(sentimentSpec.isSatisfiedBy(aboveRangeRecord));
    }
    
    @Test
    public void testSourceSpecification() {
        // Given
        String source = "TWITTER";
        Specification<SentimentRecord> sourceSpec = new SourceSpecification(source);
        
        // When
        String sqlClause = sourceSpec.toSqlClause();
        Map<String, Object> params = sourceSpec.getParameters();
        
        // Then
        assertEquals("source = :source", sqlClause);
        assertEquals(1, params.size());
        assertEquals(source, params.get("source"));
        
        // Test with matching entity
        SentimentRecord twitterRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.now(), "TWITTER"
        );
        assertTrue(sourceSpec.isSatisfiedBy(twitterRecord));
        
        // Test with non-matching entity
        SentimentRecord newsRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.now(), "NEWS"
        );
        assertFalse(sourceSpec.isSatisfiedBy(newsRecord));
    }
    
    @Test
    public void testComplexSpecificationCombination() {
        // Given
        // Apple or Microsoft stocks
        Specification<SentimentRecord> appleSpec = new TickerSpecification("AAPL");
        Specification<SentimentRecord> microsoftSpec = new TickerSpecification("MSFT");
        Specification<SentimentRecord> stockSpec = new OrSpecification<>(appleSpec, microsoftSpec);
        
        // From Twitter
        Specification<SentimentRecord> twitterSpec = new SourceSpecification("TWITTER");
        
        // With positive sentiment
        Specification<SentimentRecord> positiveSpec = 
            new SentimentScoreRangeSpecification(0.6, 1.0);
        
        // Date range
        Instant start = Instant.parse("2023-01-01T00:00:00Z");
        Instant end = Instant.parse("2023-01-31T23:59:59Z");
        Specification<SentimentRecord> dateSpec = new DateRangeSpecification(start, end);
        
        // Combine them all: (Apple OR Microsoft) AND Twitter AND Positive AND DateRange
        Specification<SentimentRecord> combined = new AndSpecification<>(
            new AndSpecification<>(
                new AndSpecification<>(stockSpec, twitterSpec),
                positiveSpec
            ),
            dateSpec
        );
        
        // When
        String sqlClause = combined.toSqlClause();
        Map<String, Object> params = combined.getParameters();
        
        // Then
        assertTrue(sqlClause.contains("ticker = :ticker"));
        assertTrue(sqlClause.contains("ticker = :ticker2"));
        assertTrue(sqlClause.contains("source = :source"));
        assertTrue(sqlClause.contains("sentiment_score >= :minScore"));
        assertTrue(sqlClause.contains("timestamp >= :startDate"));
        
        assertEquals(6, params.size());
        
        // Test with matching entity
        SentimentRecord matchingRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.parse("2023-01-15T12:00:00Z"), "TWITTER"
        );
        assertTrue(combined.isSatisfiedBy(matchingRecord));
        
        // Test with non-matching source
        SentimentRecord wrongSourceRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.parse("2023-01-15T12:00:00Z"), "NEWS"
        );
        assertFalse(combined.isSatisfiedBy(wrongSourceRecord));
        
        // Test with non-matching sentiment
        SentimentRecord lowSentimentRecord = new SentimentRecord(
            null, "AAPL", 0.4, Instant.parse("2023-01-15T12:00:00Z"), "TWITTER"
        );
        assertFalse(combined.isSatisfiedBy(lowSentimentRecord));
        
        // Test with non-matching date
        SentimentRecord wrongDateRecord = new SentimentRecord(
            null, "AAPL", 0.75, Instant.parse("2022-12-15T12:00:00Z"), "TWITTER"
        );
        assertFalse(combined.isSatisfiedBy(wrongDateRecord));
        
        // Test with non-matching ticker
        SentimentRecord wrongTickerRecord = new SentimentRecord(
            null, "GOOGL", 0.75, Instant.parse("2023-01-15T12:00:00Z"), "TWITTER"
        );
        assertFalse(combined.isSatisfiedBy(wrongTickerRecord));
    }
}

class TickerSpecification implements Specification<SentimentRecord> {
    private final String ticker;
    
    public TickerSpecification(String ticker) {
        this.ticker = ticker;
    }
    
    @Override
    public boolean isSatisfiedBy(SentimentRecord entity) {
        return ticker.equals(entity.getTicker());
    }
    
    @Override
    public String toSqlClause() {
        return "ticker = :ticker";
    }
    
    @Override
    public Map<String, Object> getParameters() {
        return Collections.singletonMap("ticker", ticker);
    }
}

class DateRangeSpecification implements Specification<SentimentRecord> {
    private final Instant startDate;
    private final Instant endDate;
    
    public DateRangeSpecification(Instant startDate, Instant endDate) {
        this.startDate = startDate;
        this.endDate = endDate;
    }
    
    @Override
    public boolean isSatisfiedBy(SentimentRecord entity) {
        Instant recordTime = entity.getTimestamp();
        return !recordTime.isBefore(startDate) && !recordTime.isAfter(endDate);
    }
    
    @Override
    public String toSqlClause() {
        return "timestamp >= :startDate AND timestamp <= :endDate";
    }
    
    @Override
    public Map<String, Object> getParameters() {
        Map<String, Object> params = new java.util.HashMap<>();
        params.put("startDate", startDate);
        params.put("endDate", endDate);
        return params;
    }
}

class SentimentScoreRangeSpecification implements Specification<SentimentRecord> {
    private final double minScore;
    private final double maxScore;
    
    public SentimentScoreRangeSpecification(double minScore, double maxScore) {
        this.minScore = minScore;
        this.maxScore = maxScore;
    }
    
    @Override
    public boolean isSatisfiedBy(SentimentRecord entity) {
        double score = entity.getSentimentScore();
        return score >= minScore && score <= maxScore;
    }
    
    @Override
    public String toSqlClause() {
        return "sentiment_score >= :minScore AND sentiment_score <= :maxScore";
    }
    
    @Override
    public Map<String, Object> getParameters() {
        Map<String, Object> params = new java.util.HashMap<>();
        params.put("minScore", minScore);
        params.put("maxScore", maxScore);
        return params;
    }
}

class SourceSpecification implements Specification<SentimentRecord> {
    private final String source;
    
    public SourceSpecification(String source) {
        this.source = source;
    }
    
    @Override
    public boolean isSatisfiedBy(SentimentRecord entity) {
        return source.equals(entity.getSource());
    }
    
    @Override
    public String toSqlClause() {
        return "source = :source";
    }
    
    @Override
    public Map<String, Object> getParameters() {
        return Collections.singletonMap("source", source);
    }
}