package com.sentimark.data.exception;

/**
 * Exception thrown when a rollback operation fails.
 */
public class RollbackException extends RuntimeException {
    
    /**
     * Creates a new RollbackException with the specified message.
     *
     * @param message The error message
     */
    public RollbackException(String message) {
        super(message);
    }
    
    /**
     * Creates a new RollbackException with the specified message and cause.
     *
     * @param message The error message
     * @param cause The underlying cause
     */
    public RollbackException(String message, Throwable cause) {
        super(message, cause);
    }
}