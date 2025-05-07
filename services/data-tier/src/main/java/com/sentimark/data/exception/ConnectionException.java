package com.sentimark.data.exception;

/**
 * Exception thrown when there is a problem with the database connection.
 */
public class ConnectionException extends DatabaseException {
    
    /**
     * Create a new ConnectionException with a message and cause.
     *
     * @param message the error message
     * @param cause the underlying cause
     */
    public ConnectionException(String message, Throwable cause) {
        super(message, cause);
    }
}