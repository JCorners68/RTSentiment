-- Database schema for Sentimark

-- Sentiment Records Table
CREATE TABLE IF NOT EXISTS sentiment_records (
    id UUID PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    sentiment_score DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(100) NOT NULL,
    attributes JSONB
);

-- Indexes for Sentiment Records
CREATE INDEX IF NOT EXISTS idx_sentiment_records_ticker ON sentiment_records (ticker);
CREATE INDEX IF NOT EXISTS idx_sentiment_records_timestamp ON sentiment_records (timestamp);
CREATE INDEX IF NOT EXISTS idx_sentiment_records_ticker_timestamp ON sentiment_records (ticker, timestamp);

-- Market Events Table
CREATE TABLE IF NOT EXISTS market_events (
    id UUID PRIMARY KEY,
    headline TEXT NOT NULL,
    tickers TEXT[] NOT NULL,
    content TEXT,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    source VARCHAR(100) NOT NULL,
    credibility_score DOUBLE PRECISION NOT NULL
);

-- Indexes for Market Events
CREATE INDEX IF NOT EXISTS idx_market_events_published_at ON market_events (published_at);
CREATE INDEX IF NOT EXISTS idx_market_events_source ON market_events (source);

-- GIN index for faster array searches on tickers
CREATE INDEX IF NOT EXISTS idx_market_events_tickers ON market_events USING GIN (tickers);

-- Comments
COMMENT ON TABLE sentiment_records IS 'Stores sentiment analysis records for ticker symbols';
COMMENT ON TABLE market_events IS 'Stores market events that affect sentiment of ticker symbols';