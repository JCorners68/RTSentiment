package com.sentimark.data.repository;

import com.sentimark.data.model.SentimentRecord;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Repository interface for SentimentRecord entities.
 */
public interface SentimentRecordRepository extends Repository<SentimentRecord, UUID> {
    
    /**
     * Find sentiment records by ticker symbol.
     *
     * @param ticker the ticker symbol
     * @return a list of sentiment records for the specified ticker
     */
    List<SentimentRecord> findByTicker(String ticker);
    
    /**
     * Find sentiment records by ticker symbol within a time range.
     *
     * @param ticker the ticker symbol
     * @param start the start of the time range
     * @param end the end of the time range
     * @return a list of sentiment records for the specified ticker within the time range
     */
    List<SentimentRecord> findByTickerAndTimeRange(String ticker, Instant start, Instant end);
    
    /**
     * Get the average sentiment score for a ticker since a specified time.
     *
     * @param ticker the ticker symbol
     * @param since the time from which to calculate the average
     * @return the average sentiment score
     */
    double getAverageSentimentForTicker(String ticker, Instant since);
}