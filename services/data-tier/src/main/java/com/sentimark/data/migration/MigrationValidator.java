package com.sentimark.data.migration;

/**
 * Interface for validating data migration.
 * Implementations can define custom validation logic for specific entity types.
 *
 * @param <T> The entity type
 */
public interface MigrationValidator<T> {
    
    /**
     * Validates if a migrated entity matches the source entity.
     *
     * @param sourceEntity The source entity
     * @param targetEntity The target entity (migrated)
     * @return A validation result indicating any issues
     */
    ValidationResult validate(T sourceEntity, T targetEntity);
    
    /**
     * Gets the ID of an entity as a string.
     * This is used for matching entities between source and target.
     *
     * @param entity The entity
     * @return The entity ID as a string
     */
    Object getEntityId(T entity);
}