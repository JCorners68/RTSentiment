#!/usr/bin/env python
"""
Test script to manually push a test article through the entire data flow pipeline
from scraper to sentiment service using a Docker container.
"""

import json
import time
import subprocess
import sys

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

def run_command(cmd, use_sudo=True):
    """Run a command and return its output"""
    if use_sudo and cmd.startswith("docker"):
        cmd = f"sudo {cmd}"
    
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True
    )
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        print(f"Error executing command: {cmd}")
        print(f"Error: {stderr}")
        return None
    
    return stdout

def main():
    print("Starting test article flow...")
    
    # Save test article to a temporary file
    with open('/tmp/test_article.json', 'w') as f:
        json.dump(TEST_ARTICLE, f)
    
    # Check if Kafka is running
    print("Checking if Kafka is running...")
    kafka_status = run_command("docker ps | grep kafka")
    if not kafka_status:
        print("ERROR: Kafka container is not running. Please start the services with 'docker-compose up -d'")
        sys.exit(1)
    
    # Get the Kafka bootstrap server address
    print("Getting Kafka connection info...")
    kafka_container = run_command("docker ps --format '{{.Names}}' | grep kafka | grep -v kafka-ui").strip()
    if not kafka_container:
        print("ERROR: Could not find Kafka container")
        sys.exit(1)
    
    # Send the test article to Kafka
    print("Sending test article to Kafka topic 'news-events-high'...")
    # Create a temporary script file that can be executed with sudo
    with open('/tmp/send_to_kafka.sh', 'w') as f:
        f.write(f"""#!/bin/bash
docker exec {kafka_container} \\
kafka-console-producer \\
--bootstrap-server localhost:9092 \\
--topic news-events-high \\
< /tmp/test_article.json
""")
    
    # Make the script executable
    run_command("chmod +x /tmp/send_to_kafka.sh", use_sudo=False)
    
    # Run the script with sudo
    send_cmd = "sudo /tmp/send_to_kafka.sh"
    result = run_command(send_cmd)
    
    if result is None:
        print("ERROR: Failed to send message to Kafka")
        sys.exit(1)
    
    print("Test article sent successfully!")
    print("Waiting for sentiment service to process the article...")
    
    # Wait a moment for processing
    time.sleep(5)
    
    # Check results in sentiment-results topic
    print("Checking sentiment-results topic for our article...")
    # Create a temporary script file for consuming messages
    with open('/tmp/consume_from_kafka.sh', 'w') as f:
        f.write(f"""#!/bin/bash
docker exec {kafka_container} \
kafka-console-consumer \
--bootstrap-server localhost:9092 \
--topic sentiment-results \
--from-beginning \
--max-messages 10 \
--timeout-ms 10000
""")
    
    # Make the script executable
    run_command("chmod +x /tmp/consume_from_kafka.sh", use_sudo=False)
    
    # Run the script with sudo
    consume_cmd = "sudo /tmp/consume_from_kafka.sh"
    results = run_command(consume_cmd)
    
    if not results:
        print("No results found in sentiment-results topic")
        
        # Check if sentiment service is running
        sentiment_status = run_command("docker ps | grep sentiment-analysis")
        if not sentiment_status:
            print("ERROR: Sentiment analysis service is not running")
        else:
            print("Sentiment service is running. Checking logs...")
            logs = run_command("docker logs --tail 50 $(docker ps --format '{{.Names}}' | grep sentiment-analysis)")
            print("\nSentiment service logs:")
            print(logs)
    else:
        print("\nFound results in sentiment-results topic:")
        
        # Parse and display results
        found_test_result = False
        for line in results.splitlines():
            try:
                result = json.loads(line)
                print(f"Result: {json.dumps(result, indent=2)}")
                
                # Check if this is our test article
                if result.get("source") == "TestScraper" and "AAPL" in result.get("tickers", []):
                    found_test_result = True
                    print("\n========== Found our test article's sentiment result! ==========")
                    print(f"Sentiment: {result.get('sentiment')}")
                    print(f"Score: {result.get('score')}")
                    print(f"Processing time: {result.get('processing_time_ms')} ms")
                    print(f"Model used: {result.get('model')}")
                    print("=====================================================")
            except json.JSONDecodeError:
                print(f"Not valid JSON: {line}")
        
        if not found_test_result:
            print("\nDid not find our specific test article in the results")
            print("Check if the sentiment service is properly consuming from the news-events-high topic")
    
    # Also check the API
    print("\nChecking sentiment API for AAPL results...")
    api_result = run_command("curl -s http://localhost:8001/api/sentiment/AAPL", use_sudo=False)
    
    if api_result:
        try:
            api_data = json.loads(api_result)
            print("API Response:")
            print(json.dumps(api_data, indent=2))
        except json.JSONDecodeError:
            print(f"API returned invalid JSON: {api_result}")
    else:
        print("Could not get results from API")

if __name__ == "__main__":
    main()