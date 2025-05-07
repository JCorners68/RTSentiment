package com.sentimark.data.transaction;

/**
 * Interface for managing database transactions.
 */
public interface TransactionManager {
    
    /**
     * Execute a callback within a transaction.
     *
     * @param callback the callback to execute
     * @param <T> the return type of the callback
     * @return the result of the callback
     */
    <T> T executeInTransaction(TransactionCallback<T> callback);
    
    /**
     * Begin a new transaction.
     */
    void begin();
    
    /**
     * Commit the current transaction.
     */
    void commit();
    
    /**
     * Roll back the current transaction.
     */
    void rollback();
    
    /**
     * Check if a transaction is active.
     *
     * @return true if a transaction is active, false otherwise
     */
    boolean isTransactionActive();
}