package com.sentimark.data.monitoring;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Queue;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.stream.Collectors;

/**
 * Default implementation of PerformanceMonitoringService.
 */
@Component
public class DefaultPerformanceMonitoringService implements PerformanceMonitoringService {
    
    private static final Logger logger = LoggerFactory.getLogger(DefaultPerformanceMonitoringService.class);
    
    private final Queue<QueryMetrics> recentQueries = new ConcurrentLinkedQueue<>();
    private final int maxQueriesStored = 1000;
    private final long slowQueryThresholdMillis = 100;
    
    @Override
    public QueryMetrics startQueryMetrics(String queryType, String queryDetails) {
        return startQueryMetrics(queryType, queryDetails, null);
    }
    
    @Override
    public QueryMetrics startQueryMetrics(String queryType, String queryDetails, Map<String, Object> queryParameters) {
        return new QueryMetrics(queryType, queryDetails, queryParameters);
    }
    
    @Override
    public void recordMetrics(QueryMetrics metrics) {
        // Store metrics for analysis
        addToRecentQueries(metrics);
        
        // Log slow queries
        if (metrics.getDurationMillis() > slowQueryThresholdMillis) {
            logger.warn("Slow query detected: {} - {} took {}ms", 
                      metrics.getQueryType(), 
                      metrics.getQueryDetails(), 
                      metrics.getDurationMillis());
            
            if (!metrics.getQueryParameters().isEmpty()) {
                logger.debug("Query parameters: {}", metrics.getQueryParameters());
            }
        }
        
        // Log errors
        if (!metrics.isSuccess()) {
            logger.error("Query error: {} - {} failed after {}ms", 
                       metrics.getQueryType(), 
                       metrics.getQueryDetails(), 
                       metrics.getDurationMillis(), 
                       metrics.getException());
        }
    }
    
    @Override
    public List<QueryMetrics> getSlowQueries(int maxResults) {
        return recentQueries.stream()
            .filter(metrics -> metrics.getDurationMillis() > slowQueryThresholdMillis)
            .sorted(Comparator.comparingLong(QueryMetrics::getDurationMillis).reversed())
            .limit(maxResults)
            .collect(Collectors.toList());
    }
    
    @Override
    public Map<String, Double> getAverageQueryTimes() {
        return recentQueries.stream()
            .filter(QueryMetrics::isSuccess)
            .collect(Collectors.groupingBy(
                QueryMetrics::getQueryType,
                Collectors.averagingLong(QueryMetrics::getDurationMillis)
            ));
    }
    
    /**
     * Add a QueryMetrics instance to the recent queries queue, removing the oldest if necessary.
     *
     * @param metrics the QueryMetrics instance to add
     */
    private void addToRecentQueries(QueryMetrics metrics) {
        recentQueries.add(metrics);
        
        // Trim if needed
        while (recentQueries.size() > maxQueriesStored) {
            recentQueries.poll();
        }
    }
}