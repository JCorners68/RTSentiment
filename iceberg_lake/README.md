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

## Getting Started

1. **Start the services**:
   ```bash
   docker-compose -f docker-compose.iceberg.yml up -d
   ```

2. **Access Dremio**:
   - Open http://localhost:9047 in your browser
   - Login with default credentials (dremio/dremio123)
   - Create a new Space (e.g., "iceberg")
   - Use the Dremio UI to run SQL queries or upload the provided example SQL script

3. **Use the SQL Example**:
   - Copy and paste SQL from `dremio_sql_example.sql` into Dremio's query editor
   - Run the queries step by step to create tables and insert data

4. **Explore Data in Dremio**:
   - Use Dremio's interface to browse the data structure
   - Create data visualizations and dashboards
   - Export results to various formats

## Troubleshooting

- **Service Connection Issues**: 
  - Check service status with `docker ps`
  - View logs with `docker logs container_name`
  - Ensure proper networking between containers

- **Python Client Issues**:
  - Check PyIceberg version compatibility (0.9.0+)
  - Verify connection strings and authentication
  - Check warehouse path permissions

## Docker Services

The following services are provided in `docker-compose.iceberg.yml`:

- **MinIO**: S3-compatible object storage (ports 9000/9001)
- **Iceberg REST Catalog**: REST API for Iceberg catalogs (port 8181)
- **Dremio CE**: SQL query engine (port 9047)

## Known Limitations

- Direct PyIceberg to REST Catalog connectivity requires additional setup for S3 compatibility
- Dremio CE has some limitations with Iceberg table feature support compared to Enterprise version
- Local file storage is used for simplicity in the development environment