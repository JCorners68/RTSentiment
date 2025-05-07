package com.sentimark.data.transaction;

import com.sentimark.data.exception.DatabaseException;
import org.apache.iceberg.Transaction;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;

import java.util.concurrent.atomic.AtomicInteger;

/**
 * Transaction manager implementation for Iceberg tables.
 * Supports nested transactions with proper commit and rollback semantics.
 */
@Component
public class IcebergTransactionManager implements TransactionManager {
    
    private static final Logger logger = LoggerFactory.getLogger(IcebergTransactionManager.class);
    
    private final ThreadLocal<Transaction> currentTransaction = new ThreadLocal<>();
    private final ThreadLocal<AtomicInteger> transactionDepth = ThreadLocal.withInitial(() -> new AtomicInteger(0));
    
    @Override
    public <T> T executeInTransaction(TransactionCallback<T> callback) {
        boolean isOutermostTransaction = false;
        
        try {
            if (!isTransactionActive()) {
                isOutermostTransaction = true;
                begin();
            }
            
            T result = callback.execute();
            
            if (isOutermostTransaction) {
                commit();
            }
            
            return result;
        } catch (Exception e) {
            if (isOutermostTransaction) {
                rollback();
            }
            
            if (e instanceof DatabaseException) {
                throw (DatabaseException) e;
            } else {
                throw new DatabaseException("Transaction execution failed", e);
            }
        }
    }
    
    @Override
    public void begin() {
        int depth = transactionDepth.get().incrementAndGet();
        logger.debug("Beginning transaction (depth: {})", depth);
        
        // Only create a new transaction if this is the first level
        if (depth == 1) {
            logger.debug("Creating new Iceberg transaction");
            // Note: The actual Transaction object is created when needed by the repository
        }
    }
    
    @Override
    public void commit() {
        int depth = transactionDepth.get().decrementAndGet();
        logger.debug("Committing transaction (depth: {})", depth);
        
        // Only commit the transaction if this is the outermost transaction
        if (depth == 0) {
            Transaction tx = currentTransaction.get();
            if (tx != null) {
                logger.debug("Committing Iceberg transaction");
                tx.commitTransaction();
                currentTransaction.remove();
            }
        }
    }
    
    @Override
    public void rollback() {
        logger.debug("Rolling back transaction");
        
        // Reset transaction depth
        transactionDepth.get().set(0);
        
        // Clear transaction
        Transaction tx = currentTransaction.get();
        if (tx != null) {
            logger.debug("Rolling back Iceberg transaction");
            // No explicit rollback in Iceberg, we just don't commit
            currentTransaction.remove();
        }
    }
    
    @Override
    public boolean isTransactionActive() {
        return transactionDepth.get().get() > 0;
    }
    
    /**
     * Get or set the current Iceberg transaction.
     * 
     * @param transaction The transaction to set
     * @return The current transaction, or null if none is active
     */
    public Transaction getTransaction(Transaction transaction) {
        if (isTransactionActive()) {
            if (currentTransaction.get() == null && transaction != null) {
                currentTransaction.set(transaction);
            }
            return currentTransaction.get();
        }
        return null;
    }
}