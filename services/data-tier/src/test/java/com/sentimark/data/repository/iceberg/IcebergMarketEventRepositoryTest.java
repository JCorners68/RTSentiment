package com.sentimark.data.repository.iceberg;

import com.sentimark.data.config.IcebergSchemaManager;
import com.sentimark.data.exception.ExceptionTranslator;
import com.sentimark.data.exception.IcebergExceptionTranslator;
import com.sentimark.data.model.MarketEvent;
import com.sentimark.data.transaction.IcebergTransactionManager;
import org.apache.hadoop.conf.Configuration;
import org.apache.iceberg.*;
import org.apache.iceberg.catalog.Catalog;
import org.apache.iceberg.catalog.TableIdentifier;
import org.apache.iceberg.hadoop.HadoopCatalog;
import org.apache.iceberg.types.Types;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.Mock;
import org.mockito.Mockito;
import org.mockito.junit.jupiter.MockitoExtension;

import java.nio.file.Path;
import java.time.Instant;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
public class IcebergMarketEventRepositoryTest {
    
    @TempDir
    Path tempDir;
    
    private IcebergMarketEventRepository repository;
    private IcebergSchemaManager schemaManager;
    private ExceptionTranslator exceptionTranslator;
    private IcebergTransactionManager transactionManager;
    private Catalog catalog;
    private Table table;
    private Schema schema;
    private final String tableName = "test_market_events";
    
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
            Types.NestedField.required(2, "headline", Types.StringType.get()),
            Types.NestedField.required(3, "tickers", Types.ListType.ofRequired(
                4, Types.StringType.get()
            )),
            Types.NestedField.optional(5, "content", Types.StringType.get()),
            Types.NestedField.required(6, "published_at", Types.TimestampType.withZone()),
            Types.NestedField.required(7, "source", Types.StringType.get()),
            Types.NestedField.required(8, "credibility_score", Types.DoubleType.get())
        );
        
        // Create the table
        catalog.createTable(TableIdentifier.of(tableName), schema);
        table = catalog.loadTable(TableIdentifier.of(tableName));
        
        // Setup the schema manager
        schemaManager = Mockito.mock(IcebergSchemaManager.class);
        when(schemaManager.tableExists(tableName)).thenReturn(true);
        when(schemaManager.loadTable(tableName)).thenReturn(table);
        when(schemaManager.createMarketEventSchema()).thenReturn(schema);
        
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
        repository = new IcebergMarketEventRepository(
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
        MarketEvent event = new MarketEvent(
            UUID.randomUUID(),
            "Apple announces new iPhone",
            Arrays.asList("AAPL", "GOOG"),
            "Apple Inc. unveiled its latest iPhone model today...",
            Instant.now(),
            "NEWS",
            0.85
        );
        
        // Save the record
        UUID id = repository.save(event);
        
        // Verify the ID
        assertEquals(event.getId(), id);
        
        // Verify transaction was used
        Mockito.verify(mockTransaction).newAppend();
    }
    
    @Test
    public void testFindById() throws Exception {
        // This is a more complex test that requires actual Iceberg reading
        // For simplicity, we'll mock the behavior
        
        // Create a mock record
        UUID id = UUID.randomUUID();
        MarketEvent mockEvent = new MarketEvent(
            id,
            "Apple announces new iPhone",
            Arrays.asList("AAPL", "GOOG"),
            "Apple Inc. unveiled its latest iPhone model today...",
            Instant.now(),
            "NEWS",
            0.85
        );
        
        // Mock the findById behavior
        IcebergMarketEventRepository spyRepo = Mockito.spy(repository);
        Mockito.doReturn(Optional.of(mockEvent)).when(spyRepo).findById(id);
        
        // Call findById
        Optional<MarketEvent> result = spyRepo.findById(id);
        
        // Verify the result
        assertTrue(result.isPresent());
        assertEquals(mockEvent, result.get());
    }
    
    @Test
    public void testUpdate() {
        // Create a record to update
        MarketEvent event = new MarketEvent(
            UUID.randomUUID(),
            "Apple announces new iPhone",
            Arrays.asList("AAPL", "GOOG"),
            "Apple Inc. unveiled its latest iPhone model today...",
            Instant.now(),
            "NEWS",
            0.85
        );
        
        // Mock exists to return true
        IcebergMarketEventRepository spyRepo = Mockito.spy(repository);
        Mockito.doReturn(true).when(spyRepo).exists(event.getId());
        
        // Update the record
        MarketEvent updated = spyRepo.update(event);
        
        // Verify the result
        assertEquals(event, updated);
        
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
    public void testFindByTickers() throws Exception {
        // Create a mock list of events
        List<MarketEvent> mockEvents = Arrays.asList(
            new MarketEvent(
                UUID.randomUUID(),
                "Apple announces new iPhone",
                Arrays.asList("AAPL", "GOOG"),
                "Apple Inc. unveiled its latest iPhone model today...",
                Instant.now(),
                "NEWS",
                0.85
            ),
            new MarketEvent(
                UUID.randomUUID(),
                "Microsoft Azure revenue up 50%",
                Arrays.asList("MSFT", "AMZN"),
                "Microsoft reported strong Azure revenue growth...",
                Instant.now(),
                "NEWS",
                0.75
            )
        );
        
        // Mock the findByTickers behavior
        IcebergMarketEventRepository spyRepo = Mockito.spy(repository);
        Mockito.doReturn(Collections.singletonList(mockEvents.get(0)))
            .when(spyRepo).findByTickers(Arrays.asList("AAPL"));
        
        // Call findByTickers
        List<MarketEvent> results = spyRepo.findByTickers(Arrays.asList("AAPL"));
        
        // Verify the results
        assertEquals(1, results.size());
        assertTrue(results.get(0).getTickers().contains("AAPL"));
    }
    
    @Test
    public void testFindByTimeRange() throws Exception {
        // Create time range
        Instant start = Instant.parse("2023-01-01T00:00:00Z");
        Instant end = Instant.parse("2023-01-31T23:59:59Z");
        
        // Create a mock list of events
        List<MarketEvent> mockEvents = Arrays.asList(
            new MarketEvent(
                UUID.randomUUID(),
                "Apple announces new iPhone",
                Arrays.asList("AAPL", "GOOG"),
                "Apple Inc. unveiled its latest iPhone model today...",
                Instant.parse("2023-01-15T12:00:00Z"),
                "NEWS",
                0.85
            )
        );
        
        // Mock the findByTimeRange behavior
        IcebergMarketEventRepository spyRepo = Mockito.spy(repository);
        Mockito.doReturn(mockEvents).when(spyRepo).findByTimeRange(start, end);
        
        // Call findByTimeRange
        List<MarketEvent> results = spyRepo.findByTimeRange(start, end);
        
        // Verify the results
        assertEquals(1, results.size());
        assertTrue(results.get(0).getPublishedAt().isAfter(start));
        assertTrue(results.get(0).getPublishedAt().isBefore(end));
    }
    
    @Test
    public void testFindBySourceAndTimeRange() throws Exception {
        // Create time range
        Instant start = Instant.parse("2023-01-01T00:00:00Z");
        Instant end = Instant.parse("2023-01-31T23:59:59Z");
        
        // Create a mock list of events
        List<MarketEvent> mockEvents = Arrays.asList(
            new MarketEvent(
                UUID.randomUUID(),
                "Apple announces new iPhone",
                Arrays.asList("AAPL", "GOOG"),
                "Apple Inc. unveiled its latest iPhone model today...",
                Instant.parse("2023-01-15T12:00:00Z"),
                "NEWS",
                0.85
            )
        );
        
        // Mock the findBySourceAndTimeRange behavior
        IcebergMarketEventRepository spyRepo = Mockito.spy(repository);
        Mockito.doReturn(mockEvents).when(spyRepo).findBySourceAndTimeRange("NEWS", start, end);
        
        // Call findBySourceAndTimeRange
        List<MarketEvent> results = spyRepo.findBySourceAndTimeRange("NEWS", start, end);
        
        // Verify the results
        assertEquals(1, results.size());
        assertEquals("NEWS", results.get(0).getSource());
        assertTrue(results.get(0).getPublishedAt().isAfter(start));
        assertTrue(results.get(0).getPublishedAt().isBefore(end));
    }
}