package com.sentimark.data.repository.postgres;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sentimark.data.exception.DatabaseException;
import com.sentimark.data.exception.EntityNotFoundException;
import com.sentimark.data.exception.ExceptionTranslator;
import com.sentimark.data.model.SentimentRecord;
import com.sentimark.data.repository.EnhancedSentimentRecordRepository;
import com.sentimark.data.specification.Specification;
import com.sentimark.data.transaction.TransactionAwareRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.jdbc.core.namedparam.MapSqlParameterSource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Repository;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;

/**
 * PostgreSQL implementation of the SentimentRecordRepository interface.
 */
@Repository("postgresSentimentRecordRepository")
public class PostgresSentimentRecordRepository implements EnhancedSentimentRecordRepository, TransactionAwareRepository {
    
    private static final Logger logger = LoggerFactory.getLogger(PostgresSentimentRecordRepository.class);
    
    private final DataSource dataSource;
    private final ObjectMapper objectMapper;
    private final ExceptionTranslator exceptionTranslator;
    private final ThreadLocal<Connection> connectionHolder = new ThreadLocal<>();
    
    @Autowired
    public PostgresSentimentRecordRepository(
            DataSource dataSource, 
            ObjectMapper objectMapper,
            ExceptionTranslator exceptionTranslator) {
        this.dataSource = dataSource;
        this.objectMapper = objectMapper;
        this.exceptionTranslator = exceptionTranslator;
    }
    
    @Override
    public void setConnection(Connection connection) {
        connectionHolder.set(connection);
    }
    
    protected Connection getConnection() throws SQLException {
        Connection connection = connectionHolder.get();
        if (connection != null) {
            return connection; // Use transaction-bound connection
        }
        
        // Otherwise get a new connection
        connection = dataSource.getConnection();
        try {
            // Auto-commit for non-transactional operations
            connection.setAutoCommit(true);
            return connection;
        } catch (SQLException e) {
            connection.close();
            throw e;
        }
    }
    
    protected void closeConnection(Connection connection) throws SQLException {
        if (connectionHolder.get() == null && connection != null) {
            // Only close connections we created (not transaction-bound ones)
            connection.close();
        }
    }
    
    @Override
    public Optional<SentimentRecord> findById(UUID id) {
        String sql = "SELECT * FROM sentiment_records WHERE id = ?";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setObject(1, id);
            
            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    return Optional.of(mapRowToSentimentRecord(rs));
                } else {
                    return Optional.empty();
                }
            }
        } catch (SQLException e) {
            throw exceptionTranslator.translate(e, "Error finding sentiment record by ID: " + id);
        }
    }
    
    @Override
    public List<SentimentRecord> findAll() {
        String sql = "SELECT * FROM sentiment_records ORDER BY timestamp DESC";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql);
             ResultSet rs = stmt.executeQuery()) {
            
            List<SentimentRecord> records = new ArrayList<>();
            while (rs.next()) {
                records.add(mapRowToSentimentRecord(rs));
            }
            return records;
        } catch (SQLException e) {
            throw exceptionTranslator.translate(e, "Error finding all sentiment records");
        }
    }
    
    @Override
    public List<SentimentRecord> findAll(Specification<SentimentRecord> spec) {
        String sql = "SELECT * FROM sentiment_records WHERE " + spec.toSqlClause();
        MapSqlParameterSource params = new MapSqlParameterSource(spec.getParameters());
        
        try (Connection conn = getConnection()) {
            NamedParameterJdbcTemplate namedTemplate = new NamedParameterJdbcTemplate(conn);
            return namedTemplate.query(sql, params, (rs, rowNum) -> mapRowToSentimentRecord(rs));
        } catch (SQLException e) {
            throw exceptionTranslator.translate(e, "Error finding sentiment records with specification");
        }
    }
    
    @Override
    public List<SentimentRecord> findAll(Specification<SentimentRecord> spec, String orderBy, int limit, int offset) {
        String sql = "SELECT * FROM sentiment_records WHERE " + spec.toSqlClause() + 
                     " ORDER BY " + orderBy + " LIMIT " + limit + " OFFSET " + offset;
        MapSqlParameterSource params = new MapSqlParameterSource(spec.getParameters());
        
        try (Connection conn = getConnection()) {
            NamedParameterJdbcTemplate namedTemplate = new NamedParameterJdbcTemplate(conn);
            return namedTemplate.query(sql, params, (rs, rowNum) -> mapRowToSentimentRecord(rs));
        } catch (SQLException e) {
            throw exceptionTranslator.translate(e, "Error finding sentiment records with specification and pagination");
        }
    }
    
    @Override
    public long count(Specification<SentimentRecord> spec) {
        String sql = "SELECT COUNT(*) FROM sentiment_records WHERE " + spec.toSqlClause();
        MapSqlParameterSource params = new MapSqlParameterSource(spec.getParameters());
        
        try (Connection conn = getConnection()) {
            NamedParameterJdbcTemplate namedTemplate = new NamedParameterJdbcTemplate(conn);
            return namedTemplate.queryForObject(sql, params, Long.class);
        } catch (SQLException e) {
            throw exceptionTranslator.translate(e, "Error counting sentiment records with specification");
        }
    }
    
    @Override
    public SentimentRecord save(SentimentRecord record) {
        if (record.getId() == null) {
            record.setId(UUID.randomUUID());
        }
        
        String sql = "INSERT INTO sentiment_records (id, ticker, sentiment_score, timestamp, source, attributes) " +
                    "VALUES (?, ?, ?, ?, ?, ?::jsonb)";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setObject(1, record.getId());
            stmt.setString(2, record.getTicker());
            stmt.setDouble(3, record.getSentimentScore());
            stmt.setTimestamp(4, Timestamp.from(record.getTimestamp()));
            stmt.setString(5, record.getSource());
            stmt.setString(6, convertAttributesToJson(record.getAttributes()));
            
            int rowsAffected = stmt.executeUpdate();
            
            if (rowsAffected != 1) {
                throw new DatabaseException("Failed to save sentiment record, affected rows: " + rowsAffected);
            }
            
            return record;
        } catch (SQLException e) {
            throw exceptionTranslator.translate(e, "Error saving sentiment record: " + record.getId());
        }
    }
    
    @Override
    public SentimentRecord update(SentimentRecord record) {
        if (record.getId() == null) {
            throw new IllegalArgumentException("Cannot update sentiment record with null ID");
        }
        
        String sql = "UPDATE sentiment_records SET ticker = ?, sentiment_score = ?, timestamp = ?, " +
                    "source = ?, attributes = ?::jsonb WHERE id = ?";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, record.getTicker());
            stmt.setDouble(2, record.getSentimentScore());
            stmt.setTimestamp(3, Timestamp.from(record.getTimestamp()));
            stmt.setString(4, record.getSource());
            stmt.setString(5, convertAttributesToJson(record.getAttributes()));
            stmt.setObject(6, record.getId());
            
            int rowsAffected = stmt.executeUpdate();
            
            if (rowsAffected == 0) {
                throw new EntityNotFoundException("Sentiment record not found: " + record.getId());
            }
            
            return record;
        } catch (SQLException e) {
            throw exceptionTranslator.translate(e, "Error updating sentiment record: " + record.getId());
        }
    }
    
    @Override
    public void delete(UUID id) {
        String sql = "DELETE FROM sentiment_records WHERE id = ?";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setObject(1, id);
            int rowsAffected = stmt.executeUpdate();
            
            if (rowsAffected == 0) {
                logger.warn("No sentiment record found to delete with ID: {}", id);
            }
        } catch (SQLException e) {
            throw exceptionTranslator.translate(e, "Error deleting sentiment record: " + id);
        }
    }
    
    @Override
    public void deleteAll(Specification<SentimentRecord> spec) {
        String sql = "DELETE FROM sentiment_records WHERE " + spec.toSqlClause();
        MapSqlParameterSource params = new MapSqlParameterSource(spec.getParameters());
        
        try (Connection conn = getConnection()) {
            NamedParameterJdbcTemplate namedTemplate = new NamedParameterJdbcTemplate(conn);
            int rowsAffected = namedTemplate.update(sql, params);
            logger.debug("Deleted {} sentiment records matching specification", rowsAffected);
        } catch (SQLException e) {
            throw exceptionTranslator.translate(e, "Error deleting sentiment records with specification");
        }
    }
    
    @Override
    public List<SentimentRecord> findByTicker(String ticker) {
        String sql = "SELECT * FROM sentiment_records WHERE ticker = ? ORDER BY timestamp DESC";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, ticker);
            
            try (ResultSet rs = stmt.executeQuery()) {
                List<SentimentRecord> records = new ArrayList<>();
                while (rs.next()) {
                    records.add(mapRowToSentimentRecord(rs));
                }
                return records;
            }
        } catch (SQLException e) {
            throw exceptionTranslator.translate(e, "Error finding sentiment records by ticker: " + ticker);
        }
    }
    
    @Override
    public List<SentimentRecord> findByTickerAndTimeRange(String ticker, Instant start, Instant end) {
        String sql = "SELECT * FROM sentiment_records WHERE ticker = ? AND timestamp BETWEEN ? AND ? " +
                    "ORDER BY timestamp DESC";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, ticker);
            stmt.setTimestamp(2, Timestamp.from(start));
            stmt.setTimestamp(3, Timestamp.from(end));
            
            try (ResultSet rs = stmt.executeQuery()) {
                List<SentimentRecord> records = new ArrayList<>();
                while (rs.next()) {
                    records.add(mapRowToSentimentRecord(rs));
                }
                return records;
            }
        } catch (SQLException e) {
            throw exceptionTranslator.translate(
                e, 
                "Error finding sentiment records by ticker and time range: " + 
                ticker + ", " + start + " to " + end
            );
        }
    }
    
    @Override
    public double getAverageSentimentForTicker(String ticker, Instant since) {
        String sql = "SELECT AVG(sentiment_score) FROM sentiment_records WHERE ticker = ? AND timestamp >= ?";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, ticker);
            stmt.setTimestamp(2, Timestamp.from(since));
            
            try (ResultSet rs = stmt.executeQuery()) {
                if (rs.next()) {
                    Double avg = rs.getDouble(1);
                    return rs.wasNull() ? 0.0 : avg;
                } else {
                    return 0.0;
                }
            }
        } catch (SQLException e) {
            throw exceptionTranslator.translate(
                e, 
                "Error calculating average sentiment for ticker: " + ticker + " since " + since
            );
        }
    }
    
    @Override
    public List<SentimentRecord> findTopSentimentByTicker(int limit) {
        String sql = 
            "WITH ranked_records AS (" +
            "  SELECT *, ROW_NUMBER() OVER(PARTITION BY ticker ORDER BY sentiment_score DESC) AS rank " +
            "  FROM sentiment_records" +
            ") " +
            "SELECT * FROM ranked_records WHERE rank <= ? ORDER BY ticker, rank";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setInt(1, limit);
            
            try (ResultSet rs = stmt.executeQuery()) {
                List<SentimentRecord> records = new ArrayList<>();
                while (rs.next()) {
                    records.add(mapRowToSentimentRecord(rs));
                }
                return records;
            }
        } catch (SQLException e) {
            throw exceptionTranslator.translate(e, "Error finding top sentiment records by ticker");
        }
    }
    
    @Override
    public List<SentimentRecord> findBottomSentimentByTicker(int limit) {
        String sql = 
            "WITH ranked_records AS (" +
            "  SELECT *, ROW_NUMBER() OVER(PARTITION BY ticker ORDER BY sentiment_score ASC) AS rank " +
            "  FROM sentiment_records" +
            ") " +
            "SELECT * FROM ranked_records WHERE rank <= ? ORDER BY ticker, rank";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setInt(1, limit);
            
            try (ResultSet rs = stmt.executeQuery()) {
                List<SentimentRecord> records = new ArrayList<>();
                while (rs.next()) {
                    records.add(mapRowToSentimentRecord(rs));
                }
                return records;
            }
        } catch (SQLException e) {
            throw exceptionTranslator.translate(e, "Error finding bottom sentiment records by ticker");
        }
    }
    
    private SentimentRecord mapRowToSentimentRecord(ResultSet rs) throws SQLException {
        SentimentRecord record = new SentimentRecord();
        record.setId(UUID.fromString(rs.getString("id")));
        record.setTicker(rs.getString("ticker"));
        record.setSentimentScore(rs.getDouble("sentiment_score"));
        record.setTimestamp(rs.getTimestamp("timestamp").toInstant());
        record.setSource(rs.getString("source"));
        record.setAttributes(parseAttributesJson(rs.getString("attributes")));
        return record;
    }
    
    private String convertAttributesToJson(Map<String, Double> attributes) {
        try {
            return objectMapper.writeValueAsString(attributes);
        } catch (JsonProcessingException e) {
            throw new DatabaseException("Error converting attributes to JSON", e);
        }
    }
    
    private Map<String, Double> parseAttributesJson(String json) {
        if (json == null || json.isEmpty()) {
            return new HashMap<>();
        }
        
        try {
            return objectMapper.readValue(json, new TypeReference<HashMap<String, Double>>() {});
        } catch (JsonProcessingException e) {
            throw new DatabaseException("Error parsing attributes JSON", e);
        }
    }
}