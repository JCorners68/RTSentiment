package com.sentimark.data.repository.iceberg;

import com.sentimark.data.config.IcebergSchemaManager;
import com.sentimark.data.exception.DatabaseException;
import com.sentimark.data.exception.EntityNotFoundException;
import com.sentimark.data.exception.ExceptionTranslator;
import com.sentimark.data.model.SentimentRecord;
import com.sentimark.data.repository.CommandRepository;
import com.sentimark.data.repository.EnhancedSentimentRecordRepository;
import com.sentimark.data.repository.QueryRepository;
import com.sentimark.data.repository.SentimentRecordRepository;
import com.sentimark.data.specification.Specification;
import com.sentimark.data.transaction.IcebergTransactionManager;
import com.sentimark.data.transaction.TransactionAwareRepository;
import org.apache.hadoop.conf.Configuration;
import org.apache.iceberg.*;
import org.apache.iceberg.catalog.Catalog;
import org.apache.iceberg.data.GenericRecord;
import org.apache.iceberg.data.Record;
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
import java.util.stream.Stream;
import java.util.stream.StreamSupport;

@Repository("icebergSentimentRecordRepository")
@Profile("iceberg")
public class IcebergSentimentRecordRepository implements SentimentRecordRepository, 
                                                         EnhancedSentimentRecordRepository,
                                                         TransactionAwareRepository {
    
    private static final Logger logger = LoggerFactory.getLogger(IcebergSentimentRecordRepository.class);
    
    private final Catalog catalog;
    private final IcebergSchemaManager schemaManager;
    private final ExceptionTranslator exceptionTranslator;
    private final IcebergTransactionManager transactionManager;
    private final String tableName;
    
    @Autowired
    public IcebergSentimentRecordRepository(
            Catalog catalog,
            IcebergSchemaManager schemaManager,
            ExceptionTranslator exceptionTranslator,
            IcebergTransactionManager transactionManager,
            @Value("${iceberg.tables.sentiment-records:sentiment_records}") String tableName) {
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
                Schema schema = schemaManager.createSentimentRecordSchema();
                schemaManager.createTable(tableName, schema);
                logger.info("Created sentiment records table: {}", tableName);
            }
        } catch (Exception e) {
            logger.error("Error initializing Iceberg repository: {}", e.getMessage(), e);
            throw new RuntimeException("Failed to initialize Iceberg repository", e);
        }
    }
    
    @Override
    public Optional<SentimentRecord> findById(UUID id) {
        try {
            Table table = schemaManager.loadTable(tableName);
            
            CloseableIterable<org.apache.iceberg.data.Record> result = IcebergGenerics.read(table)
                .where(Expressions.equal("id", id.toString()))
                .build();
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = result) {
                for (org.apache.iceberg.data.Record record : records) {
                    return Optional.of(mapToSentimentRecord(record));
                }
            }
            
            return Optional.empty();
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public List<SentimentRecord> findAll() {
        try {
            Table table = schemaManager.loadTable(tableName);
            List<SentimentRecord> results = new ArrayList<>();
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = 
                    IcebergGenerics.read(table).build()) {
                for (org.apache.iceberg.data.Record record : records) {
                    results.add(mapToSentimentRecord(record));
                }
            }
            
            return results;
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public UUID save(SentimentRecord entity) {
        if (entity.getId() == null) {
            entity.setId(UUID.randomUUID());
        }
        
        try {
            Table table = schemaManager.loadTable(tableName);
            
            // Create a record
            GenericRecord record = GenericRecord.create(table.schema());
            mapFromSentimentRecord(entity, record);
            
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
    public SentimentRecord update(SentimentRecord entity) {
        if (entity.getId() == null) {
            throw new DatabaseException("Cannot update entity without ID");
        }
        
        try {
            Table table = schemaManager.loadTable(tableName);
            
            // Verify the entity exists
            if (!exists(entity.getId())) {
                throw new EntityNotFoundException("SentimentRecord with ID " + entity.getId() + " not found");
            }
            
            // Delete the old record and insert the new one (Iceberg doesn't support updates directly)
            Transaction transaction = transactionManager.getTransaction(table.newTransaction());
            
            // Delete the old record
            transaction.newDelete()
                     .deleteFromRowFilter(Expressions.equal("id", entity.getId().toString()))
                     .commit();
            
            // Create a record for the updated entity
            GenericRecord record = GenericRecord.create(table.schema());
            mapFromSentimentRecord(entity, record);
            
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
    public List<SentimentRecord> findByTicker(String ticker) {
        try {
            Table table = schemaManager.loadTable(tableName);
            List<SentimentRecord> results = new ArrayList<>();
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = 
                    IcebergGenerics.read(table)
                        .where(Expressions.equal("ticker", ticker))
                        .build()) {
                for (org.apache.iceberg.data.Record record : records) {
                    results.add(mapToSentimentRecord(record));
                }
            }
            
            return results;
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public List<SentimentRecord> findByTickerAndTimeRange(String ticker, Instant start, Instant end) {
        try {
            Table table = schemaManager.loadTable(tableName);
            List<SentimentRecord> results = new ArrayList<>();
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = 
                    IcebergGenerics.read(table)
                        .where(Expressions.and(
                            Expressions.equal("ticker", ticker),
                            Expressions.greaterThanOrEqual("timestamp", start),
                            Expressions.lessThanOrEqual("timestamp", end)
                        ))
                        .build()) {
                for (org.apache.iceberg.data.Record record : records) {
                    results.add(mapToSentimentRecord(record));
                }
            }
            
            return results;
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public double getAverageSentimentForTicker(String ticker, Instant since) {
        try {
            Table table = schemaManager.loadTable(tableName);
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = 
                    IcebergGenerics.read(table)
                        .where(Expressions.and(
                            Expressions.equal("ticker", ticker),
                            Expressions.greaterThanOrEqual("timestamp", since)
                        ))
                        .build()) {
                
                double sum = 0.0;
                int count = 0;
                
                for (org.apache.iceberg.data.Record record : records) {
                    sum += (Double) record.getField("sentiment_score");
                    count++;
                }
                
                return count > 0 ? sum / count : 0.0;
            }
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public List<SentimentRecord> findBySpecification(Specification<SentimentRecord> specification) {
        try {
            Table table = schemaManager.loadTable(tableName);
            
            // Convert specification to Iceberg expressions
            Expression expression = createExpressionFromSpecification(specification);
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = 
                    IcebergGenerics.read(table)
                        .where(expression)
                        .build()) {
                
                return StreamSupport.stream(records.spliterator(), false)
                        .map(this::mapToSentimentRecord)
                        .collect(Collectors.toList());
            }
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public List<SentimentRecord> findAll(int limit, int offset) {
        try {
            Table table = schemaManager.loadTable(tableName);
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = 
                    IcebergGenerics.read(table).build()) {
                
                return StreamSupport.stream(records.spliterator(), false)
                        .skip(offset)
                        .limit(limit)
                        .map(this::mapToSentimentRecord)
                        .collect(Collectors.toList());
            }
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public List<SentimentRecord> findBySource(String source) {
        try {
            Table table = schemaManager.loadTable(tableName);
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = 
                    IcebergGenerics.read(table)
                        .where(Expressions.equal("source", source))
                        .build()) {
                
                return StreamSupport.stream(records.spliterator(), false)
                        .map(this::mapToSentimentRecord)
                        .collect(Collectors.toList());
            }
        } catch (Exception e) {
            throw exceptionTranslator.translate(e);
        }
    }
    
    @Override
    public long count() {
        try {
            Table table = schemaManager.loadTable(tableName);
            
            try (CloseableIterable<org.apache.iceberg.data.Record> records = 
                    IcebergGenerics.read(table).build()) {
                
                return StreamSupport.stream(records.spliterator(), false).count();
            }
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
    
    private SentimentRecord mapToSentimentRecord(org.apache.iceberg.data.Record record) {
        String idStr = (String) record.getField("id");
        UUID id = UUID.fromString(idStr);
        String ticker = (String) record.getField("ticker");
        Double sentimentScore = (Double) record.getField("sentiment_score");
        Instant timestamp = (Instant) record.getField("timestamp");
        String source = (String) record.getField("source");
        
        // Handle attributes (may be null)
        Map<String, Double> attributes = new HashMap<>();
        @SuppressWarnings("unchecked")
        Map<String, Double> recordAttributes = (Map<String, Double>) record.getField("attributes");
        if (recordAttributes != null) {
            attributes.putAll(recordAttributes);
        }
        
        return new SentimentRecord(id, ticker, sentimentScore, timestamp, source, attributes);
    }
    
    private void mapFromSentimentRecord(SentimentRecord entity, GenericRecord record) {
        record.setField("id", entity.getId().toString());
        record.setField("ticker", entity.getTicker());
        record.setField("sentiment_score", entity.getSentimentScore());
        record.setField("timestamp", entity.getTimestamp());
        record.setField("source", entity.getSource());
        record.setField("attributes", entity.getAttributes());
    }
    
    private DataFile writeDataFile(Table table, List<GenericRecord> records) throws IOException {
        // Create a temporary file
        File tempFile = File.createTempFile("iceberg-", ".parquet");
        tempFile.delete(); // We only need the path
        
        // Create an output file
        OutputFile outputFile = table.io().newOutputFile(tempFile.getAbsolutePath());
        
        // Create a file appender
        FileAppender<Record> appender = Parquet.write(outputFile)
                .schema(table.schema())
                .createWriterFunc(GenericParquetWriter::buildWriter)
                .build();
        
        try (FileAppender<Record> fileAppender = appender) {
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
    
    private Expression createExpressionFromSpecification(Specification<SentimentRecord> specification) {
        // Get the SQL clause and parameters from the specification
        String sqlClause = specification.toSqlClause();
        Map<String, Object> parameters = specification.getParameters();
        
        // Convert to Iceberg expression
        // This is a simplified implementation that handles common cases
        if (sqlClause.contains(" AND ")) {
            String[] parts = sqlClause.split(" AND ");
            Expression result = Expressions.alwaysTrue();
            
            for (String part : parts) {
                result = Expressions.and(result, parseExpressionPart(part.trim(), parameters));
            }
            
            return result;
        } else if (sqlClause.contains(" OR ")) {
            String[] parts = sqlClause.split(" OR ");
            Expression result = Expressions.alwaysFalse();
            
            for (String part : parts) {
                result = Expressions.or(result, parseExpressionPart(part.trim(), parameters));
            }
            
            return result;
        } else {
            return parseExpressionPart(sqlClause.trim(), parameters);
        }
    }
    
    private Expression parseExpressionPart(String part, Map<String, Object> parameters) {
        if (part.contains(" = ")) {
            String[] keyValue = part.split(" = ");
            String field = keyValue[0].trim();
            String param = keyValue[1].trim();
            
            if (param.startsWith(":")) {
                param = param.substring(1);
                Object value = parameters.get(param);
                return Expressions.equal(field, value);
            }
        } else if (part.contains(" >= ")) {
            String[] keyValue = part.split(" >= ");
            String field = keyValue[0].trim();
            String param = keyValue[1].trim();
            
            if (param.startsWith(":")) {
                param = param.substring(1);
                Object value = parameters.get(param);
                return Expressions.greaterThanOrEqual(field, value);
            }
        } else if (part.contains(" <= ")) {
            String[] keyValue = part.split(" <= ");
            String field = keyValue[0].trim();
            String param = keyValue[1].trim();
            
            if (param.startsWith(":")) {
                param = param.substring(1);
                Object value = parameters.get(param);
                return Expressions.lessThanOrEqual(field, value);
            }
        } else if (part.contains(" > ")) {
            String[] keyValue = part.split(" > ");
            String field = keyValue[0].trim();
            String param = keyValue[1].trim();
            
            if (param.startsWith(":")) {
                param = param.substring(1);
                Object value = parameters.get(param);
                return Expressions.greaterThan(field, value);
            }
        } else if (part.contains(" < ")) {
            String[] keyValue = part.split(" < ");
            String field = keyValue[0].trim();
            String param = keyValue[1].trim();
            
            if (param.startsWith(":")) {
                param = param.substring(1);
                Object value = parameters.get(param);
                return Expressions.lessThan(field, value);
            }
        }
        
        // Default to always true if we can't parse the expression
        return Expressions.alwaysTrue();
    }
}