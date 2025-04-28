# Getting Started with Iceberg Integration

This guide explains how to set up and use the Iceberg lakehouse integration step by step.

## Prerequisites

- Docker and Docker Compose
- Python 3.8+
- pip package manager

## Step 1: Set up the infrastructure

Run the setup script to install dependencies and start the Docker services:

```bash
./setup_iceberg.sh
```

This will:
- Install Python dependencies
- Start MinIO, Iceberg REST catalog, and Dremio services
- Create necessary directories and buckets

## Step 2: Run the example script

We've provided an example script that shows how to write sentiment data to Iceberg:

```bash
# Make sure the services are running
docker-compose -f docker-compose.iceberg.yml ps

# Run the example
python iceberg_example.py
```

The example script demonstrates:
- Loading configuration
- Creating a writer instance
- Formatting sentiment data
- Writing the data to Iceberg

## Step 3: Access the data through Dremio

1. Open Dremio at http://localhost:9047
2. Login with default credentials:
   - Username: dremio
   - Password: dremio123

3. Add a new source:
   - Click "Add Source"
   - Choose "Iceberg"
   - Set the connection details:
     - Name: Iceberg Sentiment
     - Catalog type: REST Catalog
     - Catalog URI: http://iceberg-rest:8181
     - Warehouse location: s3a://warehouse
     - Configure AWS credentials:
       - Access Key: minioadmin
       - Secret Key: minioadmin
       - Region: us-east-1
     - Enable path style access
     - Set S3 endpoint URL: http://minio:9000
   - Click "Save"

4. Navigate to your data:
   - Expand the "Iceberg Sentiment" source
   - Navigate to "sentiment" namespace
   - Open "sentiment_data" table
   - Preview the data

5. Run SQL queries:
   - Click "New Query"
   - Write SQL, for example:
     ```sql
     SELECT 
       message_id, 
       event_timestamp, 
       ticker, 
       sentiment_score, 
       primary_emotion 
     FROM 
       "Iceberg Sentiment"."sentiment"."sentiment_data"
     WHERE 
       ticker = 'AAPL'
     ORDER BY 
       event_timestamp DESC
     ```

## Step 4: Integrate with your application

To use the Iceberg integration in your application code:

1. Import the classes:
   ```python
   from iceberg_lake.utils.config import IcebergConfig
   from iceberg_lake.writer.iceberg_writer import IcebergSentimentWriter
   ```

2. Create a writer:
   ```python
   config = IcebergConfig()
   catalog_config = config.get_catalog_config()
   
   writer = IcebergSentimentWriter(
       catalog_uri=catalog_config["uri"],
       warehouse_location=catalog_config["warehouse_location"],
       namespace=catalog_config["namespace"],
       table_name=catalog_config["table_name"]
   )
   ```

3. Write sentiment data:
   ```python
   # Write a single result
   writer.write_sentiment_analysis_result(
       message_id="unique-id",
       text_content="Financial news text...",
       source_system="news",
       analysis_result={
           "sentiment_score": 0.75,
           "sentiment_magnitude": 0.85,
           "primary_emotion": "positive",
           # Other fields...
       },
       ticker="AAPL"
   )
   
   # Or write multiple records at once
   writer.write_data([record1, record2, record3])
   ```

## Troubleshooting

### Service connection issues
If you have trouble connecting to services, check their status:

```bash
docker-compose -f docker-compose.iceberg.yml logs
```

### Dremio configuration
If Dremio doesn't connect to the Iceberg catalog:
- Make sure all containers are in the same network
- Check container names match the configured endpoints
- Verify the credentials in Dremio source configuration

### Data not appearing
If your data doesn't appear in Dremio:
- Refresh the source in Dremio UI
- Check the writer logs for errors
- Verify the namespace and table name match