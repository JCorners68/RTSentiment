package com.sentimark.data.transaction;

import java.sql.Connection;

/**
 * Interface for repositories that can participate in transactions.
 */
public interface TransactionAwareRepository {
    
    /**
     * Set the connection to be used for database operations.
     *
     * @param connection the database connection
     */
    void setConnection(Connection connection);
}