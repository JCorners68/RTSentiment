package com.sentimark.data.exception;

/**
 * Base exception for all database-related errors.
 */
public class DatabaseException extends RuntimeException {
    
    /**
     * Create a new DatabaseException with a message.
     *
     * @param message the error message
     */
    public DatabaseException(String message) {
        super(message);
    }
    
    /**
     * Create a new DatabaseException with a message and cause.
     *
     * @param message the error message
     * @param cause the underlying cause
     */
    public DatabaseException(String message, Throwable cause) {
        super(message, cause);
    }
}