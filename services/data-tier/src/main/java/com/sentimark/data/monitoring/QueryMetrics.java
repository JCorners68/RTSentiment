package com.sentimark.data.monitoring;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

/**
 * Metrics for a database query.
 */
public class QueryMetrics {
    
    private final String queryType;
    private final String queryDetails;
    private final long startTimeNanos;
    private long endTimeNanos;
    private final Map<String, Object> queryParameters;
    private Exception exception;
    
    /**
     * Create a new QueryMetrics instance.
     *
     * @param queryType the type of query (e.g., "select", "insert")
     * @param queryDetails details about the query (e.g., SQL statement)
     */
    public QueryMetrics(String queryType, String queryDetails) {
        this(queryType, queryDetails, null);
    }
    
    /**
     * Create a new QueryMetrics instance with parameters.
     *
     * @param queryType the type of query (e.g., "select", "insert")
     * @param queryDetails details about the query (e.g., SQL statement)
     * @param queryParameters parameters used in the query
     */
    public QueryMetrics(String queryType, String queryDetails, Map<String, Object> queryParameters) {
        this.queryType = queryType;
        this.queryDetails = queryDetails;
        this.startTimeNanos = System.nanoTime();
        this.queryParameters = queryParameters != null ? 
                new HashMap<>(queryParameters) : Collections.emptyMap();
    }
    
    /**
     * Mark the query as complete.
     */
    public void markComplete() {
        this.endTimeNanos = System.nanoTime();
    }
    
    /**
     * Mark the query as failed with an exception.
     *
     * @param e the exception that occurred
     */
    public void markError(Exception e) {
        this.endTimeNanos = System.nanoTime();
        this.exception = e;
    }
    
    /**
     * Get the duration of the query in nanoseconds.
     *
     * @return the duration in nanoseconds
     */
    public long getDurationNanos() {
        return endTimeNanos - startTimeNanos;
    }
    
    /**
     * Get the duration of the query in milliseconds.
     *
     * @return the duration in milliseconds
     */
    public long getDurationMillis() {
        return getDurationNanos() / 1_000_000;
    }
    
    /**
     * Check if the query completed successfully.
     *
     * @return true if the query completed successfully, false if it failed
     */
    public boolean isSuccess() {
        return exception == null;
    }
    
    /**
     * Get the query type.
     *
     * @return the query type
     */
    public String getQueryType() {
        return queryType;
    }
    
    /**
     * Get the query details.
     *
     * @return the query details
     */
    public String getQueryDetails() {
        return queryDetails;
    }
    
    /**
     * Get the query parameters.
     *
     * @return the query parameters
     */
    public Map<String, Object> getQueryParameters() {
        return Collections.unmodifiableMap(queryParameters);
    }
    
    /**
     * Get the exception that occurred during the query, if any.
     *
     * @return the exception, or null if the query completed successfully
     */
    public Exception getException() {
        return exception;
    }
}