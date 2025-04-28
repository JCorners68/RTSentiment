#!/usr/bin/env python3
"""
Example script showing how to use the Iceberg integration.

This script demonstrates how to write sentiment data to Iceberg tables.
"""
import uuid
import sys
import os
from datetime import datetime

# Add the project root to Python path if needed
sys.path.insert(0, os.path.abspath('.'))

try:
    # Import the classes from our implementation
    from iceberg_lake.utils.config import IcebergConfig
    from iceberg_lake.writer.iceberg_writer import IcebergSentimentWriter
except ImportError:
    print("ERROR: Could not import Iceberg modules.")
    print("Make sure you're running this script in the virtual environment:")
    print("  source iceberg_venv/bin/activate")
    print("  python iceberg_example.py")
    sys.exit(1)


def main():
    """Main function to demonstrate Iceberg usage."""
    print("Starting Iceberg example...")
    
    # 1. Load configuration
    print("\n1. Loading configuration...")
    config = IcebergConfig()
    catalog_config = config.get_catalog_config()
    print(f"   Catalog URI: {catalog_config['uri']}")
    print(f"   Warehouse: {catalog_config['warehouse_location']}")
    print(f"   Namespace: {catalog_config['namespace']}")
    print(f"   Table: {catalog_config['table_name']}")
    
    # 2. Create a writer
    print("\n2. Creating Iceberg writer...")
    writer = IcebergSentimentWriter(
        catalog_uri=catalog_config["uri"],
        warehouse_location=catalog_config["warehouse_location"],
        namespace=catalog_config["namespace"],
        table_name=catalog_config["table_name"]
    )
    print("   Writer created successfully")
    
    # 3. Create a sample record
    print("\n3. Creating sample record...")
    message_id = f"example-{uuid.uuid4()}"
    text_content = "Apple's latest earnings report exceeded expectations, sending the stock up 5% in after-hours trading."
    print(f"   Message ID: {message_id}")
    print(f"   Text content: {text_content}")
    
    # 4. Create a sentiment analysis result (simulating what would come from a model)
    print("\n4. Creating sentiment analysis result...")
    analysis_result = {
        "sentiment_score": 0.75,  # Positive sentiment
        "sentiment_magnitude": 0.85,  # High confidence
        "primary_emotion": "optimism",
        
        # Advanced fields
        "emotion_intensity_vector": {
            "optimism": 0.8,
            "excitement": 0.6,
            "satisfaction": 0.7,
            "surprise": 0.5
        },
        "aspect_based_sentiment": {
            "earnings": 0.9,
            "stock_price": 0.8,
            "company_performance": 0.75
        },
        "entity_recognition": [
            {"text": "Apple", "type": "ORGANIZATION"},
            {"text": "earnings report", "type": "FINANCIAL_TERM"},
            {"text": "stock", "type": "FINANCIAL_ASSET"}
        ],
        "sarcasm_detection": False,
        "subjectivity_score": 0.3,  # Fairly objective
        "toxicity_score": 0.05,  # Not toxic
        "user_intent": "information_sharing"
    }
    print("   Analysis result prepared with advanced fields")
    print(f"   Sentiment score: {analysis_result['sentiment_score']}")
    print(f"   Primary emotion: {analysis_result['primary_emotion']}")
    print(f"   Entity count: {len(analysis_result['entity_recognition'])}")
    
    # 5. Write the data to Iceberg
    print("\n5. Writing data to Iceberg...")
    try:
        result = writer.write_sentiment_analysis_result(
            message_id=message_id,
            text_content=text_content,
            source_system="news",
            analysis_result=analysis_result,
            ticker="AAPL",
            article_title="Apple Beats Q2 Earnings Expectations",
            source_url="https://example.com/news/apple-earnings",
            model_name="finbert-v2"
        )
        
        print(f"   SUCCESS: Wrote {result} record to Iceberg table")
        print(f"   Message ID: {message_id}")
        print(f"   Ticker: AAPL")
        print(f"   Article title: Apple Beats Q2 Earnings Expectations")
        print(f"   Model: finbert-v2")
        
    except Exception as e:
        print(f"   ERROR: Failed to write to Iceberg: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 6. You would now query this data through Dremio
    print("\n6. Next Steps:")
    print("   a. Access Dremio at http://localhost:9047")
    print("   b. Login with default credentials (dremio/dremio123)")
    print("   c. Add a new source pointing to Iceberg catalog")
    print("   d. Navigate to 'sentiment.sentiment_data' table")
    print("   e. Run a query to see your data:")
    print("""
    SELECT 
      message_id, 
      event_timestamp, 
      ticker, 
      sentiment_score,
      primary_emotion
    FROM 
      sentiment.sentiment_data
    WHERE 
      ticker = 'AAPL' 
    ORDER BY 
      event_timestamp DESC
    """)
    print("4. Run SQL queries on your data")


if __name__ == "__main__":
    main()