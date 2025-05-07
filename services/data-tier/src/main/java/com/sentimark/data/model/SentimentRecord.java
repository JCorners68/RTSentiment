package com.sentimark.data.model;

import java.time.Instant;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

/**
 * Represents a sentiment analysis record for a specific ticker symbol.
 */
public class SentimentRecord {
    private UUID id;
    private String ticker;
    private double sentimentScore;
    private Instant timestamp;
    private String source;
    private Map<String, Double> attributes;

    /**
     * Default constructor.
     */
    public SentimentRecord() {
        this.attributes = new HashMap<>();
    }

    /**
     * Constructor with all fields.
     */
    public SentimentRecord(UUID id, String ticker, double sentimentScore, Instant timestamp, 
                          String source, Map<String, Double> attributes) {
        this.id = id;
        this.ticker = ticker;
        this.sentimentScore = sentimentScore;
        this.timestamp = timestamp;
        this.source = source;
        this.attributes = attributes != null ? new HashMap<>(attributes) : new HashMap<>();
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public String getTicker() {
        return ticker;
    }

    public void setTicker(String ticker) {
        this.ticker = ticker;
    }

    public double getSentimentScore() {
        return sentimentScore;
    }

    public void setSentimentScore(double sentimentScore) {
        this.sentimentScore = sentimentScore;
    }

    public Instant getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(Instant timestamp) {
        this.timestamp = timestamp;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    public Map<String, Double> getAttributes() {
        return attributes;
    }

    public void setAttributes(Map<String, Double> attributes) {
        this.attributes = attributes != null ? new HashMap<>(attributes) : new HashMap<>();
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        SentimentRecord that = (SentimentRecord) o;
        return Double.compare(that.sentimentScore, sentimentScore) == 0 &&
                Objects.equals(id, that.id) &&
                Objects.equals(ticker, that.ticker) &&
                Objects.equals(timestamp, that.timestamp) &&
                Objects.equals(source, that.source) &&
                Objects.equals(attributes, that.attributes);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, ticker, sentimentScore, timestamp, source, attributes);
    }

    @Override
    public String toString() {
        return "SentimentRecord{" +
                "id=" + id +
                ", ticker='" + ticker + '\'' +
                ", sentimentScore=" + sentimentScore +
                ", timestamp=" + timestamp +
                ", source='" + source + '\'' +
                ", attributes=" + attributes +
                '}';
    }
}