package com.sentimark.data.specification;

import com.sentimark.data.model.SentimentRecord;

import java.util.HashMap;
import java.util.Map;

/**
 * Specification for sentiment records with a specific ticker.
 */
public class TickerSpecification implements Specification<SentimentRecord> {
    
    private final String ticker;
    
    /**
     * Create a new specification for sentiment records with the specified ticker.
     *
     * @param ticker the ticker symbol
     */
    public TickerSpecification(String ticker) {
        this.ticker = ticker;
    }
    
    @Override
    public boolean isSatisfiedBy(SentimentRecord entity) {
        return entity.getTicker().equals(ticker);
    }
    
    @Override
    public String toSqlClause() {
        return "ticker = :ticker";
    }
    
    @Override
    public Map<String, Object> getParameters() {
        Map<String, Object> params = new HashMap<>();
        params.put("ticker", ticker);
        return params;
    }
}