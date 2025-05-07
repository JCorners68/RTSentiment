package com.sentimark.data.repository.iceberg;

import com.sentimark.data.config.IcebergSchemaManager;
import com.sentimark.data.exception.DatabaseException;
import com.sentimark.data.exception.EntityNotFoundException;
import com.sentimark.data.exception.ExceptionTranslator;
import com.sentimark.data.model.MarketEvent;
import com.sentimark.data.repository.MarketEventRepository;
import com.sentimark.data.transaction.IcebergTransactionManager;
import com.sentimark.data.transaction.TransactionAwareRepository;
import org.apache.iceberg.*;
import org.apache.iceberg.catalog.Catalog;
import org.apache.iceberg.data.GenericRecord;
import org.apache.iceberg.data.parquet.GenericParquetWriter;
import org.apache.iceberg.expressions.Expressions;
import org.apache.iceberg.io.CloseableIterable;
import org.apache.iceberg.io.FileAppender;
import org.apache.iceberg.io.OutputFile;
import org.apache.iceberg.parquet.Parquet;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Repository;

import javax.annotation.PostConstruct;
import java.io.File;
import java.io.IOException;
import java.time.Instant;
import java.util.*;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Repository("icebergMarketEventRepository")
@Profile("iceberg")
public class IcebergMarketEventRepository implements MarketEventRepository, TransactionAwareRepository {
    
    private static final Logger logger = LoggerFactory.getLogger(IcebergMarketEventRepository.class);
    
    private final Catalog catalog;
    private final IcebergSchemaManager schemaManager;
    private final ExceptionTranslator exceptionTranslator;
    private final IcebergTransactionManager transactionManager;
    private final String tableName;
    
    @Autowired
    public IcebergMarketEventRepository(
            Catalog catalog,
            IcebergSchemaManager schemaManager,
            ExceptionTranslator exceptionTranslator,
            IcebergTransactionManager transactionManager,
            @Value("${iceberg.tables.market-events:market_events}") String tableName) {
        this.catalog = catalog;
        this.schemaManager = schemaManager;
        this.exceptionTranslator = exceptionTranslator;
        this.transactionManager = transactionManager;
        this.tableName = tableName;
    }
    
    @PostConstruct
    public void init() {
        try {
            // Create the table if it doesn't exist
            if (!schemaManager.tableExists(tableName)) {
                Schema schema = schemaManager.createMarketEventSchema();
                schemaManager.createTable(tableName, schema);
                logger.info("Created market events table: {}", tableName);
            }
        } catch (Exception e) {
            logger.error("Error initializing Iceberg repository: {}", e.getMessage(), e);
            throw new RuntimeException("Failed to initialize Iceberg repository", e);
        }
    }
    
    @Override
    public Optional<MarketEvent> findById(UUID id) {
        try {
            Table table = schemaManager.loadTable(tableName);
            
            CloseableIterable<org.apache.iceberg.data.Record> result = IcebergGenerics.read(table)
                .where(Expressions.equal("id", id.toString()))
                .build();
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = result) {
                for (org.apache.iceberg.data.Record record : records) {
                    return Optional.of(mapToMarketEvent(record));
                }
            }
            
            return Optional.empty();
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public List<MarketEvent> findAll() {
        try {
            Table table = schemaManager.loadTable(tableName);
            List<MarketEvent> results = new ArrayList<>();
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = 
                    IcebergGenerics.read(table).build()) {
                for (org.apache.iceberg.data.Record record : records) {
                    results.add(mapToMarketEvent(record));
                }
            }
            
            return results;
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public UUID save(MarketEvent entity) {
        if (entity.getId() == null) {
            entity.setId(UUID.randomUUID());
        }
        
        try {
            Table table = schemaManager.loadTable(tableName);
            
            // Create a record
            GenericRecord record = GenericRecord.create(table.schema());
            mapFromMarketEvent(entity, record);
            
            // Create a transaction if one doesn't exist
            Transaction transaction = transactionManager.getTransaction(table.newTransaction());
            
            // Create a data file from the record
            DataFile dataFile = writeDataFile(table, Collections.singletonList(record));
            
            // Append the data file to the transaction
            transaction.newAppend()
                     .appendFile(dataFile)
                     .commit();
            
            // If we're not in a managed transaction, commit immediately
            if (!transactionManager.isTransactionActive()) {
                transaction.commitTransaction();
            }
            
            return entity.getId();
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public MarketEvent update(MarketEvent entity) {
        if (entity.getId() == null) {
            throw new DatabaseException("Cannot update entity without ID");
        }
        
        try {
            Table table = schemaManager.loadTable(tableName);
            
            // Verify the entity exists
            if (!exists(entity.getId())) {
                throw new EntityNotFoundException("MarketEvent with ID " + entity.getId() + " not found");
            }
            
            // Delete the old record and insert the new one (Iceberg doesn't support updates directly)
            Transaction transaction = transactionManager.getTransaction(table.newTransaction());
            
            // Delete the old record
            transaction.newDelete()
                     .deleteFromRowFilter(Expressions.equal("id", entity.getId().toString()))
                     .commit();
            
            // Create a record for the updated entity
            GenericRecord record = GenericRecord.create(table.schema());
            mapFromMarketEvent(entity, record);
            
            // Create a data file from the record
            DataFile dataFile = writeDataFile(table, Collections.singletonList(record));
            
            // Append the data file to the transaction
            transaction.newAppend()
                     .appendFile(dataFile)
                     .commit();
            
            // If we're not in a managed transaction, commit immediately
            if (!transactionManager.isTransactionActive()) {
                transaction.commitTransaction();
            }
            
            return entity;
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public void delete(UUID id) {
        try {
            Table table = schemaManager.loadTable(tableName);
            
            // Create a transaction if one doesn't exist
            Transaction transaction = transactionManager.getTransaction(table.newTransaction());
            
            // Delete the record
            transaction.newDelete()
                     .deleteFromRowFilter(Expressions.equal("id", id.toString()))
                     .commit();
            
            // If we're not in a managed transaction, commit immediately
            if (!transactionManager.isTransactionActive()) {
                transaction.commitTransaction();
            }
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public boolean exists(UUID id) {
        return findById(id).isPresent();
    }
    
    @Override
    public List<MarketEvent> findByTickers(List<String> tickers) {
        try {
            Table table = schemaManager.loadTable(tableName);
            List<MarketEvent> results = new ArrayList<>();
            
            // This is a simplification - in a real implementation, we would use a more efficient
            // approach for searching within arrays in Iceberg
            try (CloseableIterable<org.apache.iceberg.data.Record> records = 
                    IcebergGenerics.read(table).build()) {
                for (org.apache.iceberg.data.Record record : records) {
                    MarketEvent event = mapToMarketEvent(record);
                    if (event.getTickers().stream().anyMatch(tickers::contains)) {
                        results.add(event);
                    }
                }
            }
            
            return results;
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public List<MarketEvent> findByTimeRange(Instant start, Instant end) {
        try {
            Table table = schemaManager.loadTable(tableName);
            List<MarketEvent> results = new ArrayList<>();
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = 
                    IcebergGenerics.read(table)
                        .where(Expressions.and(
                            Expressions.greaterThanOrEqual("published_at", start),
                            Expressions.lessThanOrEqual("published_at", end)
                        ))
                        .build()) {
                for (org.apache.iceberg.data.Record record : records) {
                    results.add(mapToMarketEvent(record));
                }
            }
            
            return results;
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public List<MarketEvent> findBySourceAndTimeRange(String source, Instant start, Instant end) {
        try {
            Table table = schemaManager.loadTable(tableName);
            List<MarketEvent> results = new ArrayList<>();
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = 
                    IcebergGenerics.read(table)
                        .where(Expressions.and(
                            Expressions.equal("source", source),
                            Expressions.greaterThanOrEqual("published_at", start),
                            Expressions.lessThanOrEqual("published_at", end)
                        ))
                        .build()) {
                for (org.apache.iceberg.data.Record record : records) {
                    results.add(mapToMarketEvent(record));
                }
            }
            
            return results;
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public void setTransaction(Object transaction) {
        // Do nothing, transactions are handled by IcebergTransactionManager
    }
    
    @Override
    public void clearTransaction() {
        // Do nothing, transactions are handled by IcebergTransactionManager
    }
    
    // Helper methods
    
    private MarketEvent mapToMarketEvent(org.apache.iceberg.data.Record record) {
        String idStr = (String) record.getField("id");
        UUID id = UUID.fromString(idStr);
        String headline = (String) record.getField("headline");
        
        @SuppressWarnings("unchecked")
        List<String> tickers = (List<String>) record.getField("tickers");
        
        String content = (String) record.getField("content");
        Instant publishedAt = (Instant) record.getField("published_at");
        String source = (String) record.getField("source");
        Double credibilityScore = (Double) record.getField("credibility_score");
        
        return new MarketEvent(id, headline, tickers, content, publishedAt, source, credibilityScore);
    }
    
    private void mapFromMarketEvent(MarketEvent entity, GenericRecord record) {
        record.setField("id", entity.getId().toString());
        record.setField("headline", entity.getHeadline());
        record.setField("tickers", entity.getTickers());
        record.setField("content", entity.getContent());
        record.setField("published_at", entity.getPublishedAt());
        record.setField("source", entity.getSource());
        record.setField("credibility_score", entity.getCredibilityScore());
    }
    
    private DataFile writeDataFile(Table table, List<GenericRecord> records) throws IOException {
        // Create a temporary file
        File tempFile = File.createTempFile("iceberg-", ".parquet");
        tempFile.delete(); // We only need the path
        
        // Create an output file
        OutputFile outputFile = table.io().newOutputFile(tempFile.getAbsolutePath());
        
        // Create a file appender
        FileAppender<org.apache.iceberg.data.Record> appender = Parquet.write(outputFile)
                .schema(table.schema())
                .createWriterFunc(GenericParquetWriter::buildWriter)
                .build();
        
        try (FileAppender<org.apache.iceberg.data.Record> fileAppender = appender) {
            // Write the records
            for (GenericRecord record : records) {
                fileAppender.add(record);
            }
        }
        
        // Create a data file from the written file
        return DataFiles.builder(table.spec())
                .withInputFile(outputFile.toInputFile())
                .withMetrics(appender.metrics())
                .build();
    }
}