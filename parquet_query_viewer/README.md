# Parquet Query Viewer

A comprehensive utility for querying, analyzing, and managing Parquet files in the Real-Time Sentiment Analysis system.

## Overview

The Parquet Query Viewer provides a unified interface to explore, analyze, and optimize Parquet files containing sentiment data. It leverages PostgreSQL's Foreign Data Wrapper (FDW) for Parquet files to enable SQL queries on Parquet data without loading it into traditional database tables.

Key features:
- Command-line interface for Parquet file management
- Web UI for interactive data exploration
- Integration with PostgreSQL for SQL-based queries
- Optimization utilities for Parquet files
- Deduplication functionality to maintain data quality

## Installation

### Prerequisites

- Python 3.7+
- PostgreSQL 14+ with Parquet FDW extension
- pandas, pyarrow, and psycopg2 Python packages

### Setup

1. **Install required Python packages:**

```bash
pip install pandas pyarrow psycopg2-binary aiohttp requests
pip install streamlit plotly matplotlib rich
```

2. **Setup PostgreSQL with Parquet FDW:**

Use the provided Docker setup for the easiest installation:

```bash
# Build and start the PostgreSQL container with Parquet FDW
docker-compose build postgres
docker-compose up -d postgres
```

Or manually install Parquet FDW following instructions in `Documentation/parquet_fdw.md`.

3. **Configure environment variables:**

```bash
# PostgreSQL connection settings
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_DB=sentimentdb
export POSTGRES_USER=pgadmin
export POSTGRES_PASSWORD=localdev

# Parquet file settings
export PARQUET_DATA_DIR=./data/output
export PARQUET_OPTIMIZE_INTERVAL=86400  # in seconds
export PARQUET_ROW_GROUP_SIZE=100000
export PARQUET_COMPRESSION=SNAPPY
```

## CLI Usage

The `parquet_query.py` script provides a command-line interface for Parquet file management:

### View Parquet Schema

```bash
# Show schema of a specific parquet file
python parquet_query_viewer/cli/parquet_query.py --query "SHOW SCHEMA aapl_sentiment"
```

Example output:
```
Schema for aapl_sentiment:
  Field 0: timestamp - string
  Field 1: ticker - string
  Field 2: sentiment - double
  Field 3: confidence - double
  Field 4: source - string
  Field 5: model - string
  Field 6: article_id - string
  Field 7: article_title - string
```

### List Available Tables

```bash
# List all available Parquet tables
python parquet_query_viewer/cli/parquet_query.py --query "LIST TABLES"
```

### Query Parquet Data

```bash
# Simple query
python parquet_query_viewer/cli/parquet_query.py --query "SELECT * FROM aapl_sentiment LIMIT 10"

# Query with filtering
python parquet_query_viewer/cli/parquet_query.py --query "SELECT timestamp, ticker, sentiment FROM aapl_sentiment WHERE sentiment > 0.5 ORDER BY sentiment DESC LIMIT 20"

# Export results to CSV
python parquet_query_viewer/cli/parquet_query.py --query "SELECT * FROM aapl_sentiment WHERE source = 'Twitter'" --output results.csv
```

### Interactive Mode

```bash
# Start interactive CLI mode
python parquet_query_viewer/cli/parquet_query.py
```

In interactive mode, you can enter SQL-like queries to explore Parquet files:

```
parquet-query> LIST TABLES
parquet-query> SHOW SCHEMA aapl_sentiment
parquet-query> SELECT timestamp, ticker, sentiment FROM aapl_sentiment WHERE sentiment > 0.5 LIMIT 10
```

### Process Queries from File

```bash
# Execute queries from a file
python parquet_query_viewer/cli/parquet_query.py --query-file queries.sql --output results.csv
```

## Web UI Features

The Parquet Query Viewer includes a web interface for interactive exploration of sentiment data:

### Starting the Web UI

```bash
# Start the web interface
streamlit run parquet_query_viewer/web/app.py

# Specify custom port and host
streamlit run parquet_query_viewer/web/app.py --server.port 8080 --server.address 0.0.0.0
```

### Web UI Features

The web interface provides:

1. **Dashboard View**: Overview of sentiment data with key metrics
2. **Query Interface**: Form-based interface for creating SQL queries
3. **Visualization Tools**: Charts and graphs to visualize sentiment trends
4. **Table Explorer**: Browse and filter data in a tabular format
5. **Export Options**: Download data in various formats (CSV, JSON, etc.)
6. **Ticker Comparison**: Compare sentiment across multiple tickers

## Integration with Existing Systems

The Parquet Query Viewer integrates with other components of the Real-Time Sentiment Analysis system:

### API Integration

The API layer has been enhanced to query Parquet data through PostgreSQL FDW:

```python
# Example API usage
import requests

# Get ticker sentiment
response = requests.get("http://localhost:8001/sentiment/ticker/AAPL")

# Query sentiment events
response = requests.post(
    "http://localhost:8001/sentiment/query",
    json={
        "start_date": "2025-04-01T00:00:00",
        "end_date": "2025-04-23T23:59:59",
        "limit": 10
    }
)

# Get top sentiment
response = requests.get("http://localhost:8001/sentiment/top?limit=5&sort_by=score&order=desc")
```

### Data Pipeline Integration

The system integrates with the data acquisition and sentiment analysis pipeline:

1. **Data Scrapers** → **Kafka** → **Sentiment Analysis** → **Parquet Files** → **FDW** → **Query Interface**

## Configuration Options

### Global Settings

Configuration can be set via environment variables or a configuration file:

```bash
# Environment variables
export PARQUET_DATA_DIR=./data/output
export PARQUET_OPTIMIZE_INTERVAL=86400
export PARQUET_ROW_GROUP_SIZE=100000
export PARQUET_COMPRESSION=SNAPPY
```

### Parquet Optimization Settings

| Parameter | Description | Default | Options |
|-----------|-------------|---------|---------|
| `sort_by` | Column to sort by | `timestamp` | Any column name |
| `compression` | Compression algorithm | `SNAPPY` | `SNAPPY`, `GZIP`, `ZSTD`, `NONE` |
| `row_group_size` | Rows per row group | `100000` | Any positive integer |

### PostgreSQL FDW Configuration

See `Documentation/parquet_fdw.md` for detailed PostgreSQL FDW configuration options.

## Requirements

### Software Requirements

- **Python 3.7+**
  - pandas
  - pyarrow
  - psycopg2-binary
  - streamlit
  - plotly
  - matplotlib
  - rich

- **PostgreSQL 14+**
  - Parquet FDW extension

- **Docker** (optional, for containerized deployment)

### Hardware Recommendations

- **Minimum**: 4GB RAM, 2 CPU cores, 20GB storage
- **Recommended**: 8GB RAM, 4 CPU cores, 50GB+ storage
- **Production**: 16GB+ RAM, 8+ CPU cores, 200GB+ SSD storage

## Troubleshooting

### Common Issues

1. **Invalid Parquet Files**
   - Check Parquet file integrity: `python parquet_query_viewer/cli/parquet_query.py --query "SHOW SCHEMA file_name"`
   - Regenerate files if necessary

2. **FDW Connection Issues**
   - Ensure Parquet files are mounted correctly in the Docker container
   - Check permissions: The postgres user must have read access to the files
   - Verify FDW is installed: `SELECT * FROM pg_extension WHERE extname = 'parquet_fdw'`

3. **Query Performance**
   - Large files may need optimization
   - Check for appropriate filtering in your queries
   - Consider materialized views for frequent queries

### Logs

Logs are written to:
- Command-line output
- `data/logs/parquet_utils.log`
- PostgreSQL logs for FDW operations

## License

This project is licensed under the MIT License - see the LICENSE file for details.