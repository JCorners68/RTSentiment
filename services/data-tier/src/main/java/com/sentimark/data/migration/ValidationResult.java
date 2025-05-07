package com.sentimark.data.migration;

import java.util.ArrayList;
import java.util.List;

/**
 * Result of validating a migrated entity.
 * Contains details about any validation issues found.
 */
public class ValidationResult {
    private final String entityId;
    private final List<String> issues;
    
    /**
     * Creates a new ValidationResult.
     *
     * @param entityId The ID of the entity
     */
    public ValidationResult(String entityId) {
        this.entityId = entityId;
        this.issues = new ArrayList<>();
    }
    
    /**
     * Creates a new ValidationResult with an initial issue.
     *
     * @param entityId The ID of the entity
     * @param issue The validation issue
     */
    public ValidationResult(String entityId, String issue) {
        this.entityId = entityId;
        this.issues = new ArrayList<>();
        this.issues.add(issue);
    }
    
    /**
     * Gets the ID of the entity.
     *
     * @return the entity ID
     */
    public String getEntityId() {
        return entityId;
    }
    
    /**
     * Gets the list of validation issues.
     *
     * @return the issues
     */
    public List<String> getIssues() {
        return issues;
    }
    
    /**
     * Adds a validation issue.
     *
     * @param issue the issue to add
     */
    public void addIssue(String issue) {
        issues.add(issue);
    }
    
    /**
     * Checks if the validation is valid (no issues).
     *
     * @return true if valid, false if there are issues
     */
    public boolean isValid() {
        return issues.isEmpty();
    }
    
    /**
     * Creates a valid result.
     *
     * @param entityId The ID of the entity
     * @return a valid validation result
     */
    public static ValidationResult valid(String entityId) {
        return new ValidationResult(entityId);
    }
    
    /**
     * Creates an invalid result with an issue.
     *
     * @param entityId The ID of the entity
     * @param issue The validation issue
     * @return an invalid validation result
     */
    public static ValidationResult invalid(String entityId, String issue) {
        return new ValidationResult(entityId, issue);
    }
}