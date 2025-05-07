package com.sentimark.data.exception;

/**
 * Exception thrown when a concurrent modification is detected during a database operation.
 * This typically occurs when multiple transactions attempt to modify the same data.
 */
public class ConcurrentModificationException extends DatabaseException {
    
    public ConcurrentModificationException(String message) {
        super(message);
    }
    
    public ConcurrentModificationException(String message, Throwable cause) {
        super(message, cause);
    }
}