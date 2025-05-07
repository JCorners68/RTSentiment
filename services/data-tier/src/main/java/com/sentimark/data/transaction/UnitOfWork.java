package com.sentimark.data.transaction;

import com.sentimark.data.repository.Repository;

/**
 * Interface for the Unit of Work pattern.
 */
public interface UnitOfWork {
    
    /**
     * Begin a new unit of work.
     */
    void begin();
    
    /**
     * Commit the unit of work.
     */
    void commit();
    
    /**
     * Roll back the unit of work.
     */
    void rollback();
    
    /**
     * Get a repository for the specified entity class.
     *
     * @param entityClass the entity class
     * @param <T> the entity type
     * @return the repository
     */
    <T> Repository<T, ?> getRepository(Class<T> entityClass);
}