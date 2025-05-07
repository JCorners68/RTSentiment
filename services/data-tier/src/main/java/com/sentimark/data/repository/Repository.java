package com.sentimark.data.repository;

import java.util.List;
import java.util.Optional;

/**
 * Generic repository interface for CRUD operations.
 *
 * @param <T> The entity type
 * @param <ID> The ID type
 */
public interface Repository<T, ID> {
    /**
     * Find an entity by its ID.
     *
     * @param id the ID of the entity
     * @return an Optional containing the entity if found, or empty if not found
     */
    Optional<T> findById(ID id);
    
    /**
     * Find all entities.
     *
     * @return a list of all entities
     */
    List<T> findAll();
    
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
}