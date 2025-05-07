package com.sentimark.data.repository;

import com.sentimark.data.specification.Specification;

import java.util.List;

/**
 * Interface for enhanced repository operations.
 *
 * @param <T> the entity type
 * @param <ID> the ID type
 */
public interface EnhancedRepository<T, ID> extends Repository<T, ID> {
    
    /**
     * Find all entities that match the given specification.
     *
     * @param spec the specification to match
     * @return a list of matching entities
     */
    List<T> findAll(Specification<T> spec);
    
    /**
     * Find all entities that match the given specification, with ordering and pagination.
     *
     * @param spec the specification to match
     * @param orderBy the ordering to apply
     * @param limit the maximum number of results to return
     * @param offset the number of results to skip
     * @return a list of matching entities
     */
    List<T> findAll(Specification<T> spec, String orderBy, int limit, int offset);
    
    /**
     * Count the number of entities that match the given specification.
     *
     * @param spec the specification to match
     * @return the number of matching entities
     */
    long count(Specification<T> spec);
    
    /**
     * Delete all entities that match the given specification.
     *
     * @param spec the specification to match
     */
    void deleteAll(Specification<T> spec);
}