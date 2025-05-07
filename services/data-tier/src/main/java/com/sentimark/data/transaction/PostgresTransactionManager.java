package com.sentimark.data.transaction;

import com.sentimark.data.exception.DatabaseException;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;

/**
 * PostgreSQL implementation of TransactionManager.
 */
@Component
public class PostgresTransactionManager implements TransactionManager {
    
    private static final Logger logger = LoggerFactory.getLogger(PostgresTransactionManager.class);
    
    private final DataSource dataSource;
    private final ThreadLocal<Connection> connectionHolder = new ThreadLocal<>();
    private final ThreadLocal<Integer> transactionDepth = ThreadLocal.withInitial(() -> 0);
    
    @Autowired
    public PostgresTransactionManager(DataSource dataSource) {
        this.dataSource = dataSource;
    }
    
    @Override
    public <T> T executeInTransaction(TransactionCallback<T> callback) {
        boolean isNewTransaction = !isTransactionActive();
        
        if (isNewTransaction) {
            begin();
        } else {
            incrementTransactionDepth();
        }
        
        try {
            T result = callback.doInTransaction();
            
            if (isNewTransaction) {
                commit();
            } else {
                decrementTransactionDepth();
            }
            
            return result;
        } catch (Exception e) {
            if (isNewTransaction) {
                rollback();
            } else {
                decrementTransactionDepth();
            }
            
            throw e instanceof RuntimeException ? 
                (RuntimeException) e : new RuntimeException(e);
        }
    }
    
    @Override
    public void begin() {
        try {
            if (isTransactionActive()) {
                incrementTransactionDepth();
                logger.debug("Nesting transaction - depth {}", getTransactionDepth());
                return;
            }
            
            logger.debug("Beginning new transaction");
            Connection connection = dataSource.getConnection();
            connection.setAutoCommit(false);
            connectionHolder.set(connection);
            transactionDepth.set(1);
        } catch (SQLException e) {
            throw new DatabaseException("Failed to begin transaction", e);
        }
    }
    
    @Override
    public void commit() {
        if (!isTransactionActive()) {
            throw new IllegalStateException("No active transaction to commit");
        }
        
        try {
            if (getTransactionDepth() > 1) {
                decrementTransactionDepth();
                logger.debug("Committing nested transaction - depth now {}", getTransactionDepth());
                return;
            }
            
            logger.debug("Committing transaction");
            Connection connection = connectionHolder.get();
            connection.commit();
            connection.close();
            connectionHolder.remove();
            transactionDepth.remove();
        } catch (SQLException e) {
            throw new DatabaseException("Failed to commit transaction", e);
        }
    }
    
    @Override
    public void rollback() {
        if (!isTransactionActive()) {
            throw new IllegalStateException("No active transaction to rollback");
        }
        
        try {
            if (getTransactionDepth() > 1) {
                decrementTransactionDepth();
                logger.debug("Rolling back nested transaction - depth now {}", getTransactionDepth());
                return;
            }
            
            logger.debug("Rolling back transaction");
            Connection connection = connectionHolder.get();
            connection.rollback();
            connection.close();
            connectionHolder.remove();
            transactionDepth.remove();
        } catch (SQLException e) {
            throw new DatabaseException("Failed to rollback transaction", e);
        }
    }
    
    @Override
    public boolean isTransactionActive() {
        return connectionHolder.get() != null;
    }
    
    /**
     * Get the current database connection for transaction management.
     *
     * @return the current transaction connection
     * @throws IllegalStateException if no transaction is active
     */
    public Connection getCurrentConnection() {
        if (!isTransactionActive()) {
            throw new IllegalStateException("No active transaction");
        }
        
        return connectionHolder.get();
    }
    
    /**
     * Get the current transaction depth.
     *
     * @return the current transaction depth
     */
    private int getTransactionDepth() {
        return transactionDepth.get();
    }
    
    /**
     * Increment the transaction depth.
     */
    private void incrementTransactionDepth() {
        transactionDepth.set(getTransactionDepth() + 1);
    }
    
    /**
     * Decrement the transaction depth.
     */
    private void decrementTransactionDepth() {
        transactionDepth.set(getTransactionDepth() - 1);
    }
}