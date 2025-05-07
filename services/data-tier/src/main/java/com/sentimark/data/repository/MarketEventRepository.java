package com.sentimark.data.repository;

import com.sentimark.data.model.MarketEvent;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * Repository interface for MarketEvent entities.
 */
public interface MarketEventRepository extends Repository<MarketEvent, UUID> {
    
    /**
     * Find market events that are associated with any of the specified tickers.
     *
     * @param tickers a list of ticker symbols
     * @return a list of market events for the specified tickers
     */
    List<MarketEvent> findByTickers(List<String> tickers);
    
    /**
     * Find market events within a time range.
     *
     * @param start the start of the time range
     * @param end the end of the time range
     * @return a list of market events within the time range
     */
    List<MarketEvent> findByTimeRange(Instant start, Instant end);
    
    /**
     * Find market events from a specific source within a time range.
     *
     * @param source the source of the market events
     * @param start the start of the time range
     * @param end the end of the time range
     * @return a list of market events from the specified source within the time range
     */
    List<MarketEvent> findBySourceAndTimeRange(String source, Instant start, Instant end);
}