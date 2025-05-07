package com.sentimark.data.repository;

import com.sentimark.data.specification.Specification;

/**
 * Interface for write-only repository operations.
 *
 * @param <T> the entity type
 * @param <ID> the ID type
 */
public interface CommandRepository<T, ID> {
    
    /**
     * Save a new entity.
     *
     * @param entity the entity to save
     * @return the saved entity
     */
    T save(T entity);
    
    /**
     * Update an existing entity.
     *
     * @param entity the entity to update
     * @return the updated entity
     */
    T update(T entity);
    
    /**
     * Delete an entity by its ID.
     *
     * @param id the ID of the entity to delete
     */
    void delete(ID id);
    
    /**
     * Delete all entities that match the given specification.
     *
     * @param spec the specification to match
     */
    void deleteAll(Specification<T> spec);
}