#!/usr/bin/env python3
"""
Simple manual test script to create a test file locally
that can be used with bash commands.
"""

import json
import os

# Test article to process
TEST_ARTICLE = {
    "title": "AAPL stock surges after earnings beat expectations",
    "content": "Apple (AAPL) reported quarterly earnings that exceeded analyst expectations, causing the stock to rise 5% in after-hours trading. The company announced record iPhone sales and strong growth in its services business.",
    "url": "https://example.com/apple-earnings",
    "source_name": "Test Financial News",
    "tickers": ["AAPL"],
    "timestamp": "2023-04-21T12:00:00+00:00",
    "weight": 0.8,  # High priority item
    "source": "TestScraper",
    "source_type": "news"
}

# Save test article to a file
print("Saving test article to test_article.json...")
with open('test_article.json', 'w') as f:
    json.dump(TEST_ARTICLE, f)

print("\nTo test the flow, follow these manual steps:\n")
print("1. Make sure Docker services are running:")
print("   sudo docker-compose up -d")
print("\n2. Get the Kafka container name:")
print("   sudo docker ps | grep kafka | grep -v kafka-ui")
print("\n3. Send the test article to Kafka:")
print("   sudo docker exec <kafka_container_name> kafka-console-producer --bootstrap-server localhost:9092 --topic news-events-high < test_article.json")
print("\n4. Wait a few seconds for processing")
print("\n5. Check for results in the sentiment-results topic:")
print("   sudo docker exec <kafka_container_name> kafka-console-consumer --bootstrap-server localhost:9092 --topic sentiment-results --from-beginning --max-messages 10 --timeout-ms 10000")
print("\n6. Check the API for sentiment results:")
print("   curl -s http://localhost:8001/api/sentiment/AAPL | python3 -m json.tool")