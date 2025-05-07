package com.sentimark.data.monitoring;

import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.HashMap;
import java.util.Map;

/**
 * Aspect for monitoring repository method performance.
 */
@Aspect
@Component
public class RepositoryMonitoringAspect {
    
    private final PerformanceMonitoringService monitoringService;
    
    @Autowired
    public RepositoryMonitoringAspect(PerformanceMonitoringService monitoringService) {
        this.monitoringService = monitoringService;
    }
    
    /**
     * Monitor the performance of repository methods.
     *
     * @param joinPoint the join point
     * @return the result of the method
     * @throws Throwable if an error occurs
     */
    @Around("execution(* com.sentimark.data.repository.*Repository.*(..))")
    public Object monitorRepositoryMethod(ProceedingJoinPoint joinPoint) throws Throwable {
        String methodName = joinPoint.getSignature().getName();
        String className = joinPoint.getTarget().getClass().getSimpleName();
        String queryType = className + "." + methodName;
        
        Map<String, Object> parameters = new HashMap<>();
        Object[] args = joinPoint.getArgs();
        String[] paramNames = ((MethodSignature) joinPoint.getSignature()).getParameterNames();
        
        for (int i = 0; i < args.length && i < paramNames.length; i++) {
            // Avoid adding large objects to the parameters map
            if (args[i] != null && !args[i].getClass().isArray() && 
                (args[i] instanceof String || args[i] instanceof Number || args[i] instanceof Boolean)) {
                parameters.put(paramNames[i], args[i]);
            } else {
                parameters.put(paramNames[i], args[i] != null ? args[i].getClass().getSimpleName() : "null");
            }
        }
        
        QueryMetrics metrics = monitoringService.startQueryMetrics(queryType, queryType, parameters);
        
        try {
            Object result = joinPoint.proceed();
            metrics.markComplete();
            return result;
        } catch (Exception e) {
            metrics.markError(e);
            throw e;
        } finally {
            monitoringService.recordMetrics(metrics);
        }
    }
}