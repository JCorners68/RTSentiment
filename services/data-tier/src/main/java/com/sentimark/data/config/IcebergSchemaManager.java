package com.sentimark.data.config;

import org.apache.iceberg.Schema;
import org.apache.iceberg.Table;
import org.apache.iceberg.TableIdentifier;
import org.apache.iceberg.catalog.Catalog;
import org.apache.iceberg.catalog.TableAlreadyExistsException;
import org.apache.iceberg.types.Types;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;

@Component
public class IcebergSchemaManager {
    private final Catalog catalog;
    private final Logger logger = LoggerFactory.getLogger(IcebergSchemaManager.class);
    
    @Autowired
    public IcebergSchemaManager(Catalog catalog) {
        this.catalog = catalog;
    }
    
    public void createTable(String tableName, Schema schema) {
        TableIdentifier tableId = TableIdentifier.of(tableName);
        
        try {
            if (!catalog.tableExists(tableId)) {
                catalog.createTable(tableId, schema);
                logger.info("Created Iceberg table: {}", tableName);
            } else {
                logger.info("Table already exists: {}", tableName);
            }
        } catch (TableAlreadyExistsException e) {
            logger.info("Table already exists (concurrent creation): {}", tableName);
        } catch (Exception e) {
            logger.error("Error creating table {}: {}", tableName, e.getMessage());
            throw new RuntimeException("Failed to create Iceberg table", e);
        }
    }
    
    public void updateSchema(String tableName, Schema newSchema) {
        TableIdentifier tableId = TableIdentifier.of(tableName);
        
        try {
            Table table = catalog.loadTable(tableId);
            table.updateSchema()
                 .addColumns(newSchema.columns())
                 .commit();
            logger.info("Updated schema for table: {}", tableName);
        } catch (Exception e) {
            logger.error("Error updating schema for table {}: {}", tableName, e.getMessage());
            throw new RuntimeException("Failed to update schema", e);
        }
    }
    
    public Schema createSentimentRecordSchema() {
        return new Schema(
            Types.NestedField.required(1, "id", Types.StringType.get()),
            Types.NestedField.required(2, "ticker", Types.StringType.get()),
            Types.NestedField.required(3, "sentiment_score", Types.DoubleType.get()),
            Types.NestedField.required(4, "timestamp", Types.TimestampType.withZone()),
            Types.NestedField.required(5, "source", Types.StringType.get()),
            Types.NestedField.optional(6, "attributes", Types.MapType.ofRequired(
                7, 8, Types.StringType.get(), Types.DoubleType.get()
            ))
        );
    }
    
    public Schema createMarketEventSchema() {
        return new Schema(
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
    }
    
    public boolean tableExists(String tableName) {
        return catalog.tableExists(TableIdentifier.of(tableName));
    }
    
    public Table loadTable(String tableName) {
        return catalog.loadTable(TableIdentifier.of(tableName));
    }
}