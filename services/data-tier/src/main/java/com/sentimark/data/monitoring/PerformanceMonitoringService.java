package com.sentimark.data.monitoring;

import java.util.List;
import java.util.Map;

/**
 * Interface for monitoring database performance.
 */
public interface PerformanceMonitoringService {
    
    /**
     * Start collecting metrics for a query.
     *
     * @param queryType the type of query (e.g., "select", "insert")
     * @param queryDetails details about the query (e.g., SQL statement)
     * @return the QueryMetrics instance
     */
    QueryMetrics startQueryMetrics(String queryType, String queryDetails);
    
    /**
     * Start collecting metrics for a query with parameters.
     *
     * @param queryType the type of query (e.g., "select", "insert")
     * @param queryDetails details about the query (e.g., SQL statement)
     * @param queryParameters parameters used in the query
     * @return the QueryMetrics instance
     */
    QueryMetrics startQueryMetrics(String queryType, String queryDetails, Map<String, Object> queryParameters);
    
    /**
     * Record metrics for a completed query.
     *
     * @param metrics the QueryMetrics instance
     */
    void recordMetrics(QueryMetrics metrics);
    
    /**
     * Get the slowest queries.
     *
     * @param maxResults the maximum number of results to return
     * @return a list of the slowest queries
     */
    List<QueryMetrics> getSlowQueries(int maxResults);
    
    /**
     * Get the average query times by query type.
     *
     * @return a map of query types to average execution times in milliseconds
     */
    Map<String, Double> getAverageQueryTimes();
}