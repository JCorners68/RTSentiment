package com.sentimark.data.model;

import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * Represents a market event, such as a news article, social media post, or analyst report
 * that may affect sentiment for one or more tickers.
 */
public class MarketEvent {
    private UUID id;
    private String headline;
    private List<String> tickers;
    private String content;
    private Instant publishedAt;
    private String source;
    private double credibilityScore;

    /**
     * Default constructor.
     */
    public MarketEvent() {
        this.tickers = new ArrayList<>();
    }

    /**
     * Constructor with all fields.
     */
    public MarketEvent(UUID id, String headline, List<String> tickers, String content,
                       Instant publishedAt, String source, double credibilityScore) {
        this.id = id;
        this.headline = headline;
        this.tickers = tickers != null ? new ArrayList<>(tickers) : new ArrayList<>();
        this.content = content;
        this.publishedAt = publishedAt;
        this.source = source;
        this.credibilityScore = credibilityScore;
    }

    public UUID getId() {
        return id;
    }

    public void setId(UUID id) {
        this.id = id;
    }

    public String getHeadline() {
        return headline;
    }

    public void setHeadline(String headline) {
        this.headline = headline;
    }

    public List<String> getTickers() {
        return tickers;
    }

    public void setTickers(List<String> tickers) {
        this.tickers = tickers != null ? new ArrayList<>(tickers) : new ArrayList<>();
    }

    public String getContent() {
        return content;
    }

    public void setContent(String content) {
        this.content = content;
    }

    public Instant getPublishedAt() {
        return publishedAt;
    }

    public void setPublishedAt(Instant publishedAt) {
        this.publishedAt = publishedAt;
    }

    public String getSource() {
        return source;
    }

    public void setSource(String source) {
        this.source = source;
    }

    public double getCredibilityScore() {
        return credibilityScore;
    }

    public void setCredibilityScore(double credibilityScore) {
        this.credibilityScore = credibilityScore;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        MarketEvent that = (MarketEvent) o;
        return Double.compare(that.credibilityScore, credibilityScore) == 0 &&
                Objects.equals(id, that.id) &&
                Objects.equals(headline, that.headline) &&
                Objects.equals(tickers, that.tickers) &&
                Objects.equals(content, that.content) &&
                Objects.equals(publishedAt, that.publishedAt) &&
                Objects.equals(source, that.source);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, headline, tickers, content, publishedAt, source, credibilityScore);
    }

    @Override
    public String toString() {
        return "MarketEvent{" +
                "id=" + id +
                ", headline='" + headline + '\'' +
                ", tickers=" + tickers +
                ", content='" + (content != null ? content.substring(0, Math.min(50, content.length())) + "..." : null) + '\'' +
                ", publishedAt=" + publishedAt +
                ", source='" + source + '\'' +
                ", credibilityScore=" + credibilityScore +
                '}';
    }
}