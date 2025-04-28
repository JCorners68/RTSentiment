-- Dremio SQL Example for Iceberg Integration

-- Create an Iceberg table in the temp space
CREATE OR REPLACE TABLE temp.iceberg_sentiment (
  id VARCHAR,
  timestamp TIMESTAMP,
  message VARCHAR,
  score DOUBLE
);

-- Insert some sample data
INSERT INTO temp.iceberg_sentiment VALUES 
('1', CURRENT_TIMESTAMP, 'This is a positive message', 0.85),
('2', CURRENT_TIMESTAMP, 'This is a negative message', -0.35);

-- View the data
SELECT * FROM temp.iceberg_sentiment;

-- Filter for positive sentiment
SELECT * FROM temp.iceberg_sentiment WHERE score > 0;

-- Filter for negative sentiment
SELECT * FROM temp.iceberg_sentiment WHERE score < 0;

-- Count sentiment by type
SELECT 
  CASE 
    WHEN score > 0 THEN 'Positive'
    WHEN score < 0 THEN 'Negative'
    ELSE 'Neutral' 
  END as sentiment_type,
  COUNT(*) as count
FROM temp.iceberg_sentiment
GROUP BY sentiment_type
ORDER BY sentiment_type;