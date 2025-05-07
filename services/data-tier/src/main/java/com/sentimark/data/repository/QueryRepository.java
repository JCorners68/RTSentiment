package com.sentimark.data.repository;

import com.sentimark.data.specification.Specification;

import java.util.List;
import java.util.Optional;

/**
 * Interface for read-only repository operations.
 *
 * @param <T> the entity type
 * @param <ID> the ID type
 */
public interface QueryRepository<T, ID> {
    
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
     * Find all entities that match the given specification.
     *
     * @param spec the specification to match
     * @return a list of matching entities
     */
    List<T> findAll(Specification<T> spec);
    
    /**
     * Count the number of entities that match the given specification.
     *
     * @param spec the specification to match
     * @return the number of matching entities
     */
    long count(Specification<T> spec);
}