package com.sentimark.data.migration;

import java.util.ArrayList;
import java.util.List;

/**
 * Summary of validation between two repositories.
 * Contains statistics about data consistency between source and target.
 */
public class ValidationSummary {
    private int sourceCount;
    private int targetCount;
    private int missingInTarget;
    private int missingInSource;
    private int differenceCount;
    private double successPercentage;
    private String errorMessage;
    private List<ValidationResult> validationIssues;
    
    /**
     * Default constructor.
     */
    public ValidationSummary() {
        this.sourceCount = 0;
        this.targetCount = 0;
        this.missingInTarget = 0;
        this.missingInSource = 0;
        this.differenceCount = 0;
        this.successPercentage = 0.0;
        this.errorMessage = null;
        this.validationIssues = new ArrayList<>();
    }
    
    /**
     * Gets the count of entities in the source repository.
     *
     * @return the source count
     */
    public int getSourceCount() {
        return sourceCount;
    }
    
    /**
     * Sets the count of entities in the source repository.
     *
     * @param sourceCount the source count
     */
    public void setSourceCount(int sourceCount) {
        this.sourceCount = sourceCount;
    }
    
    /**
     * Gets the count of entities in the target repository.
     *
     * @return the target count
     */
    public int getTargetCount() {
        return targetCount;
    }
    
    /**
     * Sets the count of entities in the target repository.
     *
     * @param targetCount the target count
     */
    public void setTargetCount(int targetCount) {
        this.targetCount = targetCount;
    }
    
    /**
     * Gets the count of entities missing in the target repository.
     *
     * @return the missing in target count
     */
    public int getMissingInTarget() {
        return missingInTarget;
    }
    
    /**
     * Sets the count of entities missing in the target repository.
     *
     * @param missingInTarget the missing in target count
     */
    public void setMissingInTarget(int missingInTarget) {
        this.missingInTarget = missingInTarget;
    }
    
    /**
     * Gets the count of entities missing in the source repository (extras in target).
     *
     * @return the missing in source count
     */
    public int getMissingInSource() {
        return missingInSource;
    }
    
    /**
     * Sets the count of entities missing in the source repository.
     *
     * @param missingInSource the missing in source count
     */
    public void setMissingInSource(int missingInSource) {
        this.missingInSource = missingInSource;
    }
    
    /**
     * Gets the count of entities that have differences between source and target.
     *
     * @return the difference count
     */
    public int getDifferenceCount() {
        return differenceCount;
    }
    
    /**
     * Sets the count of entities that have differences.
     *
     * @param differenceCount the difference count
     */
    public void setDifferenceCount(int differenceCount) {
        this.differenceCount = differenceCount;
    }
    
    /**
     * Gets the success percentage (entities that match perfectly).
     *
     * @return the success percentage (0-100)
     */
    public double getSuccessPercentage() {
        return successPercentage;
    }
    
    /**
     * Sets the success percentage.
     *
     * @param successPercentage the success percentage (0-100)
     */
    public void setSuccessPercentage(double successPercentage) {
        this.successPercentage = successPercentage;
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
     * Gets the list of validation issues.
     *
     * @return the validation issues
     */
    public List<ValidationResult> getValidationIssues() {
        return validationIssues;
    }
    
    /**
     * Sets the list of validation issues.
     *
     * @param validationIssues the validation issues
     */
    public void setValidationIssues(List<ValidationResult> validationIssues) {
        this.validationIssues = validationIssues;
    }
    
    /**
     * Checks if the validation is successful.
     * Success is defined as no missing entities and no differences.
     *
     * @return true if successful, false otherwise
     */
    public boolean isSuccessful() {
        return errorMessage == null && missingInTarget == 0 && differenceCount == 0;
    }
    
    /**
     * Checks if there are any inconsistencies.
     * Inconsistencies include missing entities, differences, or errors.
     *
     * @return true if there are inconsistencies, false otherwise
     */
    public boolean hasInconsistencies() {
        return errorMessage != null || missingInTarget > 0 || missingInSource > 0 || differenceCount > 0;
    }
}