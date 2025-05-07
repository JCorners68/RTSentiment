package com.sentimark.data.repository.postgres;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.sentimark.data.model.MarketEvent;
import com.sentimark.data.repository.MarketEventRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.EmptyResultDataAccessException;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

import javax.sql.DataSource;
import java.sql.Array;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.time.Instant;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * PostgreSQL implementation of the MarketEventRepository interface.
 */
@Repository("postgresMarketEventRepository")
public class PostgresMarketEventRepository implements MarketEventRepository {
    
    private final DataSource dataSource;
    private final JdbcTemplate jdbcTemplate;
    private final ObjectMapper objectMapper;
    
    @Autowired
    public PostgresMarketEventRepository(DataSource dataSource, ObjectMapper objectMapper) {
        this.dataSource = dataSource;
        this.jdbcTemplate = new JdbcTemplate(dataSource);
        this.objectMapper = objectMapper;
    }
    
    @Override
    public Optional<MarketEvent> findById(UUID id) {
        try {
            MarketEvent event = jdbcTemplate.queryForObject(
                "SELECT * FROM market_events WHERE id = ?",
                new Object[]{id},
                marketEventRowMapper()
            );
            return Optional.ofNullable(event);
        } catch (EmptyResultDataAccessException e) {
            return Optional.empty();
        }
    }
    
    @Override
    public List<MarketEvent> findAll() {
        return jdbcTemplate.query(
            "SELECT * FROM market_events ORDER BY published_at DESC",
            marketEventRowMapper()
        );
    }
    
    @Override
    public MarketEvent save(MarketEvent event) {
        if (event.getId() == null) {
            event.setId(UUID.randomUUID());
        }
        
        jdbcTemplate.update(
            "INSERT INTO market_events (id, headline, tickers, content, published_at, source, credibility_score) " +
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            event.getId(),
            event.getHeadline(),
            createSqlArray(event.getTickers()),
            event.getContent(),
            java.sql.Timestamp.from(event.getPublishedAt()),
            event.getSource(),
            event.getCredibilityScore()
        );
        
        return event;
    }
    
    @Override
    public MarketEvent update(MarketEvent event) {
        jdbcTemplate.update(
            "UPDATE market_events SET headline = ?, tickers = ?, content = ?, published_at = ?, source = ?, credibility_score = ? " +
            "WHERE id = ?",
            event.getHeadline(),
            createSqlArray(event.getTickers()),
            event.getContent(),
            java.sql.Timestamp.from(event.getPublishedAt()),
            event.getSource(),
            event.getCredibilityScore(),
            event.getId()
        );
        
        return event;
    }
    
    @Override
    public void delete(UUID id) {
        jdbcTemplate.update("DELETE FROM market_events WHERE id = ?", id);
    }
    
    @Override
    public List<MarketEvent> findByTickers(List<String> tickers) {
        // Using ANY operator to match any of the tickers
        String sql = "SELECT * FROM market_events WHERE EXISTS (SELECT 1 FROM unnest(tickers) as t WHERE t = ANY(?)) " +
                     "ORDER BY published_at DESC";
        
        return jdbcTemplate.query(
            sql,
            new Object[]{createSqlArray(tickers)},
            marketEventRowMapper()
        );
    }
    
    @Override
    public List<MarketEvent> findByTimeRange(Instant start, Instant end) {
        return jdbcTemplate.query(
            "SELECT * FROM market_events WHERE published_at BETWEEN ? AND ? ORDER BY published_at DESC",
            new Object[]{
                java.sql.Timestamp.from(start),
                java.sql.Timestamp.from(end)
            },
            marketEventRowMapper()
        );
    }
    
    @Override
    public List<MarketEvent> findBySourceAndTimeRange(String source, Instant start, Instant end) {
        return jdbcTemplate.query(
            "SELECT * FROM market_events WHERE source = ? AND published_at BETWEEN ? AND ? " +
            "ORDER BY published_at DESC",
            new Object[]{
                source,
                java.sql.Timestamp.from(start),
                java.sql.Timestamp.from(end)
            },
            marketEventRowMapper()
        );
    }
    
    private RowMapper<MarketEvent> marketEventRowMapper() {
        return (rs, rowNum) -> {
            MarketEvent event = new MarketEvent();
            event.setId(UUID.fromString(rs.getString("id")));
            event.setHeadline(rs.getString("headline"));
            event.setTickers(parseTickersArray(rs.getArray("tickers")));
            event.setContent(rs.getString("content"));
            event.setPublishedAt(rs.getTimestamp("published_at").toInstant());
            event.setSource(rs.getString("source"));
            event.setCredibilityScore(rs.getDouble("credibility_score"));
            return event;
        };
    }
    
    private Object createSqlArray(List<String> list) {
        try {
            return jdbcTemplate.getDataSource()
                .getConnection()
                .createArrayOf("text", list.toArray());
        } catch (SQLException e) {
            throw new RuntimeException("Error creating SQL array", e);
        }
    }
    
    private List<String> parseTickersArray(Array sqlArray) throws SQLException {
        if (sqlArray == null) {
            return List.of();
        }
        
        String[] array = (String[]) sqlArray.getArray();
        return Arrays.asList(array);
    }
}