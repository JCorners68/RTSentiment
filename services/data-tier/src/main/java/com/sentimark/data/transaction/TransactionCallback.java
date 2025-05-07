package com.sentimark.data.transaction;

/**
 * Functional interface for operations that should be executed within a transaction.
 *
 * @param <T> the return type of the transaction callback
 */
@FunctionalInterface
public interface TransactionCallback<T> {
    
    /**
     * Execute operations within a transaction.
     *
     * @return the result of the transaction
     */
    T doInTransaction();
}