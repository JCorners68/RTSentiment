package com.sentimark.data.exception;

/**
 * Exception thrown when an entity is not found in the database.
 */
public class EntityNotFoundException extends DatabaseException {
    
    /**
     * Create a new EntityNotFoundException with a message.
     *
     * @param message the error message
     */
    public EntityNotFoundException(String message) {
        super(message);
    }
}