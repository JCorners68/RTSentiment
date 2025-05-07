package com.sentimark.data;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

/**
 * Main application class for the Sentimark Data Tier service.
 */
@SpringBootApplication
public class DataTierApplication {

    public static void main(String[] args) {
        SpringApplication.run(DataTierApplication.class, args);
    }
    
    /**
     * Create an ObjectMapper bean with JavaTimeModule for JSON serialization/deserialization.
     *
     * @return the configured ObjectMapper
     */
    @Bean
    public ObjectMapper objectMapper() {
        ObjectMapper objectMapper = new ObjectMapper();
        objectMapper.registerModule(new JavaTimeModule());
        return objectMapper;
    }
}