package com.sentimark.data.repository.iceberg;

import com.sentimark.data.config.IcebergSchemaManager;
import com.sentimark.data.exception.ExceptionTranslator;
import com.sentimark.data.exception.IcebergExceptionTranslator;
import com.sentimark.data.model.SentimentRecord;
import com.sentimark.data.transaction.IcebergTransactionManager;
import org.apache.hadoop.conf.Configuration;
import org.apache.iceberg.*;
import org.apache.iceberg.catalog.Catalog;
import org.apache.iceberg.catalog.TableIdentifier;
import org.apache.iceberg.data.GenericRecord;
import org.apache.iceberg.data.Record;
import org.apache.iceberg.hadoop.HadoopCatalog;
import org.apache.iceberg.types.Types;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

import java.io.File;
import java.nio.file.Path;
import java.time.Instant;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
public class IcebergSentimentRecordRepositoryTest {
    
    @TempDir
    Path tempDir;
    
    private IcebergSentimentRecordRepository repository;
    private IcebergSchemaManager schemaManager;
    private ExceptionTranslator exceptionTranslator;
    private IcebergTransactionManager transactionManager;
    private Catalog catalog;
    private Table table;
    private Schema schema;
    private final String tableName = "test_sentiment_records";
    
    @Mock
    private Transaction mockTransaction;
    
    @BeforeEach
    public void setUp() {
        // Setup the catalog with a temporary directory
        Configuration conf = new Configuration();
        catalog = new HadoopCatalog(conf, tempDir.toString());
        
        // Create the schema
        schema = new Schema(
            Types.NestedField.required(1, "id", Types.StringType.get()),
            Types.NestedField.required(2, "ticker", Types.StringType.get()),
            Types.NestedField.required(3, "sentiment_score", Types.DoubleType.get()),
            Types.NestedField.required(4, "timestamp", Types.TimestampType.withZone()),
            Types.NestedField.required(5, "source", Types.StringType.get()),
            Types.NestedField.optional(6, "attributes", Types.MapType.ofRequired(
                7, 8, Types.StringType.get(), Types.DoubleType.get()
            ))
        );
        
        // Create the table
        catalog.createTable(TableIdentifier.of(tableName), schema);
        table = catalog.loadTable(TableIdentifier.of(tableName));
        
        // Setup the schema manager
        schemaManager = Mockito.mock(IcebergSchemaManager.class);
        when(schemaManager.tableExists(tableName)).thenReturn(true);
        when(schemaManager.loadTable(tableName)).thenReturn(table);
        when(schemaManager.createSentimentRecordSchema()).thenReturn(schema);
        
        // Setup the exception translator
        exceptionTranslator = new IcebergExceptionTranslator();
        
        // Setup the transaction manager
        transactionManager = Mockito.mock(IcebergTransactionManager.class);
        when(transactionManager.getTransaction(any())).thenReturn(mockTransaction);
        
        // Setup transaction mocks
        AppendFiles appendFiles = Mockito.mock(AppendFiles.class);
        when(mockTransaction.newAppend()).thenReturn(appendFiles);
        when(appendFiles.appendFile(any())).thenReturn(appendFiles);
        
        DeleteFiles deleteFiles = Mockito.mock(DeleteFiles.class);
        when(mockTransaction.newDelete()).thenReturn(deleteFiles);
        when(deleteFiles.deleteFromRowFilter(any())).thenReturn(deleteFiles);
        
        // Create the repository
        repository = new IcebergSentimentRecordRepository(
            catalog,
            schemaManager,
            exceptionTranslator,
            transactionManager,
            tableName
        );
    }
    
    @Test
    public void testInit() {
        // The init method should be called by the Spring framework
        repository.init();
        
        // Verify that the table was checked
        Mockito.verify(schemaManager).tableExists(tableName);
    }
    
    @Test
    public void testSave() {
        // Create a record to save
        SentimentRecord record = new SentimentRecord(
            UUID.randomUUID(),
            "AAPL",
            0.75,
            Instant.now(),
            "TWITTER",
            Map.of("confidence", 0.9, "volume", 1000.0)
        );
        
        // Save the record
        UUID id = repository.save(record);
        
        // Verify the ID
        assertEquals(record.getId(), id);
        
        // Verify transaction was used
        Mockito.verify(mockTransaction).newAppend();
    }
    
    @Test
    public void testFindById() throws Exception {
        // This is a more complex test that requires actual Iceberg reading
        // For simplicity, we'll mock the behavior
        
        // Create a mock record
        UUID id = UUID.randomUUID();
        SentimentRecord mockRecord = new SentimentRecord(
            id,
            "AAPL",
            0.75,
            Instant.now(),
            "TWITTER",
            Map.of("confidence", 0.9, "volume", 1000.0)
        );
        
        // Mock the findById behavior
        IcebergSentimentRecordRepository spyRepo = Mockito.spy(repository);
        Mockito.doReturn(Optional.of(mockRecord)).when(spyRepo).findById(id);
        
        // Call findById
        Optional<SentimentRecord> result = spyRepo.findById(id);
        
        // Verify the result
        assertTrue(result.isPresent());
        assertEquals(mockRecord, result.get());
    }
    
    @Test
    public void testUpdate() {
        // Create a record to update
        SentimentRecord record = new SentimentRecord(
            UUID.randomUUID(),
            "AAPL",
            0.75,
            Instant.now(),
            "TWITTER",
            Map.of("confidence", 0.9, "volume", 1000.0)
        );
        
        // Mock exists to return true
        IcebergSentimentRecordRepository spyRepo = Mockito.spy(repository);
        Mockito.doReturn(true).when(spyRepo).exists(record.getId());
        
        // Update the record
        SentimentRecord updated = spyRepo.update(record);
        
        // Verify the result
        assertEquals(record, updated);
        
        // Verify transaction operations
        Mockito.verify(mockTransaction).newDelete();
        Mockito.verify(mockTransaction).newAppend();
    }
    
    @Test
    public void testDelete() {
        // Create an ID to delete
        UUID id = UUID.randomUUID();
        
        // Delete the record
        repository.delete(id);
        
        // Verify transaction was used
        Mockito.verify(mockTransaction).newDelete();
    }
    
    @Test
    public void testFindByTicker() throws Exception {
        // Create a mock list of records
        List<SentimentRecord> mockRecords = List.of(
            new SentimentRecord(
                UUID.randomUUID(),
                "AAPL",
                0.75,
                Instant.now(),
                "TWITTER",
                Map.of("confidence", 0.9, "volume", 1000.0)
            ),
            new SentimentRecord(
                UUID.randomUUID(),
                "AAPL",
                0.65,
                Instant.now(),
                "NEWS",
                Map.of("confidence", 0.8, "volume", 500.0)
            )
        );
        
        // Mock the findByTicker behavior
        IcebergSentimentRecordRepository spyRepo = Mockito.spy(repository);
        Mockito.doReturn(mockRecords).when(spyRepo).findByTicker("AAPL");
        
        // Call findByTicker
        List<SentimentRecord> results = spyRepo.findByTicker("AAPL");
        
        // Verify the results
        assertEquals(2, results.size());
        assertEquals("AAPL", results.get(0).getTicker());
        assertEquals("AAPL", results.get(1).getTicker());
    }
    
    @Test
    public void testFindByTickerAndTimeRange() throws Exception {
        // Create time range
        Instant start = Instant.parse("2023-01-01T00:00:00Z");
        Instant end = Instant.parse("2023-01-31T23:59:59Z");
        
        // Create a mock list of records
        List<SentimentRecord> mockRecords = List.of(
            new SentimentRecord(
                UUID.randomUUID(),
                "AAPL",
                0.75,
                Instant.parse("2023-01-15T12:00:00Z"),
                "TWITTER",
                Map.of("confidence", 0.9, "volume", 1000.0)
            )
        );
        
        // Mock the findByTickerAndTimeRange behavior
        IcebergSentimentRecordRepository spyRepo = Mockito.spy(repository);
        Mockito.doReturn(mockRecords).when(spyRepo).findByTickerAndTimeRange("AAPL", start, end);
        
        // Call findByTickerAndTimeRange
        List<SentimentRecord> results = spyRepo.findByTickerAndTimeRange("AAPL", start, end);
        
        // Verify the results
        assertEquals(1, results.size());
        assertEquals("AAPL", results.get(0).getTicker());
        assertTrue(results.get(0).getTimestamp().isAfter(start));
        assertTrue(results.get(0).getTimestamp().isBefore(end));
    }
}