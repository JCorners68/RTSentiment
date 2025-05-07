package com.sentimark.data.specification;

import com.sentimark.data.model.SentimentRecord;

import java.util.HashMap;
import java.util.Map;

/**
 * Specification for sentiment records with scores in a specified range.
 */
public class SentimentScoreRangeSpecification implements Specification<SentimentRecord> {
    
    private final double minScore;
    private final double maxScore;
    
    /**
     * Create a new specification for sentiment records with scores in the specified range.
     *
     * @param minScore the minimum score (inclusive)
     * @param maxScore the maximum score (inclusive)
     */
    public SentimentScoreRangeSpecification(double minScore, double maxScore) {
        this.minScore = minScore;
        this.maxScore = maxScore;
    }
    
    @Override
    public boolean isSatisfiedBy(SentimentRecord entity) {
        return entity.getSentimentScore() >= minScore && 
               entity.getSentimentScore() <= maxScore;
    }
    
    @Override
    public String toSqlClause() {
        return "sentiment_score BETWEEN :minScore AND :maxScore";
    }
    
    @Override
    public Map<String, Object> getParameters() {
        Map<String, Object> params = new HashMap<>();
        params.put("minScore", minScore);
        params.put("maxScore", maxScore);
        return params;
    }
}