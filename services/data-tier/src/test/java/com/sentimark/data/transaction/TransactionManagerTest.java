package com.sentimark.data.transaction;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.sql.Connection;
import java.sql.SQLException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import com.sentimark.data.exception.ConnectionException;

public class TransactionManagerTest {

    @Mock
    private Connection mockConnection;
    
    private PostgresTransactionManager transactionManager;
    
    @BeforeEach
    public void setUp() {
        MockitoAnnotations.openMocks(this);
        transactionManager = new PostgresTransactionManager(() -> mockConnection);
    }
    
    @Test
    public void testBeginTransaction() throws SQLException {
        // Given
        when(mockConnection.getAutoCommit()).thenReturn(true);
        
        // When
        transactionManager.begin();
        
        // Then
        verify(mockConnection).setAutoCommit(false);
        assertTrue(transactionManager.isTransactionActive());
    }
    
    @Test
    public void testCommitTransaction() throws SQLException {
        // Given
        when(mockConnection.getAutoCommit()).thenReturn(true);
        transactionManager.begin();
        
        // When
        transactionManager.commit();
        
        // Then
        verify(mockConnection).commit();
        verify(mockConnection).setAutoCommit(true);
        assertFalse(transactionManager.isTransactionActive());
    }
    
    @Test
    public void testRollbackTransaction() throws SQLException {
        // Given
        when(mockConnection.getAutoCommit()).thenReturn(true);
        transactionManager.begin();
        
        // When
        transactionManager.rollback();
        
        // Then
        verify(mockConnection).rollback();
        verify(mockConnection).setAutoCommit(true);
        assertFalse(transactionManager.isTransactionActive());
    }
    
    @Test
    public void testNestedTransactions() throws SQLException {
        // Given
        when(mockConnection.getAutoCommit()).thenReturn(true);
        
        // When - Begin outer transaction
        transactionManager.begin();
        
        // Then
        verify(mockConnection).setAutoCommit(false);
        
        // When - Begin nested transaction
        transactionManager.begin();
        
        // Then - No additional calls to connection
        verify(mockConnection, times(1)).setAutoCommit(false);
        
        // When - Commit nested transaction
        transactionManager.commit();
        
        // Then - No commit yet
        verify(mockConnection, never()).commit();
        
        // When - Commit outer transaction
        transactionManager.commit();
        
        // Then - Now we commit
        verify(mockConnection).commit();
        verify(mockConnection).setAutoCommit(true);
        assertFalse(transactionManager.isTransactionActive());
    }
    
    @Test
    public void testRollbackNestedTransactions() throws SQLException {
        // Given
        when(mockConnection.getAutoCommit()).thenReturn(true);
        
        // Begin outer transaction
        transactionManager.begin();
        
        // Begin nested transaction
        transactionManager.begin();
        
        // When - Rollback nested transaction
        transactionManager.rollback();
        
        // Then - Entire transaction is rolled back
        verify(mockConnection).rollback();
        verify(mockConnection).setAutoCommit(true);
        assertFalse(transactionManager.isTransactionActive());
    }
    
    @Test
    public void testExecuteInTransaction() throws SQLException {
        // Given
        when(mockConnection.getAutoCommit()).thenReturn(true);
        
        // When
        String result = transactionManager.executeInTransaction(() -> {
            // Simulate some work
            return "Success";
        });
        
        // Then
        assertEquals("Success", result);
        verify(mockConnection).setAutoCommit(false);
        verify(mockConnection).commit();
        verify(mockConnection).setAutoCommit(true);
    }
    
    @Test
    public void testExecuteInTransactionWithException() throws SQLException {
        // Given
        when(mockConnection.getAutoCommit()).thenReturn(true);
        
        // When/Then
        assertThrows(RuntimeException.class, () -> {
            transactionManager.executeInTransaction(() -> {
                throw new RuntimeException("Test exception");
            });
        });
        
        // Verify rollback was called
        verify(mockConnection).rollback();
        verify(mockConnection).setAutoCommit(true);
    }
    
    @Test
    public void testExecuteInTransactionWithSQLException() throws SQLException {
        // Given
        when(mockConnection.getAutoCommit()).thenReturn(true);
        doThrow(new SQLException("Database error")).when(mockConnection).commit();
        
        // When/Then
        assertThrows(ConnectionException.class, () -> {
            transactionManager.executeInTransaction(() -> "Should fail");
        });
        
        // Verify rollback was called
        verify(mockConnection).rollback();
        verify(mockConnection).setAutoCommit(true);
    }
}