# Iceberg Lakehouse Integration for RT Sentiment

This module implements an advanced data tier for the RT Sentiment Analysis system using Apache Iceberg, Dremio CE, and MinIO.

## Features

- **Advanced Schema**: Support for complex sentiment analysis fields including emotion vectors, entity recognition, and aspect-based sentiment
- **Efficient Storage**: Columnar storage with partition pruning and file compaction
- **ACID Transactions**: Snapshot isolation and schema evolution capabilities
- **SQL Queries**: SQL-based access through Dremio CE
- **Redis Integration**: Real-time caching layer integrated with Iceberg

## Architecture

```
┌────────────────┐     ┌──────────────┐     ┌─────────────┐
│                │     │              │     │             │
│  Data Sources  ├────►│ Iceberg Lake ├────►│ Dremio CE   │
│                │     │              │     │             │
└────────────────┘     └──────────────┘     └──────┬──────┘
                                                  │
                                                  ▼
┌────────────────┐     ┌──────────────┐     ┌─────────────┐
│                │     │              │     │             │
│ Client Apps    │◄────┤ API Services │◄────┤ Redis Cache │
│                │     │              │     │             │
└────────────────┘     └──────────────┘     └─────────────┘
```

## Components

### Schema

The schema is defined in `schema/iceberg_schema.py` and includes:

- Core fields (timestamps, sources, content)
- Sentiment analysis fields (scores, emotion vectors, aspect-based sentiment)
- Entity recognition
- Financial context (tickers, sources)

### Writer

The writer in `writer/iceberg_writer.py` provides:

- ACID transaction support
- Schema validation
- Default values for backward compatibility
- Error handling and retry logic

### Configuration

Configuration in `utils/config.py` supports:

- Environment variable overrides
- JSON configuration files
- Validation and defaults

## Getting Started

1. **Start the services**:
   ```bash
   ./setup_iceberg.sh
   ```

2. **Use the writer in your code**:
   ```python
   from iceberg_lake.utils.config import IcebergConfig
   from iceberg_lake.writer.iceberg_writer import IcebergSentimentWriter

   # Load configuration
   config = IcebergConfig()
   catalog_config = config.get_catalog_config()

   # Create a writer
   writer = IcebergSentimentWriter(
       catalog_uri=catalog_config["uri"],
       warehouse_location=catalog_config["warehouse_location"],
       namespace=catalog_config["namespace"],
       table_name=catalog_config["table_name"]
   )

   # Write data
   writer.write_sentiment_analysis_result(
       message_id="unique-id",
       text_content="Apple stock is rising due to strong iPhone sales.",
       source_system="news",
       analysis_result={
           "sentiment_score": 0.75,
           "sentiment_magnitude": 0.85,
           "primary_emotion": "positive"
       },
       ticker="AAPL",
       article_title="Apple Reports Strong Q3 Earnings"
   )
   ```

3. **Query with Dremio**:
   - Access Dremio at http://localhost:9047
   - Add a new Source pointing to Iceberg
   - Run SQL queries against the sentiment data

## Docker Services

The following services are provided in `docker-compose.iceberg.yml`:

- **MinIO**: S3-compatible object storage (ports 9000/9001)
- **Iceberg REST Catalog**: REST API for Iceberg catalogs (port 8181)
- **Dremio CE**: SQL query engine (port 9047)

## Testing

Run the integration tests with:

```bash
python -m unittest tests/test_iceberg_integration.py
```