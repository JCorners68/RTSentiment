package com.sentimark.data.exception;

import org.apache.iceberg.exceptions.CommitFailedException;
import org.apache.iceberg.exceptions.NoSuchTableException;
import org.apache.iceberg.exceptions.RuntimeIOException;
import org.apache.iceberg.exceptions.ValidationException;
import org.springframework.stereotype.Component;

@Component
public class IcebergExceptionTranslator implements ExceptionTranslator {
    
    @Override
    public DatabaseException translate(Exception e) {
        if (e instanceof ValidationException) {
            return new ConstraintViolationException("Validation failed: " + e.getMessage(), e);
        } else if (e instanceof NoSuchTableException) {
            return new EntityNotFoundException("Table not found: " + e.getMessage(), e);
        } else if (e instanceof CommitFailedException) {
            return new ConcurrentModificationException("Commit failed due to concurrent modification", e);
        } else if (e instanceof RuntimeIOException) {
            return new ConnectionException("I/O error: " + e.getMessage(), e);
        } else {
            return new DatabaseException("Iceberg error: " + e.getMessage(), e);
        }
    }
}