package com.sentimark.data.transaction;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 * Aspect for handling transactional methods.
 */
@Aspect
@Component
public class TransactionAspect {
    
    private final TransactionManager transactionManager;
    
    @Autowired
    public TransactionAspect(TransactionManager transactionManager) {
        this.transactionManager = transactionManager;
    }
    
    /**
     * Execute methods annotated with @Transactional within a transaction.
     *
     * @param joinPoint the join point
     * @return the result of the method
     * @throws Throwable if an error occurs
     */
    @Around("@annotation(com.sentimark.data.transaction.Transactional)")
    public Object aroundTransactionalMethod(ProceedingJoinPoint joinPoint) throws Throwable {
        return transactionManager.executeInTransaction(() -> {
            try {
                return joinPoint.proceed();
            } catch (Throwable e) {
                if (e instanceof RuntimeException) {
                    throw (RuntimeException) e;
                } else {
                    throw new RuntimeException(e);
                }
            }
        });
    }
}