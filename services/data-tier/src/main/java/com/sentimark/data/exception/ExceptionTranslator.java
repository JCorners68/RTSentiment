package com.sentimark.data.exception;

/**
 * Interface for translating database-specific exceptions to application exceptions.
 */
public interface ExceptionTranslator {
    
    /**
     * Translate an exception to an application exception.
     *
     * @param e the exception to translate
     * @return a RuntimeException representing the translated exception
     */
    RuntimeException translate(Exception e);
    
    /**
     * Translate an exception to an application exception with contextual information.
     *
     * @param e the exception to translate
     * @param contextMessage additional context for the error
     * @return a RuntimeException representing the translated exception
     */
    RuntimeException translate(Exception e, String contextMessage);
}