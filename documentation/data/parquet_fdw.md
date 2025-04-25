# Parquet Foreign Data Wrapper (parquet_fdw) Integration

This document outlines the integration of the PostgreSQL Foreign Data Wrapper for Parquet files in the Senti Hub application.

## Overview

The Parquet Foreign Data Wrapper (parquet_fdw) allows PostgreSQL to directly query Parquet files stored on disk. This integration enables the Senti Hub application to query sentiment data directly from Parquet files, bypassing the need to load data into PostgreSQL tables.

## Architecture

<!-- Image missing: Parquet FDW Architecture diagram would be shown here -->

<!-- TODO: Create and add parquet_fdw_architecture.png to the architecture directory -->

### Components

1. **PostgreSQL with parquet_fdw**
   - Custom Docker image based on postgres:14
   - Includes parquet_fdw extension and all dependencies
   - Automatically configures foreign tables on startup

2. **Parquet Files**
   - Stored in `data/output/` directory
   - Mounted as a read-only volume to PostgreSQL container
   - Contains sentiment data from various sources
   - Examples: `aapl_sentiment.parquet`, `tsla_sentiment.parquet`, `multi_ticker_sentiment.parquet`

3. **API Layer**
   - Enhanced to query sentiment data directly from Parquet files via PostgreSQL
   - Falls back to traditional database tables if Parquet FDW fails
   - Provides consistent responses regardless of data source

## Setup and Configuration

### Docker Setup

1. **Custom PostgreSQL Dockerfile**

The `postgres.Dockerfile` builds a custom PostgreSQL image with parquet_fdw:

```dockerfile
FROM postgres:14

# Install necessary build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc make pkg-config postgresql-server-dev-14 \
    ca-certificates git cmake libssl-dev zlib1g-dev wget

# Install Apache Arrow and Parquet development libraries
RUN wget -O - https://apache.jfrog.io/artifactory/arrow/.../apache-arrow-apt-source-latest.deb | apt-get install -y \
    && apt-get update \
    && apt-get install -y libarrow-dev libparquet-dev

# Clone and build parquet_fdw
WORKDIR /tmp
RUN git clone https://github.com/adjust/parquet_fdw.git \
    && cd parquet_fdw \
    && make \
    && make install

# Copy initialization script
COPY init-fdw.sql /docker-entrypoint-initdb.d/

# Reset workdir and set entry point
WORKDIR /
CMD ["postgres"]
```

2. **PostgreSQL FDW Initialization**

The `init-fdw.sql` script automatically executed on container startup:

```sql
-- Load the parquet_fdw extension
CREATE EXTENSION IF NOT EXISTS parquet_fdw;

-- Create the server
CREATE SERVER IF NOT EXISTS parquet_srv FOREIGN DATA WRAPPER parquet_fdw;

-- Create user mappings
CREATE USER MAPPING IF NOT EXISTS FOR pgadmin SERVER parquet_srv;

-- Create foreign tables
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
    filename '/var/lib/postgresql/data/output/aapl_sentiment.parquet'
);

-- More foreign tables...

-- Create unified view
CREATE OR REPLACE VIEW all_sentiment AS
    SELECT * FROM aapl_sentiment
    UNION ALL
    SELECT * FROM tsla_sentiment
    UNION ALL
    SELECT * FROM multi_ticker_sentiment;
```

3. **Docker Compose Configuration**

```yaml
postgres:
  build:
    context: .
    dockerfile: postgres.Dockerfile
  environment:
    POSTGRES_USER: pgadmin
    POSTGRES_PASSWORD: localdev
    POSTGRES_DB: sentimentdb
  ports:
    - "5432:5432"
  volumes:
    - postgres-data:/var/lib/postgresql/data
    - ./data/output:/var/lib/postgresql/data/output:ro  # Mount Parquet files as read-only
```

## Configuration

This section explains how to configure the parquet_fdw integration for different environments and use cases.

### Environment Variables

The following environment variables can be used to customize the behavior of the parquet_fdw integration:

```
# PostgreSQL connection settings
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=sentimentdb
POSTGRES_USER=pgadmin
POSTGRES_PASSWORD=localdev

# Parquet file settings
PARQUET_DATA_DIR=./data/output
PARQUET_OPTIMIZE_INTERVAL=86400  # in seconds, default is daily
PARQUET_ROW_GROUP_SIZE=100000
PARQUET_COMPRESSION=SNAPPY
```

### Adding New Ticker Symbols

To add support for a new ticker symbol:

1. Create a new Parquet file in the `data/output` directory:
   ```
   {ticker_lower}.sentiment.parquet
   ```

2. Add a new foreign table definition to `init-fdw.sql`:
   ```sql
   CREATE FOREIGN TABLE IF NOT EXISTS {ticker_lower}_sentiment (
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
       filename '/var/lib/postgresql/data/output/{ticker_lower}_sentiment.parquet'
   );
   ```

3. Update the `all_sentiment` view in `init-fdw.sql`:
   ```sql
   CREATE OR REPLACE VIEW all_sentiment AS
       SELECT * FROM existing_tables
       UNION ALL
       SELECT * FROM {ticker_lower}_sentiment;
   ```

4. Rebuild and restart the PostgreSQL container:
   ```bash
   docker-compose build postgres
   docker-compose up -d postgres
   ```

### Performance Tuning

Parquet FDW performance can be tuned by adjusting:

1. **Row Group Size**: Controls the number of rows in each Parquet row group
   ```bash
   python3 parquet_utils.py optimize --file file.parquet --row-group-size 100000
   ```

2. **Compression**: Balance between file size and query speed
   ```bash
   python3 parquet_utils.py optimize --file file.parquet --compression SNAPPY
   ```

3. **Column Sorting**: Improve filter performance by sorting on frequently filtered columns
   ```bash
   python3 parquet_utils.py optimize --file file.parquet --sort-by timestamp
   ```

## Usage

This section provides examples of how to use the parquet_fdw integration in various scenarios.

### Querying Sentiment Data

#### Via API Endpoints

The API provides several endpoints that utilize the Parquet FDW:

1. **Get Ticker Sentiment**
   ```bash
   curl -X GET "http://localhost:8001/sentiment/ticker/AAPL"
   ```

2. **Query Sentiment Events**
   ```bash
   curl -X POST "http://localhost:8001/sentiment/query" \
     -H "Content-Type: application/json" \
     -d '{"start_date":"2025-01-01T00:00:00", "end_date":"2025-04-23T00:00:00", "limit":10}'
   ```

3. **Get Top Sentiment**
   ```bash
   curl -X GET "http://localhost:8001/sentiment/top?limit=5&sort_by=score&order=desc"
   ```

#### Direct PostgreSQL Queries

You can also query the Parquet data directly using SQL:

1. **Connect to PostgreSQL**
   ```bash
   psql -h localhost -U pgadmin -d sentimentdb
   ```

2. **Query the `all_sentiment` view**
   ```sql
   SELECT * FROM all_sentiment WHERE ticker = 'AAPL' LIMIT 10;
   ```

3. **Query specific ticker tables**
   ```sql
   SELECT * FROM aapl_sentiment WHERE sentiment > 0.5 LIMIT 10;
   ```

4. **Aggregate queries**
   ```sql
   SELECT ticker, AVG(sentiment) as avg_sentiment, COUNT(*) 
   FROM all_sentiment 
   GROUP BY ticker 
   ORDER BY avg_sentiment DESC;
   ```

### Maintaining Parquet Files

#### Manual Operations

1. **View Parquet Schema**
   ```bash
   python3 parquet_utils.py schema --file data/output/aapl_sentiment.parquet
   ```

2. **Deduplicate Parquet Files**
   ```bash
   python3 parquet_utils.py dedup --file data/output/aapl_sentiment.parquet
   ```

3. **Optimize Parquet Files**
   ```bash
   python3 parquet_utils.py optimize --file data/output/aapl_sentiment.parquet
   ```

4. **Process All Parquet Files**
   ```bash
   python3 parquet_utils.py process-all --dir data/output --action optimize
   ```

#### Automated Maintenance

The cron job automatically runs optimization and deduplication daily at 2 AM:

```bash
# Run manually if needed
./cron_jobs/optimize_parquet.sh
```

### Monitoring and Debugging

1. **Check FDW Extension Status**
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'parquet_fdw';
   ```

2. **Verify Foreign Tables**
   ```sql
   SELECT ftrelid::regclass AS foreign_table, ftoptions 
   FROM pg_foreign_table ft 
   JOIN pg_class c ON c.oid = ft.ftrelid 
   JOIN pg_foreign_server fs ON fs.oid = ft.ftserver 
   WHERE fs.srvname = 'parquet_srv';
   ```

3. **Check Query Performance**
   ```sql
   EXPLAIN ANALYZE SELECT * FROM all_sentiment WHERE ticker = 'AAPL' LIMIT 10;
   ```

## API Integration

The API layer has been enhanced to directly query Parquet data through PostgreSQL:

### Database Module

```python
# Example from database.py
def query_sentiment_data(db, ticker=None, start_date=None, end_date=None, source=None, limit=100, offset=0):
    """Query sentiment data from Parquet files through Foreign Data Wrapper."""
    query = """
    SELECT timestamp, ticker, sentiment, confidence, source, model, article_id, article_title 
    FROM all_sentiment
    WHERE 1=1
    """
    
    # Add filters...
    
    # Execute the query
    result = db.execute(text(query), params)
    
    # Return formatted results
    return [dict(row._mapping) for row in result]
```

### API Routes

```python
# Example from routes/sentiment.py
@router.post("/query", response_model=List[EventResponse])
async def query_sentiment_events(query_params: QueryParams, db: Session = Depends(get_db)):
    """Query sentiment events with various filters."""
    try:
        # Try to use Parquet FDW first
        data = query_sentiment_data(db, ...)
        if data:
            return [
                EventResponse(
                    id=i,
                    event_id=item.get('article_id', f"parquet-{i}"),
                    timestamp=datetime.fromisoformat(item.get('timestamp')),
                    # ...other fields
                )
                for i, item in enumerate(data)
            ]
    except Exception as e:
        # Fall back to traditional database query if Parquet FDW fails
        logger.warning(f"Falling back to traditional database query: {e}")
        pass
    
    # Traditional database query as fallback
    # ...
```

## Parquet Optimization

### Parquet Utils

The `parquet_utils.py` script provides utilities for managing Parquet files:

```bash
# View schema
python3 parquet_utils.py schema --file data/output/aapl_sentiment.parquet

# Deduplicate a file
python3 parquet_utils.py dedup --file data/output/aapl_sentiment.parquet

# Optimize a file for FDW queries
python3 parquet_utils.py optimize --file data/output/aapl_sentiment.parquet --sort-by timestamp

# Process all Parquet files in a directory
python3 parquet_utils.py process-all --dir data/output --action optimize
```

### Cron Job

A cron job is set up to regularly optimize and deduplicate Parquet files:

```bash
# /etc/cron.d/optimize_parquet
0 2 * * * /home/user/WSL_RT_Sentiment/cron_jobs/optimize_parquet.sh
```

The `optimize_parquet.sh` script runs the optimization and deduplication:

```bash
#!/bin/bash
# Run the parquet optimization
python3 parquet_utils.py process-all --dir "$DATA_DIR" --action optimize --sort-by timestamp

# Run deduplication
python3 parquet_utils.py process-all --dir "$DATA_DIR" --action dedup --key-cols article_id ticker
```

## Best Practices

1. **Parquet File Structure**
   - Keep a consistent schema across all Parquet files
   - Sort data by frequently filtered columns (e.g., timestamp)
   - Use appropriate compression (SNAPPY is recommended)
   - Optimize row group size for your query patterns

2. **Query Optimization**
   - Use column pruning (SELECT only needed columns)
   - Apply filters that match Parquet's predicate pushdown capabilities
   - Use materialized views for frequently accessed aggregations
   - Monitor query performance with EXPLAIN ANALYZE

3. **Error Handling**
   - Always implement fallback mechanisms for FDW failures
   - Log FDW errors for monitoring and debugging
   - Regularly check FDW connection and functionality

## Troubleshooting

### Common Issues

1. **Invalid Parquet Files**
   - Check Parquet file integrity: `python3 parquet_utils.py schema --file file.parquet`
   - Regenerate files if necessary

2. **FDW Connection Issues**
   - Ensure Parquet files are mounted correctly in the Docker container
   - Check permissions: The postgres user must have read access to the files
   - Verify FDW is installed: `SELECT * FROM pg_extension WHERE extname = 'parquet_fdw'`

3. **Query Performance**
   - Large files may need optimization: `python3 parquet_utils.py optimize --file file.parquet`
   - Check for appropriate filtering in your queries
   - Consider materialized views for frequent queries