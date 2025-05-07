package com.sentimark.data.config;

import org.apache.iceberg.PartitionSpec;
import org.apache.iceberg.Schema;

/**
 * Utility class for creating different partitioning strategies for Iceberg tables.
 */
public class PartitioningStrategies {
    
    /**
     * Creates a time-based partitioning strategy with year, month, and day partitions.
     * 
     * @param schema The schema to create the partitioning for
     * @param timestampColumn The name of the timestamp column to partition by
     * @return A partitioning specification for the table
     */
    public static PartitionSpec timeBasedPartitioning(Schema schema, String timestampColumn) {
        return PartitionSpec.builderFor(schema)
            .year(timestampColumn)
            .month(timestampColumn)
            .day(timestampColumn)
            .build();
    }
    
    /**
     * Creates a ticker-based partitioning strategy.
     * 
     * @param schema The schema to create the partitioning for
     * @return A partitioning specification for the table
     */
    public static PartitionSpec tickerBasedPartitioning(Schema schema) {
        return PartitionSpec.builderFor(schema)
            .identity("ticker")
            .build();
    }
    
    /**
     * Creates a source-based partitioning strategy.
     * 
     * @param schema The schema to create the partitioning for
     * @return A partitioning specification for the table
     */
    public static PartitionSpec sourceBasedPartitioning(Schema schema) {
        return PartitionSpec.builderFor(schema)
            .identity("source")
            .build();
    }
    
    /**
     * Creates a combined partitioning strategy with ticker and time-based partitioning.
     * 
     * @param schema The schema to create the partitioning for
     * @param timestampColumn The name of the timestamp column to partition by
     * @return A partitioning specification for the table
     */
    public static PartitionSpec combinedPartitioning(Schema schema, String timestampColumn) {
        return PartitionSpec.builderFor(schema)
            .identity("ticker")
            .year(timestampColumn)
            .month(timestampColumn)
            .build();
    }
    
    /**
     * Creates a sentiment score range partitioning strategy.
     * 
     * @param schema The schema to create the partitioning for
     * @return A partitioning specification for the table
     */
    public static PartitionSpec sentimentScoreRangePartitioning(Schema schema) {
        return PartitionSpec.builderFor(schema)
            .bucket("sentiment_score", 10)
            .build();
    }
}