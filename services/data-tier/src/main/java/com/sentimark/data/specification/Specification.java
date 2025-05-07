package com.sentimark.data.specification;

import java.util.Map;

/**
 * Interface for query specifications.
 *
 * @param <T> the type of entity this specification operates on
 */
public interface Specification<T> {
    
    /**
     * Check if an entity satisfies this specification.
     *
     * @param entity the entity to check
     * @return true if the entity satisfies the specification, false otherwise
     */
    boolean isSatisfiedBy(T entity);
    
    /**
     * Convert this specification to a SQL WHERE clause.
     *
     * @return the SQL WHERE clause
     */
    String toSqlClause();
    
    /**
     * Get the parameters for the SQL query.
     *
     * @return a map of parameter names to values
     */
    Map<String, Object> getParameters();
}