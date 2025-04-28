#!/usr/bin/env python3
"""
Example script showing how to use the Iceberg integration.

This script demonstrates how to write sentiment data to Iceberg tables.
"""
import uuid
from datetime import datetime

# Import the classes from our implementation
from iceberg_lake.utils.config import IcebergConfig
from iceberg_lake.writer.iceberg_writer import IcebergSentimentWriter


def main():
    """Main function to demonstrate Iceberg usage."""
    print("Starting Iceberg example...")
    
    # 1. Load configuration
    config = IcebergConfig()
    catalog_config = config.get_catalog_config()
    
    # 2. Create a writer
    writer = IcebergSentimentWriter(
        catalog_uri=catalog_config["uri"],
        warehouse_location=catalog_config["warehouse_location"],
        namespace=catalog_config["namespace"],
        table_name=catalog_config["table_name"]
    )
    
    # 3. Create a sample record
    message_id = f"example-{uuid.uuid4()}"
    text_content = "Apple's latest earnings report exceeded expectations, sending the stock up 5% in after-hours trading."
    
    # 4. Create a sentiment analysis result (simulating what would come from a model)
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
    
    # 5. Write the data to Iceberg
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
        
        print(f"Successfully wrote {result} record to Iceberg table")
        print(f"Message ID: {message_id}")
        
    except Exception as e:
        print(f"Error writing to Iceberg: {str(e)}")
    
    # 6. You would now query this data through Dremio at http://localhost:9047
    print("You can now view this data in Dremio at http://localhost:9047")
    print("1. Login with default credentials (dremio/dremio123)")
    print("2. Add a new source pointing to Iceberg catalog")
    print("3. Navigate to 'sentiment.sentiment_data' table")
    print("4. Run SQL queries on your data")


if __name__ == "__main__":
    main()