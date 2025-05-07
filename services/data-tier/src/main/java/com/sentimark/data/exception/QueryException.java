package com.sentimark.data.exception;

/**
 * Exception thrown when there is a problem with a database query.
 */
public class QueryException extends DatabaseException {
    
    /**
     * Create a new QueryException with a message.
     *
     * @param message the error message
     */
    public QueryException(String message) {
        super(message);
    }
    
    /**
     * Create a new QueryException with a message and cause.
     *
     * @param message the error message
     * @param cause the underlying cause
     */
    public QueryException(String message, Throwable cause) {
        super(message, cause);
    }
}