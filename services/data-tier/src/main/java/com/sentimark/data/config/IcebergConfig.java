package com.sentimark.data.config;

import org.apache.hadoop.conf.Configuration;
import org.apache.iceberg.catalog.Catalog;
import org.apache.iceberg.hadoop.HadoopCatalog;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Profile;

import java.util.HashMap;
import java.util.Map;

@org.springframework.context.annotation.Configuration
@Profile("iceberg")
public class IcebergConfig {
    
    private static final Logger logger = LoggerFactory.getLogger(IcebergConfig.class);
    
    @Value("${iceberg.warehouse:/home/jonat/real_senti/data/iceberg/warehouse}")
    private String warehousePath;
    
    @Value("${iceberg.catalog-name:sentimark}")
    private String catalogName;
    
    @Bean
    public Catalog icebergCatalog() {
        logger.info("Initializing Iceberg catalog with warehouse path: {}", warehousePath);
        
        Map<String, String> properties = new HashMap<>();
        properties.put("warehouse", warehousePath);
        properties.put("catalog-impl", "org.apache.iceberg.hadoop.HadoopCatalog");
        
        Configuration hadoopConf = new Configuration();
        
        HadoopCatalog catalog = new HadoopCatalog();
        catalog.setConf(hadoopConf);
        catalog.initialize(catalogName, properties);
        
        logger.info("Iceberg catalog initialized successfully");
        return catalog;
    }
    
    @Bean
    public IcebergSchemaManager icebergSchemaManager(Catalog catalog) {
        return new IcebergSchemaManager(catalog);
    }
}