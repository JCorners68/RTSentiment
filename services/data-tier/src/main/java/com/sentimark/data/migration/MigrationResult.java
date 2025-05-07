package com.sentimark.data.migration;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Result of a data migration operation.
 * Contains statistics and details about the migration process.
 */
public class MigrationResult {
    private boolean success;
    private String errorMessage;
    private int totalRecords;
    private int successCount;
    private int failureCount;
    private double progress;
    private final List<ValidationResult> validationIssues = new ArrayList<>();
    private final Map<Object, Exception> failures = new HashMap<>();
    
    /**
     * Default constructor.
     */
    public MigrationResult() {
        this.success = false;
        this.errorMessage = null;
        this.totalRecords = 0;
        this.successCount = 0;
        this.failureCount = 0;
        this.progress = 0.0;
    }
    
    /**
     * Gets whether the migration succeeded.
     *
     * @return true if the migration succeeded, false otherwise
     */
    public boolean isSuccess() {
        return success;
    }
    
    /**
     * Sets whether the migration succeeded.
     *
     * @param success true if the migration succeeded, false otherwise
     */
    public void setSuccess(boolean success) {
        this.success = success;
    }
    
    /**
     * Gets the error message, if any.
     *
     * @return the error message, or null if no error occurred
     */
    public String getErrorMessage() {
        return errorMessage;
    }
    
    /**
     * Sets the error message.
     *
     * @param errorMessage the error message
     */
    public void setErrorMessage(String errorMessage) {
        this.errorMessage = errorMessage;
    }
    
    /**
     * Gets the total number of records processed.
     *
     * @return the total number of records
     */
    public int getTotalRecords() {
        return totalRecords;
    }
    
    /**
     * Sets the total number of records to process.
     *
     * @param totalRecords the total number of records
     */
    public void setTotalRecords(int totalRecords) {
        this.totalRecords = totalRecords;
    }
    
    /**
     * Gets the number of records successfully migrated.
     *
     * @return the success count
     */
    public int getSuccessCount() {
        return successCount;
    }
    
    /**
     * Increments the success count by 1.
     */
    public void incrementSuccessCount() {
        this.successCount++;
        updateProgress();
    }
    
    /**
     * Increments the success count by the specified amount.
     *
     * @param count the amount to increment
     */
    public void incrementSuccessCount(int count) {
        this.successCount += count;
        updateProgress();
    }
    
    /**
     * Gets the number of records that failed to migrate.
     *
     * @return the failure count
     */
    public int getFailureCount() {
        return failureCount;
    }
    
    /**
     * Increments the failure count by 1.
     */
    public void incrementFailureCount() {
        this.failureCount++;
        updateProgress();
    }
    
    /**
     * Increments the failure count by the specified amount.
     *
     * @param count the amount to increment
     */
    public void incrementFailureCount(int count) {
        this.failureCount += count;
        updateProgress();
    }
    
    /**
     * Gets the progress of the migration (0.0 to 1.0).
     *
     * @return the progress
     */
    public double getProgress() {
        return progress;
    }
    
    /**
     * Sets the progress of the migration.
     *
     * @param progress the progress (0.0 to 1.0)
     */
    public void setProgress(double progress) {
        this.progress = progress;
    }
    
    /**
     * Updates the progress based on success and failure counts.
     */
    private void updateProgress() {
        if (totalRecords > 0) {
            this.progress = (double) (successCount + failureCount) / totalRecords;
        }
    }
    
    /**
     * Gets the list of validation issues.
     *
     * @return the validation issues
     */
    public List<ValidationResult> getValidationIssues() {
        return validationIssues;
    }
    
    /**
     * Adds a validation issue.
     *
     * @param issue the validation issue
     */
    public void addValidationIssue(ValidationResult issue) {
        validationIssues.add(issue);
    }
    
    /**
     * Adds multiple validation issues.
     *
     * @param issues the validation issues
     */
    public void addValidationIssues(List<ValidationResult> issues) {
        validationIssues.addAll(issues);
    }
    
    /**
     * Gets the map of failed entities and their exceptions.
     *
     * @return the failures
     */
    public Map<Object, Exception> getFailures() {
        return failures;
    }
    
    /**
     * Adds a failure.
     *
     * @param entity the entity that failed
     * @param exception the exception that occurred
     */
    public void addFailure(Object entity, Exception exception) {
        failures.put(entity, exception);
    }
    
    /**
     * Adds multiple failures.
     *
     * @param failures the failures to add
     */
    public void addFailures(Map<?, Exception> failures) {
        for (Map.Entry<?, Exception> entry : failures.entrySet()) {
            this.failures.put(entry.getKey(), entry.getValue());
        }
    }
}