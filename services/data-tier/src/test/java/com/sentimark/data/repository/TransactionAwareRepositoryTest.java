package com.sentimark.data.repository;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.Collections;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;

import com.sentimark.data.exception.DatabaseException;
import com.sentimark.data.exception.ExceptionTranslator;
import com.sentimark.data.model.SentimentRecord;
import com.sentimark.data.repository.postgres.PostgresSentimentRecordRepository;
import com.sentimark.data.transaction.PostgresTransactionManager;
import com.sentimark.data.transaction.TransactionManager;

public class TransactionAwareRepositoryTest {

    @Mock
    private Connection mockConnection;
    
    @Mock
    private PreparedStatement mockPreparedStatement;
    
    @Mock
    private ResultSet mockResultSet;
    
    @Mock
    private ExceptionTranslator exceptionTranslator;
    
    private TransactionManager transactionManager;
    private PostgresSentimentRecordRepository repository;
    
    @BeforeEach
    public void setUp() throws SQLException {
        MockitoAnnotations.openMocks(this);
        
        // Setup connection
        when(mockConnection.prepareStatement(anyString())).thenReturn(mockPreparedStatement);
        
        // Setup mock resultset
        when(mockPreparedStatement.executeQuery()).thenReturn(mockResultSet);
        when(mockResultSet.next()).thenReturn(true).thenReturn(false); // Return one row
        
        // Setup mock result data
        UUID mockId = UUID.randomUUID();
        when(mockResultSet.getObject("id", UUID.class)).thenReturn(mockId);
        when(mockResultSet.getString("ticker")).thenReturn("AAPL");
        when(mockResultSet.getDouble("sentiment_score")).thenReturn(0.75);
        when(mockResultSet.getObject("timestamp", Instant.class)).thenReturn(Instant.now());
        when(mockResultSet.getString("source")).thenReturn("TWITTER");
        
        // Setup exception translator
        when(exceptionTranslator.translate(any(SQLException.class))).thenReturn(new DatabaseException("Test exception"));
        
        // Create transaction manager and repository
        transactionManager = new PostgresTransactionManager(() -> mockConnection);
        repository = new PostgresSentimentRecordRepository(
            () -> mockConnection, 
            exceptionTranslator
        );
    }
    
    @Test
    public void testFindAllUsesActiveTransaction() throws SQLException {
        // Begin a transaction
        transactionManager.begin();
        
        // Execute repository method
        List<SentimentRecord> results = repository.findAll();
        
        // Verify connection wasn't closed (because we're in a transaction)
        verify(mockConnection, never()).close();
        
        // Verify we got results
        assertFalse(results.isEmpty());
        assertEquals("AAPL", results.get(0).getTicker());
        
        // Commit the transaction
        transactionManager.commit();
    }
    
    @Test
    public void testSaveUsesActiveTransaction() throws SQLException {
        // Begin a transaction
        transactionManager.begin();
        
        // Setup mock for save
        when(mockPreparedStatement.executeUpdate()).thenReturn(1);
        
        // Create entity to save
        SentimentRecord record = new SentimentRecord(
            UUID.randomUUID(),
            "MSFT",
            0.85,
            Instant.now(),
            "NEWS"
        );
        
        // Save the entity
        UUID savedId = repository.save(record);
        
        // Verify correct statement execution and no connection close
        verify(mockPreparedStatement).executeUpdate();
        verify(mockConnection, never()).close();
        
        // Commit the transaction
        transactionManager.commit();
        
        // Verify connection is now committed but not closed
        verify(mockConnection).commit();
    }
    
    @Test
    public void testTransactionRollbackOnException() throws SQLException {
        // Setup failure scenario
        when(mockPreparedStatement.executeUpdate()).thenThrow(new SQLException("Database error"));
        
        // Create entity to save
        SentimentRecord record = new SentimentRecord(
            UUID.randomUUID(),
            "MSFT",
            0.85,
            Instant.now(),
            "NEWS"
        );
        
        // Begin transaction
        transactionManager.begin();
        
        // Execute operation that will fail
        assertThrows(DatabaseException.class, () -> {
            repository.save(record);
        });
        
        // Rollback the transaction
        transactionManager.rollback();
        
        // Verify connection was rolled back
        verify(mockConnection).rollback();
    }
    
    @Test
    public void testCompleteTransactionFlow() throws SQLException {
        // Setup success scenario
        when(mockPreparedStatement.executeUpdate()).thenReturn(1);
        
        // Create records to save
        SentimentRecord record1 = new SentimentRecord(
            UUID.randomUUID(),
            "AAPL",
            0.75,
            Instant.now(),
            "TWITTER"
        );
        
        SentimentRecord record2 = new SentimentRecord(
            UUID.randomUUID(),
            "MSFT",
            0.85,
            Instant.now(),
            "NEWS"
        );
        
        // Execute the entire flow in a transaction
        transactionManager.executeInTransaction(() -> {
            repository.save(record1);
            repository.save(record2);
            return "Success";
        });
        
        // Verify connection was committed
        verify(mockConnection).commit();
        verify(mockConnection).setAutoCommit(true);
        verify(mockPreparedStatement, times(2)).executeUpdate();
    }
}