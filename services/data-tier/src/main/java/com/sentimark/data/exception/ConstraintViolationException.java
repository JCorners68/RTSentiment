package com.sentimark.data.exception;

/**
 * Exception thrown when a database constraint is violated.
 */
public class ConstraintViolationException extends DatabaseException {
    
    private final String constraintName;
    
    /**
     * Create a new ConstraintViolationException with a message, constraint name, and cause.
     *
     * @param message the error message
     * @param constraintName the name of the violated constraint
     * @param cause the underlying cause
     */
    public ConstraintViolationException(String message, String constraintName, Throwable cause) {
        super(message, cause);
        this.constraintName = constraintName;
    }
    
    /**
     * Get the name of the violated constraint.
     *
     * @return the constraint name
     */
    public String getConstraintName() {
        return constraintName;
    }
}