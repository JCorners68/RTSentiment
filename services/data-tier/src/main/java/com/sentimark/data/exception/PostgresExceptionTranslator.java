package com.sentimark.data.exception;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.sql.SQLException;

/**
 * Implementation of ExceptionTranslator for PostgreSQL database errors.
 */
@Component
public class PostgresExceptionTranslator implements ExceptionTranslator {
    
    private static final Logger logger = LoggerFactory.getLogger(PostgresExceptionTranslator.class);
    
    @Override
    public RuntimeException translate(Exception e) {
        return translate(e, null);
    }
    
    @Override
    public RuntimeException translate(Exception e, String contextMessage) {
        String baseMessage = contextMessage != null ? contextMessage : "Database operation failed";
        
        if (e instanceof SQLException) {
            SQLException sqlException = (SQLException) e;
            String sqlState = sqlException.getSQLState();
            
            // Log the exception with SQL state and error code
            logger.error("SQL Exception: {} - State: {}, Code: {}", 
                         baseMessage, sqlState, sqlException.getErrorCode(), e);
            
            // Connection-related errors
            if (sqlState != null) {
                // Connection errors (08xxx)
                if (sqlState.startsWith("08")) {
                    return new ConnectionException(baseMessage + ": Connection failed", e);
                }
                
                // Constraint violations (23xxx)
                if (sqlState.startsWith("23")) {
                    String constraintName = extractConstraintName(sqlException.getMessage());
                    return new ConstraintViolationException(
                        baseMessage + ": Constraint violation", constraintName, e);
                }
                
                // Data exceptions (22xxx)
                if (sqlState.startsWith("22")) {
                    return new QueryException(baseMessage + ": Data error", e);
                }
                
                // Syntax or access rule violations (42xxx)
                if (sqlState.startsWith("42")) {
                    return new QueryException(baseMessage + ": Query syntax or access rule violation", e);
                }
                
                // Entity not found - Class 02: No Data
                if (sqlState.startsWith("02")) {
                    return new EntityNotFoundException(baseMessage + ": Entity not found");
                }
            }
            
            // Default SQL exception handling
            return new DatabaseException(baseMessage, e);
        }
        
        // Non-SQL exceptions
        return new DatabaseException(baseMessage, e);
    }
    
    /**
     * Extract the constraint name from a PostgreSQL error message.
     * 
     * @param message the error message
     * @return the extracted constraint name or "unknown" if not found
     */
    private String extractConstraintName(String message) {
        // Example message: "ERROR: duplicate key value violates unique constraint "users_pkey""
        if (message == null) {
            return "unknown";
        }
        
        int constraintIndex = message.indexOf("constraint");
        if (constraintIndex != -1 && message.length() > constraintIndex + 12) {
            int startQuote = message.indexOf("\"", constraintIndex);
            int endQuote = message.indexOf("\"", startQuote + 1);
            if (startQuote != -1 && endQuote != -1) {
                return message.substring(startQuote + 1, endQuote);
            }
        }
        
        return "unknown";
    }
}