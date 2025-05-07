package com.sentimark.data.transaction;

import com.sentimark.data.exception.DatabaseException;
import com.sentimark.data.repository.Repository;
import com.sentimark.data.repository.RepositoryFactory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.PreDestroy;
import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.HashMap;
import java.util.Map;

/**
 * PostgreSQL implementation of UnitOfWork.
 */
@Component
public class PostgresUnitOfWork implements UnitOfWork {
    
    private static final Logger logger = LoggerFactory.getLogger(PostgresUnitOfWork.class);
    
    private final DataSource dataSource;
    private final RepositoryFactory repositoryFactory;
    private final Map<Class<?>, Repository<?, ?>> repositories;
    private Connection connection;
    
    @Autowired
    public PostgresUnitOfWork(DataSource dataSource, RepositoryFactory repositoryFactory) {
        this.dataSource = dataSource;
        this.repositoryFactory = repositoryFactory;
        this.repositories = new HashMap<>();
    }
    
    @Override
    public void begin() {
        try {
            if (connection != null && !connection.isClosed()) {
                logger.warn("Unit of work already active");
                return;
            }
            
            logger.debug("Beginning unit of work");
            connection = dataSource.getConnection();
            connection.setAutoCommit(false);
        } catch (SQLException e) {
            throw new DatabaseException("Failed to begin unit of work", e);
        }
    }
    
    @Override
    public void commit() {
        try {
            if (connection == null || connection.isClosed()) {
                throw new IllegalStateException("No active unit of work to commit");
            }
            
            logger.debug("Committing unit of work");
            connection.commit();
            repositories.clear();
        } catch (SQLException e) {
            throw new DatabaseException("Failed to commit unit of work", e);
        }
    }
    
    @Override
    public void rollback() {
        try {
            if (connection == null || connection.isClosed()) {
                throw new IllegalStateException("No active unit of work to roll back");
            }
            
            logger.debug("Rolling back unit of work");
            connection.rollback();
            repositories.clear();
        } catch (SQLException e) {
            throw new DatabaseException("Failed to roll back unit of work", e);
        }
    }
    
    @SuppressWarnings("unchecked")
    @Override
    public <T> Repository<T, ?> getRepository(Class<T> entityClass) {
        if (connection == null) {
            throw new IllegalStateException("Unit of work not active");
        }
        
        if (!repositories.containsKey(entityClass)) {
            Repository<T, ?> repository = repositoryFactory.getRepository(entityClass);
            
            if (repository instanceof TransactionAwareRepository) {
                ((TransactionAwareRepository) repository).setConnection(connection);
                logger.debug("Created transaction-aware repository for {}", entityClass.getSimpleName());
            } else {
                logger.warn("Repository for {} is not transaction-aware", entityClass.getSimpleName());
            }
            
            repositories.put(entityClass, repository);
        }
        
        return (Repository<T, ?>) repositories.get(entityClass);
    }
    
    @PreDestroy
    public void close() {
        try {
            if (connection != null && !connection.isClosed()) {
                logger.debug("Closing unit of work connection");
                connection.close();
            }
        } catch (SQLException e) {
            logger.error("Error closing connection", e);
        } finally {
            connection = null;
            repositories.clear();
        }
    }
}