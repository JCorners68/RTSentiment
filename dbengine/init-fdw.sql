-- Load the parquet_fdw extension
CREATE EXTENSION IF NOT EXISTS parquet_fdw;

-- Create the server for parquet_fdw
CREATE SERVER IF NOT EXISTS parquet_srv FOREIGN DATA WRAPPER parquet_fdw;

-- Create user mapping for the pgadmin user
CREATE USER MAPPING IF NOT EXISTS FOR pgadmin SERVER parquet_srv;

-- Create foreign table for AAPL sentiment data
CREATE FOREIGN TABLE IF NOT EXISTS aapl_sentiment (
    timestamp TEXT,
    ticker TEXT,
    sentiment FLOAT8,
    confidence FLOAT8,
    source TEXT,
    model TEXT,
    article_id TEXT,
    article_title TEXT
) SERVER parquet_srv
OPTIONS (
    filename '/parquet_data/aapl_sentiment.parquet' -- <<< UPDATED PATH
);

-- Create foreign table for TSLA sentiment data
CREATE FOREIGN TABLE IF NOT EXISTS tsla_sentiment (
    timestamp TEXT,
    ticker TEXT,
    sentiment FLOAT8,
    confidence FLOAT8,
    source TEXT,
    model TEXT,
    article_id TEXT,
    article_title TEXT
) SERVER parquet_srv
OPTIONS (
    filename '/parquet_data/tsla_sentiment.parquet' -- <<< UPDATED PATH
);

-- Create foreign table for multi-ticker sentiment data
CREATE FOREIGN TABLE IF NOT EXISTS multi_ticker_sentiment (
    timestamp TEXT,
    ticker TEXT,
    sentiment FLOAT8,
    confidence FLOAT8,
    source TEXT,
    model TEXT,
    article_id TEXT,
    article_title TEXT
) SERVER parquet_srv
OPTIONS (
    filename '/parquet_data/multi_ticker_sentiment.parquet' -- <<< UPDATED PATH
);

-- Create a unified view that combines all sentiment data
CREATE OR REPLACE VIEW all_sentiment AS
    SELECT * FROM aapl_sentiment
    UNION ALL
    SELECT * FROM tsla_sentiment
    UNION ALL
    SELECT * FROM multi_ticker_sentiment;

-- Create index on the unified view (note: this is a materialized view approach instead)
-- For better performance, we'd create a materialized view and refresh it periodically
CREATE MATERIALIZED VIEW IF NOT EXISTS all_sentiment_mv AS
    SELECT * FROM all_sentiment;

-- Create indexes on the materialized view
-- Consider changing timestamp column type to TIMESTAMPTZ for better indexing/querying
CREATE INDEX IF NOT EXISTS idx_all_sentiment_ticker ON all_sentiment_mv (ticker);
CREATE INDEX IF NOT EXISTS idx_all_sentiment_timestamp ON all_sentiment_mv (timestamp);
CREATE INDEX IF NOT EXISTS idx_all_sentiment_source ON all_sentiment_mv (source);

-- Grant permissions
-- These ARE correct
GRANT ALL ON aapl_sentiment TO pgadmin;
GRANT ALL ON tsla_sentiment TO pgadmin;
GRANT ALL ON multi_ticker_sentiment TO pgadmin;

GRANT ALL ON all_sentiment TO pgadmin;
GRANT ALL ON all_sentiment_mv TO pgadmin;